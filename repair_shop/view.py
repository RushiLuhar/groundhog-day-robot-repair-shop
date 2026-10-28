"""Escaped event-log rendering. Animation and banter never call a model."""
import html
import json
from .engine import MODES, LABELS
from .costs import money, total_cost, COST_NOTE, PRICE_URL

EVENT_LABELS = {'start':'Starting job', 'thinking':'Waiting for model response',
                'action':'Tool result', 'finish':'Repair attempt ended',
                'maintenance_start':'Saving memory', 'memory_rejected':'New notes failed validation', 'memory':'Memory updated', 'invoice':'Usage recorded'}

def event_label(kind, live=True):
    if kind=='thinking' and not live:
        return 'Choosing the next action'
    if kind=='maintenance_start' and not live:
        return 'Saving demo notes'
    return EVENT_LABELS.get(kind,kind)


def readable_reason(reason):
    return {
        'passed test':'Final test passed.',
        'step cap reached':'Reached the step limit.',
        'stopped by user':'Stopped by you.',
        'stopped by user after in-flight request; returned usage recorded':'Stopped by you. Token usage from the last request was recorded.',
        'non-action or incomplete model response':'The model did not return a complete repair action.',
        'Memory write skipped after stop.':'Stopped before saving new notes.',
        'Memory update rejected; previous validated notes retained. No retry.':'The new notes failed validation. Previous notes were kept; the app did not retry.'
    }.get(reason,reason)


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
<g class="done-sign"><rect x="161" y="35" width="94" height="22" fill="#c8ef89"/><text x="169" y="50" fill="#182323" font-size="12" font-family="monospace">CLOCKED OUT</text></g><text x="16" y="171" fill="#747487" font-size="8" font-family="monospace">ROBOT REPAIRS • BAD COFFEE</text></svg>'''


CSS += """
.scene-stage{background:#232634;padding-top:12px}.scene-stage .quip{position:relative;margin:0 14px 0;padding:12px 14px;min-height:62px;border:2px solid var(--accent);border-radius:14px;background:#f2ead8;color:#282731;font-size:12px;line-height:1.5;z-index:1}.scene-stage .quip:before{content:"";position:absolute;left:28%;bottom:-15px;border-top:15px solid var(--accent);border-right:16px solid transparent}.scene-stage .quip:after{content:"";position:absolute;left:calc(28% + 2px);bottom:-10px;border-top:12px solid #f2ead8;border-right:12px solid transparent}.shift-banner{margin:0 0 22px;padding:22px;border:2px solid #666c83;border-radius:12px;background:#202637}.shift-banner h2{margin:0 0 8px;font-size:26px;color:#f4ead5}.shift-banner.completed{border-color:#c8ef89;background:#243329}.shift-banner.error,.shift-banner.stopped{border-color:#ff947d}.shift-banner p{margin:8px 0;line-height:1.5}.shift-banner progress{width:100%;height:12px;accent-color:#c8ef89}.metrics{display:flex;gap:26px;flex-wrap:wrap;margin:14px 0}.metrics b{font-size:23px;display:block;color:#c8ef89}.phase{padding:11px 16px;background:#2a3041;font-size:12px;color:#f1d392;min-height:44px}.done-sign{display:none}.clocked-out .done-sign{display:block}.clocked-out .mechanic{animation:lean 2s steps(3,end) infinite;transform-origin:103px 150px}.clocked-out .arm{transform:rotate(30deg);transform-origin:120px 94px}.clocked-out .customer{animation:depart 2.5s steps(8,end) forwards}.clocked-out .scanner,.passed .scanner,.break .scanner{display:none}.clocked-out .steam{animation:smoke 2s steps(5,end) infinite}.saving .crt{animation:blink .4s steps(2,end) infinite}.thinking .mechanic{animation:lean 1s steps(2,end) infinite;transform-origin:103px 150px}.tag{font-weight:bold}.completed .tag{border-color:#c8ef89}.shop a{color:#c8ef89}.report-info{padding:12px;border:1px solid #454958;overflow-wrap:anywhere}@keyframes lean{50%{transform:rotate(-3deg)}}@keyframes depart{to{transform:translateX(150px);opacity:0}}@media(prefers-reduced-motion:reduce){.shop *{animation:none!important}.clocked-out .customer{transform:translateX(35px)}}
"""

def experiment_description(live=False, model=None, count=3, phase='planned'):
    """Describe only the selected setup or the actual run; no credential access."""
    count=int(count)
    heading={'planned':'Next shift', 'running':'Current shift', 'completed':'Completed shift',
             'stopped':'Stopped shift', 'error':'Shift with an error', 'replay':'Replaying the previous shift'}[phase]
    engine=esc(model) if live and model else 'Your configured OpenAI model (name shown after you start)' if live else 'Free demo (scripted, no AI model)'
    mode_note=('OpenAI calls are paid. The results include the cost of both repairs and memory updates.' if live else
               'The free demo shows how the workshop works. Its results do not measure AI performance.')
    return f'''<section class="experiment-explainer">
