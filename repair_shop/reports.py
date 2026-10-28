"""Portable result exports with explicit safe fields; never serialize a model/client."""
import csv
import io
import json
from pathlib import Path
from .view import CSS, render, esc
from .costs import PRICE_DATE, PRICE_URL, COST_NOTE, RATES
from .world import SEED


def summary(run):
    return {'schema_version':1, 'task_set':'baseline-v1', 'run_id':run.id,
            'started_at':run.started_at, 'state':run_state(run), 'seed':SEED,
            'configuration':{'model':run.model.name, 'live':run.model.live,
                'reasoning':'provider default', 'jobs_per_bay':run.selected_jobs, 'tool_step_cap':run.cap},
            'pricing':{'checked':PRICE_DATE,'source':PRICE_URL,'note':COST_NOTE,
                'standard_usd_per_million_input_output':RATES.get(run.model.name)},
            'usage':run.totals(), 'usage_complete':run.error is None,
            'results':run.results, 'error':run.error}


def run_state(run):
    return 'error' if run.error else 'completed' if run.completed else 'stopped'


def export(run, directory=None):
    data=summary(run)
    target=Path(directory) if directory else Path(__file__).resolve().parents[1]/'runs'
    target.mkdir(exist_ok=True,parents=True)
    base=target/f'shift-{run.id}'
    document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Robot Repair Shop · shift results</title>'
    document+=f'<style>{CSS} body{{padding:20px;max-width:1500px;margin:auto}} @media print{{.shop *{{animation:none!important}} details{{display:block}}}}</style><body>'
    document+=f'<p class="report-info">Portable shift report · baseline-v1 · {esc(run.started_at)} · run {esc(run.id)}<br>Seed {SEED} · reasoning: provider default · tool-step cap {run.cap}. This small run is not a benchmark ranking.</p>'
    document+=render(run.events,run.results,run.model.live,run.model.name,error=run.error,
                     selected_jobs=run.selected_jobs,state=run_state(run),calls=run.calls)+'</body></html>'
    html_path=base.with_suffix('.html'); html_path.write_text(document)
    json_path=base.with_suffix('.json'); json_path.write_text(json.dumps(data,indent=2))
    output=io.StringIO(); fields=['mode','model','job','passed','steps','input','output','maintenance','calls','cost_usd','reason','warning']
    writer=csv.DictWriter(output,fieldnames=fields,extrasaction='ignore'); writer.writeheader(); writer.writerows(run.results)
    csv_path=base.with_suffix('.csv'); csv_path.write_text(output.getvalue())
    return [str(html_path),str(json_path),str(csv_path)]
