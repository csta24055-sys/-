#!/usr/bin/env python3
"""Research completeness gates for an evidence-based AI document market study.

This script checks structure, references, evidence counts, and submitted artifacts.
It CANNOT independently validate that a website's contents or a user quote is true.
Independent original-source review is therefore still mandatory. No app code here.

Usage:
    python3 scripts/research_gates.py check
    python3 scripts/research_gates.py check --root /path/to/project
    python3 scripts/research_gates.py evaluate  # saves research/gate_evaluation.json; does NOT edit research_status.json
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STEPS=[
('S0','repo_and_registry_audit'),('S1','collection'),('S2','verification'),
('S3','user_segments'),('S4','competitors'),('S5','quantitative_research'),
('S6','alternative_assessment'),('S7','decision_analysis'),
('S8','final_outputs'),('S9','final_audit_no_implementation')]
MARKERS=('NOT_STARTED','【要調査】','[TODO]','TODO:')


def read_csv(path:Path)->list[dict]:
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def text_at(path:Path)->str:
    return path.read_text(encoding='utf-8') if path.exists() else ''

def has_substance(path:Path,min_length=400)->bool:
    s=text_at(path)
    return len(s.strip())>=min_length and not any(x in s for x in MARKERS)

def ids(value:str)->set[str]:
    return {x.strip() for x in (value or '').split(';') if x.strip()}

def nonempty(value)->bool:
    return bool(value is not None and str(value).strip() and str(value).strip().upper() not in ('UNKNOWN','N/A','NONE','NULL'))

def assess(root:Path)->dict:
    r=root/'registry';research=root/'research';d=root/'deliverables'
    axes=read_csv(r/'research_axes.csv')
    sources=read_csv(r/'source_evidence.csv')
    searches=read_csv(r/'search_log.csv')
    companies=read_csv(r/'competitor_candidates.csv')
    results=read_csv(r/'quant_results.csv')
    claims=read_csv(r/'product_claims.csv')
    accepted=[x for x in sources if x.get('is_accepted','').strip().lower()=='yes']
    origins={x.get('origin_group_id','').strip() for x in accepted if nonempty(x.get('origin_group_id'))}
    source_ids={x.get('source_id','').strip() for x in accepted if nonempty(x.get('source_id'))}
    index={x.get('topic_id','') for x in axes}
    verified={'DIRECT_ORIGINAL','VERIFIED_SECONDARY'}
    direct=[x for x in accepted if x.get('verified_state')=='DIRECT_ORIGINAL']
    conditions={}
    def gate(stage:str,condition:bool,detail:str):
        conditions.setdefault(stage,[]).append({'pass':bool(condition),'detail':detail})

    # S0: Research setup checks and audit. Never PASS on merely receiving this ZIP.
    try: manifest=json.loads(text_at(research/'research_manifest.json'))
    except (ValueError,FileNotFoundError): manifest={}
    try: state=json.loads(text_at(research/'research_status.json'))
    except (ValueError,FileNotFoundError): state={}
    gate('S0',len(axes)==manifest.get('expected_topic_count') and len({x['topic_id'] for x in axes})==len(axes) and len({x['axis_id'] for x in axes})==manifest.get('expected_axis_count'),f'current manifest registry: {len(axes)} topics')
    gate('S0',len(list((root/'reference_images').glob('IMG_*')))==8,'eight supplied user reference images available')
    gate('S0',manifest.get('product_implementation_allowed') is False and manifest.get('research_must_stop_after_report') is True,'explicit app implementation ban and report stop in manifest')
    gate('S0',len(state.get('steps',{}))==10,'ten research step statuses in state')
    audit=text_at(research/'REPO_AUDIT.md')
    gate('S0','STATUS = AUDITED' in audit and ('REPO_PATH:' in audit or 'REPO_UNAVAILABLE:' in audit) and len(audit)>250,'real repo/tools audit recorded (not prefilled)')

    # S1: The following counts are MINIMUM COVERAGE CHECKS, not statistically adequate sample claims.
    gate('S1',len(searches)>=24 and len({x.get('query','') for x in searches})>=20,f'logged search queries: {len(searches)}')
    gate('S1',len({x.get('platform','') for x in searches if nonempty(x.get('platform'))})>=5,'at least five search platforms represented')
    gate('S1',len(accepted)>=20 and len(direct)>=10 and len(origins)>=12,f'accepted={len(accepted)}, direct={len(direct)}, independent origins={len(origins)}')
    gate('S1',len({x.get('axis_id','') for x in accepted})>=12 and len({x.get('source_type','') for x in accepted})>=4,'multiple research axes and publication categories')
    gate('S1',{x.get('topic_id') for x in searches if x.get('topic_id') in index}==index,'every registered topic has an actual logged source-search/access attempt; planned queries alone do not count')
    gate('S1',has_substance(research/'COLLECTION_COVERAGE_AUDIT.md',500),'audited gaps, search failures and actual source acquisition')

    # S2: Validation of every accepted record's formal provenance; manual truth-check still required.
    issues=[]
    if not accepted: issues.append('no accepted sources')
    if len(source_ids)!=len(accepted): issues.append('duplicate/missing source_id')
    for x in accepted:
        for field in ('source_id','origin_group_id','url','publisher','checked_at','source_type','axis_id','topic_id','page_or_section'):
            if not nonempty(x.get(field)): issues.append(f'{x.get("source_id", "?")}: missing {field}')
        if x.get('verified_state') not in verified: issues.append(f'{x.get("source_id", "?")}: not verified original/secondary')
        if x.get('topic_id') not in index: issues.append(f'{x.get("source_id", "?")}: invalid topic')
        if not str(x.get('url','')).startswith(('https://','http://')): issues.append(f'{x.get("source_id", "?")}: URL malformed')
    gate('S2',not issues and len(accepted)>=20,f'source provenance errors: {len(issues)}'+(': '+', '.join(issues[:4]) if issues else ''))
    gate('S2',has_substance(research/'SOURCE_DEPENDENCY_AUDIT.md',500),'independent-origin, sponsorship and repost review recorded')
    gate('S2',has_substance(research/'CONTRADICTIONS.md',300),'competing evidence and corrections described')

    # S3: User data are not invented; real source IDs need to be cited.
    segment=text_at(research/'SEGMENT_ANALYSIS.md')
    gate('S3',has_substance(research/'SEGMENT_ANALYSIS.md',1000),'substantive, evidence-based jobs-to-be-done segmentation')
    gate('S3',len(source_ids)>=20 and len([x for x in source_ids if x in segment])>=5,'at least five real evidence IDs cited in segmentation')
    gate('S3',all(x in segment for x in ('仕事','学校','支払','守秘','反証')),'job, academic, payer, privacy, counterexamples addressed')

    # S4: Minimum set of verified competitors; each one needs a SOURCE ID.
    verified_comp=[x for x in companies if x.get('verification_state')=='VERIFIED_OFFICIAL']
    invalid_comp=[x for x in verified_comp if not ids(x.get('sources','')).issubset(source_ids) or not ids(x.get('sources',''))]
    gate('S4',len(verified_comp)>=8 and not invalid_comp,f'verified competitors={len(verified_comp)}, invalid sources={len(invalid_comp)}')
    core=[x for x in companies if x.get('research_priority')=='P0']
    checked={x.get('competitor_id') for x in verified_comp}
    gate('S4',all(x.get('competitor_id') in checked for x in core),f'all {len(core)} highest-priority candidate companies have evidence-backed official verification')
    gate('S4',has_substance(research/'COMPETITOR_COMPARISON.md',1200),'substantial comparisons with sources, limits and pricing checks')

    # S5: Count only observed or real-data-based estimates; hypotheticals cannot unlock stats.
    admissible=[]
    for x in results:
        if x.get('evidence_category') not in ('OBSERVED','MODEL_BASED','MIXED'): continue
        if not ids(x.get('source_ids','')).issubset(source_ids) or not ids(x.get('source_ids','')): continue
        if not all(nonempty(x.get(k)) for k in ('result_id','estimate','unit','metric','segment','geography','period')): continue
        if x.get('evidence_category') in ('MODEL_BASED','MIXED') and not nonempty(x.get('model_id')): continue
        if x.get('evidence_category')=='OBSERVED' and not nonempty(x.get('sample_n')): continue
        admissible.append(x)
    gate('S5',len(admissible)>=5,f'quant results with traceable real-world evidence={len(admissible)}')
    gate('S5',has_substance(research/'QUANT_MODEL_REPORT.md',1000),'model assumptions, identification, bias and sensitivity documented')
    gate('S5',has_substance(research/'QUANT_REPRODUCIBILITY.md',500),'recomputation and independent checking documented')

    # S6 through S9: content plus source lineage. These gates are review aids, not truth or quality guarantees.
    alt=text_at(research/'PRODUCT_ALTERNATIVES.md')
    gate('S6',has_substance(research/'PRODUCT_ALTERNATIVES.md',1500) and all(f'案{x}' in alt for x in 'ABCDEFG'),'A-G product alternatives analyzed and counterarguments included')
    gate('S6',len([x for x in source_ids if x in alt])>=5,'product tradeoffs cite at least five accepted sources')
    decision=text_at(research/'DECISION_ANALYSIS.md')
    gate('S7',has_substance(research/'DECISION_ANALYSIS.md',1400),'conditional statistical decision and sensitivity analysis documented')
    gate('S7',all(word in decision for word in ('下振れ','期待後悔','条件付き','NON_IDENTIFIABLE')),'downside, regret, conditions, unidentifiable issues explicitly covered')
    outputs=['FINAL_RESEARCH_REPORT.md','FEATURE_PRIORITIZATION.md','UX_BUTTON_FLOW_SPEC.md','EXTERNAL_CONNECTION_POLICY_SPEC.md','DECISION_AND_OPEN_RISKS.md']
    gate('S8',all(has_substance(d/x,700) for x in outputs),'all five substantive and non-placeholder final artifacts exist')
    report=text_at(d/'FINAL_RESEARCH_REPORT.md')
    gate('S8',len([x for x in source_ids if x in report])>=8,'main report cites at least eight distinct accepted source IDs')
    gate('S8',all(word in report for word in ('文字入力','学校','仕事','外部接続','競合','統計')),'critical user requirements covered')
    gate('S9',has_substance(research/'REPORT_QA.md',500),'final review / implementation-stop proof exists')
    qa=text_at(research/'REPORT_QA.md')
    gate('S9',all(word in qa for word in ('APP_IMPLEMENTATION_CHANGED = NO','検証','未完了')),'manual app-change audit and research quality check attested')
    gate('S9',bool(claims) and all(ids(x.get('source_ids','')).issubset(source_ids) for x in claims if nonempty(x.get('source_ids'))),'product conclusions linked to accepted sources')

    out={}
    prior_pass=True
    for key,label in STEPS:
        checks=conditions[key]
        meets_all=all(v['pass'] for v in checks)
        declared=state.get('steps',{}).get(key,{}).get('state','NOT_STARTED')
        if prior_pass and meets_all:
            state_value='PASS'
        elif declared=='NOT_STARTED':
            state_value='NOT_STARTED'
        else:
            state_value='BLOCKED'
        out[key]={'label':label,'state':state_value,'checks':checks,'pass_count':sum(c['pass'] for c in checks),'total_checks':len(checks)}
        prior_pass=prior_pass and meets_all
    overall='COMPLETE' if prior_pass else 'INCOMPLETE'
    return {'research_status':overall,'checked_at':datetime.now(timezone.utc).isoformat(),
            'source_rows':len(sources),'accepted_rows':len(accepted),'independent_origins':len(origins),
            'verified_competitors':len(verified_comp),'admissible_quant_results':len(admissible),
            'steps':out,'warning':'Mechanical checks do not establish source truth, sample representativeness or statistical validity; independent review required.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['check','evaluate'],nargs='?',default='check')
    parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    args=parser.parse_args();root=Path(args.root).resolve()
    result=assess(root)
    if args.action=='evaluate':
        (root/'research').mkdir(exist_ok=True,parents=True)
        (root/'research'/'gate_evaluation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        status_path=root/'research'/'research_status.json'
        if status_path.exists():
            current=json.loads(status_path.read_text(encoding='utf-8'))
            current['research_state']=result['research_status']
            current['last_evaluated']=result['checked_at']
            for step_id, step in result['steps'].items():
                current.setdefault('steps',{}).setdefault(step_id,{})['state']=step['state']
                current['steps'][step_id]['evaluated_at']=result['checked_at']
                current['steps'][step_id]['failure_reasons']=[c['detail'] for c in step['checks'] if not c['pass']]
            status_path.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RESEARCH_STATUS:',result['research_status'])
    print('Accepted sources:',result['accepted_rows'],'Independent origins:',result['independent_origins'])
    for key,step in result['steps'].items():
        print(f'{key} {step["state"]} ({step["pass_count"]}/{step["total_checks"]})')
        for ck in step['checks']:
            if not ck['pass']:print('  - FAIL:',ck['detail'])
    print('NOTICE:',result['warning'])

if __name__=='__main__':main()
