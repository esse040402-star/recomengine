"""Team survey 1e186d7: immutable question IDs, server-side evidence weights."""
import json
from pathlib import Path
from collections import defaultdict
from .normalization import GROUPS
VERSION='team-survey-2.0.0'
QUESTIONS=json.loads((Path(__file__).parent/'data/team_questions.json').read_text(encoding='utf-8'))
# Each row follows the team file's option order. Blank entries are stored, not inferred.
QUICK_G={3:['genre:action','genre:strategy tag:puzzle','tag:story_rich','tag:open_world','genre:simulation tag:building',''],4:['category:single_player','category:co_op','category:pvp',''],5:['genre:action','tag:turn_based','tag:point_and_click',''],6:['-tag:3d','-tag:grindy','','-tag:puzzle','-category:pvp',''],7:['tag:realistic','tag:anime','tag:pixel_graphics','tag:cute','']}
QUICK_N={3:['genre:action','tag:story_rich','tag:open_world','genre:simulation tag:building','genre:strategy tag:puzzle',''],4:QUICK_G[4],5:['genre:action','tag:point_and_click','tag:turn_based','',''],6:['-tag:puzzle','-tag:difficult','','-tag:3d','-tag:horror -tag:gore',''],7:QUICK_G[7]}
PROFILE_G={
3:['genre:rpg genre:adventure','genre:action tag:souls_like','genre:shooter','genre:strategy genre:simulation','tag:roguelike tag:puzzle','tag:building tag:relaxing',''],
4:['-tag:difficult','','tag:difficult',''],5:['tag:realistic','tag:pixel_graphics','tag:anime','',''],
6:['tag:difficult','genre:action','','tag:turn_based'],7:['genre:action','','tag:destruction','',''],
8:['perspective:first_person','perspective:third_person','perspective:top_down','tag:side_scroller',''],
9:['tag:turn_based genre:simulation','genre:rpg','genre:action',''],10:['genre:rpg','genre:rpg','genre:rpg','tag:character_customization','tag:difficult'],
11:['','','','','','category:single_player'],12:['category:pvp','category:pvp category:co_op','tag:competitive','','category:single_player category:co_op -category:pvp'],
13:['category:co_op','category:multiplayer','category:co_op','category:co_op','category:single_player'],14:['tag:open_world','tag:exploration','tag:exploration','',''],
15:['tag:character_customization','tag:character_customization','tag:building','genre:rpg',''],
17:['tag:realistic','tag:pixel_graphics','tag:anime','',''],18:['tag:difficult','tag:difficult','genre:strategy','-tag:difficult',''],
19:['tag:exploration','tag:collectathon','','tag:multiple_endings','tag:story_rich'],20:['tag:fantasy','tag:sci_fi tag:cyberpunk','tag:post_apocalyptic','tag:dark_fantasy tag:mystery','tag:historical tag:military',''],
21:['tag:cinematic tag:story_rich','tag:choices_matter','tag:exploration tag:story_rich','tag:visual_novel',''],
23:['','','tag:idle',''],24:['','','',''],26:['-tag:open_world','','-tag:difficult','-tag:grindy','',''],
28:['-tag:difficult','','-tag:grindy','-tag:horror -tag:gore',''],29:['tag:story_rich','tag:difficult','tag:relaxing','category:co_op','tag:exploration'],
30:['tag:collectathon','tag:difficult','tag:multiple_endings','','','']}
PROFILE_N={
3:['category:single_player','category:co_op','category:pvp','',''],4:['tag:point_and_click','tag:turn_based','genre:action','tag:idle',''],
5:['tag:cute','tag:realistic','tag:anime','tag:pixel_graphics','',''],
7:['tag:relaxing','tag:building','tag:puzzle','tag:collectathon',''],8:['tag:point_and_click','','','tag:turn_based',''],
9:['tag:puzzle','tag:building','genre:strategy','tag:relaxing',''],10:['tag:relaxing tag:story_rich','tag:choices_matter','tag:mystery','tag:story_rich',''],
11:['tag:relaxing','','genre:action',''],12:['tag:building','tag:farming','tag:building tag:sci_fi','tag:building',''],
13:['tag:hidden_object','tag:word_game','tag:puzzle','tag:casual','tag:puzzle'],14:['tag:cute','tag:cute','tag:fantasy','',''],
15:['tag:idle','tag:point_and_click','genre:action',''],16:['','tag:pixel_graphics','tag:2d','tag:realistic',''],
17:['category:single_player -category:pvp','category:pvp','tag:competitive','',''],18:['-tag:difficult','','tag:difficult',''],
19:['category:multiplayer','category:co_op','category:co_op','category:single_player',''],21:['tag:nature','tag:relaxing','tag:space','',''],
22:['tag:character_customization','tag:building','tag:collectathon','genre:simulation',''],23:['tag:destruction','tag:relaxing','tag:farming','tag:puzzle',''],
26:['-tag:visual_novel','','tag:visual_novel','tag:cinematic'],27:['','genre:simulation','','tag:relaxing',''],28:['-tag:horror','','','-tag:difficult',''],
29:['tag:relaxing','','tag:casual','tag:exploration','category:multiplayer'],30:['tag:collectathon','tag:multiple_endings','','','']}
RULES={('gamer','onboarding'):QUICK_G,('nongamer','onboarding'):QUICK_N,('gamer','profile'):PROFILE_G,('nongamer','profile'):PROFILE_N}