<h3>Does memory help with the next repair?</h3>
<p>Each bay gets the same jobs, tools and model. We change what the mechanic remembers between jobs, then compare attempts passed, steps taken and cost.</p>
<p><strong>{heading}:</strong> {count} job{'s' if count!=1 else ''} × 3 bays = {count*3} repair attempts. We use the first {count} tickets from the fixed ten-job set.<br><strong>Run mode:</strong> {engine}</p>
<p>{mode_note}</p>
<h3>How a shift works</h3>
<ul>
<li><strong>Job:</strong> one repair ticket, with a robot and its starting faults. Each bay gets its own copy of that ticket, starting in the same condition.</li>
<li><strong>Repair attempt:</strong> one bay working on one job, from start to finish. Each bay gets one attempt per job. An attempt can include several repair actions and tests.</li>
<li><strong>Step:</strong> one tool action within an attempt: inspect the robot, make a repair, or run a test. Each attempt has its own limit of 12 steps.</li>
<li><strong>Shift:</strong> the whole run across all selected jobs and all three bays.</li>
</ul>
<p><strong>Example:</strong> choose 2 jobs and each bay tries both: 2 jobs × 3 bays = 6 attempts. A loose-cable attempt might use 3 steps: inspect → reconnect the cable → test. The other bays may take different steps on that same job.</p>
<p>All three bays attempt job 1, one at a time, then all three attempt job 2, and so on. Each attempt starts with a fresh copy of its job. Only the memory allowed for that bay carries over to the next job.</p>
<div class="scroll"><table><thead><tr><th>Bay</th><th>What it remembers</th></tr></thead><tbody>
<tr><td>Groundhog Day</td><td>Only the current job. Earlier repairs are forgotten.</td></tr>
<tr><td>Raw notebook</td><td>The last 12 actions and their results, kept word for word.</td></tr>
<tr><td>Four-level memory</td><td>Current-job details plus saved notes about past repairs, facts and procedures.</td></tr>
</tbody></table></div>
<p>All bays use the same model, reasoning settings, tools and job order. Starting a new shift clears every bay’s memory. Saving notes after an attempt can use a separate model call: its tokens and cost count in the results, but it does not use a repair step.</p>
<p><strong>An attempt passes when a test confirms the robot is fixed.</strong> A failed test uses a step, but the attempt can continue. An attempt that reaches 12 steps without passing stays unfinished; stopping or an error can end it earlier. “Shift complete” means all attempts have ended, including unfinished repairs. Compare passes alongside steps and cost; a short run is not enough to rank the memory approaches.</p>
<p class="subtle">Run mode and job count apply to the next shift. This description stays with the displayed results until you start again or reset.</p>
</section>'''

CSS += """
.experiment-explainer{font-size:14px;line-height:1.65;max-width:1000px;color:#eee9df}.experiment-explainer h3{font-size:22px;color:#c8ef89;margin:0 0 12px}.experiment-explainer p{margin:12px 0}.experiment-explainer ul{padding-left:22px;list-style:disc}.experiment-explainer li{margin:8px 0}.experiment-explainer h3:not(:first-child){margin-top:22px}.experiment-explainer table{width:100%;border-collapse:collapse;min-width:0}.experiment-explainer td,.experiment-explainer th{text-align:left;padding:10px;border-bottom:1px solid #48505f;vertical-align:top}.experiment-explainer td:first-child{width:26%;color:#c8ef89}
"""

def render(events=None, results=None, live=False, model="offline scripted demo", running=False,
           error=None, selected_jobs=10, state=None, elapsed=0, calls=None, experiment=None):
    events,results=events or [],results or []
    settings={m['bay_id']:m for m in experiment['mechanics']} if experiment else {}
    names={m:settings.get(m,{}).get('name',LABELS[m]) for m in MODES}
    repeats=experiment['repetitions'] if experiment else 1
    per_bay=selected_jobs*repeats
    expected=per_bay*len(MODES)
    state=state or ('error' if error else 'running' if running else 'completed' if results and len(results)==expected else 'stopped' if results else 'ready')
    settled=len(results); passes=sum(r['passed'] for r in results)
    title={'ready':'READY TO START','running':'SHIFT IN PROGRESS','completed':'SHIFT COMPLETE',
           'stopped':'SHIFT STOPPED · PARTIAL RESULTS','error':'SHIFT STOPPED · ERROR','replay':'REPLAY · NO MODEL CALLS'}[state]
    latest=events[-1] if events else {}
    phase={'start':'Loading memory','thinking':event_label('thinking',live),'action':'Using a repair tool',
           'finish':'Repair test passed' if latest.get('passed') else 'Repair attempt ended',
           'maintenance_start':'Saving notes for the next job','memory':'Memory updated','invoice':'Usage recorded'}.get(latest.get('kind'),'Waiting for the first job')
    activity=f"{names.get(latest.get('mode'),'Workshop')} · repeat {latest.get('repetition',1)} · job {latest.get('job','—')} · {phase}"
    if state in ('running','replay'):
        detail=('Recorded: ' if state=='replay' else '') + activity + (f' · {elapsed}s since last event' if elapsed else '')
    elif state=='completed':
        detail=f'All {expected} repair attempts have ended. {passes} passed; {settled-passes} unfinished.'
    elif state in ('stopped','error'):
        detail=f'{settled} of {expected} attempts ended; {max(0,expected-settled)} not attempted. The shift has stopped.'
    else:
        detail='Choose your experiment settings, then select Start experiment.'
    warning_count=sum(bool(r.get('warning')) for r in results)
    if warning_count: detail+=f' {warning_count} attempt(s) have a memory warning; see the bay cards and attempt results.'
    bill_rows=calls if calls is not None else results
    input_tokens=sum(r.get('input',0) for r in bill_rows); output_tokens=sum(r.get('output',0) for r in bill_rows)
    cost=total_cost(bill_rows) if live else 0.0
    cards=[]
    for index,mode in enumerate(MODES):
        es=[e for e in events if e['mode']==mode]; last=es[-1] if es else {}
        start=next((e for e in reversed(es) if e['kind']=='start'),{})
        job=last.get('job',0)
        a=next((e for e in reversed(es) if e['kind']=='action' and e['job']==job and e.get('repetition',1)==last.get('repetition',1)),{})
        done=next((e for e in reversed(es) if e['kind']=='finish' and e['job']==job and e.get('repetition',1)==last.get('repetition',1)),None)
        kind=last.get('kind','idle'); rs=[r for r in results if r['mode']==mode]
        cls='idle'; quip='Clock in. Try not to become a spare part.'
        bay_phase='Waiting to start'; tag='WAITING'
        if a:
            name=a['action']['name']; op=a['action']['arguments'].get('operation',name)
            cls='inspect' if name=='inspect' else 'active'; bay_phase={'inspect':'Inspecting the robot','test':'Testing the repair','vent':'Venting the cooler','tune':'Adjusting the cooler','seal':'Sealing the cooler','reseat_cable':'Reconnecting the cable','replace_fuse':'Replacing the fuse'}.get(op,op); tag='REPAIRING'
            quip={'inspect':'Let’s see what broke this time.','test':'Let’s test it before anyone asks about the spare screws.',
                  'vent':'Letting off steam. The robot, for once.','tune':'Adjusting the cooler. Hold the applause.',
                  'seal':'Sealed. That should keep the mess inside.','reseat_cable':'Loose cable. I’d like to unplug for a bit too.',
                  'replace_fuse':'New fuse. That’s coming out of your budget.'}.get(op,'One repair at a time. I only have two hands.')
            if a['result'].get('ok') is False: cls='rejected'; quip='That didn’t work. Nobody put that on the poster.'
        if done:
            cls='passed' if done['passed'] else 'break'; tag='PASS' if done['passed'] else 'UNFINISHED'
            bay_phase='Test passed · recording the result' if done['passed'] else 'Attempt ended · '+readable_reason(done.get('reason','unfinished'))
            quip='Test passed. You’re paying. I’m taking a break.' if done['passed'] else 'Still needs work. I need coffee.'
        if kind=='thinking':
            cls='thinking'; tag='THINKING' if live else 'CHOOSING ACTION'; bay_phase=event_label('thinking',live); quip='Thinking. Yes, that counts as work.'
        elif kind=='maintenance_start':
            cls='saving'; tag='SAVING MEMORY'; bay_phase='Saving notes · paid model call' if live else 'Saving demo notes'; quip='Writing this down so I don’t have to learn it twice.'
        elif kind=='invoice':
            bay_phase='Usage recorded · waiting for the next job'
            if len(rs)==per_bay:
                cls='clocked-out' if done and done['passed'] else 'break'; tag='CLOCKED OUT'
                bay_phase=f'BAY DONE · {sum(r["passed"] for r in rs)}/{per_bay} passed'
                quip='Shift’s over. I’ve earned the bad coffee.' if done and done['passed'] else 'Shift’s over. The unfinished ones are still your problem.'
        if state=='replay' and es: bay_phase='Recorded: '+bay_phase
        tokens=sum(r['input']+r['output'] for r in rs)
        memory=next((e for e in reversed(es) if e['kind']=='memory'),{})
        memory_warning=('<p class="subtle" role="note">Memory warning: '+esc(readable_reason(memory["warning"]))+'</p>') if memory.get("warning") else ""
        working={'job':job or 'waiting','steps_used':last.get('steps',0),'latest_observation':a.get('result',{})}
        color=['#efb974','#94d7c9','#bdacf1'][index]
        cards.append(f'''<article class="bay" style="--accent:{color}"><div class="bay-head"><div><small>BAY 0{index+1}</small><h2>{esc(names[mode])}</h2></div><span class="tag">{tag}</span></div><div class="scene-stage"><div class="quip" role="note" aria-label="Mechanic says">{esc(quip)}</div><button type="button" data-bay="{mode}" aria-label="Configure {esc(names[mode])}" class="mechanic-button">{scene(color,cls)}<span>Configure this mechanic</span></button></div>
