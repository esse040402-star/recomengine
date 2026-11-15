"""Match survey codes against Steam metadata and the team's curated labels."""
import json
from pathlib import Path

SEED = Path(__file__).parent / 'data/catalog.json'
CACHE = SEED.parents[2] / 'results/steam_details_cache.json'
def recommend(weights, constraints, rows=None, updates=None):
    """Only fetched normalized facts participate. Unknown fields never earn points."""
    if rows is None: rows=json.loads(SEED.read_text(encoding='utf-8'))
    if updates is None:
        updates=json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}
    candidates=[]; available=0
    for g in rows:
        live=updates.get(g['id']) or {}
        n=live.get('normalized') or {}
        if n.get('schema_version')!='game-facts-1.0.0' or not n.get('recommendable'):continue
        available+=1
        requested=set(constraints.get('platforms',[]))
        # UMPC compatibility is not implied by Windows support.
        if requested and not requested.intersection(n['platforms']):continue
        codes=set(n['codes'])
        hits={k:v for k,v in weights.items() if k in codes and v}
        score=sum(hits.values())
        if score<=0:continue
        candidates.append(dict(app_id=g['app'],game_id=g['id'],title=n['name'],score=score,
            matched_weights=hits, match_evidence={k:n['evidence'][k] for k in hits},
            unmatched_weights={k:v for k,v in weights.items() if k not in codes and v},
            price=n['price'],detail_source='steam_igdb_normalized',
            source_status=n['source_status']))
    candidates.sort(key=lambda g:(-g['score'],g['app_id']))
    unsupported=[k for k in weights if k.startswith(('session:','hardware:','preference:'))]
    return {'status':'matched' if candidates else ('data_required' if not available else 'no_match'),
            'games':candidates[:5],'fetched_candidates':available,'candidate_pool_size':len(rows),
            'unsupported_weights':unsupported,
            'warnings':['UMPC 호환성은 현재 API 응답으로 검증되지 않습니다.'] if 'umpc' in constraints.get('platforms',[]) else []}
