import json
import logging
import os
import asyncio
import re
from urllib.parse import urlencode, quote
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)

BOSS_BASE_URL = "https://www.zhipin.com/web/geek/jobs"


def build_search_url(config: dict) -> str:
    params = {}
    if config.get("city_code"):
        params["city"] = config["city_code"]
    if config.get("job_type"):
        params["jobType"] = config["job_type"]
    if config.get("salary"):
        params["salary"] = config["salary"]
    if config.get("experience"):
        params["experience"] = config["experience"]
    if config.get("degree"):
        params["degree"] = config["degree"]
    if config.get("scale"):
        params["scale"] = config["scale"]
    if config.get("stage"):
        params["stage"] = config["stage"]
    if config.get("industry"):
        params["industry"] = config["industry"]

    if params:
        return f"{BOSS_BASE_URL}?{urlencode(params)}"
    return BOSS_BASE_URL


def decode_salary(text: str) -> str:
    font_map = {
        '': '0', '': '1', '': '2', '': '3', '': '4',
        '': '5', '': '6', '': '7', '': '8', '': '9',
    }
    return "".join(font_map.get(c, c) for c in text)


def parse_salary_range(salary_text: str) -> Optional[List[int]]:
    salary_text = salary_text.replace("K", "").replace("k", "")
    if "元/天" in salary_text:
        salary_text = salary_text.replace("元/天", "")
    if "薪" in salary_text:
        salary_text = re.sub(r"·\d+薪", "", salary_text)
    try:
        parts = [int(re.sub(r"[^0-9]", "", p)) for p in salary_text.split("-")]
        return parts
    except (ValueError, IndexError):
        return None


def is_salary_not_expected(salary: str, expected: Optional[List[int]]) -> bool:
    if not expected or len(expected) < 2:
        return False
    job_range = parse_salary_range(salary)
    if not job_range:
        return True
    min_expected, max_expected = expected[0], expected[1]
    if len(job_range) >= 2:
        if job_range[1] <= min_expected:
            return True
        if job_range[0] >= max_expected:
            return True
    elif len(job_range) == 1:
        if job_range[0] < min_expected or job_range[0] > max_expected:
            return True
    return False


_ANTI_DETECTION_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "anti-detection.js")
try:
    with open(_ANTI_DETECTION_PATH, "r", encoding="utf-8") as f:
        ANTI_DETECTION_JS = f.read()
except FileNotFoundError:
    ANTI_DETECTION_JS = ""
    logger.warning(f"anti-detection.js not found at {_ANTI_DETECTION_PATH}")


