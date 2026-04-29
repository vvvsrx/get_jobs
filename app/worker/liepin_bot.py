import json
import logging
import os
import asyncio
import re
from urllib.parse import urlencode, quote
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)

_ANTI_DETECTION_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "anti-detection.js")
try:
    with open(_ANTI_DETECTION_PATH, "r", encoding="utf-8") as f:
        ANTI_DETECTION_JS = f.read()
except FileNotFoundError:
    ANTI_DETECTION_JS = ""
    logger.warning("anti-detection.js not found at %s", _ANTI_DETECTION_PATH)


def _build_search_url(city_code: str = "", salary_code: str = "") -> str:
    base = "https://www.liepin.com/zhaopin/"
    params = {}
    if city_code:
        params["city"] = city_code
        params["dq"] = city_code
    if salary_code:
        params["salary"] = salary_code
    if params:
        params["currentPage"] = "0"
        return f"{base}?{urlencode(params)}"
    return base


def _parse_search_response(json_text: str) -> List[dict]:
    try:
        data = json.loads(json_text)
        card_list = data.get("data", {}).get("data", {}).get("jobCardList")
        if not card_list:
            card_list = data.get("data", {}).get("jobCardList")
        if not card_list:
            return []
        results = []
        for item in card_list:
            job = item.get("job", {})
            comp = item.get("comp", {})
            recruiter = item.get("recruiter", {})
            results.append({
                "job_id": str(job.get("jobId", "")),
                "job_title": job.get("title") or "",
                "job_link": job.get("link") or "",
                "job_salary_text": job.get("salary") or "",
                "job_area": job.get("dq") or "",
                "job_edu_req": job.get("requireEduLevel") or "",
                "job_exp_req": job.get("requireWorkYears") or "",
                "job_publish_time": job.get("refreshTime") or "",
                "comp_id": str(comp.get("compId", "")),
                "comp_name": comp.get("compName") or "",
                "comp_industry": comp.get("compIndustry") or "",
                "comp_scale": comp.get("compScale") or "",
                "hr_id": recruiter.get("recruiterId") or "",
                "hr_name": recruiter.get("recruiterName") or "",
                "hr_title": recruiter.get("recruiterTitle") or "",
                "hr_im_id": recruiter.get("imId") or "",
            })
        return results
    except Exception as e:
        logger.warning("解析猎聘搜索响应失败：%s", e)
        return []


