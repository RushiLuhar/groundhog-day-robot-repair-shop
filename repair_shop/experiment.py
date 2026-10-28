"""Reproduce saved experiment versions from the local command line."""
import argparse
import json
from dataclasses import replace
from .config import ExperimentConfig
from .storage import ExperimentStore
from .engine import Run
from .reports import export


def run_config(config,reference=None,db=None):
    db=db or ExperimentStore()
    run=Run(experiment=config);run.selected_jobs=config.jobs_per_bay;run.config_reference=reference
    db.begin_run(run,reference)
    run.on_checkpoint=lambda r:db.checkpoint(r)
    run.on_event=lambda e:db.checkpoint(run) if e['kind']=='invoice' else None
    try:
        for _ in run.run():pass
    except KeyboardInterrupt:
        run.interrupt('Interrupted from the command line; any outstanding request may have unknown usage.')
    except Exception:
        run.error=run.error or 'Local execution error; no automatic retry. Returned usage is retained.'
        run.interrupt('Local execution error; known usage is retained.')
    finally:
        try: db.checkpoint(run,True)
        except Exception: run.persistence_error='Saving the run checkpoint failed.'
        try: export(run)
        except Exception: run.export_error='Report export failed.'
        if run.export_error:
            try: db.checkpoint(run,True)
            except Exception: run.persistence_error='Saving the run checkpoint failed.'
    return run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['list','run'])
    p.add_argument('--config',help='Saved configuration ID')
    p.add_argument('--version',type=int)
    p.add_argument('--live',action='store_true',help='Explicitly permit paid calls for a saved live configuration')
    args=p.parse_args();db=ExperimentStore()
    if args.action=='list':print(json.dumps(db.list_configs(),indent=2));return
    if not args.config or args.version is None:p.error('run needs --config and --version')
    c=db.load_config(args.config,args.version)
    if c.live and not args.live:p.error('This saved version uses paid OpenAI calls. Add --live to run it, or save an offline version in the UI.')
    r=run_config(c,{'id':args.config,'version':args.version},db)
    print(json.dumps({'run_id':r.id,'completed':r.completed,'attempts':len(r.results),'usage':r.totals(),
        'usage_complete':r.report()['usage_complete'],'error':r.error,'persistence_error':r.persistence_error,
        'export_error':r.export_error,'stop_reason':r.stop_reason},indent=2))
    return 1 if r.error or r.interrupted or r.persistence_error or r.export_error else 0

if __name__=='__main__':raise SystemExit(main())
