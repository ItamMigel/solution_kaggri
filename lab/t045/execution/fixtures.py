import contextlib
import copy
import io
import json
import random
from pathlib import Path
from types import SimpleNamespace
import build
from terminal import liquidate, post_unit_shed


def main():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        import kaggle_environments.envs.kaggriculture.kaggriculture as K
    vendor = {}; exec(build.unit_engine_source(), vendor)
    env = make('kaggriculture', configuration={'seed': 929451001})
    obs = copy.deepcopy(env.reset()[0].observation)
    obs['step'] = 718; obs['player'] = 0
    config = dict(env.configuration)
    obs['farms'][0]['farmer'] = [4,4]
    obs['farms'][0]['hands'] = [[4,4], [5,4]]
    obs['private']['inventories'] = [{'MILK': 5, 'WOOL': 5}, {'WHEAT': 5}, {'EGG': 4}]
    obs['private']['shed'] = {'WHEAT': 98}
    action = {'farmer': ['DROP'], 'hands': [['PICKUP','MILK',1], ['DROP']], 'market': []}
    before = copy.deepcopy(obs)
    post = post_unit_shed(obs, action, config, vendor)
    assert post == {'WHEAT':98,'MILK':1,'EGG':1}, post
    assert obs == before
    r = liquidate(obs, action, config, vendor, True)
    assert r['farmer'] == action['farmer'] and r['hands'] == action['hands']
    assert {x[1]:x[2] for x in r['market']} == post
    # Sequential animal PLACE: first fills structure, second deposits into shed.
    obs['farms'][0]['tiles'][4][4] = {'kind':'PASTURE'}
    obs['private']['shed'] = {}
    obs['private']['inventories'] = [{'COW':1}, {'COW':1}, {}]
    a = {'farmer':['PLACE','COW'], 'hands':[['PLACE','COW']], 'market':[]}
    assert post_unit_shed(obs,a,config,vendor) == {'COW':1}
    # New purchases are unavailable to units, but a later SELL can liquidate them.
    obs['private']['inventories'] = [{},{},{}]
    obs['private']['shed'] = {'WHEAT':5,'MILK':2}
    a = {'farmer':['PASS'],'hands':[], 'market':[['SELL','WHEAT',2], ['BUY_PRODUCT','WHEAT',7], ['NOOP'], ['SELL','WHEAT',1]]}
    r = liquidate(obs,a,config,vendor,True)
    assert r['market'][:3] == a['market'][:3]
    assert r['market'][3] == ['SELL','WHEAT',10]
    assert r['market'][4] == ['SELL','MILK',2]
    # Capacity/running cash can reduce a buy fill: upper-bound SELL stays legal.
    for cash in (0, 10, 100000):
        for variant in (a,r):
            farms = copy.deepcopy(obs['farms']); farms[0]['money']=cash
            market = copy.deepcopy(obs['market'])
            priv = [copy.deepcopy(obs['private']), {'shed':{},'seeds':{},'inventories':[{}]}]
            state = [SimpleNamespace(action=variant if p==0 else {'market':[]},
                     observation=SimpleNamespace(farms=farms,market=market,private=priv[p])) for p in (0,1)]
            K._process_market(state,SimpleNamespace(configuration=config))
            assert all(n>=0 for n in priv[0]['shed'].values())
    full = dict(a,market=[['NOOP']]*9+[['BUY_PRODUCT','WHEAT',1]])
    assert liquidate(obs,full,config,vendor,True) == full
    full = dict(a,market=[['NOOP']]*9+[['SELL','MILK',1]])
    out=liquidate(obs,full,config,vendor,True)
    assert len(out['market'])==10 and out['market'][-1]==['SELL','MILK',2]
    for step in range(719):
        obs['step']=step
        assert liquidate(obs,a,config,vendor,False) is a
        if step<718: assert liquidate(obs,a,config,vendor,True) is a
    # Official engine vs standalone exact unit subset, overflow and shared tile states.
    rng=random.Random(929451001)
    for _ in range(100):
        obs['step']=718
        obs['private']['shed']={'WHEAT':rng.randrange(101)}
        obs['private']['inventories']=[{'MILK':rng.randrange(15),'COW':1} for i in range(3)]
        obs['farms'][0]['tiles'][4][4]={'kind':'PASTURE'}
        ops=[rng.choice([['DROP'],['PICKUP','WHEAT',9],['PLACE','MILK',3],['PLACE','COW'],['DIG'],['BUILD_PASTURE']]) for i in range(3)]
        a={'farmer':ops[0],'hands':ops[1:],'market':[]}
        farm=copy.deepcopy(obs['farms'][0]); priv=copy.deepcopy(obs['private'])
        for i,op in enumerate(ops):K._apply_unit_action(farm,priv,i,op,10,29,24,100)
        assert post_unit_shed(obs,a,config,vendor)==priv['shed']
    # Extract only HG (no neural/model load), with both fixes default off.
    source=build.BASES['m15ens'].read_text()
    hg=source[source.index('# ================= HG:'):]
    patched=build.build_source(source,'off')
    patched=patched[patched.index('# ================= HG:'):patched.index('\n_T045_ENGINE =')]
    orig={'agent':lambda o,c=None:{}};exec(hg,orig)
    new={'agent':lambda o,c=None:{}};exec(patched,new)
    tiles=[[None]*10 for _ in range(10)]
    for x in (4,5):tiles[4][x]={'kind':'PASTURE','animal':'COW','consecutive_unfed':1,'fed_today':False}
    o={'player':0,'step':23,'farms':[{'tiles':tiles,'farmer':[4,4],'hands':[],'money':0}],
       'private':{'shed':{},'inventories':[{'WHEAT':2}]},'market':{'prices':{'WHEAT':30}}}
    a={'farmer':['FEED'],'hands':[],'market':[]}
    assert orig['_hg_apply'](o,copy.deepcopy(a))['farmer']==['EAST']
    assert new['_hg_apply'](o,copy.deepcopy(a))==orig['_hg_apply'](o,copy.deepcopy(a))
    new['_T045_FLAGS']['a1']=True
    assert new['_hg_apply'](o,copy.deepcopy(a))['farmer']==['FEED']
    new['_T045_FLAGS']['a1']=False;new['_T045_FLAGS']['a2']=True
    o['farms'][0]['farmer']=[0,0];a['farmer']=['HARVEST']
    assert orig['_hg_apply'](o,copy.deepcopy(a))['farmer']!=['HARVEST']
    assert new['_hg_apply'](o,copy.deepcopy(a))['farmer']==['HARVEST']
    o['farms'][0]['farmer']=[4,4];o['private']['inventories']=[{'WHEAT':1}];a['farmer']=['PASS']
    assert new['_hg_apply'](o,copy.deepcopy(a))['farmer']==['FEED']
    o['step']=14*24+23
    assert new['_hg_apply'](o,copy.deepcopy(a))==a
    report={'status':'PASS','unit_engine_random_fixtures':100,'identity_steps':719,
            'fixtures':['prefix BUY/SELL/NOOP','partial buy','full 10 slots','DROP overflow',
                        'farmer/hands sequential PLACE','A1 native urgent FEED','A2 unreachable and exact deadline','d13 unchanged']}
    (build.HERE/'fixtures.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
