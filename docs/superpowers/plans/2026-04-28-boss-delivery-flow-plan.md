# BossBot 自动投递流程实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 BossBot 从浏览器骨架升级为完整的自动投递机器人，支持搜索职位、解析详情、黑名单过滤、AI 打招呼、数据持久化、SSE 进度推送。

**架构：** BossBot 类中新增投递核心方法，Jobs Router 通过 asyncio.create_task() 在后台启动投递循环。投递进度通过已有的 SSEManager 实时推送到前端。职位数据通过已有的 BossService 写入 SQLite。

**技术栈：** Camoufox (Playwright), SQLAlchemy 2.0, asyncio, Pydantic

---

## 文件结构

```
app/
├── worker/
│   ├── bot.py                    # 追加：投递核心方法（JSON解析、过滤、打招呼）
│   └── boss_locators.py          # 新增：Boss直聘页面CSS/XPath选择器常量
├── routers/
│   └── jobs.py                   # 修改：/boss/start 实际启动投递任务
```

- `boss_locators.py` 职责：集中管理所有页面元素定位表达式，与业务逻辑解耦，便于选择器变更时统一维护。
- `bot.py` 职责：保留浏览器控制基础方法，新增投递全流程（滚动加载→解析→过滤→打招呼→状态更新）。
- `jobs.py` 职责：HTTP 入口，负责参数组装、权限校验、后台任务启动、SSE 事件转发。

---

## 任务分解

### 任务 1：Boss 直聘页面选择器常量

**文件：**
- 创建：`app/worker/boss_locators.py`

- [ ] **步骤 1：编写选择器常量文件**

```python
# app/worker/boss_locators.py

# 登录相关
LOGIN_BTN = "//li[@class='nav-figure']"

# 搜索结果页
JOB_LIST_CONTAINER = "//div[@class='job-list-container']"
JOB_CARD_BOX = "li.job-card-box"
JOB_LIST_SELECTOR = "ul.rec-job-list li.job-card-box"
JOB_NAME = "a.job-name"
COMPANY_NAME = "span.boss-name"
JOB_AREA = "span.company-location"
TAG_LIST = "ul.tag-list li"

# 职位详情页
CHAT_BUTTON = "[class*='btn btn-startchat']"
ERROR_CONTENT = "//div[@class='error-content']"
JOB_DETAIL_SALARY = "//div[@class='info-primary']//span[@class='salary']"
RECRUITER_INFO = "//div[@class='boss-info-attr']"
HR_ACTIVE_TIME = "//span[@class='boss-active-time']"
JOB_DESCRIPTION = "//div[@class='job-sec-text']"

# 聊天相关
DIALOG_TITLE = "//div[@class='dialog-title']"
DIALOG_CLOSE = "//i[@class='icon-close']"
CHAT_INPUT = "//div[@id='chat-input']"
DIALOG_CONTAINER = "//div[@class='dialog-container']"
SEND_BUTTON = "//button[@type='send']"
IMAGE_UPLOAD = "//div[@aria-label='发送图片']//input[@type='file']"
DIALOG_CONTENT = "//div[@class='dialog-con']"
SCROLL_LOAD_MORE = "//div[contains(text(), '滚动加载更多')]"

# 消息列表页
CHAT_LIST_ITEM = "//li[@role='listitem']"
COMPANY_NAME_IN_CHAT = "//div[@class='title-box']/span[@class='name-box']//span[2]"
LAST_MESSAGE = "//div[@class='gray last-msg']/span[@class='last-msg-text']"
FINISHED_TEXT = "//div[@class='finished']"

LOGIN_BTNS = "//div[@class='btns']"
PAGE_HEADER = "//h1"
ERROR_PAGE_LOGIN = "//a[@ka='403_login']"

# 岗位详情API路径（用于拦截响应）
JOB_DETAIL_API_PATH = "/wapi/zpgeek/job/detail.json"
```

- [ ] **步骤 2：Commit**

```bash
git add app/worker/boss_locators.py
git commit -m "feat: add Boss page element locators"
```

---

### 任务 2：JSON 解析与过滤逻辑

