import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import pytest
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '기존프로젝트'))

@pytest.fixture(params=['기존프로젝트', '새작업물/스팀ID_게임태그조회'])
def steam(request):
    spec = importlib.util.spec_from_file_location('review_service', ROOT / request.param / 'app/services/steam.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_contract(steam, monkeypatch):
    calls=[]
    async def get(url, params, timeout=15):
        calls.append(json.loads(params['input_json']))
        assert url.endswith('/IUserReviewsService/GetAppReviews/v1/')
        return {'response': {'query_summary': {'total_positive': 8, 'total_negative': 2, 'total_reviews': 10},
                             'reviews': [{'review': '좋아요', 'voted_up': True, 'recommendationid': '1'}], 'cursor': 'next+/='}}
    monkeypatch.setattr(steam,'_get_json',get)
    assert asyncio.run(steam.fetch_reviews(1174180)) == [{'text':'좋아요','voted_up':True}]
    assert asyncio.run(steam.fetch_review_summary(1174180))['total'] == 10
    page=asyncio.run(steam.fetch_review_page(1174180, sentiment='negative', language='koreana', cursor='next+/='))
    assert page['items'][0]['text']=='좋아요'
    assert calls[-1]['cursor']=='next+/='
    assert calls[-1]['review_type']==2 and calls[-1]['filter']==1
    assert calls[-1]['languages']==['koreana'] and calls[-1]['purchase_type']==1

@pytest.mark.parametrize('response', [{}, {'response': {}}, {'response': {'reviews': 'bad'}}])
def test_invalid_not_empty(steam, monkeypatch, response):
    async def get(*args, **kwargs): return response
    monkeypatch.setattr(steam,'_get_json',get)
    with pytest.raises(ValueError): asyncio.run(steam.fetch_reviews(1))

def test_empty_is_valid(steam,monkeypatch):
    async def get(*args,**kwargs): return {'response':{'query_summary':{'total_reviews':0},'reviews':[]}}
    monkeypatch.setattr(steam,'_get_json',get)
    assert asyncio.run(steam.fetch_reviews(1))==[]
    assert asyncio.run(steam.fetch_review_summary(1))['total']==0
