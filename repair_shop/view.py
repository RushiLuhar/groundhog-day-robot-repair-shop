"""Escaped event-log rendering. Animation and banter never call a model."""
import html
import json
from .engine import MODES, LABELS
from .costs import money, total_cost, COST_NOTE, PRICE_URL

def esc(v): return html.escape(str(v),quote=True)

CSS = """
body,.gradio-container {background:#10121b!important;color:#eee9df!important;font-family:ui-monospace,SFMono-Regular,monospace!important}
.gradio-container {max-width:1500px!important} .shop{color:#f3ecdb}.mast{display:flex;justify-content:space-between;align-items:end;padding:28px 0 20px;border-bottom:1px solid #45434b;margin-bottom:24px}.eyebrow{color:#c8ef89;font-size:11px;letter-spacing:3px}.shop h1{font-size:clamp(25px,4vw,49px);line-height:1.05;margin:10px 0;color:#f4ead5;letter-spacing:-2px}.mast p{color:#a8a4af;max-width:650px;line-height:1.6}.open-sign{color:#ff947d;border:2px solid #ff947d;padding:12px;box-shadow:0 0 17px #ff947d25;transform:rotate(3deg);font-weight:bold}.bays{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.bay{background:#1b1e29;border:1px solid #434655;border-radius:12px;overflow:hidden;min-width:0}.bay-head{padding:16px;display:flex;justify-content:space-between;gap:8px}.bay-head h2{font-size:17px;margin:6px 0}.bay-head small{color:var(--accent);letter-spacing:2px}.tag{font-size:10px;border:1px solid #4f5360;padding:6px;height:fit-content;white-space:nowrap}.scene{width:100%;height:auto;background:#252735;image-rendering:pixelated;display:block}.hud{padding:14px 16px;display:flex;justify-content:space-between;gap:6px;border-top:1px solid #414453;font-size:12px}.hud strong{font-size:21px;color:var(--accent);display:block}.quip{padding:12px 16px;background:#12151f;color:#d4cbbc;font-size:12px;min-height:48px}.bay details{border-top:1px solid #353a48;padding:13px 16px;font-size:12px}.bay summary{cursor:pointer;color:#c9c5d2}.bay pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:250px;overflow:auto;color:#b9d4ae;font-size:11px}.ledger{margin-top:25px;background:#1b1e29;border:1px solid #414655;border-radius:12px;padding:20px}.ledger h2{font-size:19px;margin:0 0 16px}.scroll{overflow:auto}.ledger table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}.ledger th{text-align:left;color:#aaa5b6;font-weight:normal;padding:10px;border-bottom:1px solid #454958}.ledger td{padding:12px 10px;border-bottom:1px solid #313642}.ledger .good{color:#c8ef89}.ledger .bad{color:#ff947d}.receipt{color:#e6cd8c}.subtle{color:#a4a0af;font-size:12px;line-height:1.6}.timeline{max-height:220px;overflow:auto;font-size:11px;line-height:1.8}.timeline p{margin:0;border-bottom:1px dashed #323746;padding:4px}.active .arm{animation:wrench .45s steps(2,end) infinite;transform-origin:110px 93px}.active .sparks{animation:blink .3s steps(2,end) infinite}.thinking .crt{animation:blink .7s steps(2,end) infinite}.passed .customer{animation:hop .65s steps(3,end) infinite}.break .steam{animation:smoke 2s steps(5,end) infinite}.idle .steam{animation:smoke 3s steps(5,end) infinite}.inspect .scanner{animation:scan .8s steps(6,end) infinite}.rejected .customer{animation:shake .35s steps(2,end) 3}.neon{animation:neon 6s steps(2,end) infinite}.smoke{animation:smoke 3s steps(5,end) infinite}.sparks{opacity:0}.footnote{margin:18px 0 0;font-size:11px;color:#96909e}@keyframes wrench{to{transform:rotate(-15deg)}}@keyframes blink{50%{opacity:.2}}@keyframes hop{50%{transform:translateY(-5px)}}@keyframes smoke{to{transform:translate(4px,-12px);opacity:0}}@keyframes scan{to{transform:translateY(24px)}}@keyframes shake{50%{transform:translateX(4px)}}@keyframes neon{96%{opacity:1}98%{opacity:.3}}@media(max-width:850px){.bays{grid-template-columns:1fr}.mast{align-items:start}.open-sign{display:none}.scene{max-height:320px}.bay-head h2{font-size:19px}}@media(prefers-reduced-motion:reduce){.shop *{animation:none!important}}
"""