def rows(track,stage):
    if track not in ('gamer','nongamer') or stage not in ('onboarding','profile'):raise ValueError('설문 종류 오류')
    return [q for q in QUESTIONS if q['track']==track and q['stage']==stage]

def limit(q):
    t=q['select_type']
    if t=='SINGLE':return 1
    if t.startswith('MULTI_MAX_'):return int(t.rsplit('_',1)[1])
    return len(q['options'])

def neutral(label):return any(x in label for x in ('상관없','선호하는 스타일 없음','잘 모르','피하고 싶은 요소가 없','싫어하는 요소가 없','피하고 싶은 요소 없음','싫어하는 요소 없음','불편한 화면 연출 없음'))

def definition(track,stage='onboarding'):
    return {'survey_id':('quick_' if stage=='onboarding' else 'profile_')+track,'version':VERSION,
      'questions':[{'id':q['id'],'title':q['question_text'],'max':limit(q),'field':q['category'] or 'preference',
      'options':[{'id':str(i),'label':label,'prefs':{'none':neutral(label)}} for i,label in enumerate(q['options'])]} for q in rows(track,stage)]}

def calculate(track,answers,stage='onboarding'):
    qs=rows(track,stage)
    if not isinstance(answers,dict) or set(answers)!={q['id'] for q in qs}:raise ValueError('모든 문항에 답해주세요.')
    weights=defaultdict(float);audit=[];platforms=[]
    for q in qs:
        selected=answers[q['id']]
        if not isinstance(selected,list) or not 1<=len(selected)<=limit(q) or any(type(i)!=str for i in selected) or len(set(selected))!=len(selected):raise ValueError('선택 개수 오류')
        if any(i not in [str(n) for n in range(len(q['options']))] for i in selected):raise ValueError('선택지 오류')
        if len(selected)>1 and any(neutral(q['options'][int(i)]) for i in selected):raise ValueError('상관없음/없음은 단독 선택해주세요.')
        for value in selected:
            i=int(value);label=q['options'][i];codes=RULES[(track,stage)].get(q['question_no'],[])
            tokens=codes[i].split() if i<len(codes) else []
            applied={};mapping_type="unavailable"
            if q['question_no']==1:
                platforms+= {0:['pc'],1:['console'],2:['pc'],3:['pc','console']}.get(i,[])
                mapping_type='constraint'
                reason='기기 필터. 휴대용 PC는 PC 후보이며 기종별 호환성은 별도 확인 필요.'
            elif tokens:
                mapping_type='direct' if all(any(alias.casefold() in label.casefold() for alias in GROUPS[token.lstrip('-')]) for token in tokens) else 'approximate'
                confidence=1 if mapping_type=='direct' else 0.5
                # Approximate links get half weight; split the answer budget across labels.
                for token in tokens:
                    code=token.lstrip('-');w=(-1 if token.startswith('-') else 1)*6*confidence/len(tokens)/len(selected)
                    applied[code]=round(w,3);weights[code]+=w
                reason=('직접 대응: 선택 문구와 API 분류가 일치합니다.' if mapping_type=='direct' else '근접 대응: 활동 선호를 관련 태그로 해석하여 기본 가중치의 50%만 적용합니다.')+' 실제 API 근거가 있는 게임에만 반영합니다.'
            else:reason='중립 응답 또는 직접 검증할 API 필드 없음. 응답은 저장하고 추천 점수에는 미반영.'
            audit.append({'question_id':q['id'],'question':q['question_text'],'option_id':value,'answer':label,'weights':applied,'mapping_type':mapping_type,'reason':reason})
    weights={k:round(v,3) for k,v in weights.items() if v}
    positives=sorted(((k,v) for k,v in weights.items() if v>0),key=lambda x:-x[1])
    labels=[GROUPS.get(k,[k])[0] for k,v in positives[:3]]
    return {'weights':weights,'constraints':{'platforms':sorted(set(platforms))},'mapping_audit':audit,
      'summary':{'title':' · '.join(labels) or '열린 취향 탐색형','count':len(qs),'track':track,'stage':stage,'evidence':audit},
      'unapplied_answers':[a for a in audit if not a['weights'] and not a['question_id'].endswith('_01')]}
