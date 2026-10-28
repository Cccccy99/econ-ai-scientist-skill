#!/usr/bin/env python3
"""Local, auditable panel-analysis mechanics. MIT; no network or model calls."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys

VERSION='1.0.0'
SCHEMA='econ-ai-scientist/1.0'
MISSING={'','na','n/a','nan','null','none'}
EVIDENCE={'SYNTHETIC_TEST_EXECUTION','REAL_DATA_EMPIRICAL'}

class SkillError(Exception):
    def __init__(self,code,message):
        self.code=code;super().__init__(message)

def fail(code,message):raise SkillError(code,message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def missing(value):return value is None or str(value).strip().lower() in MISSING
def number(value):
    if missing(value):return None
    try:v=float(value)
    except (TypeError,ValueError):fail('NONNUMERIC_COLUMN',f'Not a finite numeric value: {str(value)[:60]}')
    if not math.isfinite(v):fail('NONNUMERIC_COLUMN','Non-finite numeric value')
    return v
def dump(path,obj):
    path=Path(path)
    if path.exists():fail('OUTPUT_EXISTS',f'Preserve the existing artifact; choose a new path: {path}')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def read_json(path):
    try:
        with Path(path).open(encoding='utf-8-sig') as f:value=json.load(f)
    except (OSError,ValueError) as e:fail('INVALID_JSON',str(e))
    if not isinstance(value,dict):fail('INVALID_PLAN','Expected a JSON object')
    return value

def panel(data,entity,time):
    path=Path(data).expanduser().resolve()
    if not path.is_file():fail('INPUT_NOT_FOUND',str(path))
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        headers=reader.fieldnames or []
        if not headers or len(set(headers))!=len(headers) or any(not h or h!=h.strip() for h in headers):
            fail('INVALID_HEADER','CSV headers must be unique, nonempty, and without surrounding spaces')
        if entity==time:fail('INVALID_PLAN','Entity and time columns must differ')
        for name in (entity,time):
            if name not in headers:fail('UNKNOWN_COLUMN',str(name))
        rows=list(reader)
    if not rows:fail('EMPTY_INPUT','CSV has no observations')
    keys=set();duplicates=0;entities=set();years=set()
    for row in rows:
        if None in row or any(v is None for v in row.values()):fail('MALFORMED_CSV','Rows must have the same number of fields as the header')
        if missing(row[entity]) or missing(row[time]):fail('INVALID_PANEL_KEY','Missing entity or time key')
        try:t=number(row[time])
        except SkillError:fail('INVALID_TIME','Time must be a finite integer such as a year')
        if t is None or not t.is_integer():fail('INVALID_TIME','Time must be an integer')
        key=(row[entity].strip(),int(t));duplicates+=key in keys;keys.add(key)
        entities.add(key[0]);years.add(key[1])
    stats={}
    for col in headers:
        absent=0;numeric=0;other=0
        for row in rows:
            v=row[col]
            if missing(v):absent+=1;continue
            try:number(v);numeric+=1
            except SkillError:other+=1
        stats[col]={'missing':absent,'finite_numeric':numeric,'other_nonmissing':other}
    profile={'schema_version':SCHEMA,'data_path':str(path),'sha256':sha(path),'rows':len(rows),
             'entities':len(entities),'time_periods':len(years),'time_range':[min(years),max(years)],
             'entity_time_duplicates':duplicates,'columns':stats}
    return profile,rows

def validate(p):
    if p.get('schema_version')!=SCHEMA:fail('INVALID_PLAN','Unsupported or missing schema_version')
    for key in ('data_path','data_sha256','entity','time','x','y','question'):
        if not isinstance(p.get(key),str) or not p[key].strip():fail('INVALID_PLAN',f'Missing or invalid {key}')
    if p.get('evidence_class') not in EVIDENCE:fail('INVALID_PLAN','Explicit evidence_class is required')
    controls=p.get('controls',[])
    if not isinstance(controls,list) or any(not isinstance(x,str) for x in controls):fail('INVALID_PLAN','controls must be column names')
    if len(set(controls))!=len(controls):fail('INVALID_PLAN','Duplicate controls')
    alt=p.get('alternative_x')
    if alt is not None and not isinstance(alt,str):fail('INVALID_PLAN','alternative_x must be a column name or null')
    numeric=[p['x'],p['y'],*controls]+([alt] if alt else [])
    if len(numeric)!=len(set(numeric)) or set(numeric)&{p['entity'],p['time']}:
        fail('INVALID_PLAN','Outcome, exposures, controls and keys must have distinct roles')
    profile,rows=panel(p['data_path'],p['entity'],p['time'])
    if profile['sha256']!=p['data_sha256']:fail('INPUT_CHANGED','CSV hash differs from the approved draft; make a new plan revision')
    if profile['entity_time_duplicates']:fail('DUPLICATE_PANEL_KEYS','Repeated entity/time keys must be resolved explicitly')
    for col in numeric:
        if col not in profile['columns']:fail('UNKNOWN_COLUMN',col)
        if profile['columns'][col]['other_nonmissing']:fail('NONNUMERIC_COLUMN',f'Non-numeric or infinite values in {col}')
        if not profile['columns'][col]['finite_numeric']:fail('NONNUMERIC_COLUMN',f'No finite values in {col}')
    return profile,rows,numeric

def make_plan(args):
    profile,_=panel(args.data,args.entity,args.time)
    p={'schema_version':SCHEMA,'created_at':stamp(),'question':args.question,
       'data_path':profile['data_path'],'data_sha256':profile['sha256'],
       'entity':args.entity,'time':args.time,'x':args.x,'y':args.y,
       'controls':args.control or [],'alternative_x':args.alternative_x,
       'evidence_class':args.evidence_class,'method':'two_way_fixed_effects',
       'inference':'entity_clustered_use_t','sample_strategy':'common_complete_case',
       'approval':{'required':True,'approved':False},
       'interpretation':'association_only','review_notes':[]}
    validate(p);dump(args.out,p)
    return {'status':'DRAFT_REVIEW_REQUIRED','plan':str(Path(args.out).resolve()),'data_sha256':profile['sha256']}

def versions():
    result={'python':sys.version.split()[0],'skill':VERSION}
    for pkg in ('numpy','pandas','scipy','statsmodels','patsy'):
        try:result[pkg]=importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:result[pkg]=None
    return result

def execute(plan_path,out_path,approved):
    if not approved:fail('APPROVAL_REQUIRED','Ask the user to confirm the plan; only then use --approve')
    p=read_json(plan_path)
    profile,rows,numeric=validate(p)
    if p.get('method')!='two_way_fixed_effects' or p.get('sample_strategy')!='common_complete_case' or p.get('interpretation')!='association_only':
        fail('INVALID_PLAN','Only declared association-only TWFE with common samples is supported')
    out=Path(out_path).expanduser().resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):fail('OUTPUT_EXISTS','Use a new empty run directory; existing revisions are preserved')
    try:
        import numpy as np
        import pandas as pd
        import statsmodels.api as sm
    except ImportError as e:fail('MISSING_DEPENDENCY',f'{e}. Install requirements.txt in the selected environment')
    selected=[r for r in rows if all(not missing(r[c]) for c in numeric)]
    if not selected:fail('NO_COMPLETE_SAMPLE','No complete observations across all requested specifications')
    frame=pd.DataFrame(selected)
    for col in numeric:frame[col]=[number(v) for v in frame[col]]
    ent=frame[p['entity']].str.strip()
    time=frame[p['time']].map(lambda v:int(float(v)))
    nentities=ent.nunique();nperiods=time.nunique()
    if nentities<5 or nperiods<2:fail('INSUFFICIENT_PANEL','Require at least 5 entities and 2 periods; inferential adequacy still needs review')
    entity_fe=pd.get_dummies(ent,prefix='entity',drop_first=True,dtype=float)
    time_fe=pd.get_dummies(time.astype(str),prefix='time',drop_first=True,dtype=float)
    specs=[('baseline',p['x'],[])]
    if p.get('alternative_x'):specs.append(('alternative_x',p['alternative_x'],[]))
    if p['controls']:specs.append(('with_controls',p['x'],p['controls']))
    results=[]
    for name,x,controls in specs:
        columns=[x,*controls]
        # Internal design names prevent data labels colliding with dummy/intercept names.
        X=frame[columns].copy();X.columns=[f'regressor_{i}' for i in range(len(columns))]
        X=pd.concat([X,entity_fe,time_fe],axis=1).astype(float)
        X=sm.add_constant(X,has_constant='add')
        if len(frame)<=X.shape[1]:fail('INSUFFICIENT_DF',f'No positive residual degrees of freedom in {name}')
        if np.linalg.matrix_rank(X.to_numpy())!=X.shape[1]:fail('RANK_DEFICIENT',f'Collinear design in {name}; do not silently drop requested variables')
        fit=sm.OLS(frame[p['y']].astype(float),X,missing='raise').fit(cov_type='cluster',cov_kwds={'groups':ent},use_t=True)
        index=X.columns.get_loc('regressor_0');ci=fit.conf_int().iloc[index]
        values=[float(fit.params.iloc[index]),float(fit.bse.iloc[index]),float(fit.pvalues.iloc[index]),float(ci.iloc[0]),float(ci.iloc[1])]
        if not all(math.isfinite(v) for v in values):fail('NONFINITE_RESULT',f'Non-finite inference in {name}')
        results.append({'specification':name,'x':x,'controls':controls,'nobs':int(fit.nobs),
                        'coefficient':values[0],'standard_error':values[1],'p_value':values[2],
                        'confidence_interval_95':values[3:],'r_squared':float(fit.rsquared),
                        'design_columns':int(X.shape[1]),'covariance':'entity_clustered','use_t':True})
    res={'schema_version':SCHEMA,'execution_status':'COMPLETED','created_at':stamp(),
         'evidence_class':p['evidence_class'],'data_sha256':profile['sha256'],
         'plan_sha256':sha(plan_path),'question':p['question'],'sample_strategy':'common_complete_case',
         'input_rows':len(rows),'sample_rows':len(frame),'excluded_rows':len(rows)-len(frame),
         'entities_used':int(nentities),'periods_used':int(nperiods),'models':results,
         'runtime':versions(),'human_approval_declared':True,
         'interpretation':'association_only','caveats':['Complete-case filtering may introduce selection bias.','Fixed effects and small p-values do not establish causality.','Clustered inference needs subject-matter review, especially with few clusters.']}
    dimensions={
        'data':{'status':'PASS','evidence':'Input hash, keys, selected numeric columns and common-sample counts verified.'},
        'hypothesis':{'status':'NOT_ASSESSABLE','evidence':'Variable meaning, measurement and theoretical relevance require agent and human review.'},
        'model':{'status':'WARN','evidence':'Finite full-rank TWFE executed; endogeneity and inference assumptions are not established.'},
        'robustness':{'status':'WARN','evidence':f'{len(results)} specifications retained on a common sample; sensitivity adequacy needs expert review.'},
        'claims':{'status':'WARN','evidence':f"Evidence class {p['evidence_class']}; report is restricted to association or synthetic execution."}}
    audit={'schema_version':SCHEMA,'kind':'deterministic_evidence_check','overall':'REVIEW_REQUIRED',
           'dimensions':dimensions,'auto_apply':False,'human_approval_required':True,
           'repair_actions':[{'target':'hypothesis_review','action':'Confirm construct meanings and interpretation.'},{'target':'model_review','action':'Review specification, sample selection, inference and sensitivity evidence.'}]}
    out.mkdir(parents=True,exist_ok=True)
    dump(out/'plan.snapshot.json',p);dump(out/'profile.json',profile);dump(out/'results.json',res);dump(out/'audit.json',audit)
    report=['# 面板研究执行与审计记录','',f"证据类别：{p['evidence_class']}",'',
            '本例为自建模拟数据的技术演示，不代表真实经济规律。' if p['evidence_class']=='SYNTHETIC_TEST_EXECUTION' else '真实数据分析仍为关联性结果，需要核查数据授权、理论与识别假设。','',
            f"输入 {len(rows)} 行；共同样本 {len(frame)} 行；排除 {len(rows)-len(frame)} 行。",'',
            '| 模型 | 样本数 | 解释变量 | 系数 | 标准误 | p值 |','|---|---:|---|---:|---:|---:|']
    clean=lambda v:str(v).replace('|','\\|').replace('\n',' ').replace('\r',' ')
    for m in results:report.append(f"| {m['specification']} | {m['nobs']} | {clean(m['x'])} | {m['coefficient']:.9g} | {m['standard_error']:.9g} | {m['p_value']:.9g} |")
    report+=['','## 审计与后续工作','','执行成功与科学有效性分开；总体状态 REVIEW_REQUIRED。没有依据宣称因果关系、教学增益或模型性能领先。',
             '保留所有规格及不显著结果；不能为了显著性改变量、样本或删结果。',
             '确定性检查不能代替独立的五维学科审查。请核对变量含义、遗漏因素、共同样本选择、聚类推断及敏感性设计。',
             '修复应生成新计划和运行目录，原修订保留。','',f"环境：{json.dumps(res['runtime'],ensure_ascii=False)}"]
    (out/'report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    files={f.name:sha(f) for f in out.iterdir() if f.is_file()}
    dump(out/'manifest.json',{'schema_version':SCHEMA,'files':files})
    return {'status':'COMPLETED','scientific_review':'REVIEW_REQUIRED','output':str(out),'models':len(results),'sample_rows':len(frame)}

def verify_run(path):
    root=Path(path).resolve();m=read_json(root/'manifest.json')
    if m.get('schema_version')!=SCHEMA or not isinstance(m.get('files'),dict):fail('INVALID_MANIFEST','Invalid manifest')
    required={'plan.snapshot.json','profile.json','results.json','audit.json','report.md'}
    if not required.issubset(m['files']):fail('INVALID_MANIFEST','Manifest omits required artifacts')
    for name,expected in m['files'].items():
        file=(root/name).resolve()
        if file.parent!=root or not file.is_file() or sha(file)!=expected:fail('ARTIFACT_CHANGED',f'Missing, changed, or unsafe artifact: {name}')
    return {'status':'VERIFIED','files':len(m['files']),'note':'Hash consistency is not proof of source authenticity or scientific validity.'}

def parser():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('profile');a.add_argument('--data',required=True);a.add_argument('--entity',required=True);a.add_argument('--time',required=True)
    a.add_argument('--out')
    a=sub.add_parser('plan')
    for name in ('data','entity','time','x','y','question','out'):a.add_argument('--'+name,required=True)
    a.add_argument('--control',action='append',default=[]);a.add_argument('--alternative-x')
    a.add_argument('--evidence-class',choices=sorted(EVIDENCE),required=True)
    a=sub.add_parser('check');a.add_argument('--plan',required=True)
    a=sub.add_parser('run');a.add_argument('--plan',required=True);a.add_argument('--out',required=True);a.add_argument('--approve',action='store_true')
    a=sub.add_parser('verify');a.add_argument('--run',required=True)
    a=sub.add_parser('demo');a.add_argument('--out',required=True);a.add_argument('--approve',action='store_true')
    return p

def main():
    a=parser().parse_args()
    try:
        if a.command=='profile':
            result,_=panel(a.data,a.entity,a.time)
            if a.out:dump(a.out,result)
        elif a.command=='plan':result=make_plan(a)
        elif a.command=='check':
            profile,_,_=validate(read_json(a.plan))
            result={'status':'MECHANICALLY_VALID','approval_required':True,'rows':profile['rows'],'scientific_review':'REVIEW_REQUIRED'}
        elif a.command=='run':result=execute(a.plan,a.out,a.approve)
        elif a.command=='verify':result=verify_run(a.run)
        else:
            if not a.approve:fail('APPROVAL_REQUIRED','The synthetic demo also requires explicit --approve')
            root=Path(a.out).resolve()
            if root.exists():fail('OUTPUT_EXISTS','Choose a new demo directory')
            data=Path(__file__).resolve().parents[1]/'assets'/'demo_panel.csv'
            args=argparse.Namespace(data=str(data),entity='country',time='year',x='internet',y='youth_unemployment',control=['ln_gdp_pc','urban'],alternative_x='mobile',question='Synthetic panel workflow demonstration',evidence_class='SYNTHETIC_TEST_EXECUTION',out=str(root/'plan.json'))
            make_plan(args);result=execute(root/'plan.json',root/'run',True)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False));return 0
    except SkillError as e:print(json.dumps({'status':'BLOCKED','code':e.code,'message':str(e)},ensure_ascii=False));return 2
    except (OSError,UnicodeError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'status':'BLOCKED','code':'INVALID_INPUT','message':str(e)},ensure_ascii=False));return 2

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