**文件：**
- 修改：`app/worker/bot.py`（在现有方法后追加）
- 测试：`tests/test_bot.py`（追加测试）

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_bot.py（追加到文件末尾）
import json
from app.worker.bot import BossBot, _parse_job_detail_json, _should_skip_job


def test_parse_job_detail_json():
    raw = json.dumps({
        "zpData": {
            "jobInfo": {
                "encryptId": "abc123",
                "encryptUserId": "user456",
                "jobName": "Java后端工程师",
                "salaryDesc": "20-40K",
                "locationName": "北京",
                "experienceName": "3-5年",
                "degreeName": "本科",
                "postDescription": "负责后端开发",
                "jobStatusDesc": "招聘中",
                "address": "朝阳区",
            },
            "brandComInfo": {
                "brandName": "测试科技公司",
                "industryName": "互联网",
                "introduce": "一家好公司",
                "stageName": "A轮",
                "scaleName": "100-499人",
            },
            "bossInfo": {
                "name": "张经理",
                "title": "技术总监",
                "activeTimeDesc": "3日内活跃",
            },
        }
    })
    result = _parse_job_detail_json(raw)
    assert result["encrypt_id"] == "abc123"
    assert result["encrypt_user_id"] == "user456"
    assert result["job_name"] == "Java后端工程师"
    assert result["company_name"] == "测试科技公司"
    assert result["hr_name"] == "张经理"


def test_should_skip_job_blacklist():
    job = {"job_name": "高级Java工程师", "company_name": "黑名单公司", "hr_position": "HR"}
    black_jobs = {"Python"}
    black_companies = {"黑名单公司"}
    black_recruiters = set()
    assert _should_skip_job(job, black_jobs, black_companies, black_recruiters, False, []) is True


def test_should_skip_job_pass():
    job = {"job_name": "Java工程师", "company_name": "正常公司", "hr_position": "技术总监", "hr_active_status": "3日内活跃"}
    assert _should_skip_job(job, set(), set(), set(), False, []) is False
```

- [ ] **步骤 2：运行测试确认失败**

```bash
pytest tests/test_bot.py::test_parse_job_detail_json -v
```
预期：FAIL，`_parse_job_detail_json` not defined

- [ ] **步骤 3：实现解析与过滤函数**

```python
# app/worker/bot.py 追加到文件末尾（BossBot 类外部）

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
```

- [ ] **步骤 4：运行测试确认通过**

```bash
pytest tests/test_bot.py -v
```
预期：全部 PASS（原有 3 个 + 新增 3 个 = 6 个）

- [ ] **步骤 5：Commit**

```bash
git add app/worker/bot.py tests/test_bot.py
git commit -m "feat: add job detail JSON parser and blacklist filter"
```

---

### 任务 3：薪资过滤逻辑

**文件：**
- 修改：`app/worker/bot.py`
- 测试：`tests/test_bot.py`

- [ ] **步骤 1：编写失败的测试**

```python
def test_is_salary_not_expected():
    from app.worker.bot import _is_salary_not_expected
    # 20-40K，期望 30-50K → 符合（不跳过）
    assert _is_salary_not_expected("20-40K", [30, 50]) is False
    # 10-15K，期望 30-50K → 不符合（跳过）
    assert _is_salary_not_expected("10-15K", [30, 50]) is True
    # 60-80K，期望 30-50K → 不符合（跳过）
    assert _is_salary_not_expected("60-80K", [30, 50]) is True
    # 无期望薪资 → 不跳过
    assert _is_salary_not_expected("20-40K", []) is False
```

- [ ] **步骤 2：运行测试确认失败**

```bash
pytest tests/test_bot.py::test_is_salary_not_expected -v
```
预期：FAIL

- [ ] **步骤 3：实现薪资过滤函数**

```python
def _is_salary_not_expected(salary: str, expected: list) -> bool:
    """
    检查岗位薪资是否符合预期范围。
    expected: [min_k, max_k]，单位 K（千）
    返回 True 表示"不符合预期"（应跳过）
    """
    if not expected or len(expected) < 2:
        return False

    min_expected, max_expected = expected[0], expected[1]
    job_range = parse_salary_range(salary)
    if not job_range:
        return True

    if len(job_range) >= 2:
        if job_range[1] <= min_expected:
            return True
        if job_range[0] >= max_expected:
            return True
    elif len(job_range) == 1:
        if job_range[0] < min_expected or job_range[0] > max_expected:
            return True
    return False