<div class="phase">{esc(bay_phase)} · repeat {last.get("repetition",1)}/{repeats}</div><div class="hud"><span>CUSTOMER<strong>{esc(last.get('ticket',{}).get('customer','—'))}</strong></span><span>JOB TICKET<strong>{job or '—'}/{selected_jobs}</strong></span><span>ATTEMPT STEPS<strong>{last.get('steps',0)}/{settings.get(mode,{}).get('step_limit',12)}</strong></span></div>
<div class="hud receipt"><span>{'TOKENS · ENDED ATTEMPTS' if live else 'FREE DEMO · NO MODEL CALLS'}</span><b>{tokens:,} tokens</b></div>
<details><summary>Current job details</summary><pre>{esc(json.dumps(working,indent=2))}</pre></details>
<details><summary>Memory used for this job</summary><pre>{esc(json.dumps(start.get('prior',[]),indent=2))}</pre></details>
{memory_warning}
<details><summary>Memory kept for the next job</summary><pre>{esc(json.dumps(memory.get('notes',[]),indent=2))}</pre></details></article>''')
    rows=[]
    for mode in MODES:
        rs=[r for r in results if r['mode']==mode]; passed=[r for r in rs if r['passed']]
        bs=[r for r in bill_rows if r['mode']==mode]
        avg=f'{sum(r["steps"] for r in passed)/len(passed):.1f}' if passed else '—'
        maint=sum(r['input']+r['output'] for r in bs if r.get('kind')=='memory') if calls is not None else sum(r['maintenance'] for r in rs)
        rows.append(f'<tr><td>{esc(names[mode])}<br>{esc(LABELS[settings.get(mode,{}).get("memory",mode)])}</td><td>{esc(settings.get(mode,{}).get("model",model)) if live else "Scripted demo"}<br>{esc(settings.get(mode,{}).get("reasoning","default"))}</td><td>{len(passed)}/{len(rs)}</td><td>{len(rs)}/{per_bay}</td><td>{avg}</td><td>{sum(r["input"] for r in bs):,}</td><td>{sum(r["output"] for r in bs):,}</td><td>{maint:,}</td><td>{money(total_cost(bs) if live else 0)}</td></tr>')
    jobs=''.join(f'<tr><td>{r.get("repetition",1)} / {r["job"]}</td><td>{esc(names[r["mode"]])}</td><td class="{"good" if r["passed"] else "bad"}">{"PASS" if r["passed"] else "UNFINISHED"}</td><td>{r["steps"]}/{r.get("step_limit",12)}</td><td>{r["input"]+r["output"]:,}</td><td>{money(r.get("cost_usd") if live else 0)}</td><td>{esc(readable_reason(r["reason"]))} {esc(readable_reason(r.get("warning","")))}</td></tr>' for r in results)
    timeline=''.join(f'<p>#{e["sequence"]:03} · {esc(e.get("at","")[11:19])} · {esc(names[e["mode"]])} · repeat {e.get("repetition",1)} · job {e["job"]} · {esc(event_label(e["kind"],live))} {esc(json.dumps(e.get("result",e.get("usage",e.get("validation_reason",e.get("warning",""))))))}</p>' for e in events[-60:][::-1])
    notice=('OPENAI SELECTED · NO MODEL CALLS YET' if state=='ready' else 'LIVE OPENAI · models listed below') if live else 'FREE DEMO · NO AI MODEL'
    return f'''<section class="shop"><header class="mast"><div><div class="eyebrow">COMPARE REPAIR AGENTS</div><h1>Groundhog Day<br>Robot Repair Shop<span style="color:#c8ef89">.</span></h1><p>Compare models, reasoning and memory on the same repair jobs.</p><div class="subtle">{notice}</div></div><div class="open-sign">{'SHIFT<br>OVER.' if state=='completed' else 'OPEN<br>AGAIN.'}</div></header>
