from .scoring import VERSION,calculate

def evaluate(payload):
    if not isinstance(payload,dict) or set(payload)!={'survey_id','version','answers'}:raise ValueError('요청 형식 오류')
    sid=payload['survey_id']
    types={f'{kind}_{track}':(track,stage) for kind,stage in [('quick','onboarding'),('profile','profile')] for track in ('gamer','nongamer')}
    if sid not in types or payload['version']!=VERSION:raise ValueError('설문 버전 오류. 새로 시작해주세요.')
    track,stage=types[sid];result=calculate(track,payload['answers'],stage)
    from .cloud import recommend
    result['recommendation']=recommend(result['weights'],result['constraints'])
    return {**payload,**result}