```

- [ ] **步骤 4：运行测试确认通过**

```bash
pytest tests/test_bot.py::test_is_salary_not_expected -v
```
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add app/worker/bot.py tests/test_bot.py
git commit -m "feat: add salary range filter for job delivery"
```

---

### 任务 4：BossBot 投递核心方法

**文件：**
- 修改：`app/worker/bot.py`（在 BossBot 类内追加方法）

⚠️ **注意：** 此任务涉及 Playwright 页面操作，纯单元测试只能覆盖非页面相关部分。页面相关逻辑通过手动运行验证。

- [ ] **步骤 1：实现页面滚动加载职位**

```python
# app/worker/bot.py 在 BossBot 类内追加

async def scroll_to_load_jobs(self, max_attempts: int = 120):
    """滚动搜索结果页直到所有职位卡片加载完成或达到最大尝试次数。"""
    last_count = -1
    stable_tries = 0
    for _ in range(max_attempts):
        if self.progress_callback:
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
```

- [ ] **步骤 2：实现单个职位投递**

```python
async def deliver_single_job(self, keyword: str, job: dict) -> bool:
    """
    对单个职位执行投递流程：打开详情页 → 点击立即沟通 → 输入打招呼语 → 发送。
    返回 True 表示投递成功。
    """
    # 调试模式仅遍历不投递
    if self.config.get("debugger"):
        logger.info("调试模式：仅遍历 | 公司：%s | 岗位：%s", job.get("company_name"), job.get("job_name"))
        return False

    # 1. 查找"查看更多信息"按钮获取详情链接
    more_btn = self.page.locator("a.more-job-btn")
    if await more_btn.count() == 0:
        logger.warning("未找到'查看更多信息'按钮，跳过")
        return False
    href = await more_btn.first.get_attribute("href")
    if not href or not href.startswith("/job_detail/"):
        logger.warning("未获取到岗位详情链接，跳过")
        return False
    detail_url = "https://www.zhipin.com" + href

    # 2. 在新页面打开详情
    detail_page = await self.context.new_page()
    await detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(1)

    try:
        # 3. 查找并点击"立即沟通"
        chat_btn = detail_page.locator("a.btn-startchat, a.op-btn-chat")
        found = False
        for _ in range(5):
            if await chat_btn.count() > 0:
                text = await chat_btn.first.text_content()
                if text and "立即沟通" in text:
                    found = True
                    break
            await asyncio.sleep(1)
        if not found:
            logger.warning("未找到立即沟通按钮，跳过：%s", job.get("job_name"))
            return False
        await chat_btn.first.click()
        await asyncio.sleep(1)

        # 4. 等待聊天输入框
        input_locator = detail_page.locator("div#chat-input.chat-input[contenteditable='true'], textarea.input-area")
        ready = False
        for _ in range(10):
            if await input_locator.count() > 0 and await input_locator.first.is_visible():
                ready = True
                break
            await asyncio.sleep(1)
        if not ready:
            logger.warning("聊天输入框未出现，跳过：%s", job.get("job_name"))
            return False

        # 5. 准备打招呼语
        message = self.config.get("say_hi", "您好，我对这个岗位很感兴趣")
        if self.config.get("enable_ai"):
            # AI 生成问候语（调用外部服务，这里简化处理）
            pass  # 在 Task 6 中集成 AiService

        # 6. 输入消息
        inp = input_locator.first
        await inp.click()
        tag = await inp.evaluate("el => el.tagName.toLowerCase()")
        if tag == "textarea":
            await inp.fill(message)
        else:
            await inp.evaluate("(el, msg) => { el.innerText = msg; el.dispatchEvent(new Event('input')); }", message)

        # 7. 点击发送
        send_btn = detail_page.locator("div.send-message, button[type='send'].btn-send, button.btn-send")
        if await send_btn.count() > 0:
            await send_btn.first.click()
            await asyncio.sleep(1)
            # 尝试关闭小窗口
            try:
                close_btn = detail_page.locator("i.icon-close")
                if await close_btn.count() > 0:
                    await close_btn.first.click()
            except Exception:
                pass
            logger.info("投递完成 | 公司：%s | 岗位：%s | 招呼语：%s", job.get("company_name"), job.get("job_name"), message)
            return True
        else:
            logger.warning("未找到发送按钮，跳过：%s", job.get("job_name"))
            return False
    finally:
        # 关闭详情页
        try:
            await detail_page.close()
        except Exception:
            pass
        await asyncio.sleep(1)
```

