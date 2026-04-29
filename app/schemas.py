from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BossConfigSchema(BaseModel):
    id: Optional[int] = None
    debugger: int = 0
    wait_time: int = 10
    keywords: Optional[str] = None
    city_code: Optional[str] = None
    industry: Optional[str] = None
    job_type: Optional[str] = None
    experience: Optional[str] = None
    degree: Optional[str] = None
    salary: Optional[str] = None
    scale: Optional[str] = None
    stage: Optional[str] = None
    say_hi: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    enable_ai: int = 1
    send_img_resume: int = 0
    filter_dead_hr: int = 1
    dead_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BossBlacklistCreate(BaseModel):
    type: str
    value: str


class BossBlacklistResponse(BaseModel):
    id: int
    type: str
    value: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BossOptionSchema(BaseModel):
    type: str
    name: str
    code: str

    class Config:
        from_attributes = True


class CookieSchema(BaseModel):
    platform: str
    cookie_value: str
    remark: Optional[str] = None

    class Config:
        from_attributes = True


class AiConfigSchema(BaseModel):
    id: Optional[int] = None
    introduce: Optional[str] = None
    prompt: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobProgressEvent(BaseModel):
    type: str = "progress"
    platform: str
    message: str
    current: Optional[int] = None
    total: Optional[int] = None


class LoginStatusEvent(BaseModel):
    type: str = "login"
    platform: str
    is_logged_in: bool
    message: Optional[str] = None


class ApiResponse(BaseModel):
    success: bool
    message: str
    status: Optional[str] = None


class BossDataResponse(BaseModel):
    id: int
    encrypt_id: Optional[str] = None
    encrypt_user_id: Optional[str] = None
    company_name: Optional[str] = None
    job_name: Optional[str] = None
    salary: Optional[str] = None
    delivery_status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BossStatsResponse(BaseModel):
    total: int
    delivered: int
    filtered: int
    pending: int

    class Config:
        from_attributes = True


class LiepinConfigSchema(BaseModel):
    id: Optional[int] = None
    keywords: Optional[str] = None
    city_code: Optional[str] = None
    salary_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LiepinDataResponse(BaseModel):
    id: int
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    comp_name: Optional[str] = None
    job_salary_text: Optional[str] = None
    delivered: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LiepinStatsResponse(BaseModel):
    total: int
    delivered: int
    pending: int

    class Config:
        from_attributes = True


class ZhilianConfigSchema(BaseModel):
    id: Optional[int] = None
    keywords: Optional[str] = None
    city_code: Optional[str] = None
    salary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ZhilianDataResponse(BaseModel):
    id: int
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    salary: Optional[str] = None
    delivered: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ZhilianStatsResponse(BaseModel):
    total: int
    delivered: int
    pending: int

    class Config:
        from_attributes = True


class ZhilianOptionSchema(BaseModel):
    type: str
    name: str
    code: str

    class Config:
        from_attributes = True


class Job51ConfigSchema(BaseModel):
    id: Optional[int] = None
    keywords: Optional[str] = None
    job_area: Optional[str] = None
    salary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Job51DataResponse(BaseModel):
    id: int
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    comp_name: Optional[str] = None
    job_salary_text: Optional[str] = None
    delivered: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Job51StatsResponse(BaseModel):
    total: int
    delivered: int
    pending: int

    class Config:
        from_attributes = True


class Job51OptionSchema(BaseModel):
    type: str
    name: str
    code: str

    class Config:
        from_attributes = True