class LiepinBot:
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
        self._last_api_jobs: List[dict] = []
        self._monitoring_registered = False

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
            if (domain := c.get("domain", "")) == "liepin.com" or domain.endswith(".liepin.com")
        ]
        if filtered:
            await self.context.add_cookies(filtered)

    async def navigate(self, url: str, timeout: int = 60000):
        await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    async def is_logged_in(self) -> bool:
        try:
            avatar = self.page.locator(".header-avatar").first
            if await avatar.is_visible():
                return True
        except Exception:
            pass
        try:
            logout_btn = self.page.locator("a:has-text('退出')").first
            if await logout_btn.is_visible():
                return True
        except Exception:
            pass
        try:
            user_el = self.page.locator("[class*=user]").first
            if await user_el.is_visible():
                return True
        except Exception:
            pass
        try:
            cookies = await self.context.cookies()
            for c in cookies:
                name = c.get("name", "").lower()
                if name in ("user_token", "lt", "session", "access_token"):
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

    async def run_delivery(self):
        from app.worker.liepin_locators import (
            SEARCH_API_PATH,
            SEARCH_API_EXCLUDE,
            PAGINATION_BOX,
            NEXT_PAGE,
            SUBSCRIBE_CLOSE_BTN,
            JOB_CARDS,
            CHAT_HEADER,
            CHAT_CLOSE,
            CHAT_BUTTON_SELECTORS,
            HR_AREA_SELECTORS,
        )

        # 1. 加载配置
        async with self.db_session_factory() as session:
            from app.services.config_service import ConfigService
            config_service = ConfigService(session)
            db_config = await config_service.get_or_create_liepin_config()

        # 2. 加载 Cookie
        async with self.db_session_factory() as session:
            from app.services.cookie_service import CookieService
            cookie_service = CookieService(session)
            cookie_record = await cookie_service.get_cookie("liepin")
            if cookie_record and cookie_record.cookie_value:
                await self.load_cookies(cookie_record.cookie_value)

        # 3. 检查登录状态
        await self.navigate("https://www.liepin.com")
        await asyncio.sleep(2)
        if not await self.is_logged_in():
            self._info("猎聘未登录，请扫码登录")
            logger.warning("猎聘未登录，终止投递")
            return

        # 4. 注册 API 拦截器
        if not self._monitoring_registered:
            self._register_response_handler()
            self._monitoring_registered = True

        keywords = db_config.keywords or self.config.get("keywords", "")
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if not keyword_list:
            keyword_list = [""]

        city_code = db_config.city_code or self.config.get("city_code", "")
        salary_code = db_config.salary_code or self.config.get("salary_code", "")

        total_posted = 0

        for keyword in keyword_list:
            from app.worker.task_state import task_state
            if task_state.should_stop():
                self._info("收到停止信号，终止投递")
                return

            self._info(f"开始投递关键词：{keyword}")
            await self._submit_keyword(
                keyword,
                city_code,
                salary_code,
                task_state,
                total_posted,
            )

        self._info(f"投递完成，共投递 {total_posted} 个职位")

    def _register_response_handler(self):
        from app.worker.liepin_locators import SEARCH_API_PATH, SEARCH_API_EXCLUDE

        async def _handler(response):
            try:
                url = response.url
                if SEARCH_API_PATH not in url or SEARCH_API_EXCLUDE in url:
                    return
                if response.status != 200:
                    return
                text = await response.text()
                if not text:
                    return
                jobs = _parse_search_response(text)
                self._last_api_jobs = jobs
                await self._insert_snapshots(jobs)
            except Exception as e:
                logger.debug("猎聘 API 拦截处理异常：%s", e)
        self.page.on("response", lambda resp: asyncio.create_task(_handler(resp)))

    async def _insert_snapshots(self, jobs: List[dict]):
        if not jobs:
            return
        try:
            async with self.db_session_factory() as session:
                from app.services.liepin_service import LiepinService
                service = LiepinService(session)
                for job in jobs:
                    job_id = job.get("job_id")
                    if not job_id:
                        continue
                    if not await service.exists_job(job_id):
                        data = {k: v for k, v in job.items()}
                        data["delivered"] = 0
                        await service.insert_job(data)
        except Exception as e:
            logger.warning("批量保存猎聘岗位数据失败：%s", e)

    async def _submit_keyword(self, keyword, city_code, salary_code, task_state, total_posted):
        from app.worker.liepin_locators import (
            PAGINATION_BOX, NEXT_PAGE, SUBSCRIBE_CLOSE_BTN, JOB_CARDS,
            CHAT_HEADER, CHAT_CLOSE, CHAT_BUTTON_SELECTORS, HR_AREA_SELECTORS,
        )

        clean_keyword = keyword.replace('"', '').strip()
        search_url = _build_search_url(city_code, salary_code)
        encoded_keyword = quote(clean_keyword, safe="")
        await self.navigate(search_url + "&key=" + encoded_keyword)

        # 等待分页加载
        try:
            await self.page.wait_for_selector(PAGINATION_BOX, timeout=10000)
        except Exception:
            logger.warning("猎聘分页未加载")
            return

        # 读取总页数
        pagination_box = self.page.locator(PAGINATION_BOX)
        lis = pagination_box.locator("li")
        max_page = await self._set_max_page(lis)

        for page_num in range(max_page):
            if task_state.should_stop():
                self._info("收到停止指令，结束分页循环")
                return

            # 关闭订阅弹窗
            try:
                close_btn = self.page.locator(SUBSCRIBE_CLOSE_BTN)
                if await close_btn.count() > 0:
                    await close_btn.click()
            except Exception:
                pass

            # 等待岗位卡片挂载
            try:
                await self.page.wait_for_selector(
                    JOB_CARDS, state="attached", timeout=15000
                )
            except Exception:
                logger.warning("岗位卡片未加载")
                break

            # 额外等待一次接口响应，确保 last_api_jobs 刷新
            try:
                await self.page.wait_for_response(
                    lambda r: "com.liepin.searchfront4c.pc-search-job" in r.url and r.status == 200,
                    timeout=10000,
                )
            except Exception:
                pass

            self._info(f"正在投递【{clean_keyword}】第【{page_num + 1}】页...")
            posted = await self._deliver_page_cards()
            total_posted += posted
            self._info(f"已投递第【{page_num + 1}】页所有的岗位...")

            # 查找下一页按钮
            pagination_box = self.page.locator(PAGINATION_BOX)
            next_li = pagination_box.locator(NEXT_PAGE)
            if await next_li.count() > 0:
                cls = await next_li.first.get_attribute("class")
                disabled = cls and "ant-pagination-disabled" in cls
                if not disabled:
                    btn = next_li.first.locator("button.ant-pagination-item-link")
                    clicked = False
                    if await btn.count() > 0:
                        try:
                            await btn.first.click(timeout=5000)
                            clicked = True
                        except Exception:
                            pass
                    if not clicked:
                        try:
                            await next_li.first.click(timeout=5000)
                            clicked = True
                        except Exception:
                            pass
                    if not clicked:
                        try:
                            await self.page.evaluate(
                                "(el) => el.click()",
                                await next_li.first.element_handle(),
                            )
                        except Exception:
                            break
                    await asyncio.sleep(2)
                else:
                    break
            else:
                break

        self._info(f"【{clean_keyword}】关键词投递完成！")

    async def _set_max_page(self, lis) -> int:
        try:
            count = await lis.count()
            if count >= 2:
                page_text = await lis.nth(count - 2).text_content()
                page = int(page_text)
                if page > 1:
                    return min(page, 50)
        except Exception:
            pass
        return 50

    async def _deliver_page_cards(self) -> int:
        from app.worker.liepin_locators import (
            JOB_CARDS, CHAT_CLOSE,
            JOB_TITLE_LINKS, DETAIL_APPLY_BUTTONS,
        )

        job_cards = self.page.locator(JOB_CARDS)
        count = await job_cards.count()
        posted = 0
        list_page_url = self.page.url

        for i in range(count):
            from app.worker.task_state import task_state
            if task_state.should_stop():
                self._info("收到停止指令，结束卡片遍历")
                return posted

            current_card = job_cards.nth(i)

            # 跳过广告卡片
            try:
                card_html = await current_card.inner_html()
                if any(marker in card_html for marker in ["广告", "data-ad", "promotion", "sponsor", "hot-job"]):
                    continue
                card_class = await current_card.get_attribute("class") or ""
                if "ad" in card_class.lower() or "promo" in card_class.lower():
                    continue
            except Exception:
                pass

            # 提取 job_id
            job_id_for_update = None
            if i < len(self._last_api_jobs):
                job_id_for_update = self._last_api_jobs[i].get("job_id")
            if not job_id_for_update:
                job_id_for_update = await self._extract_job_id_from_card(current_card)

            job_title = "岗位"
            if i < len(self._last_api_jobs):
                job_title = self._last_api_jobs[i].get("job_title") or "岗位"

            # 滚动到卡片位置
            try:
                await self.page.evaluate(
                    "(element) => element.scrollIntoView({behavior: 'instant', block: 'center'})",
                    await current_card.element_handle(),
                )
                await asyncio.sleep(0.3)
            except Exception:
                pass

            # 查找职位标题链接
            title_link = None
            for selector in JOB_TITLE_LINKS:
                try:
                    links = current_card.locator(selector)
                    if await links.count() > 0:
                        link = links.first
                        href = await link.get_attribute("href")
                        if href and ("/job/" in href or "liepin.com" in href):
                            title_link = link
                            break
                except Exception:
                    pass

            if not title_link:
                continue

            # 点击进入详情页（在新标签页打开）
            popup = None
            try:
                async with self.page.expect_popup(timeout=5000) as popup_info:
                    await title_link.click()
                popup = await popup_info.value
                await popup.wait_for_load_state("domcontentloaded", timeout=10000)
                await asyncio.sleep(1.5)
            except Exception:
                # 没有弹出窗口，尝试当前页
                try:
                    await title_link.click()
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.debug("点击详情页失败：%s", e)
                    continue

            detail_page = popup if popup else self.page

            # 在详情页查找"投简历"或"聊一聊"按钮（优先投简历）
            # 先检查是否已投递（继续聊）
            already_delivered = False
            from app.worker.liepin_locators import ALREADY_DELIVERED_MARKERS
            for marker in ALREADY_DELIVERED_MARKERS:
                try:
                    els = detail_page.locator(marker)
                    if await els.count() > 0:
                        for j in range(await els.count()):
                            if await els.nth(j).is_visible():
                                already_delivered = True
                                break
                except Exception:
                    pass
                if already_delivered:
                    break

            if already_delivered:
                logger.debug("职位已投递过，跳过：%s", job_title)
                if job_id_for_update:
                    await self._mark_delivered(job_id_for_update)
                if popup:
                    try:
                        await popup.close()
                        await asyncio.sleep(0.3)
                    except Exception:
                        pass
                continue

            apply_btn = None
            for selector in DETAIL_APPLY_BUTTONS:
                try:
                    btns = detail_page.locator(selector)
                    btn_count = await btns.count()
                    for j in range(btn_count):
                        btn = btns.nth(j)
                        try:
                            if await btn.is_visible():
                                text = (await btn.text_content() or "").strip()
                                if text and ("投简历" in text or "投递简历" in text or "聊一聊" in text or "立即沟通" in text or "沟通" in text):
                                    apply_btn = btn
                                    break
                        except Exception:
                            pass
                    if apply_btn:
                        break
                except Exception:
                    pass

            if apply_btn:
                try:
                    btn_text = (await apply_btn.text_content() or "").strip()
                    await apply_btn.click()
                    await asyncio.sleep(2)

                    # 如果是"投简历"，需要处理后续确认弹窗
                    if "投简历" in btn_text or "投递" in btn_text:
                        # 查找并点击确认按钮
                        confirm_selectors = [
                            "button:has-text('确认投递')",
                            "button:has-text('确定')",
                            "button:has-text('发送')",
                            "button:has-text('提交')",
                            "button.ant-btn-primary",
                            "[class*='confirm'] button",
                            "button",
                        ]
                        for sel in confirm_selectors:
                            try:
                                cbtns = detail_page.locator(sel)
                                ccount = await cbtns.count()
                                for k in range(ccount):
                                    cbtn = cbtns.nth(k)
                                    if await cbtn.is_visible():
                                        ctext = (await cbtn.text_content() or "").strip()
                                        if ctext and ("确认" in ctext or "确定" in ctext or "发送" in ctext or "提交" in ctext or "投递" in ctext):
                                            await cbtn.click()
                                            await asyncio.sleep(1)
                                            break
                            except Exception:
                                pass

                    # 如果是"聊一聊"或"立即沟通"，输入打招呼语
                    if "聊一聊" in btn_text or "沟通" in btn_text:
                        await asyncio.sleep(1)
                        greeting = self.config.get("greeting", "您好，我对这个职位很感兴趣，希望能有机会进一步沟通。")
                        await self._send_chat_message(detail_page, greeting)

                    # 关闭聊天窗口或弹窗
                    try:
                        close = detail_page.locator(CHAT_CLOSE)
                        if await close.count() > 0:
                            await asyncio.sleep(0.5)
                            await close.click()
                    except Exception:
                        pass

                    posted += 1
                    self._info(f"已投递：{job_title}")
                    if job_id_for_update:
                        await self._mark_delivered(job_id_for_update)

                except Exception as e:
                    logger.error("详情页点击投递按钮失败：%s", e)
            else:
                logger.debug("详情页未找到投递按钮：%s", job_title)

            # 如果是新标签页，关闭它；否则返回列表页
            if popup:
                try:
                    await popup.close()
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            else:
                try:
                    await self.page.go_back()
                    await asyncio.sleep(1)
                except Exception:
                    try:
                        await self.navigate(list_page_url)
                        await asyncio.sleep(1)
                    except Exception:
                        pass

        return posted

    async def _send_chat_message(self, page, message: str):
        """在聊天窗口中输入并发送消息"""
        from app.worker.liepin_locators import CHAT_INPUT_SELECTORS, CHAT_SEND_BUTTONS

        # 等待聊天框出现
        try:
            await page.wait_for_selector(CHAT_INPUT_SELECTORS[0], timeout=3000)
        except Exception:
            pass

        # 查找输入框
        input_el = None
        for selector in CHAT_INPUT_SELECTORS:
            try:
                el = page.locator(selector).first
                if await el.is_visible():
                    input_el = el
                    break
            except Exception:
                pass

        if not input_el:
            logger.debug("未找到聊天输入框")
            return

        # 输入消息
        try:
            await input_el.fill(message)
            await asyncio.sleep(0.5)
        except Exception:
            # 如果 fill 失败，尝试用键盘输入
            try:
                await input_el.click()
                await asyncio.sleep(0.2)
                await page.keyboard.type(message)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug("输入聊天消息失败：%s", e)
                return

        # 查找并点击发送按钮
        for selector in CHAT_SEND_BUTTONS:
            try:
                btns = page.locator(selector)
                bcount = await btns.count()
                for i in range(bcount):
                    btn = btns.nth(i)
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                        return
            except Exception:
                pass

        # 如果没有找到发送按钮，尝试按 Enter 键
        try:
            await page.keyboard.press("Enter")
        except Exception:
            pass

    async def _mark_delivered(self, job_id: str):
        try:
            async with self.db_session_factory() as session:
                from app.services.liepin_service import LiepinService
                service = LiepinService(session)
                await service.mark_delivered(job_id)
        except Exception as e:
            logger.warning("标记猎聘已投递失败：%s", e)

    async def _extract_job_id_from_card(self, card) -> Optional[str]:
        try:
            ext = await card.get_attribute("data-tlg-ext")
            if ext:
                m = re.search(r'"jobId":"(\d+)"', ext)
                if m:
                    return m.group(1)
            scm = await card.get_attribute("data-tlg-scm")
            if scm:
                m = re.search(r"jobId=(\d+)", scm)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return None
