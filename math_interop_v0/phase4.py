"""Stage 4: deterministic dependency DAG, content-addressed cache, exact validation.

Synthetic/educational only. Does not execute arbitrary expressions from outside
Math IR 0.1, and does not mutate external research data.
"""
from __future__ import annotations
import copy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import duckdb
import mpmath
import numpy
import scipy
import sympy
import phase1
import phase2

SCHEMA = 'math-ir-phase4/1'
CODE_VERSION = 'math-ir-phase4-algorithm-1'


def check(value, reason):
    if not value:
        raise ValueError(reason)


def version(engine, numpy_salt):
    return {'Source':'1', 'SymPy':sympy.__version__,
            'NumPy':numpy.__version__+'-'+numpy_salt,
            'mpmath':mpmath.__version__, 'SciPy':scipy.__version__,
            'DuckDB':duckdb.__version__}.get(engine)


def digest(obj):
    return phase1.digest(obj)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(phase1.canonical(obj)+'\n', encoding='utf8')
    os.replace(temp, path)


class CalcDAG:
    def __init__(self, cache, numpy_salt='default'):
        self.cache = Path(cache)
        self.numpy_salt = numpy_salt
        self.nodes = {}
        self.values = {}
        self.computed = []
        self.reused = []

    def eval(self, name, operation, engine, depends, params, callback):
        check(name not in self.nodes, 'duplicate DAG node: ' + name)
        check(all(x in self.nodes for x in depends), 'unresolved DAG dependencies')
        keys = {k:self.nodes[k] for k in depends}
        descriptor = {'schema':SCHEMA, 'code_version':CODE_VERSION,
                      'name':name, 'operation':operation, 'engine':engine,
                      'engine_version':version(engine,self.numpy_salt),
                      'dependencies':keys, 'params':params}
        key = digest(descriptor)
        file = self.cache / (key+'.json')
        if file.exists():
            try:
                row = json.loads(file.read_text(encoding='utf8'))
            except (ValueError, OSError) as e:
                raise ValueError('corrupted cached JSON: ' + name) from e
            check(type(row) is dict and set(row)=={'descriptor','key','payload','payload_sha256'},
                  'cache fields missing or unexpected')
            check(row['descriptor']==descriptor and row['key']==key,
                  'cache descriptor mismatch: '+name)
            check(row['payload_sha256']==digest(row['payload']),
                  'cache payload corrupted: '+name)
            payload = row['payload']
            self.reused.append(name)
        else:
            payload = callback({d:self.values[d] for d in depends})
            # Verify serialization before marking persistent cache as usable.
            phase1.canonical(payload)
            row = {'descriptor':descriptor, 'key':key, 'payload':payload,
                   'payload_sha256':digest(payload)}
            write_json(file,row)
            self.computed.append(name)
        self.nodes[name]=key
        self.values[name]=payload
        return payload


def build(cache, variant='base', numpy_salt='default'):
    check(variant in {'base','shifted'}, 'unknown synthetic scenario')
    check(numpy_salt in {'default','v2'}, 'unsupported version salt')
    dag = CalcDAG(cache,numpy_salt)
    cases=copy.deepcopy(phase1.make_cases()['cases'])
    if variant == 'shifted':
        item=next(c for c in cases if c['case_id']=='rational_input')
        item['substitution']['x']=phase1.rat_node(2,7)
    for case in cases:
        phase1.check_envelope(case)
        cid=case['case_id']
        src='source_'+cid
        exact='exact_'+cid
        n='numpy_'+cid
        m='mpmath_'+cid
        v='validated_'+cid
        dag.eval(src,'canonical_source','Source',[],{'case':case}, lambda d, case=case: case)
        dag.eval(exact,'exact_sympy','SymPy',[src],{},
                 lambda d,src=src: phase1.sympy_eval(d[src]))
        dag.eval(n,'explicit_binary64','NumPy',[exact],{'dtype':'float64'},
                 lambda d,exact=exact: phase2.numpy_repr(phase2.fraction_of(d[exact])))
        dag.eval(m,'explicit_high_precision','mpmath',[exact],
                 {'work_dps':phase2.WORK_DPS,'output_digits':phase2.OUTPUT_DIGITS},
                 lambda d,exact=exact: phase2.mpmath_repr(phase2.fraction_of(d[exact])))
        def validate(d,src=src,exact=exact,n=n,m=m):
            reference=phase2.case_record(d[src])
            check(reference['exact']==d[exact], 'exact result mismatch')
            check(reference['numpy']==d[n], 'NumPy precision record mismatch')
            check(reference['mpmath']==d[m], 'mpmath precision record mismatch')
            return {'case_id':d[src]['case_id'], 'source_sha256':digest(d[src]),
                    'exact':d[exact], 'numpy':d[n], 'mpmath':d[m],
                    'unit':d[src]['unit'], 'assumptions':d[src]['symbols']}
        dag.eval(v,'validate_exact_and_approx','SymPy',[src,exact,n,m],{},validate)
    dag.eval('scipy_reference','quadrature_reference','SciPy',[],
             {'integral':'x^2 on [0,1]','tolerance':'1e-12'},lambda d:phase2.scipy_record())
    inputs=['validated_'+c['case_id'] for c in cases]+['scipy_reference']
    def aggregate(d):
        con=duckdb.connect(':memory:')
        con.execute('CREATE TABLE t(case_id VARCHAR, unit VARCHAR, n VARCHAR, den VARCHAR)')
        for c in cases:
            record=d['validated_'+c['case_id']]
            node=record['exact']
            con.execute('INSERT INTO t VALUES (?, ?, ?, ?)',
                        (record['case_id'],record['unit'],node['numerator'],node['denominator']))
        found=con.execute('SELECT unit, n, den FROM t ORDER BY unit, n, den').fetchall()
        summary={}
        for unit,n,den in found:
            group=summary.setdefault(unit,{'count':0,'sum':Fraction()})
            group['count']+=1
            group['sum']+=Fraction(int(n),int(den))
        con.close()
        groups={unit:{'count':v['count'],'exact_sum':phase1.rat_node(v['sum'].numerator,v['sum'].denominator)}
                for unit,v in sorted(summary.items())}
        check(sum(v['count'] for v in groups.values())==len(cases), 'incomplete DuckDB summary')
        return {'groups':groups, 'case_count':len(cases),
                'scipy':d['scipy_reference'], 'case_ids':[c['case_id'] for c in cases],
                'unit_policy':'metadata labels only; no dimensional algebra'}
    result=dag.eval('duckdb_summary','grouped_exact_sum','DuckDB',inputs,{},aggregate)
    # For synthetic scenarios, independently derive the expected exact grouped sums.
    expected={}
    for case in cases:
        unit=case['unit']; expected[unit]=expected.get(unit,Fraction())+phase2.fraction_of(phase1.sympy_eval(case))
    check({unit:phase2.fraction_of(row['exact_sum']) for unit,row in result['groups'].items()}==expected,
          'summary does not match independent exact reference')
    return {'schema':SCHEMA, 'scenario':variant, 'numpy_salt':numpy_salt,
            'cache_keys':dag.nodes, 'computed':dag.computed, 'reused':dag.reused,
            'result':result, 'result_sha256':digest(result)}