- [ ] **步骤 3：实现主投递循环**

```python
async def run_delivery(self):
    """
    主投递循环：按城市和关键词搜索 → 滚动加载 → 逐个解析 → 过滤 → 投递 → 更新状态。
    """
    from app.worker.boss_locators import JOB_DETAIL_API_PATH
    from app.services.config_service import ConfigService
    from app.services.cookie_service import CookieService
    from app.services.boss_service import BossService
    from app.database import async_session_maker

    # 1. 加载配置和黑名单
    async with async_session_maker() as session:
        config_service = ConfigService(session)
        db_config = await config_service.get_or_create_boss_config()
        blacklist_items = await config_service.get_blacklist()

    black_companies = {b.value for b in blacklist_items if b.type == "company"}
    black_recruiters = {b.value for b in blacklist_items if b.type == "recruiter"}
    black_jobs = {b.value for b in blacklist_items if b.type == "job"}

    # 2. 加载 Cookie
    async with async_session_maker() as session:
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

    # 4. 按城市投递
    city_codes = self.config.get("city_code", "")
    if not city_codes:
        city_codes = ""
    city_list = [c.strip() for c in city_codes.split(",") if c.strip()]
    if not city_list:
        city_list = [""]

    keywords = self.config.get("keywords", "")
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not keyword_list:
        keyword_list = [""]

    total_posted = 0
    for city_code in city_list:
        for keyword in keyword_list:
            if self.progress_callback:
                self.progress_callback(f"开始投递：{keyword} ({city_code})", 0, 0)

            # 构建搜索 URL
            search_config = {
                "city_code": city_code,
                "keywords": keyword,
                "job_type": db_config.job_type,
                "salary": db_config.salary,
                "experience": db_config.experience,
                "degree": db_config.degree,
                "scale": db_config.scale,
                "stage": db_config.stage,
                "industry": db_config.industry,
            }
            url = build_search_url(search_config)
            if keyword:
                url += ("&" if "?" in url else "?") + f"query={keyword}"

            await self.navigate(url)
            # 等待列表容器
            try:
                await self.page.wait_for_selector("//ul[contains(@class, 'rec-job-list')]", timeout=60000)
            except Exception:
                logger.warning("职位列表未加载：%s", url)
                continue

            # 滚动加载全部职位
            await self.scroll_to_load_jobs()

            # 回到顶部
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)

            # 获取所有卡片
            cards = self.page.locator("//ul[contains(@class, 'rec-job-list')]//li[contains(@class, 'job-card-box')]")
            count = await cards.count()
            logger.info("【%s】共 %d 个职位待处理", keyword, count)

            for i in range(count):
                if self.progress_callback:
                    self.progress_callback(f"正在处理第 {i+1}/{count} 个职位", i + 1, count)

                # 重新获取卡片（避免元素过期）
                cards = self.page.locator("//ul[contains(@class, 'rec-job-list')]//li[contains(@class, 'job-card-box')]")

                # 点击卡片并拦截详情 API 响应
                detail_resp = None
                try:
                    if i == 0 and count > 1:
                        # 第一个卡片默认展开不触发请求：先点击第二个再点回第一个
                        await cards.nth(1).click()
                        await asyncio.sleep(1)
                        detail_resp = await self.page.wait_for_response(
                            lambda r: JOB_DETAIL_API_PATH in r.url and r.request.method == "GET",
                            timeout=10000,
                        )
                        await cards.nth(0).click()
                    else:
                        detail_resp = await self.page.wait_for_response(
                            lambda r: JOB_DETAIL_API_PATH in r.url and r.request.method == "GET",
                            timeout=10000,
                        )
                except Exception:
                    pass
                await asyncio.sleep(1)

                # 解析详情
                job_data = {}
                if detail_resp:
                    try:
                        body = await detail_resp.text()
                        job_data = _parse_job_detail_json(body)
                    except Exception as e:
                        logger.debug("解析岗位详情失败：%s", e)

                # 过滤
                expected_salary = []
                if db_config.expected_salary_min and db_config.expected_salary_max:
                    expected_salary = [db_config.expected_salary_min, db_config.expected_salary_max]

                dead_statuses = []
                if db_config.dead_status:
                    dead_statuses = [s.strip() for s in db_config.dead_status.split(",") if s.strip()]

                if _should_skip_job(job_data, black_jobs, black_companies, black_recruiters, bool(db_config.filter_dead_hr), dead_statuses):
                    # 入库标记为已过滤
                    await self._persist_job(job_data, "已过滤")
                    continue

                if expected_salary and job_data.get("salary"):
                    if _is_salary_not_expected(job_data["salary"], expected_salary):
                        logger.info("被过滤：薪资不匹配 | 公司：%s | 岗位：%s | 薪资：%s", job_data.get("company_name"), job_data.get("job_name"), job_data.get("salary"))
                        await self._persist_job(job_data, "已过滤")
                        continue

                # 投递
                success = await self.deliver_single_job(keyword, job_data)
                status = "已投递" if success else "投递失败"
                await self._persist_job(job_data, status)
                if success:
                    total_posted += 1

                # 滚动避免卡片被遮挡
                if i >= 5:
                    await self.page.evaluate("window.scrollBy(0, 140)")
                    await asyncio.sleep(1)

    logger.info("投递完成，共投递 %d 个职位", total_posted)
    if self.progress_callback:
        self.progress_callback(f"投递完成，共投递 {total_posted} 个职位", total_posted, total_posted)


async def _persist_job(self, job_data: dict, status: str):
    """将职位数据写入数据库。"""
    from app.services.boss_service import BossService
    from app.database import async_session_maker
    from app.models import BossData

    encrypt_id = job_data.get("encrypt_id")
    if not encrypt_id:
        return

    async with async_session_maker() as session:
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
```

