"""Behavioral differential tests for money-moving wrappers; no model tuning."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import contextlib
import copy
import io
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import build
from postprocess import Postprocessor, SALE_PRODUCTS

def run():
    log=io.StringIO()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        from kaggle_environments import make
        env=make('kaggriculture',configuration={'seed':93048299},debug=False)
        env.reset(2)
    engine=env.interpreter.__globals__
    extracted={};exec((HERE/'market_engine.py').read_text(),extracted)
    term={};exec((HERE.parent/'t045/execution/terminal.py').read_text(),term)
    units={};exec(build.source_closure(build.ENGINE.read_text(),['_apply_unit_action']),units)
    rng=random.Random(4801);checks=[]
    template=copy.deepcopy(env.state)
    for k in range(120):
        s=copy.deepcopy(template);o=s[0].observation
        for item in engine['PRODUCTS']:
            o.market['inventory'][item]=10000+rng.randint(-800,800)
        for i in (0,1):
            s[i].observation.market=o.market;s[i].observation.farms=o.farms
            o.farms[i]['money']=rng.choice([0,25,100,10000])
            sd=s[i].observation.private['shed']
            sd.update({it:0 for it in sd})
            for _ in range(rng.randint(0,100)):
                sd[rng.choice(engine['PRODUCTS'])]+=1
            s[i].action={'market':[]}
            for _ in range(rng.randint(0,10)):
                op=rng.choice(['SELL','SELL','BUY_PRODUCT','BUY_SEED','HIRE','NOOP','BUY_LAND'])
                it=rng.choice(('WHEAT','FERTILIZER')) if op=='BUY_PRODUCT' else rng.choice(engine['PRODUCTS'])
                s[i].action['market'].append([op,it,rng.randint(0,120)] if op not in ('HIRE','NOOP','BUY_LAND') else [op])
        a,b=copy.deepcopy(s),copy.deepcopy(s)
        engine['_process_market'](a,env);extracted['_process_market'](b,env)
        assert a==b,(k,'official/extracted market mismatch')
    checks.append('120 randomized official/extracted complete market transitions exact')
    obs=copy.deepcopy(template[0].observation);obs['player']=0;obs['step']=672
    action={'farmer':['PASS'],'hands':[],'market':[['SELL','MILK',5],['HIRE'],['SELL','WOOL',4],['SELL','WHEAT',8]]}
    off=Postprocessor(extracted,units,term)
    before=copy.deepcopy((obs,action));assert off.apply(obs,action,env.configuration) is action
    assert before==(obs,action)
    checks.append('default-off returns identical object without mutation')
    obs.private.shed.update(MILK=5,WOOL=4,WHEAT=8)
    beam=Postprocessor(extracted,units,term,'sale_beam')
    before=copy.deepcopy((obs,action));new=beam.apply(obs,action,env.configuration)
    assert before==(obs,action)
    assert new['market'][:2]==action['market'][:2]
    assert sorted(new['market'][2:])==sorted(action['market'][2:])
    assert new['farmer']==action['farmer'] and new['hands']==action['hands']
    checks.append('beam preserves units, funding prefix, suffix multiset; inputs immutable')
    # Floor sales stop supply; product buy is quoted at post-buy inventory.
    obs.market.inventory['WOOL']=11000
    late=Postprocessor(extracted,units,term,'late_ev')
    assert late.batch_value(obs,'WOOL',11000,80)==80
    obs.town.unlocked_shops=['YARN_STORE','YARN_STORE','SMOOTHIE_SHOP']
    assert late.demand(obs,env.configuration,672,673,'WOOL')==5
    assert late.demand(obs,env.configuration,672,673,'MILK')==2
    assert late.demand(obs,env.configuration,673,676,'WOOL')==0
    checks.append('price floor and duplicate-town/boundary consumption exact')
    # Empty rival flow + a milk demand tick: postpone exactly eight units,
    # preserve NOOP index and explicitly release next turn even with empty BC queue.
    obs.market.inventory['MILK']=10010;engine['_refresh_prices'](obs.market)
    obs.private.shed.update({it:0 for it in obs.private.shed});obs.private.shed['MILK']=8
    obs.farms[0]['money']=10000
    late.flow={it:[0]*24 for it in SALE_PRODUCTS}
    native={'farmer':['PASS'],'hands':[],'market':[['SELL','MILK',8]]}
    new=late.schedule(obs,native,env.configuration,dict(obs.private.shed))
    assert new['market']==[['NOOP']],new
    assert late.pending=={'MILK':(673,8)}
    obs['step']=673
    release=late.schedule(obs,{'farmer':['PASS'],'hands':[],'market':[]},env.configuration,dict(obs.private.shed))
    assert release['market']==[['SELL','MILK',8]] and not late.pending,release
    checks.append('one-turn hold preserves slot, next-turn release explicitly executes')
    # Full shed or cash requirement forbids suppressing financing sales.
    for cash,stock in ((0,8),(10000,80)):
        late.pending={};obs['step']=672;obs.farms[0]['money']=cash;obs.private.shed['MILK']=stock
        new=late.schedule(obs,native,env.configuration,dict(obs.private.shed))
        assert new['market'][0]==native['market'][0]
    checks.append('holds fail open under cash/space pressure')
    # Known negative drift allows a bounded append, with existing orders intact.
    obs['step']=673;obs.farms[0]['money']=10000;obs.private.shed['MILK']=20
    late.flow['MILK']=[4]*24;late.pending={}
    native={'farmer':['PASS'],'hands':[],'market':[['HIRE'],['SELL','MILK',2]]}
    new=late.schedule(obs,native,env.configuration,dict(obs.private.shed))
    assert new['market'][:2]==native['market'] and new['market'][2]==['SELL','MILK',8],new
    checks.append('negative-flow EV appends at most8 after protected prefix')
    result={'passed':True,'checks':checks}
    (HERE/'fixtures.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':run()
