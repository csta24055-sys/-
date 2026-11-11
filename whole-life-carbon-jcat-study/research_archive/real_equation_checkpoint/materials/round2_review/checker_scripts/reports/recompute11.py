import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
tr=L('03_MODELS/judge_proposal_trace.json')
print({k:(v if not isinstance(v,(list,dict)) else (type(v).__name__,len(v))) for k,v in tr.items()})
for k,v in tr.items():
    if isinstance(v,list) and v: print(k,'[0]=',json.dumps(v[0],ensure_ascii=False)[:500])
    if isinstance(v,dict): print(k, json.dumps(v,ensure_ascii=False)[:600])
