"""Behavioral tests for the portable skill (stdlib unittest runner)."""
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'econ.py'

class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=os.environ.get('ECON_TEST_TMP'))
        self.root=Path(self.tmp.name)
        self.data=self.root/'panel.csv'
        rng=random.Random(42)
        self.rows=[]
        for g in range(10):
            for t in range(10):
                x=rng.uniform(0,10);z=rng.uniform(0,3);alt=rng.uniform(0,10)
                self.rows.append({'country':f'C{g}','year':2000+t,'x':x,'y':1.75*x+0.7*z+g+t*0.4+rng.gauss(0,.2),'z':z,'alt':alt})
        self.write_rows()
    def tearDown(self):self.tmp.cleanup()
    def write_rows(self):
        with self.data.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['country','year','x','y','z','alt']);w.writeheader();w.writerows(self.rows)
    def cmd(self,*args):
        r=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True,encoding='utf-8')
        try:body=json.loads(r.stdout)
        except ValueError:body={'unparsed':r.stdout,'stderr':r.stderr}
        return r,body
    def plan(self,**extra):
        p=self.root/extra.pop('name','plan.json')
        args=['plan','--data',self.data,'--entity','country','--time','year','--x','x','--y','y','--question','Does x relate to y?','--evidence-class','SYNTHETIC_TEST_EXECUTION','--control','z','--alternative-x','alt','--out',p]
        r,b=self.cmd(*args)
        self.assertEqual(r.returncode,0,b)
        return p,b
    def test_profile_reports_hash_missing_and_dimensions(self):
        self.rows[0]['x']='';self.write_rows()
        r,b=self.cmd('profile','--data',self.data,'--entity','country','--time','year')
        self.assertEqual(r.returncode,0,b)
        self.assertEqual(b['rows'],100)
        self.assertEqual(b['columns']['x']['missing'],1)
        self.assertEqual(b['entities'],10)
        self.assertEqual(b['sha256'],hashlib.sha256(self.data.read_bytes()).hexdigest())
    def test_plan_rejects_duplicate_panel_keys(self):
        self.rows.append(self.rows[0].copy());self.write_rows()
        r,b=self.cmd('plan','--data',self.data,'--entity','country','--time','year','--x','x','--y','y','--question','test','--evidence-class','SYNTHETIC_TEST_EXECUTION','--out',self.root/'p.json')
        self.assertEqual(b.get('code'),'DUPLICATE_PANEL_KEYS',b)
        self.assertNotEqual(r.returncode,0)
    def test_unknown_columns_are_not_silently_substituted(self):
        r,b=self.cmd('plan','--data',self.data,'--entity','country','--time','year','--x','typo_x','--y','y','--question','test','--evidence-class','REAL_DATA_EMPIRICAL','--out',self.root/'p.json')
        self.assertEqual(b.get('code'),'UNKNOWN_COLUMN',b)
    def test_plan_is_draft_and_requires_consent(self):
        p,b=self.plan()
        plan=json.loads(p.read_text(encoding='utf-8'))
        self.assertFalse(plan['approval']['approved'])
        r,b=self.cmd('run','--plan',p,'--out',self.root/'r')
        self.assertEqual(b.get('code'),'APPROVAL_REQUIRED',b)
        self.assertFalse((self.root/'r').exists())
    def test_changed_input_is_blocked_before_execution(self):
        p,_=self.plan();self.rows[0]['y']=999;self.write_rows()
        r,b=self.cmd('run','--plan',p,'--approve','--out',self.root/'r')
        self.assertEqual(b.get('code'),'INPUT_CHANGED',b)
        self.assertFalse((self.root/'r').exists())
    def test_existing_plan_is_not_overwritten(self):
        p,_=self.plan();old=p.read_bytes()
        r,b=self.cmd('plan','--data',self.data,'--entity','country','--time','year','--x','x','--y','y','--question','new','--evidence-class','SYNTHETIC_TEST_EXECUTION','--out',p)
        self.assertEqual(b.get('code'),'OUTPUT_EXISTS',b)
        self.assertEqual(p.read_bytes(),old)
    def test_nonfinite_and_nonnumeric_x_are_rejected(self):
        for val in ['inf','not-a-number']:
            self.rows[0]['x']=val;self.write_rows()
            r,b=self.cmd('plan','--data',self.data,'--entity','country','--time','year','--x','x','--y','y','--question','test','--evidence-class','SYNTHETIC_TEST_EXECUTION','--out',self.root/(val+'.json'))
            self.assertEqual(b.get('code'),'NONNUMERIC_COLUMN',b)
    def test_invalid_time_and_missing_key_are_blocked(self):
        for val in ['','2000.5','unknown']:
            self.rows[0]['year']=val;self.write_rows()
            r,b=self.cmd('profile','--data',self.data,'--entity','country','--time','year')
            self.assertIn(b.get('code'),{'INVALID_PANEL_KEY','INVALID_TIME'},b)
    def test_run_uses_common_sample_and_retains_nonsignificant_model(self):
        self.rows[0]['z']='';self.rows[1]['alt']='';self.write_rows()
        p,_=self.plan()
        out=self.root/'run'
        r,b=self.cmd('run','--plan',p,'--approve','--out',out)
        self.assertEqual(r.returncode,0,b)
        res=json.loads((out/'results.json').read_text(encoding='utf-8'))
        self.assertEqual([m['nobs'] for m in res['models']],[98,98,98])
        self.assertLess(abs(res['models'][2]['coefficient']-1.75),.1)
        self.assertGreater(res['models'][1]['p_value'],.05)
        self.assertEqual(res['sample_strategy'],'common_complete_case')
    def test_execution_success_is_not_scientific_approval(self):
        p,_=self.plan();out=self.root/'run'
        r,b=self.cmd('run','--plan',p,'--approve','--out',out)
        self.assertEqual(r.returncode,0,b)
        audit=json.loads((out/'audit.json').read_text(encoding='utf-8'))
        self.assertEqual(audit['overall'],'REVIEW_REQUIRED')
        self.assertEqual(audit['dimensions']['hypothesis']['status'],'NOT_ASSESSABLE')
        report=(out/'report.md').read_text(encoding='utf-8')
        self.assertIn('SYNTHETIC_TEST_EXECUTION',report)
        self.assertIn('模拟',report)
    def test_manifest_can_detect_tampered_results(self):
        p,_=self.plan();out=self.root/'run'
        r,b=self.cmd('run','--plan',p,'--approve','--out',out)
        self.assertEqual(r.returncode,0,b)
        r,b=self.cmd('verify','--run',out)
        self.assertEqual(r.returncode,0,b)
        with (out/'results.json').open('a') as f:f.write(' ')
        r,b=self.cmd('verify','--run',out)
        self.assertEqual(b.get('code'),'ARTIFACT_CHANGED',b)
    def test_nonempty_execution_directory_is_preserved(self):
        p,_=self.plan();out=self.root/'run';out.mkdir();(out/'keep.txt').write_text('keep')
        r,b=self.cmd('run','--plan',p,'--approve','--out',out)
        self.assertEqual(b.get('code'),'OUTPUT_EXISTS',b)
        self.assertEqual((out/'keep.txt').read_text(),'keep')
    def test_rank_deficient_design_is_rejected(self):
        for row in self.rows:row['z']=row['x']
        self.write_rows();p,_=self.plan()
        r,b=self.cmd('run','--plan',p,'--approve','--out',self.root/'run')
        self.assertEqual(b.get('code'),'RANK_DEFICIENT',b)
    def test_bad_plan_and_injected_columns_are_not_executed(self):
        p,_=self.plan();plan=json.loads(p.read_text(encoding='utf-8'))
        plan['x']="x;__import__('os').system('no')"
        p.write_text(json.dumps(plan),encoding='utf-8')
        r,b=self.cmd('check','--plan',p)
        self.assertEqual(b.get('code'),'UNKNOWN_COLUMN',b)
    def test_csv_duplicate_headers_are_rejected(self):
        self.data.write_text('country,year,x,x\nA,2020,1,2\n',encoding='utf-8')
        r,b=self.cmd('profile','--data',self.data,'--entity','country','--time','year')
        self.assertEqual(b.get('code'),'INVALID_HEADER',b)

if __name__=='__main__':unittest.main()
