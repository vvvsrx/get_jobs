import json
import logging
import os
import asyncio
import re
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)

_ANTI_DETECTION_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "anti-detection.js")
try:
    with open(_ANTI_DETECTION_PATH, "r", encoding="utf-8") as f:
        ANTI_DETECTION_JS = f.read()
except FileNotFoundError:
    ANTI_DETECTION_JS = ""
    logger.warning("anti-detection.js not found at %s", _ANTI_DETECTION_PATH)


class ZhilianBot:
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
        self._monitoring_registered = False
        self.is_limit = False

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
            if (domain := c.get("domain", "")) == "zhaopin.com" or domain.endswith(".zhaopin.com")
        ]
        if filtered:
            await self.context.add_cookies(filtered)

    async def navigate(self, url: str, timeout: int = 60000):
        await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    async def is_logged_in(self) -> bool:
        # 1. Check cookies for login indicators
        try:
            cookies = await self.context.cookies()
            cookie_names = {c.get("name", "") for c in cookies}
            # Zhilian login cookies — these are set only after login
            login_indicators = {"acw_sc__v2", "acw_sc__v3", "sid", "ztid", "auth_token", "SESSION", "at", "rt"}
            matched = login_indicators & cookie_names
            if matched:
                logger.info("Login detected via cookies: %s", matched)
                return True
        except Exception:
            pass

        # 2. Check page elements — strict selectors only
        strict_selectors = [
            (".user-avatar", "avatar element"),
            (".user-name", "user-name element"),
            ("a:has-text('退出')", "logout link"),
            ("span:has-text('退出')", "logout span"),
        ]
        for sel, reason in strict_selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.is_visible(timeout=500):
                    logger.info("Login detected via %s", reason)
                    return True
            except Exception:
                pass

        # 3. Check localStorage for user info
        try:
            has_user = await self.page.evaluate(
                "() => { try { return !!(localStorage.getItem('userInfo') || localStorage.getItem('user') || sessionStorage.getItem('userInfo')); } catch(e) { return false; } }"
            )
            if has_user:
                logger.info("Login detected via localStorage userInfo")
                return True
        except Exception:
            pass

        return False

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
        if self.progress_callback:
            self.progress_callback(msg, None, None)
        else:
            logger.info(msg)

    def _build_search_url(self, city_code: str = "", salary: str = "", page_num: int = 1) -> str:
        base = "https://www.zhaopin.com/sou/"
        url = f"{base}jl{city_code}/p{page_num}"
        if salary:
            url += f"?sl={salary}"
        return url

    async def run_delivery(self):
        from app.worker.task_state import task_state
        from app.worker.zhilian_locators import (
            JOB_CARDS, APPLY_BUTTON, NEXT_PAGE, NEXT_PAGE_DISABLED_CLASS,
            KEYWORD_INPUT_SELECTORS, APPLY_LIMIT_INDICATOR,
        )

        # 1. 加载配置
        async with self.db_session_factory() as session:
            from app.services.config_service import ConfigService
            config_service = ConfigService(session)
            db_config = await config_service.get_or_create_zhilian_config()

        # 2. 加载 Cookie
        async with self.db_session_factory() as session:
            from app.services.cookie_service import CookieService
            cookie_service = CookieService(session)
            cookie_record = await cookie_service.get_cookie("zhilian")
            if cookie_record and cookie_record.cookie_value:
                await self.load_cookies(cookie_record.cookie_value)

        # 3. 检查登录状态
        await self.navigate("https://www.zhaopin.com")
        await asyncio.sleep(2)
        if not await self.is_logged_in():
            self._info("智联招聘未登录，请扫码登录")
            logger.warning("智联招聘未登录，终止投递")
            return

        keywords = db_config.keywords or self.config.get("keywords", "")
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if not keyword_list:
            keyword_list = [""]

        city_code = db_config.city_code or self.config.get("city_code", "")
        salary = db_config.salary or self.config.get("salary", "")

        total_posted = 0

        for keyword in keyword_list:
            if task_state.should_stop() or self.is_limit:
                self._info("收到停止信号，终止投递")
                return

            self._info(f"开始投递关键词：{keyword}")
            posted = await self._submit_keyword(keyword, city_code, salary, task_state)
            total_posted += posted

        self._info(f"投递完成，共投递 {total_posted} 个职位")

    async def _submit_keyword(self, keyword, city_code, salary, task_state):
        from app.worker.zhilian_locators import (
            JOB_CARDS, APPLY_BUTTON, NEXT_PAGE, NEXT_PAGE_DISABLED_CLASS,
            KEYWORD_INPUT_SELECTORS, APPLY_LIMIT_INDICATOR,
            ALREADY_APPLIED_MARKER,
        )

        # 导航到搜索页（第1页）
        search_url = self._build_search_url(city_code, salary, 1)
        await self.navigate(search_url)
        await asyncio.sleep(2)

        # 输入关键词并搜索
        if keyword:
            keyword_input = None
            for selector in KEYWORD_INPUT_SELECTORS:
                try:
                    inp = self.page.locator(selector).first
                    if await inp.is_visible():
                        keyword_input = inp
                        break
                except Exception:
                    pass

            if keyword_input:
                try:
                    await keyword_input.fill("")
                    await keyword_input.fill(keyword)
                    await keyword_input.press("Enter")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning("搜索框输入关键词失败：%s", e)
                    return 0
            else:
                logger.warning("未找到搜索输入框")
                return 0

        # 等待职位列表加载
        try:
            await self.page.wait_for_selector(JOB_CARDS, timeout=10000)
        except Exception:
            logger.warning("等待职位列表超时")
            return 0

        posted = 0
        page_num = 1

        while page_num <= 50:
            if task_state.should_stop() or self.is_limit:
                self._info("收到停止指令，结束分页循环")
                return posted

            self._info(f"正在投递【{keyword}】第【{page_num}】页...")

            # 等待职位列表
            try:
                await self.page.wait_for_selector(JOB_CARDS, timeout=10000)
            except Exception:
                logger.warning("等待职位列表失败")
                break

            # 投递当前页
            page_posted = await self._deliver_current_page()
            posted += page_posted

            await asyncio.sleep(2)

            # 检查是否还有下一页
            if await self._is_next_disabled():
                self._info("下一页按钮不可点击，结束翻页")
                break

            # 点击下一页
            next_btn = self.page.locator(NEXT_PAGE)
            if await next_btn.count() > 0:
                try:
                    await next_btn.first.scroll_into_view_if_needed()
                    await next_btn.first.click()
                    await asyncio.sleep(2)
                    page_num += 1
                except Exception as e:
                    logger.warning("点击下一页失败：%s", e)
                    break
            else:
                break

        self._info(f"【{keyword}】关键词投递完成！")
        return posted

    async def _deliver_current_page(self) -> int:
        from app.worker.zhilian_locators import (
            JOB_CARDS, APPLY_BUTTON, ALREADY_APPLIED_MARKER,
            JOB_TITLE, JOB_SALARY, JOB_LOCATION, JOB_EXPERIENCE,
            JOB_DEGREE, COMPANY_NAME,
        )

        job_cards = self.page.locator(JOB_CARDS)
        count = await job_cards.count()
        posted = 0

        # 先采集所有职位信息
        jobs_data = []
        for i in range(count):
            card = job_cards.nth(i)
            try:
                job_title = await self._safe_get_text(card, JOB_TITLE)
                job_link = None
                try:
                    job_link = await card.locator(JOB_TITLE).get_attribute("href")
                except Exception:
                    pass
                salary = await self._safe_get_text(card, JOB_SALARY)
                location = await self._safe_get_text(card, JOB_LOCATION)
                experience = await self._safe_get_text(card, JOB_EXPERIENCE)
                degree = await self._safe_get_text(card, JOB_DEGREE)
                company_name = await self._safe_get_text(card, COMPANY_NAME)
                job_id = self._extract_job_id(job_link, job_title, company_name)
                if not job_id:
                    logger.warning("无法提取 job_id，链接: %s", job_link)

                jobs_data.append({
                    "index": i,
                    "job_id": job_id,
                    "job_title": job_title,
                    "job_link": job_link,
                    "salary": salary,
                    "location": location,
                    "experience": experience,
                    "degree": degree,
                    "company_name": company_name,
                })
            except Exception as e:
                logger.warning("采集岗位数据失败：%s", e)

        valid_jobs = [j for j in jobs_data if j.get("job_id")]
        logger.warning("采集到 %d 个职位，有效 job_id: %d 个", len(jobs_data), len(valid_jobs))

        # 保存到数据库
        for job in valid_jobs:
            job_id = job.get("job_id")
            try:
                async with self.db_session_factory() as session:
                    from app.services.zhilian_service import ZhilianService
                    service = ZhilianService(session)
                    if not await service.exists_job(job_id):
                        data = {k: v for k, v in job.items() if k != "index"}
                        await service.insert_job(data)
                        logger.warning("保存职位成功: %s", job_id)
            except Exception as e:
                logger.warning("保存岗位数据失败 %s: %s", job_id, e)

        # 投递
        for job in jobs_data:
            from app.worker.task_state import task_state
            if task_state.should_stop() or self.is_limit:
                return posted

            card = job_cards.nth(job["index"])

            # 检查是否已投递
            try:
                applied_marker = card.locator(ALREADY_APPLIED_MARKER)
                if await applied_marker.count() > 0 and await applied_marker.first.is_visible():
                    logger.debug("职位已投递，跳过：%s", job.get("job_title"))
                    if job.get("job_id"):
                        try:
                            async with self.db_session_factory() as session:
                                from app.services.zhilian_service import ZhilianService
                                service = ZhilianService(session)
                                await service.mark_delivered(job.get("job_id"))
                        except Exception:
                            pass
                    continue
            except Exception:
                pass

            apply_btn = card.locator(APPLY_BUTTON)
            if await apply_btn.count() == 0:
                logger.debug("未找到投递按钮，跳过：%s", job.get("job_title"))
                continue

            # 点击投递，监听新窗口并关闭
            try:
                # 注册新窗口监听器（自动关闭由当前页打开的弹窗）
                async def _handle_new_page(new_page):
                    try:
                        if new_page.opener() == self.page:
                            await new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                            await asyncio.sleep(0.5)
                            await new_page.close()
                    except Exception:
                        pass

                self.context.on("page", _handle_new_page)

                await apply_btn.first.click()
                await asyncio.sleep(2.5)

                # 处理当前页可能出现的投递确认/结果对话框
                try:
                    from app.worker.zhilian_locators import (
                        DIALOG_DELIVER_RESULT, DIALOG_CLOSE_BUTTON,
                        SIMILAR_JOBS_SELECT_ALL, SIMILAR_JOBS_POST_BUTTON,
                    )
                    # 关闭投递结果对话框
                    dialog = self.page.locator(DIALOG_DELIVER_RESULT)
                    if await dialog.count() > 0 and await dialog.first.is_visible():
                        close_btn = self.page.locator(DIALOG_CLOSE_BUTTON)
                        if await close_btn.count() > 0:
                            await close_btn.first.click()
                            await asyncio.sleep(0.5)
                        else:
                            # Try pressing Escape to close dialog
                            await self.page.keyboard.press("Escape")
                            await asyncio.sleep(0.5)
                    # 处理相似职位推荐弹窗
                    similar_select = self.page.locator(SIMILAR_JOBS_SELECT_ALL)
                    if await similar_select.count() > 0 and await similar_select.first.is_visible():
                        post_btn = self.page.locator(SIMILAR_JOBS_POST_BUTTON)
                        if await post_btn.count() > 0:
                            await post_btn.first.click()
                            await asyncio.sleep(1)
                except Exception:
                    pass

                # 取消监听
                try:
                    self.context.remove_listener("page", _handle_new_page)
                except Exception:
                    pass

                posted += 1
                task_state.delivered_count += 1
                self._info(f"已投递：{job.get('job_title', '岗位')}")
                if job.get("job_id"):
                    try:
                        async with self.db_session_factory() as session:
                            from app.services.zhilian_service import ZhilianService
                            service = ZhilianService(session)
                            await service.mark_delivered(job.get("job_id"))
                    except Exception as e:
                        logger.warning("标记智联已投递失败：%s", e)

            except Exception as e:
                logger.warning("投递失败：%s", e)

            # 检查是否达到投递上限
            if await self._check_is_limit():
                self._info("今日投递已达上限！")
                self.is_limit = True
                return posted

        return posted

    async def _is_next_disabled(self) -> bool:
        from app.worker.zhilian_locators import NEXT_PAGE, NEXT_PAGE_DISABLED_CLASS
        try:
            next_btn = self.page.locator(NEXT_PAGE)
            if await next_btn.count() == 0:
                return True
            cls = await next_btn.first.get_attribute("class")
            disabled = await next_btn.first.get_attribute("disabled")
            if cls and NEXT_PAGE_DISABLED_CLASS in cls:
                return True
            return disabled is not None and disabled.lower() in ("disabled", "true")
        except Exception:
            return False

    async def _check_is_limit(self) -> bool:
        from app.worker.zhilian_locators import APPLY_LIMIT_INDICATOR
        try:
            await asyncio.sleep(0.5)
            indicator = self.page.locator(APPLY_LIMIT_INDICATOR)
            if await indicator.count() > 0:
                text = await indicator.first.text_content()
                if text and any(k in text for k in ("达到上限", "超过上限", "已达上限", "投递上限", "今日上限")):
                    return True
            return False
        except Exception:
            return False

    def _extract_job_id(self, link: Optional[str], job_title: str = "", company_name: str = "") -> Optional[str]:
        if link:
            try:
                for pattern in [
                    r"jobdetail/(\d+)",
                    r"job_detail/(\d+)",
                    r"/(\d+)\.htm",
                    r"/(\d+)\.html",
                    r"job/(\d+)",
                ]:
                    m = re.search(pattern, link)
                    if m:
                        return m.group(1)
            except Exception:
                pass
            # Fallback: hash the link itself
            import hashlib
            return hashlib.md5(link.encode()).hexdigest()[:32]
        # No link: hash title + company as fallback
        if job_title or company_name:
            import hashlib
            return hashlib.md5(f"{job_title}:{company_name}".encode()).hexdigest()[:32]
        return None

    async def _safe_get_text(self, parent, selector: str) -> str:
        try:
            el = parent.locator(selector)
            if await el.count() > 0:
                return await el.first.text_content() or ""
        except Exception:
            pass
        return ""
