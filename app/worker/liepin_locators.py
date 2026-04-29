# 搜索页
SEARCH_URL_BASE = "https://www.liepin.com/zhaopin/"
PAGINATION_BOX = ".list-pagination-box"
NEXT_PAGE = "li.ant-pagination-next"
SUBSCRIBE_CLOSE_BTN = "div[class*='subscribe-close-btn']"
JOB_CARDS = "div[class*='job-card-pc-container']"

# 聊天窗口
CHAT_HEADER = ".__im_basic__header-wrap"
CHAT_CLOSE = "div.__im_basic__contacts-title svg"

# 聊天输入框
CHAT_INPUT_SELECTORS = [
    "textarea[placeholder]",
    "[contenteditable='true']",
    "div[class*='input'] [contenteditable]",
    ".editor-content",
    "textarea",
    "input[type='text']",
]

# 发送按钮
CHAT_SEND_BUTTONS = [
    "button:has-text('发送')",
    "button.send-btn",
    "button[class*='send']",
    "svg[class*='send']",
    "button.ant-btn-primary",
    "button",
]

# 聊一聊按钮（按优先级）
CHAT_BUTTON_SELECTORS = [
    "button.ant-btn.ant-btn-primary.ant-btn-round",
    "button.ant-btn.ant-btn-round.ant-btn-primary",
    "button[class*='ant-btn'][class*='primary']",
    "button[class*='ant-btn'][class*='round']",
    "button:has-text('聊一聊')",
    "button",
]

# HR 区域选择器
HR_AREA_SELECTORS = [
    ".recruiter-info-box",
    ".recruiter-info, .hr-info, .contact-info",
    "[class*='recruiter'], [class*='hr-'], [class*='contact']",
    ".job-card-footer, .card-footer",
    ".job-bottom, .bottom-info",
]

# 职位标题链接
JOB_TITLE_LINKS = [
    "a.job-title",
    "a[data-nick='job-title']",
    "h3 a",
    "a[href*='/job/']",
]

# 详情页投递按钮（优先投简历，其次聊一聊/立即沟通）
DETAIL_APPLY_BUTTONS = [
    # 投简历按钮（优先）
    "button:has-text('投递简历')",
    "button:has-text('投简历')",
    "[class*='apply'] button",
    "button.apply-btn",
    "button.apply",
    "a:has-text('投递简历')",
    # 聊一聊/立即沟通按钮
    "button:has-text('聊一聊')",
    "button:has-text('立即沟通')",
    "button:has-text('沟通')",
    "[class*='im'] button",
    "[class*='chat'] button",
    "button[class*='primary']",
    "button.ant-btn-primary",
    # 兜底
    "button",
    "a",
]

# 已投递标记（继续聊按钮）
ALREADY_DELIVERED_MARKERS = [
    "button:has-text('继续聊')",
    "a:has-text('继续聊')",
    "[class*='continue']",
]

# API 拦截路径
SEARCH_API_PATH = "com.liepin.searchfront4c.pc-search-job"
SEARCH_API_EXCLUDE = "pc-search-job-cond-init"
