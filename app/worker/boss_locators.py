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

# 搜索框
SEARCH_INPUT = 'input[placeholder*="搜索"]'
SEARCH_BTN = ".search-btn"
SEARCH_FORM = ".search-box"

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