def scene(color, cls):
    return f'''<svg viewBox="0 0 320 180" class="scene {cls}" role="img" aria-label="Sarcastic robot mechanic repairing a robot customer; state {cls}" shape-rendering="crispEdges">
<defs><pattern id="tiles-{color[1:]}" width="24" height="12" patternUnits="userSpaceOnUse"><path d="M0 12H24M24 0V12" stroke="#343746" fill="none"/></pattern></defs>
<rect width="320" height="180" fill="#232634"/><path d="M0 32H320M32 0V32M90 32V65M160 0V32M250 32V65" stroke="#373949" stroke-width="2"/>
<rect x="15" y="15" width="89" height="22" fill="#151822" stroke="#565b6e"/><text class="neon" x="21" y="30" fill="{color}" font-size="11" font-family="monospace">SPROCKET</text>
<path d="M280 0V55H305V15M290 0V43H315" fill="none" stroke="#555568" stroke-width="7"/>
<rect x="20" y="48" width="55" height="40" fill="#111722" stroke="#555a69" stroke-width="4"/><path class="crt" d="M26 70H32L35 56L39 80L45 62L50 70H67" fill="none" stroke="{color}" stroke-width="2"/>
<path d="M42 90V103M25 103H63" stroke="#6a6978" stroke-width="4"/><rect x="14" y="111" width="65" height="39" fill="#8b514d"/><path d="M18 125H74M18 138H74" stroke="#3d343c" stroke-width="3"/><path d="M40 118H52M40 131H52" stroke="#ccb58e" stroke-width="2"/>
<rect x="0" y="151" width="320" height="29" fill="#171b28"/><rect y="151" width="320" height="29" fill="url(#tiles-{color[1:]})"/>
<g class="mechanic"><path d="M103 55V47" stroke="#aebbc5" stroke-width="3"/><rect x="100" y="43" width="7" height="5" fill="{color}"/>
<path d="M87 59H120V88H87Z" fill="#899ba8" stroke="#d0dde0" stroke-width="2"/><rect x="90" y="65" width="27" height="10" fill="#151a27"/><path d="M92 68L101 71M107 71L115 68" stroke="{color}" stroke-width="3"/><path d="M93 80H114M97 78V84M103 78V84M109 78V84" stroke="#293446" stroke-width="2"/>
<path d="M86 91H120V131H86Z" fill="#99a9af" stroke="#d0dde0" stroke-width="2"/><path d="M91 92V113H115V92M89 113H118V139H89" fill="#3f6482"/><rect x="98" y="104" width="12" height="9" fill="#c0ced3"/><path d="M90 139V151H100V136M108 136V151H119" fill="#758896" stroke="#758896" stroke-width="4"/><rect x="87" y="150" width="17" height="6" fill="#b6c4c7"/><rect x="109" y="150" width="18" height="6" fill="#b6c4c7"/>
<path d="M83 94V121H92" stroke="#aabcc5" stroke-width="7" fill="none"/><g class="arm"><path d="M120 94L132 107L147 101" stroke="#aabcc5" stroke-width="7" fill="none"/><rect x="129" y="102" width="6" height="6" fill="#465767"/><path d="M143 111L153 89M149 90L148 82M153 89L160 85" stroke="#d7e0e2" stroke-width="4"/></g>
<path d="M115 82H128" stroke="#e7d6a6" stroke-width="2"/><rect x="128" y="81" width="3" height="2" fill="#ff9068"/><path class="smoke" d="M131 78V72H135V65" stroke="#bcb4b2" stroke-width="2" fill="none"/>
</g><rect x="153" y="127" width="104" height="8" fill="#8f8792"/><path d="M160 135V159M250 135V159" stroke="#5a606f" stroke-width="7"/>
<g class="customer"><rect x="183" y="62" width="47" height="33" rx="3" fill="{color}"/><path d="M205 62V53H215" fill="none" stroke="#aeb9b6" stroke-width="3"/><rect x="189" y="72" width="9" height="8" fill="#242839"/><rect x="214" y="72" width="9" height="8" fill="#242839"/><path d="M198 87H215" stroke="#242839" stroke-width="3"/><rect x="179" y="97" width="55" height="29" fill="#727d89"/><rect x="191" y="102" width="29" height="17" fill="#292c3a"/><path d="M194 110H201L205 105L209 114H216" stroke="{color}" stroke-width="2" fill="none"/><path d="M175 100V120M239 100V120" stroke="#a7adab" stroke-width="7"/><rect x="186" y="124" width="13" height="4" fill="#c7c6af"/><rect x="215" y="124" width="13" height="4" fill="#c7c6af"/></g>
<path class="scanner" d="M174 70H239" stroke="#b7f9d5" stroke-width="2" opacity=".6"/><path class="sparks" d="M160 90L166 85M163 99H172M158 106L165 111" stroke="#ffe2a0" stroke-width="3"/>
<rect x="275" y="131" width="22" height="18" fill="#e0d1ac"/><path d="M297 135H304V144H297" stroke="#e0d1ac" stroke-width="3" fill="none"/><path class="steam" d="M281 127V119H285V113M292 128V119" fill="none" stroke="#9f9eab" stroke-width="2"/>
<g class="done-sign"><rect x="161" y="35" width="94" height="22" fill="#c8ef89"/><text x="169" y="50" fill="#182323" font-size="12" font-family="monospace">CLOCKED OUT</text></g><text x="16" y="171" fill="#747487" font-size="8" font-family="monospace">AUTHORIZED TOOLS • QUESTIONABLE COFFEE</text></svg>'''


