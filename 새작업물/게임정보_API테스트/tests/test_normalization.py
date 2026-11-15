import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from normalization import normalize
from main import app
from fastapi.testclient import TestClient
import main as m

def fixture():
 return {'appid':42,'steam':{'name':'Game','type':'game','platforms':{'windows':True},'genres':[{'description':'액션'}],'categories':[{'id':2,'description':'싱글 플레이어'}]},'steam_tags':{'values':['Open World','Singleplayer','Action']},'igdb':{'status':'ok','game':{'themes':[{'name':'Open world'}],'genres':[{'name':'Action'}],'game_modes':[{'name':'Single player'},{'name':'Multiplayer'}]},'time_to_beat_seconds':[{'normally':36000,'count':2}]}}

def test_aliases_dedupe_and_provenance():
 p=fixture(); old=copy.deepcopy(p);n=normalize(p)
 assert n['codes'].count('tag:open_world')==1
 assert len(n['evidence']['tag:open_world'])==2
 assert 'category:pvp' not in n['codes']
 assert p==old

def test_semantic_separation():
 n=normalize(fixture())
 assert n['completion_hours'][0]['normally']==10
 assert n['session_minutes'] is None and n['hardware_tier'] is None
 assert n['price']['amount'] is None

def test_mobile_only_excluded_cross_platform_kept():
 p=fixture();p['steam']['platforms']={};p['igdb']['game']['platforms']=[{'name':'Android'}]
 assert not normalize(p)['recommendable']
 p['steam']['platforms']={'windows':True}
 assert normalize(p)['recommendable'] and normalize(p)['platforms']==['pc']

def test_api_unavailable_igdb_not_fabricated():
 p=fixture();p['igdb']={'status':'error'};n=normalize(p)
 assert n['source_status']['igdb']=='error'
 assert n['completion_hours']==[]

def test_survey_api_to_ranking(monkeypatch):
 c=TestClient(app);d=c.get('/api/surveys/quick/gamer').json()
 assert all('모바일' not in o['label'] for q in d['questions'] for o in q['options'])
 def game(appid):
  p=fixture();p['appid']=appid
  if appid==43:p['steam_tags']['values']=[];p['igdb']['game']['themes']=[]
  p['normalized']=normalize(p);return p
 monkeypatch.setattr(m,'detail',game)
 body={'track':'gamer','version':d['version'],'answers':{'q1':['0'],'q2':['3'],'q3':['3'],'q4':['0'],'q5':['2'],'q6':['5'],'q7':['4']},'appids':[43,42]}
 r=c.post('/api/surveys/quick/recommend',json=body)
 assert r.status_code==200
 games=r.json()['recommendation']['games'];assert games[0]['app_id']==42
 assert games[0]['matched_weights']['tag:open_world']==10
 assert len(games[0]['match_evidence']['tag:open_world'])==2
 body['answers']['q1']=['2']
 assert c.post('/api/surveys/quick/recommend',json=body).status_code==422

def test_version_and_invalid_track():
 c=TestClient(app)
 assert c.get('/api/surveys/quick/invalid').status_code==422
