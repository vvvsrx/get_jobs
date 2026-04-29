import pytest
from app.worker.liepin_bot import LiepinBot, _build_search_url, _parse_search_response


class TestBuildSearchUrl:
    def test_basic_url(self):
        url = _build_search_url(city_code="410", salary_code="$20$30")
        assert "https://www.liepin.com/zhaopin/" in url
        assert "city=410" in url
        assert "dq=410" in url
        assert "salary=%2420%2430" in url

    def test_empty_params(self):
        url = _build_search_url()
        assert url == "https://www.liepin.com/zhaopin/"


class TestParseSearchResponse:
    def test_parse_nested_data(self):
        import json
        raw = json.dumps({
            "data": {
                "data": {
                    "jobCardList": [
                        {
                            "job": {"jobId": "123", "title": "Java", "salary": "20K", "dq": "北京"},
                            "comp": {"compId": "456", "compName": "ABC", "compIndustry": "互联网"},
                            "recruiter": {"recruiterId": "789", "recruiterName": "张三"}
                        }
                    ]
                }
            }
        })
        jobs = _parse_search_response(raw)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "123"
        assert jobs[0]["job_title"] == "Java"
        assert jobs[0]["comp_name"] == "ABC"
        assert jobs[0]["hr_name"] == "张三"

    def test_parse_flat_data(self):
        import json
        raw = json.dumps({
            "data": {
                "jobCardList": [
                    {
                        "job": {"jobId": "456", "title": "Python"},
                        "comp": {"compName": "XYZ"},
                        "recruiter": {"recruiterName": "李四"}
                    }
                ]
            }
        })
        jobs = _parse_search_response(raw)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "456"

    def test_empty_response(self):
        jobs = _parse_search_response('{}')
        assert jobs == []

    def test_invalid_json(self):
        jobs = _parse_search_response('not json')
        assert jobs == []