CSS += """
.scene-stage{background:#232634;padding-top:12px}.scene-stage .quip{position:relative;margin:0 14px 0;padding:12px 14px;min-height:62px;border:2px solid var(--accent);border-radius:14px;background:#f2ead8;color:#282731;font-size:12px;line-height:1.5;z-index:1}.scene-stage .quip:before{content:"";position:absolute;left:28%;bottom:-15px;border-top:15px solid var(--accent);border-right:16px solid transparent}.scene-stage .quip:after{content:"";position:absolute;left:calc(28% + 2px);bottom:-10px;border-top:12px solid #f2ead8;border-right:12px solid transparent}.shift-banner{margin:0 0 22px;padding:22px;border:2px solid #666c83;border-radius:12px;background:#202637}.shift-banner h2{margin:0 0 8px;font-size:26px;color:#f4ead5}.shift-banner.completed{border-color:#c8ef89;background:#243329}.shift-banner.error,.shift-banner.stopped{border-color:#ff947d}.shift-banner p{margin:8px 0;line-height:1.5}.shift-banner progress{width:100%;height:12px;accent-color:#c8ef89}.metrics{display:flex;gap:26px;flex-wrap:wrap;margin:14px 0}.metrics b{font-size:23px;display:block;color:#c8ef89}.phase{padding:11px 16px;background:#2a3041;font-size:12px;color:#f1d392;min-height:44px}.done-sign{display:none}.clocked-out .done-sign{display:block}.clocked-out .mechanic{animation:lean 2s steps(3,end) infinite;transform-origin:103px 150px}.clocked-out .arm{transform:rotate(30deg);transform-origin:120px 94px}.clocked-out .customer{animation:depart 2.5s steps(8,end) forwards}.clocked-out .scanner,.passed .scanner,.break .scanner{display:none}.clocked-out .steam{animation:smoke 2s steps(5,end) infinite}.saving .crt{animation:blink .4s steps(2,end) infinite}.thinking .mechanic{animation:lean 1s steps(2,end) infinite;transform-origin:103px 150px}.tag{font-weight:bold}.completed .tag{border-color:#c8ef89}.shop a{color:#c8ef89}.report-info{padding:12px;border:1px solid #454958;overflow-wrap:anywhere}@keyframes lean{50%{transform:rotate(-3deg)}}@keyframes depart{to{transform:translateX(150px);opacity:0}}@media(prefers-reduced-motion:reduce){.shop *{animation:none!important}.clocked-out .customer{transform:translateX(35px)}}
"""

