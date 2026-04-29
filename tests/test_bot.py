import pytest
from app.worker.bot import build_search_url, decode_salary, parse_salary_range, is_salary_not_expected


class TestBuildSearchUrl:
    def test_basic_url(self):
        config = {
            "city_code": "101010100",
            "job_type": "100101",
            "salary": "404",
            "experience": "101,102",
            "degree": "204",
        }
        url = build_search_url(config)
        assert "https://www.zhipin.com/web/geek/jobs" in url
        assert "city=101010100" in url
        assert "experience=101%2C102" in url


class TestSalaryParsing:
    def test_parse_salary_range(self):
        assert parse_salary_range("15-25K") == [15, 25]
        assert parse_salary_range("20K") == [20]
        assert parse_salary_range("12-18K·14薪") == [12, 18]  # 带薪数后缀

    def test_is_salary_not_expected(self):
        assert is_salary_not_expected("10-15K", [15, 25]) is True   # 上限低于期望下限
        assert is_salary_not_expected("20-30K", [15, 25]) is False  # 符合


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
