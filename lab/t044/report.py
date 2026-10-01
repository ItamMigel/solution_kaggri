#!/usr/bin/env python3
"""Aggregate T044 mined local replays.  No Kaggle IO or submission."""
import argparse, json
from collections import defaultdict
from pathlib import Path

def avg(d, n): return {k:v/n for k,v in d.items()}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mine',action='append',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    games=[]
    for p in a.mine: games += json.loads(Path(p).read_text())['games']
    flow=defaultdict(lambda: defaultdict(float)); events=defaultdict(lambda: defaultdict(lambda:[0,0.])); final=defaultdict(float); count=defaultdict(int)
    contest=defaultdict(lambda:[0,0,0,0.])
    for g in games:
        matchup=tuple(sorted(g['players']))
        for pid,name in enumerate(g['players']):
            key=(matchup,name); count[key]+=1; final[key]+=g['final'][pid]
            for e in g['events'][pid]:
                if e['kind']=='market':
                    fk=('sale:' if e['op']=='SELL' else 'buy:'+e['op']+':')+e['item']
                    flow[key][fk] += e['price'] if e['op']=='SELL' else e['money_delta']
                    z=events[key][(e['day'],e['op'],e['item'])]; z[0]+=1; z[1]+=e['price']
                elif e['kind'] in ('hire','land'): flow[key][e['kind']]+=e['money_delta']
        for day in range(30):
            items={e['item'] for es in g['events'] for e in es if e['kind']=='market' and e['day']==day}
            for it in items:
                x=[[e for e in es if e['kind']=='market' and e['day']==day and e['item']==it] for es in g['events']]
                if x[0] and x[1]:
                    q=contest[(matchup,it)];q[0]+=1
                    s=[[e['price'] for e in y if e['op']=='SELL'] for y in x]
                    if s[0] and s[1]:q[1]+=1;q[2]+=abs(sum(s[0])/len(s[0])-sum(s[1])/len(s[1]));q[3]+=1
    result={'games':len(games),'flow':[],'events':[],'contest':[]}
    for key,n in sorted(count.items()):
        result['flow'].append({'matchup':list(key[0]),'player':key[1],'games':n,'final_mean':final[key]/n, **avg(flow[key],n)})
        for (day,op,it),(units,price) in sorted(events[key].items()):
            result['events'].append({'matchup':list(key[0]),'player':key[1],'day':day,'op':op,'item':it,'units_per_game':units/n,'cash_per_game':(price if op=='SELL' else -price)/n,'price_mean':price/units})
    for (match,it),(both,ss,gap,gn) in sorted(contest.items()): result['contest'].append({'matchup':list(match),'item':it,'same_day_game_events':both,'both_sell_events':ss,'sell_price_gap_mean':gap/max(1,gn)})
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(a.out)
if __name__=='__main__':main()