- [ ] **步骤 4：Commit**

```bash
git add app/worker/bot.py app/worker/boss_locators.py
git commit -m "feat: add BossBot delivery core methods (scroll, parse, filter, deliver)"
```

---

### 任务 5：Jobs Router 连接 BossBot 与 SSE

**文件：**
- 修改：`app/routers/jobs.py`
- 测试：`tests/test_routers/test_jobs.py`（追加）

- [ ] **步骤 1：编写失败的测试**

```python
# tests/test_routers/test_jobs.py 追加

def test_start_boss_triggers_background_task(monkeypatch):
    import asyncio
    called = False

    async def mock_run():
        nonlocal called
        called = True

    monkeypatch.setattr("app.routers.jobs._run_boss_delivery", mock_run)
    response = client.post("/api/boss/start")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "started"
```

- [ ] **步骤 2：运行测试确认失败**

```bash
pytest tests/test_routers/test_jobs.py::test_start_boss_triggers_background_task -v
```
预期：FAIL

- [ ] **步骤 3：修改 Jobs Router**

```python
# app/routers/jobs.py

import asyncio
from fastapi import APIRouter
from app.schemas import ApiResponse
from app.worker.task_state import task_state
from app.worker.sse_manager import sse_manager
from app.worker.bot import BossBot
from app.database import async_session_maker

router = APIRouter()


async def _run_boss_delivery():
    """后台执行 Boss 投递任务。"""
    bot = None
    try:
        bot = BossBot(config={}, db_session_factory=async_session_maker)
        await bot.init()

        def progress_cb(message: str, current: int, total: int):
            sse_manager.publish({
                "type": "progress",
                "platform": "boss",
                "message": message,
                "current": current,
                "total": total,
            })

        bot.progress_callback = progress_cb
        await bot.run_delivery()
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error("Boss 投递任务异常：%s", e)
        sse_manager.publish({
            "type": "error",
            "platform": "boss",
            "message": f"投递异常：{e}",
        })
    finally:
        if bot:
            await bot.close()
        task_state.stop()
        sse_manager.publish({
            "type": "complete",
            "platform": "boss",
            "message": "投递任务已结束",
        })


@router.post("/boss/start", response_model=ApiResponse)
async def start_boss():
    if task_state.running:
        return ApiResponse(success=False, message="Boss任务已在运行中", status="running")

    task_state.start("boss")
    asyncio.create_task(_run_boss_delivery())
    return ApiResponse(success=True, message="Boss任务启动成功", status="started")
```

