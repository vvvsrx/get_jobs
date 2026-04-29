from app.schemas import (
    BossConfigSchema,
    BossBlacklistCreate,
    BossBlacklistResponse,
    BossOptionSchema,
    CookieSchema,
    AiConfigSchema,
    JobProgressEvent,
    LoginStatusEvent,
    ApiResponse,
    BossDataResponse,
    BossStatsResponse,
)


def test_boss_config_schema():
    data = {"keywords": "Java,后端", "city_code": "101010100", "say_hi": "您好"}
    config = BossConfigSchema(**data)
    assert config.keywords == "Java,后端"
    assert config.enable_ai == 1  # default
    assert config.wait_time == 10
    assert config.filter_dead_hr == 1


def test_blacklist_create():
    item = BossBlacklistCreate(type="company", value="某科技有限公司")
    assert item.type == "company"
    assert item.value == "某科技有限公司"


def test_blacklist_response():
    item = BossBlacklistResponse(id=1, type="company", value="测试公司")
    assert item.id == 1
    assert item.type == "company"


def test_boss_option_schema():
    option = BossOptionSchema(type="city", name="北京", code="101010100")
    assert option.code == "101010100"


def test_cookie_schema():
    cookie = CookieSchema(platform="boss", cookie_value="[]")
    assert cookie.platform == "boss"


def test_ai_config_schema():
    ai = AiConfigSchema(introduce="5年后端", prompt="请生成打招呼语")
    assert ai.introduce == "5年后端"


def test_job_progress_event():
    event = JobProgressEvent(platform="boss", message="测试中", current=1, total=10)
    assert event.type == "progress"


def test_login_status_event():
    event = LoginStatusEvent(platform="boss", is_logged_in=True)
    assert event.type == "login"


def test_api_response():
    resp = ApiResponse(success=True, message="ok")
    assert resp.success is True


def test_boss_data_response():
    data = BossDataResponse(id=1, job_name="Java开发", company_name="测试公司")
    assert data.encrypt_id is None


def test_boss_stats_response():
    stats = BossStatsResponse(total=100, delivered=50, filtered=30, pending=20)
    assert stats.total == 100