def experiment_description(live=False, model=None, count=3, phase='planned'):
    """Describe only the selected setup or the actual run; no credential access."""
    count=int(count)
    heading={'planned':'Next shift', 'running':'Current shift', 'completed':'Completed shift',
             'stopped':'Stopped shift', 'error':'Shift with an error', 'replay':'Recorded shift being replayed'}[phase]
    engine=esc(model) if model else 'Server-configured OpenAI model · exact name appears when the shift starts' if live else 'Offline scripted demo · no language model'
    mode_note=('This is a live model experiment. API calls cost money; the ledger includes repair calls and memory-writing calls.' if live else
               'This is a free rehearsal using a scripted mechanic. It demonstrates the tools and display, but does not tell us which memory approach works better for an AI model.')
    return f'''<section class="experiment-explainer">
<h3>Does remembering earlier repairs help?</h3>
<p>We give three mechanics the same repair jobs. The only difference is what each mechanic can remember from earlier jobs. We compare successful repairs, repair steps, tokens used and estimated dollar cost.</p>
<p><strong>{heading}:</strong> {count} job{'s' if count!=1 else ''} per bay · {count*3} repair attempts in total · first {count} of the fixed ten-job baseline.<br><strong>Engine:</strong> {engine}</p>
<p>{mode_note}</p>
<div class="scroll"><table><thead><tr><th>Mechanic</th><th>What carries over to the next job?</th></tr></thead><tbody>
<tr><td>Groundhog Day</td><td>Nothing. It starts each job without memories of previous repairs.</td></tr>
<tr><td>Raw notebook</td><td>The last 12 complete action-and-result exchanges, copied verbatim.</td></tr>
<tr><td>Four-level memory</td><td>Organized notes about past jobs, learned facts and repair procedures. Current-job working memory starts fresh.</td></tr>
</tbody></table></div>
<p><strong>What stays the same:</strong> model, reasoning defaults, tools, job order and a maximum of 12 tool steps per job. Every new shift starts with empty memory. Bays take turns; they do not share memories.</p>
<p><strong>How to read the results:</strong> a repair passes only when its final test succeeds. Reaching the step limit leaves it unfinished. “Shift complete” means every scheduled attempt has ended, even if some repairs failed. Memory-writing tokens are included in the totals. A small run is a useful check, not a reliable model ranking.</p>
<p class="subtle">Changing controls prepares the next shift; this description stays tied to the current or recorded results until you start again or reset. Sprocket is the fictional mechanic’s name.</p>
</section>'''

CSS += """
.experiment-explainer{font-size:14px;line-height:1.65;max-width:1000px;color:#eee9df}.experiment-explainer h3{font-size:22px;color:#c8ef89;margin:0 0 12px}.experiment-explainer p{margin:12px 0}.experiment-explainer table{width:100%;border-collapse:collapse;min-width:460px}.experiment-explainer td,.experiment-explainer th{text-align:left;padding:10px;border-bottom:1px solid #48505f;vertical-align:top}.experiment-explainer td:first-child{min-width:150px;color:#c8ef89}
"""