def audit(cache, first, second, shifted, numpy_changed):
    a,b,c,d=[json.loads(Path(p).read_text(encoding='utf8')) for p in (first,second,shifted,numpy_changed)]
    for doc in (a,b,c,d):
        check(doc['schema']==SCHEMA and doc['result_sha256']==digest(doc['result']), 'invalid manifest')
    keys=set(a['cache_keys']);check(len(keys)==27,'unexpected DAG size')
    check(set(a['computed'])==keys and a['reused']==[], 'cold build did not compute every node')
    check(b['cache_keys']==a['cache_keys'] and b['computed']==[] and set(b['reused'])==keys,
          'warm run not fully cached')
    changed={'source_rational_input','exact_rational_input', 'numpy_rational_input',
             'mpmath_rational_input','validated_rational_input','duckdb_summary'}
    check(set(c['computed'])==changed and set(c['reused'])==keys-changed,
          'source change did not invalidate exactly its dependent nodes')
    check(c['result_sha256']!=a['result_sha256'], 'scenario change failed to change result')
    # New numpy version invalidates all float nodes, their validators and aggregate.
    v2={'numpy_'+x for x in ('third_exact','negative_exact','boundary_zero','rational_input','large_integer')}
    v2|={'validated_'+x for x in ('third_exact','negative_exact','boundary_zero','rational_input','large_integer')}
    v2|={'duckdb_summary'}
    check(set(d['computed'])==v2 and set(d['reused'])==keys-v2,
          'engine-version change did not invalidate correct descendants')
    print('PASS 27-node cold DAG, fully cached repeat, exact 6-node scenario invalidation')
    print('PASS NumPy version change: exactly 11 dependent nodes recalculated')
    # Keep the original cache safe; corruption is injected in an independent copy.
    with TemporaryDirectory() as temp:
        shutil.copytree(cache,Path(temp)/'cache')
        key=a['cache_keys']['exact_third_exact']
        path=Path(temp)/'cache'/(key+'.json')
        row=json.loads(path.read_text(encoding='utf8'))
        row['payload']['numerator']='999'
        write_json(path,row)
        try:
            build(Path(temp)/'cache','base','default')
        except ValueError as exc:
            check('corrupted' in str(exc), 'wrong tamper detection failure')
            print('PASS cache corruption rejected rather than silently reused')
        else:
            raise AssertionError('corrupted cache was accepted')
    # Missing cache file must be recomputed with all unaffected nodes reused.
    with TemporaryDirectory() as temp:
        shutil.copytree(cache,Path(temp)/'cache')
        key=a['cache_keys']['exact_third_exact']
        (Path(temp)/'cache'/(key+'.json')).unlink()
        outcome=build(Path(temp)/'cache','base','default')
        check(outcome['computed']==['exact_third_exact'], 'missing cache not selectively rebuilt')
        print('PASS missing cache selectively rebuilt')
    print('PHASE 4: PASS all DAG, persistence, versioned invalidation, corruption and rebuild tests')


if __name__=='__main__':
    command=sys.argv[1]
    if command=='run' and len(sys.argv)==6:
        _,_,cache,report,variant,salt=sys.argv
        doc=build(cache,variant,salt)
        write_json(report,doc)
        print('DAG RESULT',variant,salt,'computed',len(doc['computed']),'reused',len(doc['reused']))
    elif command=='audit' and len(sys.argv)==7:
        _,_,cache,a,b,c,d=sys.argv
        audit(cache,a,b,c,d)
    else:
        raise SystemExit('usage: phase4.py run CACHE REPORT base|shifted default|v2 | audit CACHE BASE1 BASE2 SHIFTED V2')