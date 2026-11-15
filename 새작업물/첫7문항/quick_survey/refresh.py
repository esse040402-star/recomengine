"""Refresh the local snapshot through the team backend, without survey or account data."""
import argparse
import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError
from .steam import CACHE, SEED
from .__main__ import write_json

def fetch(base, game_id):
    url=base.rstrip('/')+'/api/steam/details?'+urlencode({'game':game_id})
    with urlopen(url,timeout=25) as response:
        d=json.load(response)['details']
    if not isinstance(d,dict) or not isinstance(d.get('os'),dict) or not isinstance(d.get('minimum'),list):
        raise ValueError('게임 상세 응답 형식 오류')
    return {k:d[k] for k in ('os','minimum','price','checkedAt','genres','categoryIds') if k in d}

def fetch_normalized(base, appid):
    url=base.rstrip('/')+'/api/games/'+str(int(appid))
    with urlopen(url,timeout=90) as response:
        data=json.load(response)
    n=data.get('normalized') or {}
    if n.get('schema_version')!='game-facts-1.0.0' or n.get('appid')!=int(appid):
        raise ValueError('통합 API 배포 또는 응답 AppID를 확인해주세요.')
    return {'normalized':n}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--base',default='https://recomengine-game-api.onrender.com')
    p.add_argument('games',nargs='*',help='프로젝트 게임 ID. 생략 시 전체.')
    args=p.parse_args()
    rows=json.loads(SEED.read_text(encoding='utf-8')); ids=[g['id'] for g in rows]; apps={g['id']:g['app'] for g in rows}
    if set(args.games)-set(ids):p.error('알 수 없는 게임 ID')
    cache=json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}
    failed=ok=0
    for game in args.games or ids:
        try:cache[game]=fetch_normalized(args.base,apps[game])
        except (OSError,URLError,ValueError,KeyError) as exc:
            failed+=1;print(game,'갱신 실패:',exc)
            if isinstance(exc,URLError) and isinstance(exc.reason,ConnectionRefusedError):break
        else:ok+=1
    if ok:write_json(CACHE,cache)
    print('갱신:',ok,'실패:',failed)
    return int(bool(failed))

if __name__=='__main__':raise SystemExit(main())
