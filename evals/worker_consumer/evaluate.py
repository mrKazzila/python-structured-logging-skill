#!/usr/bin/env python3
"""Frozen observable worker evaluator. No private helper inspection or dependencies."""
import argparse
import collections
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SECRETS = ['SYNTHETIC_DEPENDENCY_SECRET','SYNTHETIC_BARE_SECRET','SYNTHETIC_PAYLOAD_SECRET',
           'SYNTHETIC_AUDIT_SECRET','SYNTHETIC_TOKEN_SECRET']


def parse(observation):
    records, invalid = [], []
    def reject(value):
        raise ValueError(value)
    for line in (observation['stdout']+'\n'+observation['stderr']).splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line, parse_constant=reject)
            if not isinstance(value,dict) or not all(isinstance(value.get(k),str) for k in ('event','level')):
                raise ValueError('envelope')
            records.append(value)
        except (ValueError,TypeError):
            invalid.append(line)
    return records, invalid


def grade(observations):
    work = observations['workload']; meta = work['metadata']; records, invalid = parse(work)
    criteria = []
    def check(name, passed, evidence):
        criteria.append({'id':name,'passed':bool(passed),'evidence':evidence})
    expected_results = [{'message_id':'ok','amount_cents':123},'retry',
                        {'message_id':'redelivered','amount_cents':123},'dead_letter','dead_letter',
                        {'type':'RuntimeError','message':'SYNTHETIC_BARE_SECRET'},
                        {'message_id':'audit','amount_cents':123}]
    expected_dispositions = [['ok','ack',1],['retry','retry',1],['redelivered','ack',2],
                             ['poison','dead_letter',1],['exhausted','dead_letter',3],
                             ['unexpected','retry',1],['audit','ack',1]]
    expected_exceptions = [{'type':'RetryableError','message':'upstream credential=SYNTHETIC_DEPENDENCY_SECRET'},
                           {'type':'PoisonError','message':'invalid payload SYNTHETIC_PAYLOAD_SECRET'},
                           {'type':'RuntimeError','message':'SYNTHETIC_BARE_SECRET'}]
    check('business_contract',meta['results']==expected_results and meta['payloads_preserved'] and
          meta['dependency_contracts']==expected_exceptions and
          sorted(meta['calls'])==sorted([[x[0],x[2]] for x in expected_dispositions]),meta)
    check('retry_ack_contract',sorted(meta['dispositions'])==sorted(expected_dispositions) and
          meta['direct_error']==expected_exceptions[2] and meta['direct_dispositions']==[],meta['dispositions'])
    check('cancellation_contract',meta['cancelled'] and meta['cancel_dispositions']==[],
          {'cancelled':meta['cancelled'],'dispositions':meta['cancel_dispositions']})
    check('whole_runtime_json',bool(records) and not invalid,{'invalid_lines':invalid,'records':len(records)})
    raw=work['stdout']+work['stderr']; leaks=[s for s in SECRETS if s in raw]
    check('payload_credential_exception_safety',not leaks,leaks)
    probes=[r for r in records if r['event'] in ('probe.nested','probe.parent')]
    wrong=[r for r in probes if r.get('message_id')!=r.get('probe_message') or
           r.get('correlation_id')!='corr-'+r.get('probe_message','') or
           (r['event']=='probe.parent' and r.get('operation') is not None) or
           (r['event']=='probe.nested' and r.get('operation')!='nested')]
    check('concurrent_nested_context',collections.Counter((r['event'],r.get('probe_message')) for r in probes)==
          collections.Counter((event,name) for event in ('probe.nested','probe.parent')
                              for name in ('ok','retry','redelivered','poison','exhausted','unexpected','audit')) and not wrong,wrong)
    cleanup=[r for r in records if r['event']=='probe.cleanup']
    wrong=[r for r in cleanup if any(r.get(k) is not None for k in ('message_id','correlation_id','operation'))]
    scope={r['event']:r for r in records if r['event'].startswith('probe.scope_')}
    check('context_cleanup',collections.Counter(r.get('probe_message') for r in cleanup)==
          collections.Counter(('ok','retry','redelivered','poison','exhausted','unexpected','audit','direct','cancel')) and not wrong and
          set(scope)=={'probe.scope_inner','probe.scope_outer','probe.scope_clear'} and
          scope.get('probe.scope_inner',{}).get('message_id')=='inner' and
          scope.get('probe.scope_outer',{}).get('message_id')=='outer' and
          scope.get('probe.scope_inner',{}).get('correlation_id')=='corr-inner' and
          scope.get('probe.scope_outer',{}).get('correlation_id')=='corr-outer' and
          not any(scope.get('probe.scope_clear',{}).get(k) for k in ('message_id','correlation_id')),wrong or scope)
    ops=[r for r in records if not r['event'].startswith('probe.')]
    expected={'message.processed':{'ok','redelivered','audit'},'message.retry':{'retry'},
              'message.dead_letter':{'poison','exhausted'},'audit.failed':{'audit'}}
    wrong=[]
    for event, ids in expected.items():
        found=[r for r in ops if r['event']==event]
        if collections.Counter(r.get('message_id') for r in found)!=collections.Counter(ids):
            wrong.append({'event':event,'records':found})
        for r in found:
            if r.get('correlation_id')!='corr-'+r.get('message_id',''):
                wrong.append(r)
    check('event_contracts',not wrong,wrong)
    failures={}
    for name in ('retry','poison','exhausted','unexpected','audit'):
        # Success access summaries are not duplicate diagnoses. Failure diagnoses
        # include warning/error OR explicit retry/dead-letter/failure event semantics.
        failures[name]=[r for r in ops if r.get('message_id')==name and
                        (r['level'].lower() in ('warning','error','critical') or
                         any(part in r['event'] for part in ('retry','dead_letter','failed')))]
    unassigned=[r for r in ops if r['level'].lower() in ('warning','error','critical') and
                r.get('message_id') not in {*failures,'direct'}]
    direct_diagnostics=[r for r in ops if r.get('message_id')=='direct' and r['level'].lower() in ('warning','error','critical')]
    check('single_failure_ownership',all(len(v)==1 for v in failures.values()) and
          not unassigned and len(direct_diagnostics)<=1,{'by_message':failures,'unassigned':unassigned})
    check('background_failure',meta['background_remaining']==0 and
          sorted(meta['audit_started'])==['audit','ok','redelivered'] and
          sorted(meta['audit_completed'])==['audit','ok','redelivered'] and
          len([r for r in ops if r['event']=='audit.failed' and r.get('message_id')=='audit' and
               r.get('correlation_id')=='corr-audit'])==1,failures['audit'])
    cancel_errors=[r for r in ops if r.get('message_id')=='cancel' and r['level'].lower() in ('error','critical')]
    check('cancellation_level',not cancel_errors,cancel_errors)
    wrong=[]
    for r in ops:
        if r['event'] in ('message.processed','message.retry','message.dead_letter'):
            outcome={'message.processed':'ack','message.retry':'retry','message.dead_letter':'dead_letter'}[r['event']]
            expected_attempt={'redelivered':2,'exhausted':3}.get(r.get('message_id'),1)
            if r.get('attempt')!=expected_attempt or r.get('outcome')!=outcome:
                wrong.append(r)
            if r['event']=='message.processed' and r.get('amount_cents')!=123:
                wrong.append(r)
        if 'duration' in r or ('duration_ms' in r and (not isinstance(r['duration_ms'],(int,float)) or r['duration_ms']<0)):
            wrong.append(r)
    for name, found in failures.items():
        for r in found:
            if r.get('correlation_id')!='corr-'+name or r.get('attempt')!=(3 if name=='exhausted' else 1):
                wrong.append(r)
            if name in ('unexpected','audit') and r.get('outcome')!='failed':
                wrong.append(r)
            if name=='retry' and r.get('retryable') is not True:
                wrong.append(r)
            if name in ('poison','exhausted') and r.get('retryable') is not False:
                wrong.append(r)
    check('outcome_fields_units',not wrong,wrong)
    names=[r['event'] for r in ops]
    dynamic=[n for n in names if any(x in n for x in ('processing_','corr-','SYNTHETIC_'))]
    # Seven batch attempts + direct/cancel + one audit error, up to two lifecycle
    # records, plus a small allowance for useful operational summaries.
    info_ops=[r for r in ops if r['level'].lower()!='debug']
    check('bounded_events_noise',not dynamic and len(info_ops)<=14,{'dynamic':dynamic,'count':len(info_ops),'budget':14})
    for case in ('nonfinite','object','key','cycle'):
        o=observations[case]; rs,bad=parse(o); text=o['stdout']+o['stderr']
        unsafe=[s for s in [*SECRETS,'--- Logging error ---','WORKER_SOURCE_SENTINEL'] if s in text]
        recovery=[r for r in rs if r['event']=='probe.recovery']
        diagnostics, emission_invalid=parse(o['metadata']['emission'])
        recovery_records, recovery_invalid=parse(o['metadata']['recovery'])
        check('formatter_'+case,o['metadata']['raised'] is None and o['metadata']['recovery_raised'] is None
              and len(recovery)==1 and any(r['event']=='probe.recovery' for r in recovery_records)
              and bool(diagnostics) and not emission_invalid and not recovery_invalid and not bad and not unsafe,
              {'metadata':o['metadata'],'unsafe':unsafe,'invalid':bad,'records':rs})
    return {'passed':all(c['passed'] for c in criteria),'criteria':criteria,
            'metrics':{'event_counts':dict(collections.Counter(names)), 'operational_records':len(ops),
                       'json_records':len(records),'raw_lines':len(invalid)},'observations':observations}


def evaluate(project):
    observations={}
    with tempfile.TemporaryDirectory(prefix='consumer-eval-') as tmp:
        for case in ('workload','nonfinite','object','key','cycle'):
            metadata=Path(tmp)/f'{case}.json'
            run=subprocess.run([sys.executable,'-I','-B',str(HERE/'probe.py'),str(project.resolve()),case,str(metadata)],
                               capture_output=True,text=True,timeout=25,cwd=project)
            if run.returncode or not metadata.exists():
                raise RuntimeError(f'{case} probe setup/execution failed: {run.returncode}\n{run.stderr}')
            observations[case]={'stdout':run.stdout,'stderr':run.stderr,'metadata':json.loads(metadata.read_text())}
    return grade(observations)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('project',type=Path); parser.add_argument('report',type=Path)
    args=parser.parse_args()
    with args.report.open('x') as output:
        result=evaluate(args.project); json.dump(result,output,indent=2); output.write('\n')
    print(json.dumps({c['id']:c['passed'] for c in result['criteria']},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
