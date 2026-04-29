# 搜索页
SEARCH_URL_BASE = "https://we.51job.com/pc/search"

# 职位卡片
checkbox = "div.ick"
JOB_TITLES = "[class*='jname text-cut']"
JOB_COMPANIES = "[class*='cname text-cut']"

# 批量投递
BATCH_DELIVER_PARENT = "div.tabs_in"
SELECT_ALL_BUTTON = "span.ck"
BATCH_DELIVER_BUTTON = "button.p_but"

# 页码跳转
PAGE_INPUT = "#jump_page"
JUMP_BUTTON = "span.jumpPage"

# 登录检测
LOGIN_INDICATOR = "a.uname"

# 访问验证
WAF_TITLE = "p.waf-nc-title"
WAF_SCRIPT = "script[name^='aliyunwaf_']"
VERIFY_TEXT = "text=访问验证, text=请按住滑块"

# 投递成功弹窗
SUCCESS_DIALOG_CONTENT = "div.successContent"
EL_DIALOG_BODY = ".el-dialog__body"
EL_DIALOG_FOOTER_OK = ".el-dialog__footer button:has-text('确定'), .el-message-box__btns button:has-text('确定')"
DIALOG_CLOSE_ICON = "i.el-dialog__close.el-icon.el-icon-close"
DIALOG_HEADER_BTN = "button.el-dialog__headerbtn, button[aria-label='Close']"
POPUP_CLOSE_ICON = ".van-popup__close-icon, .van-icon-cross"

# 单独投递申请弹窗
SEPARATE_APPLY_DIALOG = "//div[@class='el-dialog__body']/span"
SEPARATE_APPLY_CLOSE = "#app > div > div.post > div > div > div.j_result > div > div:nth-child(2) > div > div:nth-child(2) > div:nth-child(2) > div > div.el-dialog__header > button > i"

# 日投递上限检测
DAILY_LIMIT_KEYWORDS = [
    "今日投递太多", "您今日投递太多", "休息一下明天再来",
    "达到上限", "次数过多", "今日投递已达上限",
    "投递次数已达上限", "今日已投递", "投递已达上限",
    "超出限制", "投递上限", "次数已达上限",
]
DAILY_LIMIT_LOCATORS = ".el-message, .el-message--info, .toast, .message, div[role='alert'], .el-notification__content"

# 无职位检测
NO_JOBS_KEYWORDS = ["暂无职位", "没有符合条件的职位", "暂无符合条件职位", "暂无符合职位", "暂无相关职位"]
NO_JOBS_LOCATORS = ".el-empty, .empty, .no-result, .no_res"

# 弹层覆盖层
MODAL_OVERLAYS = ".el-dialog__wrapper, .van-popup"

# 排序选项
SORT_OPTIONS = "div.ss"

# API 拦截路径
SEARCH_API_PATH = "/api/job/search-pc"

# 下载 App 弹窗
APP_DOWNLOAD_CLOSE = "[class*='van-icon van-icon-cross van-popup__close-icon van-popup__close-icon--top-right']"
