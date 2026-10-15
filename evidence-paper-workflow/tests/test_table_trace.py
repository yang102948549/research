import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from table_trace import trace_errors
from pdf_evidence import checked_box
class Rect:
    x0=y0=0
    x1=y1=100
class TableTraceTests(unittest.TestCase):
    def setUp(self):
        h=lambda text,span:dict(text=text,span=span,bbox=[1,1,10,10])
        self.e=dict(quote='49.54',locator=dict(bbox=[20,20,30,30],context_bbox=[0,0,100,100]),table_context=dict(row='지역 > 군부',column='신체적 부양자 > 없음',unit='%',cell_trace=dict(value='49.54',bbox=[20,20,30,30],row_index=6,column_index=0,row_headers=[h('지역',[5,6]),h('군부',[6,6])],column_headers=[h('신체적 부양자',[0,2]),h('없음',[0,0])],unit=dict(text='%',status='printed',bbox=[1,1,10,10]),notes=[dict(text='일상생활 수행에 제한을 받고 있는 노인',scope='panel',applies_to_cell=True,bbox=[1,80,90,90])],population_scope='ADL 제한 노인')))
    def errors(self,e): return trace_errors(e,checked_box,Rect())
    def test_valid(self):self.assertEqual(self.errors(self.e),[])
    def test_mutations(self):
        mutations=[lambda t:t.update(row_index=4),lambda t:t['column_headers'][1].update(span=[0,4]),lambda t:t['unit'].update(text='명'),lambda t:t.update(notes=[]),lambda t:t.update(value='4954'),lambda t:t['notes'][0].update(applies_to_cell='yes'),lambda t:t['row_headers'][0].update(bbox=[0,0,101,30]),lambda t:t.update(population_scope='')]
        for change in mutations:
            with self.subTest(change=change):
                e=copy.deepcopy(self.e);change(e['table_context']['cell_trace']);self.assertTrue(self.errors(e))
    def test_missing_or_malformed(self):
        for t in (None,{},'bad'):
            e=copy.deepcopy(self.e);e['table_context']=t;self.assertTrue(self.errors(e))
if __name__=='__main__':unittest.main()