def render(events=None, results=None, live=False, model="offline scripted demo", running=False,
           error=None, selected_jobs=10, state=None, elapsed=0, calls=None):
    events,results=events or [],results or []
    expected=selected_jobs*len(MODES)
    state=state or ('error' if error else 'running' if running else 'completed' if results and len(results)==expected else 'stopped' if results else 'ready')
    settled=len(results); passes=sum(r['passed'] for r in results)
    title={'ready':'READY TO CLOCK IN','running':'SHIFT IN PROGRESS','completed':'SHIFT COMPLETE',
           'stopped':'SHIFT STOPPED · PARTIAL RESULTS','error':'SHIFT ENDED WITH AN ERROR','replay':'REPLAY · NO NEW API CALLS'}[state]
    latest=events[-1] if events else {}
    phase={'start':'Loading memory','thinking':'Waiting for model response','action':'Applying repair tool',
           'finish':'Repair test passed' if latest.get('passed') else 'Repair attempt ended',
           'maintenance_start':'Saving structured memory · model call','memory':'Memory settled','invoice':'Invoice recorded'}.get(latest.get('kind'),'Waiting for first job')
    activity=f"{LABELS.get(latest.get('mode'),'Workshop')} · job {latest.get('job','—')} · {phase}"
    if state in ('running','replay'):
        detail=activity + (f' · {elapsed}s since last event' if elapsed else '')
    elif state=='completed':
        detail=f'All {expected} scheduled repair attempts settled. {passes} passed; {settled-passes} unfinished. No more model calls are running.'
    elif state in ('stopped','error'):
        detail=f'{settled} of {expected} attempts settled; {max(0,expected-settled)} not attempted. No new calls will start.'
    else:
        detail='Choose an engine and job count, then start a shift. Each bay receives the same jobs.'
    bill_rows=calls if calls is not None else results
    input_tokens=sum(r.get('input',0) for r in bill_rows); output_tokens=sum(r.get('output',0) for r in bill_rows)
    cost=total_cost(bill_rows) if live else 0.0
    cards=[]
    for index,mode in enumerate(MODES):
        es=[e for e in events if e['mode']==mode]; last=es[-1] if es else {}
        start=next((e for e in reversed(es) if e['kind']=='start'),{})
        job=last.get('job',0)
        a=next((e for e in reversed(es) if e['kind']=='action' and e['job']==job),{})
        done=next((e for e in reversed(es) if e['kind']=='finish' and e['job']==job),None)
        kind=last.get('kind','idle'); rs=[r for r in results if r['mode']==mode]
        cls='idle'; quip='Clock in. Try not to become a spare part.'
        bay_phase='Waiting for this bay'; tag='WAITING'
        if a:
            name=a['action']['name']; op=a['action']['arguments'].get('operation',name)
            cls='inspect' if name=='inspect' else 'active'; bay_phase=f'Tool: {op}'; tag='REPAIRING'
            quip={'inspect':'Another mystery. My favorite unpaid hobby.','test':'Hide the spare screws. Here comes quality control.',
                  'vent':'I vent too. Management calls it an attitude problem.','tune':'Genius at work. Please lower your expectations.',
                  'seal':'Sealed. Unlike my feelings about this job.','reseat_cable':'Your personality was unplugged. Relatable.',
                  'replace_fuse':'New fuse. Same existential dread.'}.get(op,'Union rules: one catastrophe at a time.')
            if a['result'].get('ok') is False: cls='rejected'; quip='That was a diagnostic failure. Definitely on purpose.'
        if done:
            cls='passed' if done['passed'] else 'break'; tag='PASS' if done['passed'] else 'UNFINISHED'
            bay_phase='Repair passed · settling memory and invoice' if done['passed'] else 'Attempt ended · '+done.get('reason','unfinished')
            quip='Test passed. Put it on my tab. Your tab. Whatever.' if done['passed'] else 'Wrench down. This one still needs work. I need coffee.'
        if kind=='thinking':
            cls='thinking'; tag='THINKING'; bay_phase='Waiting for model response · no tool action yet'; quip='Processing. This counts as working, legally.'
        elif kind=='maintenance_start':
            cls='saving'; tag='SAVING MEMORY'; bay_phase='Repair ended · writing memory (billable in live mode)'; quip='Writing this down. Apparently sarcasm is not a memory system.'
        elif kind=='invoice':
            bay_phase='Job settled · waiting for next customer'
            if len(rs)==selected_jobs:
                cls='clocked-out' if done and done['passed'] else 'break'; tag='CLOCKED OUT'
                bay_phase=f'BAY DONE · {sum(r["passed"] for r in rs)}/{selected_jobs} passed'
                quip='Shift over. My excellence has exceeded the coffee budget.' if done and done['passed'] else 'Shift over. Unfinished repairs stay on the record. So do my complaints.'
        tokens=sum(r['input']+r['output'] for r in rs)
        memory=next((e for e in reversed(es) if e['kind']=='memory'),{})
        working={'job':job or 'waiting','steps_used':last.get('steps',0),'latest_observation':a.get('result',{})}
        color=['#efb974','#94d7c9','#bdacf1'][index]
        cards.append(f'''<article class="bay" style="--accent:{color}"><div class="bay-head"><div><small>BAY 0{index+1}</small><h2>{LABELS[mode]}</h2></div><span class="tag">{tag}</span></div><div class="scene-stage"><div class="quip" role="note" aria-label="Mechanic says">{esc(quip)}</div>{scene(color,cls)}</div>
<div class="phase">{esc(bay_phase)}</div><div class="hud"><span>CUSTOMER<strong>{esc(last.get('ticket',{}).get('customer','—'))}</strong></span><span>JOB<strong>{job or '—'}/{selected_jobs}</strong></span><span>STEPS<strong>{last.get('steps',0)}/12</strong></span></div>
<div class="hud receipt"><span>{'SETTLED API TOKENS' if live else 'OFFLINE · NO API BILL'}</span><b>{tokens:,} tokens</b></div>
<details><summary>Working memory · current job</summary><pre>{esc(json.dumps(working,indent=2))}</pre></details>
<details><summary>Memory loaded at job start · exact contents</summary><pre>{esc(json.dumps(start.get('prior',[]),indent=2))}</pre></details>
<details><summary>Memory after maintenance · {'episodic / semantic / procedural' if mode=='structured' else 'raw exchanges' if mode=='notebook' else 'discarded at boundary'}</summary><pre>{esc(json.dumps(memory.get('notes',[]),indent=2))}</pre></details></article>''')
    rows=[]
    for mode in MODES:
        rs=[r for r in results if r['mode']==mode]; passed=[r for r in rs if r['passed']]
        bs=[r for r in bill_rows if r['mode']==mode]
        avg=f'{sum(r["steps"] for r in passed)/len(passed):.1f}' if passed else '—'
        maint=sum(r['input']+r['output'] for r in bs if r.get('kind')=='memory') if calls is not None else sum(r['maintenance'] for r in rs)
        rows.append(f'<tr><td>{LABELS[mode]}</td><td>{esc(model)}</td><td>{len(passed)}/{len(rs)}</td><td>{len(rs)}/{selected_jobs}</td><td>{avg}</td><td>{sum(r["input"] for r in bs):,}</td><td>{sum(r["output"] for r in bs):,}</td><td>{maint:,}</td><td>{money(total_cost(bs) if live else 0)}</td></tr>')
    jobs=''.join(f'<tr><td>{r["job"]}</td><td>{LABELS[r["mode"]]}</td><td class="{"good" if r["passed"] else "bad"}">{"PASS" if r["passed"] else "UNFINISHED"}</td><td>{r["steps"]}/12</td><td>{r["input"]+r["output"]:,}</td><td>{money(r.get("cost_usd") if live else 0)}</td><td>{esc(r["reason"])} {esc(r.get("warning",""))}</td></tr>' for r in results)
    timeline=''.join(f'<p>#{e["sequence"]:03} · {esc(e.get("at","")[11:19])} · {LABELS[e["mode"]]} · job {e["job"]} · {esc(e["kind"])} {esc(json.dumps(e.get("result",e.get("usage",e.get("warning","")))))}</p>' for e in events[-60:][::-1])
    notice='LIVE OPENAI · '+esc(model) if live else 'OFFLINE SCRIPTED DEMO · NOT MODEL PERFORMANCE'
    return f'''<section class="shop"><header class="mast"><div><div class="eyebrow">A MEMORY EXPERIMENT DISGUISED AS A BAD BUSINESS</div><h1>Groundhog Day<br>Robot Repair Shop<span style="color:#c8ef89">.</span></h1><p>Three robot mechanics. Same customers. Different memories.<br>Real tool events. Terrible coffee. Receipts included.</p><div class="subtle">{notice}</div></div><div class="open-sign">{'SHIFT<br>OVER.' if state=='completed' else 'OPEN<br>AGAIN.'}</div></header>
<section class="shift-banner {state}" role="status" aria-live="polite"><h2>{title}</h2><p>{esc(detail)}</p><progress value="{settled}" max="{expected}" aria-label="Settled repair attempts"></progress><div class="metrics"><span><b>{settled}/{expected}</b>attempts settled</span><span><b>{passes}</b>passed</span><span><b>{settled-passes}</b>unfinished</span><span><b>{input_tokens+output_tokens:,}</b>known API tokens</span><span><b>{money(cost)}</b>estimated USD{' · partial' if error else ''}</span></div></section>
{f'<p class="bad">{esc(error)} Usage may be incomplete. No retry was made.</p>' if error else ''}<div class="bays">{''.join(cards)}</div>
<section class="ledger"><h2>01 / The shift ledger</h2><p class="subtle">Successful-job step averages sit beside completions. Quitting early never counts as efficiency. Memory-writing tokens and cost are included in totals.</p><div class="scroll"><table><thead><tr><th>Memory policy</th><th>Model used</th><th>Passed / attempted</th><th>Settled / scheduled</th><th>Mean steps · passes only</th><th>Input tokens</th><th>Output tokens</th><th>Of which maintenance</th><th>Total $ cost · estimate</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="subtle">{esc(COST_NOTE)} <a href="{PRICE_URL}">Official pricing</a>. Offline runs cost $0 and measure no model performance.</p><details><summary>Every job · passes and unfinished work</summary><div class="scroll"><table><tr><th>Job</th><th>Policy</th><th>Outcome</th><th>Steps</th><th>Total tokens</th><th>Estimated USD</th><th>Reason</th></tr>{jobs}</table></div></details></section>
<section class="ledger"><h2>02 / Under the hood</h2><p class="subtle">Animation follows recorded events. Bays run in turn, not in parallel. Thinking and memory-writing states wait on the API; coffee and jokes use no tokens.</p><div class="timeline">{timeline or 'No events yet. Start the offline shift to meet Sprocket.'}</div></section>
<p class="footnote">FICTIONAL REPAIR RULES · ORIGINAL SVG ART · REDUCED-MOTION PREFERENCES RESPECTED</p></section>'''
