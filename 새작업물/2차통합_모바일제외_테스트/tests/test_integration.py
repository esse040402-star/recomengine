import json, tempfile, unittest, threading, http.client, copy
from pathlib import Path
from uuid import uuid4
from quick_survey.scoring import definition, calculate, QUESTIONS, RULES, VERSION
from quick_survey.normalization import normalize, GROUPS
from quick_survey import cloud
from quick_survey.local_web import create_server

class Rules(unittest.TestCase):
 def test_team_questions_and_every_option(self):
  for track in ('gamer','nongamer'):
   for stage,count in [('onboarding',7),('profile',30)]:
    d=definition(track,stage);self.assertEqual(len(d['questions']),count)
    answers={q['id']:[q['options'][0]['id']] for q in d['questions']}
    for q in d['questions']:
     self.assertNotIn('모바일',q['title']+' '.join(o['label'] for o in q['options']))
     for o in q['options']:
      a=copy.deepcopy(answers);a[q['id']]=[o['id']];result=calculate(track,a,stage)
      self.assertEqual(result['summary']['count'],count)
      self.assertTrue(set(result['weights'])<=set(GROUPS))
      self.assertEqual(len(result['mapping_audit']),count)
    for q in (q for q in QUESTIONS if q['track']==track and q['stage']==stage):
     row=RULES[(track,stage)].get(q['question_no'])
     if row:self.assertEqual(len(row),len(q['options']))
 def test_invalid_answers_and_neutral(self):
  d=definition('gamer');a={q['id']:['0'] for q in d['questions']}
  for bad in [['0','4'],['0','0'],['999'],[],[True]]:
   b=copy.deepcopy(a);b['G_ONB_01']=bad
   with self.assertRaises(ValueError):calculate('gamer',b)
  b=copy.deepcopy(a);b.pop('G_ONB_07')
  with self.assertRaises(ValueError):calculate('gamer',b)
 def test_synonyms_mobile_and_duplicate_evidence(self):
  body={'appid':1,'steam':{'name':'test','type':'game','platforms':{'windows':True},'genres':[{'description':'Action'}]},'steam_tags':{'values':['Action']},'igdb':{'status':'ok','game':{'genres':[{'name':'Action'}],'platforms':[{'name':'Android'}]}}}
  n=normalize(body);self.assertEqual(n['codes'],['genre:action']);self.assertTrue(n['recommendable']);self.assertEqual(n['excluded_platforms'],['mobile'])
  body['steam']['platforms']={};self.assertFalse(normalize(body)['recommendable'])
  body['steam']['type']='dlc';self.assertFalse(normalize(body)['recommendable'])
 def test_score_uses_actual_evidence_only(self):
  old=cloud.ROWS.copy();cloud.ROWS.clear()
  body={'appid':1,'steam':{'name':'test','type':'game','platforms':{'windows':True},'genres':[{'description':'Action'}]},'steam_tags':{'values':['Action']},'igdb':{'status':'ok','game':{'genres':[{'name':'Action'}]}}}
  try:
   cloud.ROWS[1]={'data':body,'fetched_at':1}
   r=cloud.recommend({'genre:action':6,'tag:story_rich':6},{})
   self.assertEqual(r['games'][0]['score'],6);self.assertEqual(r['games'][0]['match_percent'],50)
   self.assertEqual(cloud.recommend({'genre:action':6},{'platforms':['console']})['games'],[])
  finally:cloud.ROWS.clear();cloud.ROWS.update(old)

class Flow(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.start();self.cookies={}
  self.old=cloud.ROWS.copy();cloud.ROWS.clear()
  cloud.ROWS[1]={'data':{'appid':1,'steam':{'name':'test','type':'game','platforms':{'windows':True},'genres':[{'description':'Action'}]}},'fetched_at':1}
 def start(self):
  self.server=create_server(directory=self.temp.name);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):
  self.server.shutdown();self.thread.join();self.server.server_close();self.temp.cleanup();cloud.ROWS.clear();cloud.ROWS.update(self.old)
 def call(self,path,p=None,expect=200):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
  c.request('POST' if p is not None else 'GET',path,json.dumps(p) if p is not None else None,{'Content-Type':'application/json','Cookie':'; '.join(k+'='+v for k,v in self.cookies.items())})
  r=c.getresponse()
  for k,v in r.getheaders():
   if k.lower()=='set-cookie':
    pair=v.split(';')[0];name,value=pair.split('=',1);self.cookies[name]=value
  body=r.read().decode();self.assertEqual(r.status,expect,body);c.close()
  return json.loads(body) if body.startswith(('{','[')) else body
 def submit(self,track,kind):
  d=self.call('/api/'+kind+'-survey/definitions/'+track)
  p={'survey_id':d['survey_id'],'version':d['version'],'submission_id':str(uuid4()),'answers':{q['id']:['0'] for q in d['questions']}}
  result=self.call('/api/'+kind+'-survey/submissions',p)
  self.assertEqual(self.call('/api/'+kind+'-survey/submissions',p)['result_id'],result['result_id'])
  return result
 def test_guest_signup_both_surveys_profile_reload_isolation(self):
  self.call('/api/personal');quick=self.submit('gamer','quick')
  before=self.call('/api/personal');self.assertEqual(before['profiles'][0]['weights'],quick['weights'])
  self.call('/api/account/signup',{'name':'테스트','email':'flow@example.com','password':'test-password'})
  self.assertEqual(len(self.call('/api/personal')['profiles']),1)
  profile=self.submit('gamer','profile');self.assertEqual(profile['summary']['count'],30)
  saved=self.call('/api/personal');self.assertEqual(len(saved['profiles']),2);self.assertEqual(len(saved['profiles'][-1]['answers']),30)
  self.assertEqual(saved['profiles'][-1]['weights'],profile['weights'])
  self.call('/api/personal/settings',{'nickname':'꾸미기','bio':'저장 확인','theme':'elden','avatar':'Trophy','cover_y':20,'cover_shade':30})
  game=self.call('/api/personal/catalog')[0]['id'];self.call('/api/personal/wishlist',{'game':game,'saved':True});self.call('/api/personal/recent',{'game':game})
  self.server.shutdown();self.thread.join();self.server.server_close();self.start()
  restored=self.call('/api/personal');self.assertEqual(restored['settings']['nickname'],'꾸미기');self.assertEqual(len(restored['wishlist']),1);self.assertEqual(len(restored['recent']),1)
  self.call('/api/account/logout',{});self.assertEqual(self.call('/api/personal')['profiles'],[])
  self.call('/api/quick-survey/results/'+quick['result_id'],expect=404)
  self.call('/api/account/login',{'email':'flow@example.com','password':'test-password'})
  self.assertEqual(len(self.call('/api/personal')['profiles']),2)
  self.call('/api/account/signup',{'name':'중복','email':'flow@example.com','password':'test-password'},422)
 def test_nongamer_and_validation(self):
  self.call('/api/personal');self.submit('nongamer','quick');self.submit('nongamer','profile')
  self.call('/api/account/signup',{'name':'test','email':'invalid','password':'test-password'},422)
  d=definition('gamer');p={'survey_id':d['survey_id'],'version':'old','submission_id':str(uuid4()),'answers':{q['id']:['0'] for q in d['questions']}}
  self.call('/api/quick-survey/submissions',p,422)

if __name__=='__main__':unittest.main()