class BossBot:
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
            if (domain := c.get("domain", "")) == "zhipin.com" or domain.endswith(".zhipin.com")
        ]
        if filtered:
            await self.context.add_cookies(filtered)

    async def navigate(self, url: str, timeout: int = 60000):
        await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    async def is_logged_in(self) -> bool:
        try:
            user_label = self.page.locator("li.nav-figure span.label-text").first
            if await user_label.is_visible():
                return True
        except Exception:
            pass
        try:
            nav_figure = self.page.locator("li.nav-figure").first
            if await nav_figure.is_visible():
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

    async def scroll_to_load_jobs(self, max_attempts: int = 120):
        """滚动搜索结果页直到所有职位卡片加载完成或达到最大尝试次数。"""
        last_count = -1
        stable_tries = 0
        for attempt in range(max_attempts):
            if self.progress_callback and attempt % 10 == 0:
                self.progress_callback("正在加载职位列表...", 0, 0)
            # 检测是否到达页面底部
            footer = self.page.locator("div#footer, #footer")
            try:
                if await footer.count() > 0 and await footer.first.is_visible():
                    break
            except Exception:
                pass
            # 渐进滚动
            await self.page.evaluate("() => window.scrollBy(0, Math.floor(window.innerHeight * 1.5))")
            # 检查卡片数量变化
            cards = self.page.locator("//ul[contains(@class, 'rec-job-list')]//li[contains(@class, 'job-card-box')]")
            current_count = await cards.count()
            if current_count == last_count:
                stable_tries += 1
            else:
                stable_tries = 0
            last_count = current_count
            if stable_tries >= 3:
                await self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        logger.info("职位列表加载完成，共 %d 个", last_count)

    async def deliver_single_job(self, keyword: str, job: dict) -> bool:
        """
        在当前页面执行投递流程：右侧面板点击沟通 → 处理弹框 → 输入打招呼语 → 发送。
        返回 True 表示投递成功。
        """
        if self.config.get("debugger"):
            logger.info("调试模式：仅遍历 | 公司：%s | 岗位：%s", job.get("company_name"), job.get("job_name"))
            return False

        page = self.page

        # 1. 在右侧面板中查找"立即沟通"或"沟通"按钮
        chat_btn = page.locator(
            "a.btn-startchat, a.op-btn-chat, .job-sec-bottom a[ka^='job-detail-top'], "
            "button:has-text('立即沟通'), button:has-text('沟通'), "
            "a:has-text('立即沟通'), a:has-text('沟通')"
        )
        found = False
        for _ in range(5):
            if await chat_btn.count() > 0:
                text = await chat_btn.first.text_content() or ""
                if any(k in text for k in ("立即沟通", "沟通", "打招呼")):
                    found = True
                    break
            await asyncio.sleep(1)
        if not found:
            logger.warning("未找到沟通按钮，跳过：%s", job.get("job_name"))
            return False
        await chat_btn.first.click()
        await asyncio.sleep(2)

        # 2. 判断是否弹出"继续沟通"确认框，有则点击
        confirm_btn = page.locator(
            "button:has-text('继续沟通'), a:has-text('继续沟通'), "
            ".dialog-container button:has-text('继续沟通'), "
            ".dialog-con button:has-text('继续沟通')"
        )
        for _ in range(3):
            if await confirm_btn.count() > 0 and await confirm_btn.first.is_visible():
                await confirm_btn.first.click()
                await asyncio.sleep(2)
                break
            await asyncio.sleep(1)

        # 3. 等待聊天输入框出现
        input_locator = page.locator(
            "div#chat-input.chat-input[contenteditable='true'], "
            "textarea.input-area, "
            "div[contenteditable='true'].chat-input, "
            "#chat-input"
        )
        ready = False
        for _ in range(10):
            if await input_locator.count() > 0 and await input_locator.first.is_visible():
                ready = True
                break
            await asyncio.sleep(1)
        if not ready:
            logger.warning("聊天输入框未出现，跳过：%s", job.get("job_name"))
            return False

        # 4. 生成招呼语
        message = self.config.get("say_hi", "您好，我对这个岗位很感兴趣")
        if self.config.get("enable_ai"):
            try:
                from app.services.ai_service import AiService
                async with self.db_session_factory() as session:
                    ai_service = AiService(session)
                    ai_msg = await ai_service.generate_message(
                        introduce="",
                        keyword=keyword,
                        job_name=job.get("job_name", ""),
                        jd=job.get("job_description", ""),
                        say_hi=message,
                    )
                    if ai_msg:
                        message = ai_msg
            except Exception as e:
                logger.warning("AI 生成问候语失败，使用默认：%s", e)

        # 5. 输入招呼语
        inp = input_locator.first
        await inp.click()
        tag = await inp.evaluate("el => el.tagName.toLowerCase()")
        if tag == "textarea":
            await inp.fill(message)
        else:
            await inp.evaluate(
                "(el, msg) => { el.innerText = msg; el.dispatchEvent(new Event('input', {bubbles: true})); }",
                message,
            )
        await asyncio.sleep(1)

        # 6. 点击发送
        send_btn = page.locator(
            "button[type='send'], .btn-send, div.send-message, "
            "button:has-text('发送'), .im-send-btn"
        )
        if await send_btn.count() > 0:
            await send_btn.first.click()
            await asyncio.sleep(1)
            logger.info("投递完成 | 公司：%s | 岗位：%s | 招呼语：%s", job.get("company_name"), job.get("job_name"), message)
            return True
        else:
            logger.warning("未找到发送按钮，跳过：%s", job.get("job_name"))
            return False

    async def run_delivery(self):
        """
        主投递循环：按城市和关键词搜索 → 滚动加载 → 逐个解析 → 过滤 → 投递 → 更新状态。
        """
        from app.worker.boss_locators import JOB_DETAIL_API_PATH, SEARCH_INPUT, SEARCH_BTN

        # 1. 加载配置和黑名单
        async with self.db_session_factory() as session:
            from app.services.config_service import ConfigService
            config_service = ConfigService(session)
            db_config = await config_service.get_or_create_boss_config()
            blacklist_items = await config_service.get_blacklist()

        black_companies = {b.value for b in blacklist_items if b.type == "company"}
        black_recruiters = {b.value for b in blacklist_items if b.type == "recruiter"}
        black_jobs = {b.value for b in blacklist_items if b.type == "job"}

        # 2. 加载 Cookie
        async with self.db_session_factory() as session:
            from app.services.cookie_service import CookieService
            cookie_service = CookieService(session)
            cookie_record = await cookie_service.get_cookie("boss")
            if cookie_record and cookie_record.cookie_value:
                await self.load_cookies(cookie_record.cookie_value)

        # 3. 检查登录状态
        await self.navigate("https://www.zhipin.com")
        if not await self.is_logged_in():
            if self.progress_callback:
                self.progress_callback("未登录，请扫码登录", 0, 0)
            logger.warning("Boss 直聘未登录，终止投递")
            return

        # 4. 按城市投递（优先从数据库配置读取，否则回退到 self.config）
        city_codes = db_config.city_code or self.config.get("city_code", "")
        city_list = [c.strip() for c in city_codes.split(",") if c.strip()]
        if not city_list:
            city_list = [""]

        keywords = db_config.keywords or self.config.get("keywords", "")
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if not keyword_list:
            keyword_list = [""]

        total_posted = 0
        total_filtered = 0
        for city_code in city_list:
            for keyword in keyword_list:
                if self.progress_callback:
                    self.progress_callback(f"开始投递：{keyword} ({city_code})", 0, 0)

                search_config = {
                    "city_code": city_code,
                    "job_type": db_config.job_type,
                    "salary": db_config.salary,
                    "experience": db_config.experience,
                    "degree": db_config.degree,
                    "scale": db_config.scale,
                    "stage": db_config.stage,
                    "industry": db_config.industry,
                }
                url = build_search_url(search_config)

                await self.navigate(url)

                # 如果有关键词，在搜索框中输入并按回车触发搜索
                if keyword:
                    try:
                        search_input = self.page.locator(SEARCH_INPUT).first
                        await search_input.click()
                        await asyncio.sleep(0.3)
                        await search_input.fill(keyword)
                        await asyncio.sleep(0.3)
                        await search_input.press("Enter")
                        await asyncio.sleep(5)
                    except Exception as e:
                        logger.warning("搜索框输入失败：%s", e)

                try:
                    await self.page.wait_for_selector("//ul[contains(@class, 'rec-job-list')]", timeout=60000)
                except Exception:
                    logger.warning("职位列表未加载：%s", url)
                    continue

                await self.scroll_to_load_jobs()

                await self.page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)

                cards = self.page.locator("//ul[contains(@class, 'rec-job-list')]//li[contains(@class, 'job-card-box')]")
                count = await cards.count()
                logger.info("【%s】共 %d 个职位待处理", keyword, count)

                for i in range(count):
                    from app.worker.task_state import task_state
                    if task_state.should_stop():
                        logger.info("收到停止信号，终止投递")
                        if self.progress_callback:
                            self.progress_callback("已停止", total_posted, total_posted + total_filtered)
                        return

                    if self.progress_callback:
                        self.progress_callback(f"正在处理第 {i+1}/{count} 个职位", i + 1, count)

                    cards = self.page.locator("//ul[contains(@class, 'rec-job-list')]//li[contains(@class, 'job-card-box')]")

                    detail_resp = None
                    try:
                        if i == 0 and count > 1:
                            # 第一个卡片默认展开，先点击第二个触发一次请求再点回第一个
                            await cards.nth(1).click()
                            await asyncio.sleep(1)
                            try:
                                async with self.page.expect_response(
                                    lambda r: JOB_DETAIL_API_PATH in r.url and r.request.method == "GET",
                                    timeout=10000,
                                ) as resp_info:
                                    await cards.nth(0).click()
                                detail_resp = await resp_info.value
                            except Exception:
                                detail_resp = None
                        else:
                            async with self.page.expect_response(
                                lambda r: JOB_DETAIL_API_PATH in r.url and r.request.method == "GET",
                                timeout=10000,
                            ) as resp_info:
                                await cards.nth(i).click()
                            detail_resp = await resp_info.value
                    except Exception as e:
                        logger.debug("等待详情响应异常：%s", e)
                    logger.info("职位 %d detail_resp=%s", i + 1, detail_resp is not None)
                    await asyncio.sleep(1)

                    job_data = {}
                    if detail_resp:
                        try:
                            body = await detail_resp.text()
                            job_data = _parse_job_detail_json(body)
                        except Exception as e:
                            logger.debug("解析岗位详情失败：%s", e)

                    expected_salary = []
                    if db_config.expected_salary_min and db_config.expected_salary_max:
                        expected_salary = [db_config.expected_salary_min, db_config.expected_salary_max]

                    dead_statuses = []
                    if db_config.dead_status:
                        dead_statuses = [s.strip() for s in db_config.dead_status.split(",") if s.strip()]

                    if _should_skip_job(job_data, black_jobs, black_companies, black_recruiters, bool(db_config.filter_dead_hr), dead_statuses):
                        await self._persist_job(job_data, "已过滤")
                        total_filtered += 1
                        from app.worker.task_state import task_state
                        task_state.filtered_count = total_filtered
                        continue

                    if expected_salary and job_data.get("salary"):
                        if is_salary_not_expected(job_data["salary"], expected_salary):
                            logger.info("被过滤：薪资不匹配 | 公司：%s | 岗位：%s | 薪资：%s", job_data.get("company_name"), job_data.get("job_name"), job_data.get("salary"))
                            await self._persist_job(job_data, "已过滤")
                            total_filtered += 1
                            from app.worker.task_state import task_state
                            task_state.filtered_count = total_filtered
                            continue

                    success = await self.deliver_single_job(keyword, job_data)
                    status = "已投递" if success else "投递失败"
                    await self._persist_job(job_data, status)
                    if success:
                        total_posted += 1
                        from app.worker.task_state import task_state
                        task_state.delivered_count = total_posted

                    if i >= 5:
                        await self.page.evaluate("window.scrollBy(0, 140)")
                        await asyncio.sleep(1)

        logger.info("投递完成，共投递 %d 个职位", total_posted)
        if self.progress_callback:
            self.progress_callback(f"投递完成，共投递 {total_posted} 个职位", total_posted, total_posted)

    async def _persist_job(self, job_data: dict, status: str):
        """将职位数据写入数据库。"""
        from app.services.boss_service import BossService

        encrypt_id = job_data.get("encrypt_id")
        if not encrypt_id:
            return

        try:
            async with self.db_session_factory() as session:
                service = BossService(session)
                exists = await service.exists_job(encrypt_id, job_data.get("encrypt_user_id") or "")
                if not exists:
                    await service.insert_job(
                        encrypt_id=encrypt_id,
                        encrypt_user_id=job_data.get("encrypt_user_id"),
                        company_name=job_data.get("company_name"),
                        job_name=job_data.get("job_name"),
                        salary=job_data.get("salary"),
                        location=job_data.get("location"),
                        experience=job_data.get("experience"),
                        degree=job_data.get("degree"),
                        job_description=job_data.get("job_description"),
                        hr_name=job_data.get("hr_name"),
                        hr_position=job_data.get("hr_position"),
                        hr_active_status=job_data.get("hr_active_status"),
                        company_scale=job_data.get("company_scale"),
                        financing_stage=job_data.get("financing_stage"),
                        industry=job_data.get("industry"),
                        delivery_status=status,
                    )
                else:
                    await service.update_delivery_status(
                        encrypt_id, job_data.get("encrypt_user_id") or "", status
                    )
        except Exception as e:
            logger.warning("持久化职位数据失败：%s", e)


