import unittest
from quick_survey.steam import recommend
class MatchTests(unittest.TestCase):
 def test_normalized_changes_ranking(self):
  rows=[{'id':'a','app':10},{'id':'b','app':20}]
  def facts(codes):
   return {'normalized':{'schema_version':'game-facts-1.0.0','recommendable':True,'name':'Game','codes':codes,'platforms':['pc'],'evidence':{c:[{'source':'igdb','value':c}] for c in codes},'price':{'amount':1000,'currency':'KRW'},'source_status':{'igdb':'ok'}}}
  weights={'tag:open_world':10,'category:co_op':10}
  updates={'a':facts(['tag:open_world']),'b':facts(['tag:open_world','category:co_op'])}
  r=recommend(weights,{'platforms':['pc']},rows,updates)
  self.assertEqual([g['app_id'] for g in r['games']],[20,10])
  self.assertEqual(r['games'][0]['score'],20)
  self.assertEqual(r['games'][0]['price']['amount'],1000)
  self.assertEqual(recommend(weights,{'platforms':['mobile']},rows,updates)['games'],[])
 def test_missing_data_not_snapshot(self):
  self.assertEqual(recommend({'genre:action':10},{'platforms':[]},[{'id':'a','app':1}],{})['status'],'data_required')
 def test_unknown_session_no_points(self):
  r=recommend({'session:short':5},{'platforms':[]},[],{})
  self.assertEqual(r['unsupported_weights'],['session:short'])
