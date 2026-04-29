from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class BossConfig(Base):
    __tablename__ = "boss_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    debugger = Column(Integer, default=0)
    wait_time = Column(Integer, default=10)
    keywords = Column(String(500))
    city_code = Column(String(200))
    industry = Column(String(200))
    job_type = Column(String(50))
    experience = Column(String(50))
    degree = Column(String(200))
    salary = Column(String(50))
    scale = Column(String(200))
    stage = Column(String(200))
    say_hi = Column(Text)
    expected_salary_min = Column(Integer)
    expected_salary_max = Column(Integer)
    enable_ai = Column(Integer, default=1)
    send_img_resume = Column(Integer, default=0)
    filter_dead_hr = Column(Integer, default=1)
    dead_status = Column(String(200))
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class BossBlacklist(Base):
    __tablename__ = "boss_blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)
    value = Column(String(200), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class BossData(Base):
    __tablename__ = "boss_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    encrypt_id = Column(String)
    encrypt_user_id = Column(String)
    company_name = Column(String)
    job_name = Column(String)
    salary = Column(String)
    location = Column(String)
    experience = Column(String)
    degree = Column(String)
    hr_name = Column(String)
    hr_position = Column(String)
    hr_active_status = Column(String)
    delivery_status = Column(String)
    job_description = Column(Text)
    job_url = Column(String)
    recruitment_status = Column(String)
    company_address = Column(String)
    industry = Column(String)
    introduce = Column(Text)
    financing_stage = Column(String)
    company_scale = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Cookie(Base):
    __tablename__ = "cookie"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False)
    cookie_value = Column(Text, nullable=False)
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class AiConfig(Base):
    __tablename__ = "ai"

    id = Column(Integer, primary_key=True, autoincrement=True)
    introduce = Column(Text)
    prompt = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class LiepinConfig(Base):
    __tablename__ = "liepin_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keywords = Column(String(500))
    city_code = Column(String(200))
    salary_code = Column(String(200))
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class LiepinData(Base):
    __tablename__ = "liepin_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True)
    job_title = Column(String(200))
    job_link = Column(String(300))
    job_salary_text = Column(String(100))
    job_area = Column(String(100))
    job_edu_req = Column(String(50))
    job_exp_req = Column(String(50))
    job_publish_time = Column(String(50))
    comp_id = Column(String(64))
    comp_name = Column(String(200))
    comp_industry = Column(String(100))
    comp_scale = Column(String(50))
    hr_id = Column(String(64))
    hr_name = Column(String(50))
    hr_title = Column(String(100))
    hr_im_id = Column(String(64))
    delivered = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class LiepinOption(Base):
    __tablename__ = "liepin_option"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    sort_order = Column(Integer)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class BossOption(Base):
    __tablename__ = "boss_option"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    sort_order = Column(Integer)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class ZhilianConfig(Base):
    __tablename__ = "zhilian_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keywords = Column(String(500))
    city_code = Column(String(200))
    salary = Column(String(200))
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class ZhilianData(Base):
    __tablename__ = "zhilian_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True)
    job_title = Column(String(200))
    job_link = Column(String(300))
    salary = Column(String(100))
    location = Column(String(100))
    experience = Column(String(50))
    degree = Column(String(50))
    company_name = Column(String(200))
    company_tag = Column(String(200))
    delivered = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class ZhilianOption(Base):
    __tablename__ = "zhilian_option"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    sort_order = Column(Integer)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class Job51Config(Base):
    __tablename__ = "job51_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keywords = Column(String(500))
    job_area = Column(String(200))
    salary = Column(String(200))
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class Job51Data(Base):
    __tablename__ = "job51_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True)
    job_title = Column(String(200))
    job_link = Column(String(300))
    job_salary_text = Column(String(100))
    job_area = Column(String(100))
    job_edu_req = Column(String(50))
    job_exp_req = Column(String(50))
    job_publish_time = Column(String(50))
    comp_id = Column(String(64))
    comp_name = Column(String(200))
    comp_industry = Column(String(100))
    comp_scale = Column(String(50))
    hr_id = Column(String(64))
    hr_name = Column(String(50))
    hr_title = Column(String(100))
    delivered = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class Job51Option(Base):
    __tablename__ = "job51_option"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    sort_order = Column(Integer)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True)
    config_value = Column(Text)
    config_type = Column(String(50), default="string")
    category = Column(String(50), default="general")
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