<section class="shift-banner {state}" role="status" aria-live="polite"><h2>{title}</h2><p>{esc(detail)}</p><progress value="{settled}" max="{expected}" aria-label="Repair attempts ended"></progress><div class="metrics"><span><b>{settled}/{expected}</b>attempts ended</span><span><b>{passes}</b>passed</span><span><b>{settled-passes}</b>unfinished</span><span><b>{input_tokens+output_tokens:,}</b>reported tokens</span><span><b>{money(cost)}</b>estimated cost (USD){' · partial' if error else ''}</span></div></section>
{f'<p class="bad">{esc(error)}</p>' if error else ''}<div class="bays">{''.join(cards)}</div>
<section class="ledger"><h2>Results by bay</h2><p class="subtle">Each row summarizes one bay’s attempts. The step average includes passing attempts only. Check the pass count alongside it. Token and cost totals include memory updates. Input tokens are text sent to the model; output tokens are text it generates, including reasoning tokens.</p><div class="scroll"><table><thead><tr><th>Mechanic / memory</th><th>Model</th><th>Passed / ended attempts</th><th>Attempts ended / planned</th><th>Average steps per passing attempt</th><th>Input tokens</th><th>Output tokens</th><th>Tokens used for memory</th><th>Estimated cost (USD)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="subtle">Costs are estimates in US dollars. The free demo costs $0. N/A means we do not have a price for this model.</p><details><summary>How cost is estimated</summary><p class="subtle">{esc(COST_NOTE)} <a href="{PRICE_URL}">OpenAI pricing</a></p></details><details><summary>Results for each attempt</summary><div class="scroll"><table><tr><th>Repeat / job</th><th>Mechanic / memory</th><th>Outcome</th><th>Steps</th><th>Total tokens</th><th>Estimated cost (USD)</th><th>What happened</th></tr>{jobs}</table></div></details></section>
<section class="ledger"><h2>Activity log</h2><p class="subtle">The animation follows these recorded events. {'In OpenAI mode, each bay waits for the model to choose its next action.' if live else 'The free demo chooses actions using a fixed script.'} The jokes are scripted and use no model tokens.</p><div class="timeline">{timeline or 'No activity yet. Start a shift to see the repairs.'}</div></section>
<p class="footnote">Simulated repairs. Animations follow your device’s reduced-motion setting.</p></section>'''

CSS += """
.mechanic-button{display:block;width:100%;padding:0;border:0;background:#232634;color:#c8ef89;cursor:pointer}.mechanic-button span{display:block;padding:8px;font-size:12px}.mechanic-button:focus-visible{outline:3px solid #c8ef89}.report-info pre{white-space:pre-wrap;overflow-wrap:anywhere}
"""

def configuration_description(config):
    from .tasks import get_suite
    suite=get_suite(config.task_set)
    rows=''.join(f"<tr><td>{esc(m.name)}</td><td>{esc(m.model)} / {esc(m.reasoning)}</td><td>{esc(LABELS[m.memory])}; notebook {m.notebook_exchanges} exchanges; notes {m.memory_tokens} tokens</td><td>{m.step_limit}</td></tr>" for m in config.mechanics)
    tickets=''.join(f"<li>Job {j.number}: {esc(j.ticket())}</li>" for j in suite.jobs[:config.jobs_per_bay])
    return f"""<section class="experiment-explainer"><h3>{esc(config.name)}</h3>
<p>{esc(config.annotation)}</p><p><b>{'OpenAI (paid)' if config.live else 'Free scripted demo'}</b> · {config.jobs_per_bay} jobs × 3 mechanics × {config.repetitions} repeated shifts = <b>{config.attempts} repair attempts</b>.</p>
<p>A <b>job</b> is one repair ticket. Each mechanic gets one <b>attempt</b> at each job. A <b>step</b> is one tool call (inspect, diagnose, repair or test). Each attempt stops at its mechanic’s step limit or a passing test. Unfinished attempts remain in the results.</p>
<p>Mechanics receive identical jobs and tools in the same order. Their model, reasoning and memory settings may differ. Memory carries between jobs within a shift; it starts empty for every repeated shift. Repetitions measure fresh starts, not longer memory histories. No attempt is automatically retried.</p>
<div class="scroll"><table><tr><th>Mechanic</th><th>Model / reasoning</th><th>Memory settings</th><th>Step limit</th></tr>{rows}</table></div>
<p>“default” uses the model provider’s reasoning default. Free demos ignore model and reasoning choices and use a script; they do not measure AI performance. Model access depends on your account. Unknown prices appear as N/A.</p>
<p>Run token limit: {config.max_total_tokens:,}. The app checks returned usage after every request and stops before the next request once this limit is reached. One in-flight request can exceed it. Repair and memory calls both count.</p>
<h3>{esc(suite.title)}</h3><p>{esc(suite.description)}</p><details><summary>Selected job tickets</summary><ol>{tickets}</ol></details>
<p class="subtle">Task version {esc(suite.id)} · fingerprint {suite.fingerprint[:12]}. Saved run snapshots preserve these settings. Form edits apply only to the next run.</p></section>"""