def _parse_job_detail_json(body: str) -> dict:
    """解析 Boss 岗位详情 API 返回的 JSON，提取投递与过滤所需的字段。"""
    data = json.loads(body)
    zp_data = data.get("zpData", {})
    job_info = zp_data.get("jobInfo", {})
    brand = zp_data.get("brandComInfo", {})
    boss = zp_data.get("bossInfo", {})

    encrypt_id = job_info.get("encryptId")
    encrypt_user_id = job_info.get("encryptUserId")
    if not encrypt_user_id and boss:
        encrypt_user_id = boss.get("encryptUserId") or boss.get("encryptBossId")

    result = {
        "encrypt_id": encrypt_id,
        "encrypt_user_id": encrypt_user_id,
        "job_name": job_info.get("jobName"),
        "salary": job_info.get("salaryDesc"),
        "location": job_info.get("locationName"),
        "experience": job_info.get("experienceName"),
        "degree": job_info.get("degreeName"),
        "job_description": job_info.get("postDescription"),
        "recruitment_status": job_info.get("jobStatusDesc"),
        "company_address": job_info.get("address"),
        "company_name": brand.get("brandName") if brand else None,
        "industry": brand.get("industryName") if brand else None,
        "introduce": brand.get("introduce") if brand else None,
        "financing_stage": brand.get("stageName") if brand else None,
        "company_scale": brand.get("scaleName") if brand else None,
        "hr_name": boss.get("name") if boss else None,
        "hr_position": boss.get("title") if boss else None,
        "hr_active_status": boss.get("activeTimeDesc") if boss else None,
    }

    if encrypt_id:
        result["job_url"] = f"https://www.zhipin.com/job_detail/{encrypt_id}.html"

    return result


