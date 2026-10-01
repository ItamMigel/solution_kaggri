"""Small deterministic counterexamples using the installed official engine source."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

SOURCE = Path('/workspace/solution_kaggri/.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py')


def engine():
    tree = ast.parse(SOURCE.read_text())
    # Avoid package registration/import noise. All engine definitions are verbatim;
    # only the unused environment seed resolver import is excluded.
    tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module == 'kaggle_environments.utils')]
    ns = {'__file__': str(SOURCE), '__name__': 't046_official_engine'}
    exec(compile(tree, str(SOURCE), 'exec'), ns)
    return NS(**ns)


def mirror(f):
    f = copy.deepcopy(f)
    f['tiles'] = [row[::-1] for row in f['tiles']]
    f['farmer'][0] = 9-f['farmer'][0]
    f['hands'] = [[9-x,y] for x,y in f['hands']]
    f['unlocked_quadrants'] = [{'NW':'NE','NE':'NW','SW':'SE','SE':'SW'}[q] for q in f['unlocked_quadrants']]
    return f


def market(k, own_orders, rival_orders):
    farms = [k._new_farm(10,10000) for _ in range(2)]
    privates = [k._new_private() for _ in range(2)]
    for p in privates:
        p['shed']['STRAWBERRY'] = 2
    m = k._new_market()
    state = [NS(action={'market':orders}, observation=NS(farms=farms,market=m,private=privates[i]))
             for i,orders in enumerate([own_orders,rival_orders])]
    k._process_market(state, NS(configuration={}))
    return dict(cash=[f['money'] for f in farms], shed=[p['shed']['STRAWBERRY'] for p in privates],
                strawberry_inventory=m['inventory']['STRAWBERRY'])


def night(k, move):
    farms=[k._new_farm(10,10000) for _ in range(2)]
    privates=[k._new_private() for _ in range(2)]
    farms[0]['farmer']=[1,1]
    farms[0]['hands']=[[4,4],[5,5]]
    farms[0]['hires_today']=2
    privates[0]['inventories']=[{'MILK':3},{'WHEAT':4},{'WOOL':2}]
    m=k._new_market(); town=k._new_town()
    state=[NS(action={'farmer':['EAST'] if move and i==0 else ['PASS'],
                      'hands':[['WEST'],['NORTH']] if move and i==0 else [['PASS'],['PASS']],
                      'market':[['HIRE']] if i==0 else []},
              observation=NS(step=23,player=i,day=0,hour=23,farms=farms,market=m,town=town,private=privates[i]))
           for i in (0,1)]
    env=NS(configuration=NS(episodeSteps=720),done=False,info={'seed':46000})
    k.interpreter(state,env)
    return dict(farms=farms,private=privates,market=m,town=town,day=state[0].observation.day)


def main():
    k = engine()
    f = k._new_farm(10,10000)
    mf = mirror(f)
    a = copy.deepcopy(f); k._do_buy_land(a,10); a = mirror(a)
    b = copy.deepcopy(mf); k._do_buy_land(b,10)
    no_rival = market(k,[['SELL','STRAWBERRY',2]],[])
    with_rival = market(k,[['SELL','STRAWBERRY',2]],[['SELL','STRAWBERRY',2]])
    assert no_rival['cash'][0] != with_rival['cash'][0]
    # Even with all quadrants unlocked, the preferred spawn is not equivariant.
    ff = k._new_farm(10,10000)
    for _ in range(3):
        k._do_buy_land(ff,10)
    ff['farmer'] = [0,0]
    spawn = k._spawn_hand(ff,10)
    mirrored_spawn = k._spawn_hand(mirror(ff),10)
    assert mirrored_spawn != [9-spawn[0],spawn[1]]
    assert a != b  # mirrored NW->NE isn't the fixed game's NW->NE unlock transition
    move_night=night(k,True);pass_night=night(k,False)
    assert move_night==pass_night
    facts = dict(engine_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                 mirror_initial=dict(original_spawn=f['farmer'], mirrored_spawn=mf['farmer'],
                                     original_unlocked=f['unlocked_quadrants'],mirrored_unlocked=mf['unlocked_quadrants']),
                 mirror_land=dict(mirror_after_buy=a['unlocked_quadrants'],buy_after_mirror=b['unlocked_quadrants'],commutes=False),
                 fully_unlocked_hire=dict(original=spawn,reflected_expected=[9-spawn[0],spawn[1]],actual_mirrored=mirrored_spawn),
                 market_no_rival=no_rival,market_with_rival=with_rival,
                 h23_move_pass_equivalent=dict(equal=True,farmer=move_night['farms'][0]['farmer'],
                     hands=move_night['farms'][0]['hands'],shed=move_night['private'][0]['shed']),
                 conclusion='Own-only market simulation is exact conditional on zero rival flow, not an exact live quote.')
    dst=Path('/workspace/shared/research/t046_engine_facts.json')
    dst.write_text(json.dumps(facts,indent=2))
    print(json.dumps(facts))


if __name__ == '__main__':
    main()
