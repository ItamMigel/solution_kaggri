"""Frozen paired-world execution gate, bounded CPU and zero swallowed BC errors."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import random
import signal
import sys
import time
import traceback
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PAVEL=Path('/workspace/shared/pavel_lab/lab/pavel/candidates')
OPPS={
 'tetsu':PAVEL/'tetsu1009_public/main.py',
 'qA':PAVEL/'tetsu1009_wm_qA/main.py',
 'ozer44':HERE.parent/'public/ozer44/main.py',
 'yaxon5':Path('/workspace/shared/opponents/pool/yaxon_reactive_v5/main.py'),
 'jaxa2802':HERE.parent/'public/jaxa2802/main.py',
 'parthenos':Path('/workspace/shared/opponents/pool/parthenos_robust/main.py'),
 'bc_m15ens':PAVEL/'bc_hg_m15ens_d13/main.py',
 'bc_mix4':PAVEL/'bc_hg_mix4_d13/main.py',
}

OPPS = {name: HERE / 'frozen' / (name + '.py') for name in OPPS}


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m);return m


def terminal_replay(env, module, seat):
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    previous=env.steps[-2];last=env.steps[-1]
    obs=copy.deepcopy(previous[0].observation)
    assert obs['step']==718
    actions=[copy.deepcopy(s.action) for s in last]
    private=[copy.deepcopy(s.observation.private) for s in previous]
    own=copy.deepcopy(obs);own['private']=copy.deepcopy(private[seat]);own['player']=seat
    changed=module._T045_TERM['liquidate'](own,actions[seat],dict(env.configuration),module._T045_ENGINE,True)
    assert changed['farmer']==actions[seat]['farmer'] and changed['hands']==actions[seat]['hands']
    def finish(override):
        o=copy.deepcopy(obs); priv=copy.deepcopy(private);acts=copy.deepcopy(actions)
        if override is not None:acts[seat]=override
        for p in (0,1):
            ua=[acts[p].get('farmer',['PASS'])]+acts[p].get('hands',[])
            demand=Counter(a[1] for a in ua if a and a[0]=='PLANT' and len(a)>1)
            blocked={it for it,n in demand.items() if n>priv[p]['seeds'].get(it,0)}
            for i,a in enumerate(ua):
                if a and a[0]=='PLANT' and a[1] in blocked:a=['PASS']
                K._apply_unit_action(o['farms'][p],priv[p],i,a,10,29,24,100)
        state=[SimpleNamespace(action=acts[p],observation=SimpleNamespace(farms=o['farms'],market=o['market'],private=priv[p])) for p in (0,1)]
        K._process_market(state,SimpleNamespace(configuration=env.configuration))
        return [f['money'] for f in o['farms']]
    actual=[s.reward for s in env.state]
    reproduced=finish(None)
    assert reproduced==actual,(reproduced,actual)
    return dict(rewards=finish(changed),changed=changed!=actions[seat],before=actions[seat]['market'],after=changed['market'],exact_baseline=True)


_BASE_CACHE = {}


def identity_certificate(base, variant, opp, seed, seat):
    path = os.environ.get('T045_BASELINE_RESULTS')
    if not path or variant not in ('a1', 'a2'):
        return None
    key = (base, opp, seed, seat)
    if key not in _BASE_CACHE:
        try:
            lines = Path(path).read_text().splitlines()
        except FileNotFoundError:
            return None
        for line in lines:
            try: r = json.loads(line)
            except json.JSONDecodeError: continue  # writer may be between chunks
            if r['variant'] == 'off' and r['valid']:
                _BASE_CACHE[(r['base'], r['opp'], r['seed'], r['seat'])] = r
    r = _BASE_CACHE.get(key)
    if r is None or r['counts'].get('shadow_calls') != 719 or r['counts'].get('shadow_' + variant + '_changed_turns', 0):
        return None
    result = copy.deepcopy(r)
    result.pop('terminal', None)
    result.update(variant=variant, seconds=0.0, evaluation='exact_identity_from_baseline',
                  identity_from={'base':base, 'opp':opp, 'seed':seed, 'seat':seat, 'variant':'off'},
                  proof='Identical source except flags; enabled HG invoked on all 719 native actions with zero action differences; deterministic full trajectory identical by induction.')
    return result


def game(job):
    base,variant,opp,seed,seat,identity=job
    certificate = identity_certificate(base,variant,opp,seed,seat)
    if certificate is not None:
        return certificate
    rec=dict(base=base,variant=variant,opp=opp,seed=seed,seat=seat,evaluation='full_game')
    t0=time.monotonic();log=io.StringIO();counts=Counter();timings=[];examples=[]
    def alarm(signum,frame):raise TimeoutError('game exceeded 300s')
    signal.signal(signal.SIGALRM,alarm);signal.alarm(300)
    try:
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            import numpy as np
            from kaggle_environments import make
            random.seed(seed);np.random.seed(seed)
            mod=load(HERE/'exports'/f'{base}_{variant}.py','t045_candidate')
            opponent=load(OPPS[opp],'t045_opponent')
            original=load(PAVEL/f'bc_hg_{base}_d13/main.py','t045_original') if identity else None
            # Frozen opponents retain original actions; proxy records BC exceptions
            # before their existing wrapper can swallow them as PASS.
            if hasattr(opponent,'_AG'):
                core=opponent._AG
                def guarded(*args,**kw):
                    try:return core(*args,**kw)
                    except Exception:
                        counts['opponent_bc_exceptions']+=1
                        raise
                opponent._AG=guarded
            hg=mod._hg_apply
            def monitored_hg(obs,action):
                before=copy.deepcopy(action)
                result=hg(obs,action)
                ba=[before['farmer']]+before['hands'];aa=[result['farmer']]+result['hands']
                farm=obs['farms'][obs['player']];pos=[farm['farmer']]+farm['hands'];invs=obs['private']['inventories']
                for i,(b,a) in enumerate(zip(ba,aa)):
                    if b!=a:
                        counts['hg_unit_changes']+=1
                        if b and b[0]=='FEED' and invs[i].get('WHEAT',0)>0:
                            x,y=pos[i];tile=farm['tiles'][y][x]
                            if isinstance(tile,dict) and tile.get('animal') and not tile.get('fed_today'):
                                counts['native_feed_overwritten']+=1
                                if tile.get('consecutive_unfed',0)>=1:counts['urgent_native_feed_overwritten']+=1
                if variant == 'off':
                    flags = mod._T045_FLAGS.copy(); stats = mod._HG_STATS.copy()
                    for fix in ('a1', 'a2'):
                        mod._T045_FLAGS.update(a1=fix=='a1', a2=fix=='a2')
                        shadow = hg(obs,copy.deepcopy(before))
                        if shadow != result:
                            counts['shadow_' + fix + '_changed_turns'] += 1
                            if len(examples) < 2:
                                examples.append({'fix':fix,'step':obs['step'],'before':before,'old_hg':result,
                                                 'new_hg':shadow,'farm':copy.deepcopy(farm),'private':copy.deepcopy(obs['private'])})
                    counts['shadow_calls'] += 1
                    mod._T045_FLAGS.update(flags); mod._HG_STATS.clear(); mod._HG_STATS.update(stats)
                if int(obs['step'])<336:
                    flags=mod._T045_FLAGS.copy();stats=mod._HG_STATS.copy()
                    mod._T045_FLAGS.update(a1=False,a2=False)
                    native=hg(obs,copy.deepcopy(before))
                    mod._T045_FLAGS.update(flags);mod._HG_STATS.clear();mod._HG_STATS.update(stats)
                    if native!=result:
                        counts['fix_changed_turns']+=1
                        if len(examples)<2:
                            examples.append({'step':obs['step'],'before':before,'old_hg':native,'new_hg':result})
                return result
            mod._hg_apply=monitored_hg
            def candidate(obs,config=None):
                begin=time.perf_counter();out=mod.agent(obs,config);timings.append(time.perf_counter()-begin)
                counts['calls']+=1
                if original is not None:
                    expected=original.agent(obs,config)
                    if variant=='off' or int(obs['step'])<718:
                        assert out==expected,(base,variant,obs['step'],'identity')
                        counts['identity_calls']+=1
                return out
            env=make('kaggriculture',configuration={'seed':seed},debug=False)
            pair=[opponent.agent,opponent.agent];pair[seat]=candidate
            env.run(pair)
            rec.update(rewards=[s.reward for s in env.state],status=[s.status for s in env.state])
            rec['errors']=dict(mod._T045_ERRORS, hg=mod._HG_STATS['errors'],
                              opponent_hg=getattr(opponent,'_HG_STATS',{}).get('errors',0),
                              opponent_bc=counts['opponent_bc_exceptions'])
            assert rec['status']==['DONE','DONE'],rec['status']
            assert counts['calls']==719,counts
            assert not any(rec['errors'].values()),rec['errors']
            assert sum(max(0,t-1) for t in timings)<55,'overage budget'
            if variant=='off':rec['terminal']=terminal_replay(env,mod,seat)
            rec['valid']=True
    except BaseException:
        rec.update(valid=False,exception=traceback.format_exc())
    finally:
        signal.alarm(0)
    rec.update(seconds=time.monotonic()-t0,counts=dict(counts),examples=examples,
               latency={'max':max(timings,default=0),'p99':float(np.quantile(timings,.99)) if timings else 0,
                        'overage':sum(max(0,t-1) for t in timings)},output_tail=log.getvalue()[-1500:])
    return rec


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--workers',type=int,default=20)
    ap.add_argument('--variants',default='off,a1,a2');ap.add_argument('--worlds',type=int,default=32)
    ap.add_argument('--opponents',default=','.join(OPPS));ap.add_argument('--identity',action='store_true')
    ap.add_argument('--seed-start',type=int,default=929452001);ap.add_argument('--bases',default='m15ens,mix4')
    a=ap.parse_args();assert 1<=a.workers<=20
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    seeds=list(range(a.seed_start,a.seed_start+a.worlds))
    opponents=a.opponents.split(',');variants=a.variants.split(',')
    manifest={'seeds':seeds,'variants':variants,'workers':a.workers,'both_seats':True,
              'opponents':{k:{'path':str(OPPS[k]),'sha256':hashlib.sha256(OPPS[k].read_bytes()).hexdigest()} for k in opponents},
              'exports':json.loads((HERE/'manifest.json').read_text()),'identity':a.identity}
    mf=out/'manifest.json'
    if mf.exists():assert json.loads(mf.read_text())==manifest,'manifest changed'
    else:mf.write_text(json.dumps(manifest,indent=2))
    # All exports use byte-identical code apart from their constant feature flags.
    import re
    normalized = {}
    for b in a.bases.split(','):
        for v in ('off','terminal','a1','a2'):
            src = (HERE/'exports'/f'{b}_{v}.py').read_text()
            canon = re.sub(r'^_T045_FLAGS = .*$', '_T045_FLAGS = FLAGS', src, flags=re.M)
            h = hashlib.sha256(canon.encode()).hexdigest()
            if b in normalized: assert normalized[b] == h
            normalized[b] = h
    (out/'identity_source_hashes.json').write_text(json.dumps(normalized,indent=2))
    results=out/'games.jsonl'
    os.environ['T045_BASELINE_RESULTS'] = str(results)
    done=set()
    if results.exists():
        for line in results.read_text().splitlines():
            r=json.loads(line);done.add((r['base'],r['variant'],r['opp'],r['seed'],r['seat']))
    jobs=[(b,v,o,s,p,a.identity) for v in variants for s in seeds for b in a.bases.split(',') for o in opponents for p in (0,1)
          if (b,v,o,s,p) not in done]
    print(json.dumps({'jobs':len(jobs),'existing':len(done),'manifest':str(mf)}),flush=True)
    with results.open('a',buffering=1) as f, ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(game,j) for j in jobs]
        for i,fu in enumerate(as_completed(futures),1):
            rec=fu.result();f.write(json.dumps(rec)+'\n')
            if not rec['valid'] or i%16==0 or i==len(jobs):
                print(json.dumps({'done':i,'total':len(jobs),'last':{k:rec.get(k) for k in ('base','variant','opp','seed','seat','valid','seconds','exception')}}),flush=True)
    print('DONE',flush=True)

if __name__=='__main__':main()
