"""Explicit bounded smoke runner; saves only event/usage reports, never credentials."""
import argparse
import json
from pathlib import Path
from .engine import Run
from .model import OpenAIModel, DemoModel, ModelError
from .world import JOBS

def main():
    p=argparse.ArgumentParser(); p.add_argument('--live',action='store_true'); p.add_argument('--jobs-per-mode',type=int,default=1)
    args=p.parse_args()
    if not 1<=args.jobs_per_mode<=4: p.error('choose 1..4 (at most 12 total jobs)')
    try: model=OpenAIModel() if args.live else DemoModel()
    except ModelError as e: print(str(e)); return 1
    run=Run(model)
    try:
        for _ in run.run(JOBS[:args.jobs_per_mode]): pass
    finally:
        path=Path('runs'); path.mkdir(exist_ok=True)
        (path/f'{run.id}.json').write_text(json.dumps(run.report(),indent=2))
    print(json.dumps({k:v for k,v in run.report().items() if k not in ('events','calls')},indent=2))
    return 1 if run.error else 0

if __name__=='__main__': raise SystemExit(main())
