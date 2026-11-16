"""Render data bridge: no API key and no invented metadata."""
import json, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE='https://recomengine-game-api.onrender.com'
LOCK=threading.RLock()
ROWS={}
STATE={'running':False,'done':0,'total':0,'failed':[]}
GENRES={'1':'genre:action','2':'genre:strategy','25':'genre:adventure','28':'genre:simulation'}
TAGS={'Action':'tag:action','Puzzle':'tag:puzzle','Story Rich':'tag:story_rich','Open World':'tag:open_world','Building':'tag:building','Realistic':'tag:realistic','Anime':'tag:anime','Pixel Graphics':'tag:pixel_graphics','Cute':'tag:cute','Difficult':'tag:difficult','Grindy':'tag:grindy','Turn-Based':'tag:turn_based','Turn-Based Combat':'tag:turn_based','Point & Click':'tag:point_and_click'}
CATS={'2':'category:single_player','9':'category:co_op','38':'category:co_op','39':'category:co_op','49':'category:pvp','36':'category:pvp','37':'category:pvp'}
SUPPORTED=set(GENRES.values())|set(TAGS.values())|set(CATS.values())

def fetch(appid):
    with urlopen(BASE+'/api/games/'+str(appid),timeout=100) as response:
        body=json.load(response)
    if body.get('appid')!=appid or body.get('steam',{}).get('steam_appid')!=appid:
        raise ValueError('게임 ID 불일치')
    return {'fetched_at':time.time(),'data':body}

def snapshot():
    with LOCK:return {**STATE,'failed':list(STATE['failed']),'available':len(ROWS),'base_url':BASE}

def start():
    with LOCK:
        if STATE['running']:return
        ids=json.loads((ROOT/'candidate_appids.json').read_text(encoding='utf-8'))
        ids=list(dict.fromkeys(int(x) for x in ids if int(x)>0))
        STATE.update(running=True,done=0,total=len(ids),failed=[])
    def work():
        def one(appid):
            file=ROOT/'cache'/f'{appid}.json'
            try:
                cached=json.loads(file.read_text(encoding='utf-8')) if file.exists() else None
                row=cached if cached and time.time()-cached['fetched_at']<3600 else fetch(appid)
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(json.dumps(row,ensure_ascii=False),encoding='utf-8')
                with LOCK:ROWS[appid]=row
            except Exception as e:
                with LOCK:STATE['failed'].append({'appid':appid,'error':type(e).__name__})
            finally:
                with LOCK:STATE['done']+=1
        try:
            with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(one,ids))
        finally:
            with LOCK:STATE['running']=False
    threading.Thread(target=work,daemon=True).start()

def evidence(body):
    from .normalization import normalize
    return normalize(body)['evidence']

def recommend(weights,constraints):
    from .normalization import normalize, GROUPS
    with LOCK:rows=list(ROWS.values());state=snapshot()
    games=[]
    for row in rows:
        body=row['data'];facts=normalize(body);steam=body.get('steam') or {}
        if not facts['recommendable']:continue
        platforms=constraints.get('platforms',[])
        if platforms and not set(platforms)&set(facts['platforms']):continue
        hits={k:v for k,v in weights.items() if k in facts['codes'] and v}
        score=round(sum(hits.values()),3)
        if score<=0:continue
        budget=sum(v for v in weights.values() if v>0)
        games.append({'app_id':body['appid'],'title':steam['name'],'score':score,
          'match_percent':round(max(0,score)/budget*100) if budget else 0,'matched_weights':hits,
          'evidence':{k:facts['evidence'][k] for k in hits},'header_image':steam.get('header_image'),
          'price':facts['price'],'requirements':facts['requirements'],'platforms':facts['platforms'],
          'fetched_at':row['fetched_at'],'detail_source':BASE,'store_url':f"https://store.steampowered.com/app/{body['appid']}/"})
    games.sort(key=lambda x:(-x['score'],x['app_id']))
    return {'status':'matched' if games else 'no_match' if rows else 'loading' if state['running'] else 'unavailable',
      'games':games[:5],'collection':state,'candidate_scope':'테스트 후보 중 실제 API 조회에 성공한 게임. Steam 전체 게임의 추천 순위가 아닙니다.',
      'unmapped_weights':{k:v for k,v in weights.items() if k not in GROUPS},
      'notes':['Steam·IGDB 원본을 공통 분류로 변환하고 중복 근거는 한 번만 점수에 반영합니다.',
      '모바일 전용 게임은 제외하고 PC·콘솔 동시 지원 게임은 유지합니다.',
      '세션 시간·주간 이용시간·UI 불편함 등 검증할 API 필드가 없는 응답은 프로필에 저장하고 점수에는 반영하지 않습니다.',
      '휴대용 PC는 PC 후보로 비교하며 기기별 호환성은 보장하지 않습니다. 일치율은 추천 정확도가 아닌 선택 가중치 충족 비율입니다.']}