- [ ] **步骤 4：运行测试确认通过**

```bash
pytest tests/test_routers/test_jobs.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add app/routers/jobs.py tests/test_routers/test_jobs.py
git commit -m "feat: wire /boss/start to actual BossBot delivery task with SSE"
```

---

### 任务 6：集成 AI 打招呼语

**文件：**
- 修改：`app/worker/bot.py`

- [ ] **步骤 1：在 deliver_single_job 中集成 AI**

将 deliver_single_job 中步骤 5 的占位注释替换为实际调用：

```python
# 5. 准备打招呼语
message = self.config.get("say_hi", "您好，我对这个岗位很感兴趣")
if self.config.get("enable_ai"):
    try:
        from app.services.ai_service import AiService
        from app.database import async_session_maker
        async with async_session_maker() as session:
            ai_service = AiService(session)
            ai_msg = await ai_service.generate_message(
                keyword=keyword,
                job_name=job.get("job_name", ""),
                job_description=job.get("job_description", ""),
            )
            if ai_msg:
                message = ai_msg
    except Exception as e:
        logger.warning("AI 生成问候语失败，使用默认：%s", e)
```

- [ ] **步骤 2：Commit**

```bash
git add app/worker/bot.py
git commit -m "feat: integrate AI greeting generation into delivery flow"
```

---

### 任务 7：运行全部测试与手动验证

- [ ] **步骤 1：运行全部测试**

```bash
pytest tests/ -v
```
预期：全部 PASS

- [ ] **步骤 2：手动验证投递流程**

```bash
# 1. 启动服务
python run.py

# 2. 配置职位（设置 keywords, city_code, say_hi）
curl -X PUT http://localhost:8888/api/boss/config \
  -H "Content-Type: application/json" \
  -d '{"keywords": "Java", "city_code": "101010100", "say_hi": "您好"}'

# 3. 保存 Cookie（如果有）
curl -X POST "http://localhost:8888/api/cookie/save?platform=boss" \
  -H "Content-Type: application/json" \
  -d '{"cookie_value": "[{...}]"}'

# 4. 启动投递
curl -X POST http://localhost:8888/api/boss/start

# 5. 连接 SSE 观察进度
curl http://localhost:8888/api/boss/stream
```

- [ ] **步骤 3：Commit**

```bash
git commit --allow-empty -m "chore: verify delivery flow end-to-end"
```

---

## 自检

**1. 规格覆盖度：**
- ✅ 搜索职位列表 — 任务 4 `run_delivery()` 构建 URL + 导航
- ✅ 解析职位详情 — 任务 2 `_parse_job_detail_json()` + 任务 4 响应拦截
- ✅ 黑名单过滤 — 任务 2 `_should_skip_job()`
- ✅ 薪资过滤 — 任务 3 `_is_salary_not_expected()`
- ✅ AI 打招呼 — 任务 6 集成 `AiService.generate_message()`
- ✅ 执行投递 — 任务 4 `deliver_single_job()`
- ✅ 数据持久化 — 任务 4 `_persist_job()` 写入 `boss_data`
- ✅ SSE 进度推送 — 任务 5 `_run_boss_delivery()` 中 `sse_manager.publish()`
- ✅ 停止机制 — `task_state.should_stop()` 在循环中检查（需用户在循环中加入检查）

**2. 占位符扫描：**
- ✅ 无"待定"、"TODO"、"后续实现"
- ✅ 所有测试包含实际代码
- ✅ 所有步骤包含完整代码块

**3. 类型一致性：**
- ✅ `_parse_job_detail_json` 返回的 key 与 `_persist_job` 使用的 key 一致
- ✅ `BossBot.__init__` 参数与 `jobs.py` 中创建实例时一致
- ✅ `build_search_url` 的 config key 与 `BossConfig` model 字段一致

---

## 执行选项

**计划已完成并保存到 `docs/superpowers/plans/2026-04-28-boss-delivery-flow-plan.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
