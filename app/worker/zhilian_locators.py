# 搜索页
SEARCH_URL_BASE = "https://www.zhaopin.com/sou/"

# 关键词输入框
KEYWORD_INPUT_SELECTORS = [
    "input[placeholder*='职位']",
    "input[placeholder*='公司']",
    "input[name='kw']",
    "input[type='text']",
    "input[class*='search']",
    "input[class*='sou']",
    "input[class*='input']",
]

# 职位卡片
JOB_CARDS = "div.joblist-box__item"

# 职位标题
JOB_TITLE = "a.jobinfo__name"

# 薪资
JOB_SALARY = "p.jobinfo__salary"

# 地点
JOB_LOCATION = "div.jobinfo__other-info-item:first-child span"

# 经验
JOB_EXPERIENCE = "div.jobinfo__other-info-item:nth-child(2)"

# 学历
JOB_DEGREE = "div.jobinfo__other-info-item:nth-child(3)"

# 公司名
COMPANY_NAME = "div.companyinfo__name"

# 投递按钮（列表页直接投递）
APPLY_BUTTON = "button.collect-and-apply__btn"

# 下一页
NEXT_PAGE = "a.soupager__btn:has-text(\"下一页\")"
NEXT_PAGE_DISABLED_CLASS = "soupager__btn--disable"

# 投递上限提示
APPLY_LIMIT_INDICATOR = "div.a-job-apply-workflow"

# 投递弹窗（新窗口）
DIALOG_DELIVER_RESULT = "div.deliver-dialog"
DIALOG_CLOSE_BUTTON = "img[title='close-icon']"

# 相似职位推荐
SIMILAR_JOBS_SELECT_ALL = "div.applied-select-all input"
SIMILAR_JOBS_ITEMS = "div.recommend-job"
SIMILAR_JOBS_POST_BUTTON = "div.applied-select-all button"

# 已投递标记
ALREADY_APPLIED_MARKER = "button.collect-and-apply__btn--applied"