def _should_skip_job(
    job: dict,
    black_jobs: set,
    black_companies: set,
    black_recruiters: set,
    filter_dead_hr: bool,
    dead_statuses: list,
) -> bool:
    """根据黑名单、HR 活跃度、薪资过滤判断是否应该跳过该职位。"""
    job_name = job.get("job_name") or ""
    company_name = job.get("company_name") or ""
    hr_position = job.get("hr_position") or ""
    hr_active = job.get("hr_active_status") or ""

    for pattern in black_jobs:
        if pattern and pattern in job_name:
            logger.info("被过滤：职位黑名单命中 | 公司：%s | 岗位：%s | 关键词：%s", company_name, job_name, pattern)
            return True

    if filter_dead_hr and dead_statuses:
        for status in dead_statuses:
            if status and status in hr_active:
                logger.info("被过滤：HR活跃状态命中 | 公司：%s | 岗位：%s | 活跃：%s", company_name, job_name, hr_active)
                return True

    for pattern in black_companies:
        if pattern and pattern in company_name:
            logger.info("被过滤：公司黑名单命中 | 公司：%s | 岗位：%s | 关键词：%s", company_name, job_name, pattern)
            return True

    for pattern in black_recruiters:
        if pattern and pattern in hr_position:
            logger.info("被过滤：招聘者黑名单命中 | 公司：%s | 岗位：%s | 招聘者：%s | 关键词：%s", company_name, job_name, hr_position, pattern)
            return True

    return False
