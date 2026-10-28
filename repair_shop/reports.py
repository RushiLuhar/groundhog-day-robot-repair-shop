"""Portable result exports with explicit safe fields; never serialize a model/client."""
import csv
import io
import json
from pathlib import Path
from .view import CSS, render, esc, configuration_description


def summary(run):
    data=run.report()
    data.pop('events',None)
    data.pop('calls',None)
    data['state']=run_state(run)
    return data


def run_state(run):
    return 'error' if run.error else 'completed' if run.completed else 'stopped'


def export(run, directory=None):
    data=summary(run)
    target=Path(directory) if directory else Path(__file__).resolve().parents[1]/'runs'
    target.mkdir(exist_ok=True,parents=True)
    base=target/f'shift-{run.id}'
    document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Robot Repair Shop · shift results</title>'
    document+=f'<style>{CSS} body{{padding:20px;max-width:1500px;margin:auto}} @media print{{.shop *{{animation:none!important}} details{{display:block}}}}</style><body>'
    document+=f'<p class="report-info">Shift results · job set {esc(run.suite.id)} · {esc(run.started_at)} · run {esc(run.id)}<br>Seed {esc(run.suite.seed)} · task fingerprint {esc(data["task_fingerprint"])}. A small run is not enough to rank models or memory approaches.</p>'
    document+=render(run.events,run.results,run.model.live,run.model.name,error=run.error,
                     selected_jobs=run.selected_jobs,state=run_state(run),calls=run.calls,experiment=run.experiment.to_dict())+'<details class="report-info"><summary>Experiment setup</summary>'+configuration_description(run.experiment)+'</details><details class="report-info"><summary>Exact experiment configuration</summary><pre>'+esc(json.dumps(run.experiment.to_dict(),indent=2))+'</pre></details></body></html>'
    html_path=base.with_suffix('.html'); html_path.write_text(document)
    json_path=base.with_suffix('.json'); json_path.write_text(json.dumps(data,indent=2))
    output=io.StringIO(); fields=['mode','model','reasoning','memory_policy','repetition','step_limit','job','passed','steps','input','output','maintenance','calls','cost_usd','diagnostic_calls','invalid_actions','parts_used','reason','warning']
    writer=csv.DictWriter(output,fieldnames=fields,extrasaction='ignore'); writer.writeheader(); writer.writerows({**r,**r.get('task_metrics',{})} for r in run.results)
    csv_path=base.with_suffix('.csv'); csv_path.write_text(output.getvalue())
    return [str(html_path),str(json_path),str(csv_path)]
