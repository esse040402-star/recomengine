"""Versioned factual vocabulary; aliases merge, absent evidence stays unknown."""
import re

VERSION = 'game-facts-1.0.0'
GROUPS = {
 'genre:action':['Action','액션'], 'genre:adventure':['Adventure','어드벤처'],
 'genre:rpg':['RPG','Role-playing (RPG)','Role Playing','롤 플레잉'],
 'genre:strategy':['Strategy','전략'], 'genre:simulation':['Simulator','Simulation','시뮬레이션'],
 'genre:shooter':['Shooter','슈팅'], 'tag:puzzle':['Puzzle','퍼즐'],
 'tag:story_rich':['Story Rich','스토리 풍부'], 'tag:open_world':['Open World','오픈 월드','오픈월드'],
 'tag:building':['Building','건설','City Builder','도시 건설'],
 'tag:realistic':['Realistic','현실적'], 'tag:anime':['Anime','애니'],
 'tag:pixel_graphics':['Pixel Graphics','픽셀 그래픽'], 'tag:cute':['Cute','귀여운'],
 'tag:turn_based':['Turn-Based','Turn based','Turn-based strategy (TBS)','턴제'],
 'tag:point_and_click':['Point-and-click','Point & Click','포인트 앤 클릭'],
 'tag:difficult':['Difficult','어려운'], 'tag:grindy':['Grindy','노가다'],
 'category:single_player':['Singleplayer','Single player','싱글 플레이어'],
 'category:co_op':['Co-op','Co-operative','Online Co-op','협동','온라인 협동'],
 'category:multiplayer':['Multiplayer','Multi-player','멀티플레이어'],
 'category:pvp':['PvP','Online PvP','온라인 PvP'],
 'perspective:first_person':['First person','First-Person','1인칭'],
 'perspective:third_person':['Third person','Third-Person','3인칭'],
 'tag:3d':['3D'], 'tag:2d':['2D'],
}
def key(s): return re.sub(r'[^\w]+','',s.casefold())
ALIASES={key(s):code for code, names in GROUPS.items() for s in names}
CATEGORY_IDS={2:'category:single_player',1:'category:multiplayer',9:'category:co_op',38:'category:co_op',39:'category:co_op',49:'category:pvp',36:'category:pvp',37:'category:pvp'}

def normalize(payload):
    steam=payload.get('steam') or {}
    igdb=payload.get('igdb') or {}
    game=(igdb.get('game') or {}) if igdb.get('status')=='ok' else {}
    evidence={}; unmapped=[]
    def add(code,source,value):
        item={'source':source,'value':value}
        if item not in evidence.setdefault(code,[]): evidence[code].append(item)
    def named(value,source):
        code=ALIASES.get(key(value))
        if code: add(code,source,value)
        else: unmapped.append({'source':source,'value':value})
    for row in steam.get('genres',[]): named(row['description'],'steam.genres')
    for row in steam.get('categories',[]):
        code=CATEGORY_IDS.get(row['id'])
        if code: add(code,'steam.categories',row['description'])
    for value in (payload.get('steam_tags') or {}).get('values',[]): named(value,'steam.store_tags')
    for field in ('genres','themes','keywords','game_modes','player_perspectives'):
        for row in game.get(field,[]): named(row['name'],'igdb.'+field)
    platforms=set()
    if any(steam.get('platforms',{}).values()): platforms.add('pc')
    for row in game.get('platforms',[]):
        name=row['name'].lower()
        if name in ('pc (microsoft windows)','linux','mac'): platforms.add('pc')
        elif any(s in name for s in ('playstation','xbox','nintendo','wii','gamecube')): platforms.add('console')
        elif name in ('android','ios'): platforms.add('mobile')
    supported=platforms & {'pc','console'}
    price=steam.get('price_overview') or {}
    times=igdb.get('time_to_beat_seconds') or []
    return {'schema_version':VERSION,'appid':payload.get('appid'),'name':steam.get('name') or game.get('name'),
        'codes':sorted(evidence),'evidence':evidence,'unmapped':unmapped,
        'platforms':sorted(supported),'excluded_platforms':sorted(platforms- supported),
        'recommendable':bool(supported) and steam.get('type')=='game',
        'price':{'currency':price.get('currency'),'amount':price['final']/100 if 'final' in price else (0 if steam.get('is_free') else None),'source':'steam'},
        'requirements':steam.get('pc_requirements') or {},
        'completion_hours':[{k:(v/3600 if k in ('hastily','normally','completely') else v) for k,v in t.items()} for t in times],
        'session_minutes':None,'hardware_tier':None,
        'ratings':{'igdb_user':game.get('rating'),'igdb_total':game.get('total_rating'),'steam_reviews':(payload.get('reviews') or {}).get('query_summary')},
        'source_status':{'steam':'ok' if steam else 'missing','igdb':igdb.get('status','missing')},
        'unknown_fields':['session_minutes','hardware_tier','motion_intensity','monetization_pressure','complexity']}
