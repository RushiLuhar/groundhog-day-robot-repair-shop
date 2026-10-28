"""Honest denominators, role accounting and inspectable source-to-action traces."""
import csv,html,json
from pathlib import Path
from ..costs import money,total_cost

def esc(v):return html.escape(str(v))

def render(data):
    if not data:return '<section><h2>Ready · offline evaluation</h2><p>Validate a condition list, then start explicitly.</p></section>'
    config=data['manifest']['config'];rows=data['attempts'];usage=data['usage']
    body=f'<h2>{esc(data["state"].upper())}</h2><p>{esc(data["error"] or data["stop_reason"])}</p>'
    for k in ('persistence_error','export_error'):
        if data.get(k):body+=f'<p role="alert">{esc(data[k])}</p>'
    body+=f'<p>{"Live model calls" if config["live"] else "Scripted demonstration · no model calls"}. {sum(r["certified"] for r in rows)}/{len(rows)} scheduled attempts certified; {sum(r["status"]!="unattempted" for r in rows)} started. Elapsed execution: {data["elapsed_seconds"]:.2f}s.</p>'
    body+=f'<p>{usage["input"]+usage["output"]:,} known tokens · {money(usage["estimated_usd"])} estimated API USD · {usage["unknown_calls"]} request(s) with unknown usage. {"Usage may be incomplete." if not usage["usage_complete"] else "Returned usage accounted for."}</p>'
    body+='<p>Partial or unequal exposure is not a ranking. Early failure is not efficiency. Equal token caps are not equal dollar costs. Deterministic logs have no API calls; their supplied text contributes to request input tokens.</p>'
    table='<div class="eval-scroll"><table><tr><th>Condition</th><th>Certified / scheduled</th><th>Started</th><th>Unfinished</th><th>Interrupted</th><th>Unattempted</th><th>Infrastructure / writer / logging errors</th><th>Steps</th><th>Repair input / output</th><th>Writer input / output</th><th>Estimated USD</th></tr>'
    for c in config['conditions']:
        rs=[r for r in rows if r['condition']==c['id']]
        fields=[c['id'],f'{sum(r["certified"] for r in rs)}/{len(rs)}',sum(r['status']!='unattempted' for r in rs),
                sum(r['status']=='unfinished' for r in rs),sum(r['status']=='interrupted' for r in rs),sum(r['status']=='unattempted' for r in rs),
                f'{sum(bool(r["infrastructure_error"]) for r in rs)} / {sum(bool(r["writer_error"]) for r in rs)} / {sum(bool(r["logging_error"]) for r in rs)}',sum(r['steps'] for r in rs)]
        for role in ('repair','writer'):fields.append(' / '.join(str(sum(r['usage']['roles'][role][part] for r in rs)) for part in ('input','output')))
        fields.append(money(total_cost([{'cost_usd':r['usage']['estimated_usd']} for r in rs])))
        table+='<tr>'+''.join(f'<td>{esc(x)}</td>' for x in fields)+'</tr>'
    body+=table+'</table></div><h3>Representative trace inspection</h3><p>Inspect discovery, repeat, transfer, replacement, original return, compound service and failures. Supplied evidence does not prove causal use; citation validity does not prove truth. Raw events and logs below are historical evidence, never an extra memory channel.</p>'
    for r in rows:
        if r['status']=='unattempted':continue
        label=f"Repeat {r['repetition']} · {r['condition']} · ticket {r['job']} · {r['status']} · {r['steps']} steps"
        body+=f'<details><summary>{esc(label)}</summary><p>{esc(r["reason"])}</p>'
        body+=''.join('<p>'+esc(r[k])+'</p>' for k in ('writer_error','infrastructure_error','logging_error') if r[k])
        for name,key in [('Raw events (ground truth)','raw_events'),('Literal observation entries','observation_log'),('Missing entries','missing_entries'),('Evidence supplied at job start','memory_input'),('Supply audit','memory_supply_audit'),('Retention audit','memory_update_audit'),('Evidence kept after job','memory_after')]:
            body+=f'<details><summary>{name}</summary><pre>{esc(json.dumps(r[key],indent=2))}</pre></details>'
        body+='</details>'
    body+='<details><summary>Immutable run manifest</summary><pre>'+esc(json.dumps(data['manifest'],indent=2))+'</pre></details>'
    return '<section class="eval-report">'+body+'</section>'

CSS='''.eval-report{line-height:1.5}.eval-scroll{overflow-x:auto} .eval-report table{border-collapse:collapse;min-width:900px} .eval-report td,.eval-report th{padding:10px;text-align:left;border:1px solid #68717b} .eval-report pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:550px;overflow:auto} .eval-report details{padding:10px;border:1px solid #68717b;margin:8px 0}'''

def export(data,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=True);base=root/f'evaluation-{data["run_id"]}'
    paths=[base.with_suffix(s) for s in ('.html','.json','.csv')]
    paths[0].write_text('<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Paired evaluation report</title><style>'+CSS+'</style>'+render(data)+'</html>')
    paths[1].write_text(json.dumps(data,indent=2))
    with paths[2].open('w',newline='') as out:
        fields=['repetition','condition','job','status','certified','steps','elapsed_seconds','reason','writer_error','infrastructure_error','logging_error','repair_input','repair_output','writer_input','writer_output','estimated_usd','usage_complete']
        writer=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for r in data['attempts']:
            flat={**r,**{role+'_'+part:r['usage']['roles'][role][part] for role in ('repair','writer') for part in ('input','output')},'estimated_usd':r['usage']['estimated_usd'],'usage_complete':r['usage']['usage_complete']}
            writer.writerow(flat)
    return [str(p) for p in paths]
