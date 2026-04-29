import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Optional, List, Callable, Dict

logger = logging.getLogger(__name__)

_ANTI_DETECTION_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "anti-detection.js")
try:
    with open(_ANTI_DETECTION_PATH, "r", encoding="utf-8") as f:
        ANTI_DETECTION_JS = f.read()
except FileNotFoundError:
    ANTI_DETECTION_JS = ""
    logger.warning("anti-detection.js not found at %s", _ANTI_DETECTION_PATH)


class Job51Bot:
    def __init__(
        self,
        config: dict,
        db_session_factory,
        progress_callback: Optional[Callable] = None,
    ):
        self.config = config
        self.db_session_factory = db_session_factory
        self.progress_callback = progress_callback
        self.camoufox = None
        self.context = None
        self.page = None
        self.is_limit = False
        self.network_hooked = False
        self.processed_request_ids: set = set()
        self.current_page_job_ids: List[str] = []
        self._last_page_titles: set = set()

    async def init(self):
        from camoufox import AsyncCamoufox
        from playwright.async_api import BrowserContext, Page

        self.camoufox = AsyncCamoufox(
            headless=False,
            humanize=True,
            os="macos",
        )
        browser = await self.camoufox.__aenter__()
        self.context: BrowserContext = await browser.new_context()
        self.page: Page = await self.context.new_page()
        await self.context.add_init_script(ANTI_DETECTION_JS)

    async def load_cookies(self, cookie_json: str):
        cookies = json.loads(cookie_json)
        filtered = [
            c for c in cookies
            if (domain := c.get("domain", "")) == "51job.com" or domain.endswith(".51job.com") or domain.endswith(".zhaopin.com")
        ]
        if filtered:
            await self.context.add_cookies(filtered)

    async def navigate(self, url: str, timeout: int = 60000):
        await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    async def is_logged_in(self) -> bool:
        # 0. If we're on the login page, definitely not logged in
        try:
            url = self.page.url
            if "login.51job.com" in url:
                return False
        except Exception:
            pass

        # 1. Check page body text for login/register link text (most reliable)
        try:
            body_text = await self.page.evaluate("() => document.body ? (document.body.innerText || '') : ''")
            if body_text and ("登录/注册" in body_text or "登录注册" in body_text):
                return False
        except Exception:
            pass

        # 2. Check if explicit login link/button exists and is visible
        try:
            login_links = self.page.locator("a:has-text('登录'), a:has-text('登录/注册'), button:has-text('登录')")
            if await login_links.count() > 0:
                for i in range(min(await login_links.count(), 3)):
                    if await login_links.nth(i).is_visible(timeout=300):
                        return False
        except Exception:
            pass

        # 3. Check for logged-in user elements (51job-specific)
        logged_in_selectors = [
            (".user-name", "user-name"),
            (".user-avatar", "avatar"),
            ("a[href*='logout']", "logout-link"),
            ("a:has-text('退出')", "logout-text"),
        ]
        for sel, reason in logged_in_selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.is_visible(timeout=500):
                    return True
            except Exception:
                pass

        # 4. Fallback: if not on login page, no login text, no visible login links,
        #    and on a 51job domain -> likely logged in
        try:
            url = self.page.url
            if "51job.com" in url and "login" not in url:
                return True
        except Exception:
            pass

        return False

    async def _check_need_login(self) -> bool:
        """Return True if NOT logged in."""
        return not await self.is_logged_in()

    async def close(self):
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
        if self.camoufox:
            try:
                await self.camoufox.__aexit__(None, None, None)
            except Exception:
                pass
            self.camoufox = None

    def _info(self, msg: str):
        logger.info(msg)
        if self.progress_callback:
            self.progress_callback(msg, None, None)

    async def _wait_for_jobs_loaded(self, checkbox_selector: str, timeout_ms: int = 15000) -> bool:
        """Wait for job checkboxes to appear after navigation."""
        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) * 1000 < timeout_ms:
            count = await self.page.locator(checkbox_selector).count()
            if count > 0:
                return True
            await asyncio.sleep(0.3)
        return False

    async def run_delivery(self):
        from app.worker.task_state import task_state

        # 1. Load config
        async with self.db_session_factory() as session:
            from app.services.config_service import ConfigService
            config_service = ConfigService(session)
            db_config = await config_service.get_or_create_job51_config()

        # 2. Load cookies
        async with self.db_session_factory() as session:
            from app.services.cookie_service import CookieService
            cookie_service = CookieService(session)
            cookie_record = await cookie_service.get_cookie("job51")
            if cookie_record and cookie_record.cookie_value:
                await self.load_cookies(cookie_record.cookie_value)

        # 3. Check login
        await self.navigate("https://we.51job.com/pc/search")
        await asyncio.sleep(1)
        if await self._check_need_login():
            self._info("前程无忧未登录，请扫码登录")
            logger.warning("前程无忧未登录，终止投递")
            return

        # 4. Pre-check daily limit before starting delivery
        await asyncio.sleep(1)
        if await self._detect_daily_limit():
            self.is_limit = True
            self._info("检测到今日投递已达上限，任务终止")
            logger.warning("51job 日投递上限已触发，终止投递")
            return

        keywords = db_config.keywords or self.config.get("keywords", "")
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if not keyword_list:
            keyword_list = [""]

        job_area = db_config.job_area or self.config.get("job_area", "")
        salary = db_config.salary or self.config.get("salary", "")

        total_posted = 0

        for keyword in keyword_list:
            if task_state.should_stop() or self.is_limit:
                self._info("收到停止信号，终止投递")
                return

            self._last_page_titles = set()
            self._info(f"开始投递关键词：{keyword}")
            posted = await self._submit_keyword(keyword, job_area, salary, task_state)
            total_posted += posted

        self._info(f"投递完成，共投递 {total_posted} 个职位")

    async def _submit_keyword(self, keyword, job_area, salary, task_state):
        from app.worker.job51_locators import (
            SEARCH_API_PATH, SORT_OPTIONS, PAGE_INPUT, JUMP_BUTTON,
            NO_JOBS_KEYWORDS, NO_JOBS_LOCATORS,
        )

        # Register API interceptor
        if not self.network_hooked:
            try:
                self.page.on("response", lambda r: asyncio.create_task(self._on_search_response(r)))
                self.network_hooked = True
            except Exception:
                pass

        search_url = self._build_search_url(keyword, job_area, salary)
        try:
            await self.page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
        except Exception:
            pass
        await self.navigate(search_url)
        await asyncio.sleep(0.5)

        if await self._check_need_login():
            self._info(f"需要重新登录，跳过关键词: {keyword}")
            return 0

        # Click sort option
        try:
            sort_opts = self.page.locator(SORT_OPTIONS)
            if await sort_opts.count() > 0:
                await sort_opts.first.click(timeout=3000)
                await asyncio.sleep(0.5)
        except Exception:
            pass

        posted = 0
        for page_num in range(1, 3):  # 只投递2页
            if task_state.should_stop() or self.is_limit:
                self._info("用户取消投递")
                return posted

            self._info(f"正在投递【{keyword}】第【{page_num}】页...")

            if page_num > 1:
                # Navigate directly with pageNum instead of clicking pagination
                page_url = self._build_search_url(keyword, job_area, salary, page_num)
                await self.navigate(page_url)
                await asyncio.sleep(1)

            if await self._check_access_verification():
                self._info("出现访问验证，停止投递")
                return posted

            if await self._detect_no_jobs():
                self._info("该关键词暂无职位，提前结束")
                break

            # Check daily limit before delivering this page
            if await self._detect_daily_limit():
                self.is_limit = True
                self._info("检测到今日投递已达上限，停止投递")
                return posted

            page_posted = await self._deliver_current_page()
            posted += page_posted
            if self.is_limit:
                break

            await asyncio.sleep(1)

        return posted

    async def _on_search_response(self, response):
        from app.worker.job51_locators import SEARCH_API_PATH
        try:
            url = response.url
            if url and SEARCH_API_PATH in url and response.request.method == "GET":
                try:
                    text = await response.text()
                except Exception as e:
                    print(f"      [调试] response.text() failed: {e}")
                    return
                if not text:
                    print(f"      [调试] response text is empty")
                    return
                headers = response.headers
                is_json = "json" in headers.get("content-type", "").lower()
                if not is_json:
                    # Fallback: try to parse as JSON
                    try:
                        json.loads(text)
                    except Exception:
                        print(f"      [调试] fallback json.loads failed")
                        return

                # Parse and save job data
                await self._parse_and_persist_search_json(text)
                # Extract jobIds for current page
                job_ids = self._extract_job_ids_from_json(text)
                if job_ids:
                    self.current_page_job_ids = job_ids
        except Exception as e:
            print(f"      [调试] on_response exception: {e}")
            pass

    async def _parse_and_persist_search_json(self, text: str):
        try:
            data = json.loads(text)
            items = self._get_items_from_json(data)
            if not items:
                return

            for item in items:
                job_id = str(item.get("jobId", ""))
                if not job_id:
                    continue

                job_data = {
                    "job_id": job_id,
                    "job_title": item.get("jobName", "") or item.get("jobTitle", ""),
                    "job_link": item.get("jobHref", "") or item.get("jobLink", ""),
                    "job_salary_text": item.get("provideSalaryString", "") or item.get("salary", ""),
                    "job_area": item.get("jobAreaString", "") or item.get("workArea", ""),
                    "job_edu_req": item.get("degreeString", "") or item.get("degree", ""),
                    "job_exp_req": item.get("workYearString", "") or item.get("workYear", ""),
                    "job_publish_time": item.get("issueDateString", "") or item.get("issueDate", ""),
                    "comp_id": str(item.get("companyId", "")),
                    "comp_name": item.get("companyName", ""),
                    "comp_industry": item.get("companyTypeString", "") or item.get("industryType", ""),
                    "comp_scale": item.get("companySizeString", "") or item.get("companySize", ""),
                    "hr_id": str(item.get("hrId", "")),
                    "hr_name": item.get("hrName", ""),
                    "hr_title": item.get("hrJobTitle", ""),
                }

                async with self.db_session_factory() as session:
                    from app.services.job51_service import Job51Service
                    service = Job51Service(session)
                    if not await service.exists_job(job_id):
                        await service.insert_job(job_data)
        except Exception as e:
            logger.debug("解析并保存51job搜索JSON失败: %s", e)

    def _get_items_from_json(self, data: dict) -> List[dict]:
        for path in [
            ["data", "items"],
            ["data", "jobList"],
            ["data", "list"],
            ["data", "jobs"],
            ["resultbody", "job", "items"],
            ["job", "items"],
            ["resultbody", "items"],
        ]:
            node = data
            for key in path:
                if isinstance(node, dict):
                    node = node.get(key)
                else:
                    node = None
                    break
            if isinstance(node, list):
                return node
        return []

    def _extract_job_ids_from_json(self, text: str) -> List[str]:
        try:
            data = json.loads(text)
            items = self._get_items_from_json(data)
            return [str(item.get("jobId", "")) for item in items if item.get("jobId")]
        except Exception:
            return []

    async def _deliver_current_page(self) -> int:
        from app.worker.job51_locators import (
            checkbox, JOB_TITLES, JOB_COMPANIES,
            BATCH_DELIVER_PARENT, BATCH_DELIVER_BUTTON, SELECT_ALL_BUTTON,
        )

        try:
            # Wait for job listings to load
            if not await self._wait_for_jobs_loaded(checkbox, timeout_ms=15000):
                self._info("等待职位加载超时，跳过当前页")
                return 0

            checkboxes = self.page.locator(checkbox)
            titles = self.page.locator(JOB_TITLES)
            companies = self.page.locator(JOB_COMPANIES)
            job_count = await checkboxes.count()
            if job_count == 0:
                return 0

            # Verify content changed from last page
            current_titles = set()
            for i in range(min(job_count, 3)):
                try:
                    t = await titles.nth(i).text_content()
                    if t:
                        current_titles.add(t.strip())
                except Exception:
                    pass
            if current_titles and current_titles == self._last_page_titles:
                self._info("页面内容未变化，可能到达末页或加载失败")
                return 0
            self._last_page_titles = current_titles

            # Step 1: Click "全选" to select all jobs and reveal batch button
            select_all_clicked = await self._click_select_all(SELECT_ALL_BUTTON)
            if not select_all_clicked:
                self._info("点击全选失败，尝试逐个选择")
                for i in range(job_count):
                    try:
                        cb = checkboxes.nth(i)
                        await cb.evaluate("el => el.click()")
                    except Exception:
                        pass

            await asyncio.sleep(0.3)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.3)

            # Step 2: Click batch deliver button
            await self._click_batch_deliver()

            await asyncio.sleep(0.5)

            # Handle dialogs
            await self._handle_delivery_success_dialog()
            await self._handle_separate_delivery_dialog()

            # Mark jobs as delivered
            if self.current_page_job_ids:
                async with self.db_session_factory() as session:
                    from app.services.job51_service import Job51Service
                    service = Job51Service(session)
                    for job_id in self.current_page_job_ids:
                        await service.mark_delivered(job_id)

            return job_count
        except Exception as e:
            logger.error("投递当前页面失败: %s", e)
            return 0

    async def _click_select_all(self, selector: str) -> bool:
        try:
            btn = self.page.locator(selector)
            if await btn.count() == 0:
                return False
            await btn.first.evaluate("el => el.click()")
            self._info("点击全选")
            return True
        except Exception as e:
            self._info(f"全选点击异常: {e}")
            return False

    async def _click_batch_deliver(self):
        from app.worker.job51_locators import BATCH_DELIVER_PARENT, BATCH_DELIVER_BUTTON

        for retry in range(5):
            try:
                parent = self.page.locator(BATCH_DELIVER_PARENT)
                buttons = parent.locator(BATCH_DELIVER_BUTTON)
                count = await buttons.count()
                if count > 0:
                    await asyncio.sleep(0.3)
                    # Click the batch deliver button
                    await buttons.first.click(timeout=5000)
                    self._info("点击一键投递按钮")

                    # Detect daily limit immediately after click
                    for _ in range(5):
                        await asyncio.sleep(0.2)
                        if await self._detect_daily_limit():
                            self.is_limit = True
                            self._info("检测到日投递上限，任务已停止")
                            return

                    return
                else:
                    self._info("未找到一键投递按钮，重试中...")
                    await asyncio.sleep(0.3)
            except Exception as e:
                self._info(f"一键投递点击异常: {e}")
                await asyncio.sleep(0.3)

    async def _handle_delivery_success_dialog(self):
        from app.worker.job51_locators import (
            SUCCESS_DIALOG_CONTENT, APP_DOWNLOAD_CLOSE,
            EL_DIALOG_BODY, EL_DIALOG_FOOTER_OK,
            DIALOG_CLOSE_ICON, DIALOG_HEADER_BTN,
            POPUP_CLOSE_ICON,
        )

        try:
            await asyncio.sleep(0.5)

            # Close app download popup
            try:
                success_content = self.page.locator(SUCCESS_DIALOG_CONTENT)
                if await success_content.count() > 0:
                    text = await success_content.first.text_content()
                    if text and "快来扫码下载" in text:
                        close_btn = self.page.locator(APP_DOWNLOAD_CLOSE)
                        if await close_btn.count() > 0:
                            await close_btn.first.click(timeout=3000)
            except Exception:
                pass

            # Handle el-dialog body with delivery result
            try:
                dialog_body = self.page.locator(EL_DIALOG_BODY)
                if await dialog_body.count() > 0:
                    dialog_text = await dialog_body.first.inner_text()
                    if dialog_text and "投递成功" in dialog_text:
                        success_num = None
                        m = re.search(r"投递成功\D*(\d+)", dialog_text)
                        if m:
                            success_num = int(m.group(1))

                        self._info(f"投递结果：成功 {success_num or '?'} 个")

                        # Mark delivered in database
                        if success_num and success_num > 0 and self.current_page_job_ids:
                            mark_count = min(success_num, len(self.current_page_job_ids))
                            to_mark = self.current_page_job_ids[:mark_count]
                            for job_id in to_mark:
                                try:
                                    async with self.db_session_factory() as session:
                                        from app.services.job51_service import Job51Service
                                        service = Job51Service(session)
                                        await service.mark_delivered(job_id)
                                except Exception:
                                    pass

                        # Close dialog
                        try:
                            ok_btn = self.page.locator(EL_DIALOG_FOOTER_OK)
                            if await ok_btn.count() > 0:
                                await ok_btn.first.click(timeout=3000)
                            else:
                                closed = False
                                icon_close = self.page.locator(DIALOG_CLOSE_ICON)
                                if await icon_close.count() > 0 and await icon_close.first.is_visible():
                                    try:
                                        await icon_close.first.evaluate("el => el.parentElement && el.parentElement.click()")
                                        closed = True
                                    except Exception:
                                        pass
                                if not closed:
                                    header_btn = self.page.locator(DIALOG_HEADER_BTN)
                                    if await header_btn.count() > 0 and await header_btn.first.is_visible():
                                        try:
                                            await header_btn.first.click(force=True, timeout=2000)
                                            closed = True
                                        except Exception:
                                            pass
                                if not closed:
                                    await self.page.evaluate("document.querySelector('button.el-dialog__headerbtn')?.click() || document.querySelector(\"button[aria-label='Close']\")?.click()")
                                    closed = True
                                if not closed:
                                    await self.page.keyboard.press("Escape")
                            await asyncio.sleep(0.3)
                        except Exception:
                            pass
            except Exception:
                pass

            await self._close_any_modal_overlays()

            if await self._detect_daily_limit():
                self.is_limit = True
                self._info("处理成功弹窗后，检测到日投递上限")
        except Exception:
            pass

    async def _handle_separate_delivery_dialog(self):
        from app.worker.job51_locators import SEPARATE_APPLY_DIALOG, SEPARATE_APPLY_CLOSE

        try:
            dialog_content = self.page.locator(SEPARATE_APPLY_DIALOG)
            if await dialog_content.count() > 0:
                text = await dialog_content.first.text_content()
                if text and "需要到企业招聘平台单独申请" in text:
                    close_btn = self.page.locator(SEPARATE_APPLY_CLOSE)
                    if await close_btn.count() > 0:
                        await close_btn.first.click(timeout=3000)
        except Exception:
            pass

    async def _jump_to_page(self, page_num: int) -> bool:
        from app.worker.job51_locators import PAGE_INPUT, JUMP_BUTTON

        for retry in range(3):
            try:
                await self._close_any_modal_overlays()

                page_input = self.page.locator(PAGE_INPUT)
                if await page_input.count() == 0:
                    return False

                await asyncio.sleep(0.3)
                await page_input.first.click(timeout=3000)
                await page_input.first.fill("")
                await page_input.first.fill(str(page_num))

                jump_btn = self.page.locator(JUMP_BUTTON)
                if await jump_btn.count() > 0:
                    await jump_btn.first.click(timeout=3000)

                await self.page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                return True
            except Exception as e:
                logger.warning("跳转到第%d页失败，重试第%d次: %s", page_num, retry + 1, e)
                await asyncio.sleep(0.5)
                if await self._check_access_verification():
                    return False
                await self.page.reload()
                await asyncio.sleep(1)
        return False

    async def _close_any_modal_overlays(self):
        from app.worker.job51_locators import DIALOG_HEADER_BTN, DIALOG_CLOSE_ICON, EL_DIALOG_FOOTER_OK, POPUP_CLOSE_ICON, MODAL_OVERLAYS

        try:
            for _ in range(3):
                closed_this_round = False

                header_close = self.page.locator(DIALOG_HEADER_BTN)
                if await header_close.count() > 0 and await header_close.first.is_visible():
                    try:
                        await header_close.first.click(force=True, timeout=2000)
                        closed_this_round = True
                    except Exception:
                        pass

                icon_close = self.page.locator(DIALOG_CLOSE_ICON)
                if await icon_close.count() > 0 and await icon_close.first.is_visible():
                    try:
                        await icon_close.first.evaluate("el => el.parentElement && el.parentElement.click()")
                        closed_this_round = True
                    except Exception:
                        pass

                ok_btn = self.page.locator(EL_DIALOG_FOOTER_OK)
                if await ok_btn.count() > 0 and await ok_btn.first.is_visible():
                    try:
                        await ok_btn.first.click(timeout=3000)
                        closed_this_round = True
                    except Exception:
                        pass

                popup_close = self.page.locator(POPUP_CLOSE_ICON)
                if await popup_close.count() > 0 and await popup_close.first.is_visible():
                    try:
                        await popup_close.first.click(timeout=3000)
                        closed_this_round = True
                    except Exception:
                        pass

                # Click modal overlay / backdrop to close dialog
                if not closed_this_round:
                    overlays = self.page.locator(MODAL_OVERLAYS)
                    count = await overlays.count()
                    for i in range(count):
                        try:
                            overlay = overlays.nth(i)
                            if await overlay.is_visible():
                                # Click on a corner of the overlay (backdrop area, not dialog content)
                                box = await overlay.bounding_box()
                                if box:
                                    await self.page.mouse.click(box["x"] + 5, box["y"] + 5)
                                    closed_this_round = True
                                    break
                        except Exception:
                            pass

                if not closed_this_round:
                    break
                await asyncio.sleep(0.3)
        except Exception:
            pass

    async def _detect_daily_limit(self) -> bool:
        from app.worker.job51_locators import DAILY_LIMIT_KEYWORDS, DAILY_LIMIT_LOCATORS

        try:
            for kw in DAILY_LIMIT_KEYWORDS:
                toast = self.page.locator(f"text={kw}")
                if await toast.count() > 0 and await toast.first.is_visible():
                    return True

            msgs = self.page.locator(DAILY_LIMIT_LOCATORS)
            if await msgs.count() > 0:
                texts = await msgs.all_inner_texts()
                for t in texts:
                    if t:
                        tt = t.replace("\n", " ").strip()
                        for kw in DAILY_LIMIT_KEYWORDS:
                            if kw in tt:
                                return True

            found = await self.page.evaluate(
                """() => {
                    const kws = ['今日投递太多','您今日投递太多','休息一下明天再来','达到上限','次数过多'];
                    const bodyText = document.body ? (document.body.innerText || '') : '';
                    return kws.some(k => bodyText.includes(k));
                }"""
            )
            if found:
                return True
        except Exception:
            pass
        return False

    async def _check_access_verification(self) -> bool:
        from app.worker.job51_locators import WAF_TITLE, WAF_SCRIPT, VERIFY_TEXT

        try:
            waf_title = self.page.locator(WAF_TITLE)
            waf_script = self.page.locator(WAF_SCRIPT)
            verify_text = self.page.locator(VERIFY_TEXT)
            if (await waf_title.count() > 0 and await waf_title.first.is_visible()) or await waf_script.count() > 0 or await verify_text.count() > 0:
                logger.error("出现访问验证，需要手动处理")
                return True
            return False
        except Exception:
            return False

    async def _detect_no_jobs(self) -> bool:
        from app.worker.job51_locators import NO_JOBS_KEYWORDS, NO_JOBS_LOCATORS

        try:
            for kw in NO_JOBS_KEYWORDS:
                t = self.page.locator(f"text={kw}")
                if await t.count() > 0 and await t.first.is_visible():
                    return True

            empty = self.page.locator(NO_JOBS_LOCATORS)
            if await empty.count() > 0:
                texts = await empty.all_inner_texts()
                for t in texts:
                    if t:
                        tt = t.replace("\n", " ").strip()
                        for kw in NO_JOBS_KEYWORDS:
                            if kw in tt:
                                return True
            return False
        except Exception:
            return False

    def _build_search_url(self, keyword: str, job_area: str, salary: str, page_num: int = 1) -> str:
        from urllib.parse import quote
        params = []
        if job_area:
            params.append(f"jobArea={quote(job_area)}")
        if salary:
            params.append(f"salary={quote(salary)}")
        if keyword:
            params.append(f"keyword={quote(keyword)}")
        params.append(f"pageNum={page_num}")
        url = f"https://we.51job.com/pc/search?"
        if params:
            url += "&".join(params)
        return url
