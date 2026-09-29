"""Intentional faults must escape the exported entry point, never become PASS."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent


def main():
    checked=[]
    for base in ('m15ens','mix4'):
        path=HERE/'exports'/f'{base}_terminal.py'
        spec=importlib.util.spec_from_file_location('fault_'+base,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        def fault(*a,**k):raise RuntimeError('intentional fault fixture')
        def must_raise(obs):
            try:m.agent(obs,{})
            except Exception:return
            raise AssertionError('exception hidden as action')
        m._AG=fault;must_raise({'step':0,'player':0})
        assert m._T045_ERRORS['bc']==1
        m._AG=lambda *a,**k:{'farmer':['PASS'],'hands':[],'market':[]}
        must_raise({'step':0,'player':0})
        assert m._HG_STATS['errors']==1
        m._HG['on']=False
        must_raise({'step':718,'player':0})
        assert m._T045_ERRORS['terminal']==1
        checked.append(base)
    report={'status':'PASS','bases':checked,'injected_faults_per_base':3,'all_raise':True,'scope':'intentional BC/HG/terminal exceptions, not gate failures'}
    (HERE/'error_probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
