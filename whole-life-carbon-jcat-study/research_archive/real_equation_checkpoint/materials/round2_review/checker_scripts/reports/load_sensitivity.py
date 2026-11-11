# How much does the instruction-count reduction depend on generator settings (distinct renewal periods / factors)?
import sys, gc
sys.dont_write_bytecode=True
from refcalc import registry
from fastcalc import engine
from synth import population, generate
import synth
registry.load_all()
mon=sys.monitoring; TOOL=mon.PROFILER_ID
def count(fn):
    n=[0]
    def tick(code,off): n[0]+=1
    mon.use_tool_id(TOOL,'recheck'); mon.register_callback(TOOL,mon.events.INSTRUCTION,tick)
    mon.set_events(TOOL,mon.events.INSTRUCTION)
    try: fn()
    finally:
        mon.set_events(TOOL,0); mon.register_callback(TOOL,mon.events.INSTRUCTION,None); mon.free_tool_id(TOOL)
    return n[0]
print('default options:',{k:generate.DEFAULT_OPTIONS[k] for k in ('service_life_mode','service_life_choices','composite_share','profile_kind','grid_kind') if k in generate.DEFAULT_OPTIONS})
def case(label,scn):
    scn.boundary.baseline_scenario=None
    ref=count(lambda: registry.run_all(scn))
    full=count(lambda: engine.evaluate(scn,detail=True))
    tot=count(lambda: engine.evaluate(scn,detail=False))
    st=engine.evaluate(scn,detail=False)['_stats']
    A=engine.aggregate(scn,False)
    print('%-34s rows=%d ref=%d full=%d (-%.1f%%) totals=%d (-%.1f%%) groups=%d'%(label,len(scn.materials)+len(scn.equipment),ref,full,100*(1-full/ref),tot,100*(1-tot/ref),len(A.groups)))
b=population.standard_benchmark()
case('benchmark S (as published)',b[0])
for mode in ('MIXED','INTEGER','EXACT_DIVISOR','NON_DIVISOR','CONTINUOUS'):
    case('S seed101 life_mode=%s'%mode, synth.make_scenario(101,'RC','office','S',60.0,service_life_mode=mode))
case('benchmark M (as published)',b[1])
case('M seed102 life_mode=CONTINUOUS', synth.make_scenario(102,b[1].project.structure_type,'office','M',60.0,service_life_mode='CONTINUOUS'))
