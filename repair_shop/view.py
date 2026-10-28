"""Escaped event-log rendering. Animation and banter never call a model."""
import html
import json
from .engine import MODES, LABELS

def esc(v): return html.escape(str(v),quote=True)

CSS = """
body,.gradio-container {background:#10121b!important;color:#eee9df!important;font-family:ui-monospace,SFMono-Regular,monospace!important}
.gradio-container {max-width:1500px!important} .shop{color:#f3ecdb}.mast{display:flex;justify-content:space-between;align-items:end;padding:28px 0 20px;border-bottom:1px solid #45434b;margin-bottom:24px}.eyebrow{color:#c8ef89;font-size:11px;letter-spacing:3px}.shop h1{font-size:clamp(25px,4vw,49px);line-height:1.05;margin:10px 0;color:#f4ead5;letter-spacing:-2px}.mast p{color:#a8a4af;max-width:650px;line-height:1.6}.open-sign{color:#ff947d;border:2px solid #ff947d;padding:12px;box-shadow:0 0 17px #ff947d25;transform:rotate(3deg);font-weight:bold}.bays{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.bay{background:#1b1e29;border:1px solid #434655;border-radius:12px;overflow:hidden;min-width:0}.bay-head{padding:16px;display:flex;justify-content:space-between;gap:8px}.bay-head h2{font-size:17px;margin:6px 0}.bay-head small{color:var(--accent);letter-spacing:2px}.tag{font-size:10px;border:1px solid #4f5360;padding:6px;height:fit-content;white-space:nowrap}.scene{width:100%;height:auto;background:#252735;image-rendering:pixelated;display:block}.hud{padding:14px 16px;display:flex;justify-content:space-between;gap:6px;border-top:1px solid #414453;font-size:12px}.hud strong{font-size:21px;color:var(--accent);display:block}.quip{padding:12px 16px;background:#12151f;color:#d4cbbc;font-size:12px;min-height:48px}.bay details{border-top:1px solid #353a48;padding:13px 16px;font-size:12px}.bay summary{cursor:pointer;color:#c9c5d2}.bay pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:250px;overflow:auto;color:#b9d4ae;font-size:11px}.ledger{margin-top:25px;background:#1b1e29;border:1px solid #414655;border-radius:12px;padding:20px}.ledger h2{font-size:19px;margin:0 0 16px}.scroll{overflow:auto}.ledger table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}.ledger th{text-align:left;color:#aaa5b6;font-weight:normal;padding:10px;border-bottom:1px solid #454958}.ledger td{padding:12px 10px;border-bottom:1px solid #313642}.ledger .good{color:#c8ef89}.ledger .bad{color:#ff947d}.receipt{color:#e6cd8c}.subtle{color:#a4a0af;font-size:12px;line-height:1.6}.timeline{max-height:220px;overflow:auto;font-size:11px;line-height:1.8}.timeline p{margin:0;border-bottom:1px dashed #323746;padding:4px}.active .arm{animation:wrench .45s steps(2,end) infinite;transform-origin:110px 93px}.active .sparks{animation:blink .3s steps(2,end) infinite}.thinking .crt{animation:blink .7s steps(2,end) infinite}.passed .customer{animation:hop .65s steps(3,end) infinite}.break .steam{animation:smoke 2s steps(5,end) infinite}.idle .steam{animation:smoke 3s steps(5,end) infinite}.inspect .scanner{animation:scan .8s steps(6,end) infinite}.rejected .customer{animation:shake .35s steps(2,end) 3}.neon{animation:neon 6s steps(2,end) infinite}.smoke{animation:smoke 3s steps(5,end) infinite}.sparks{opacity:0}.footnote{margin:18px 0 0;font-size:11px;color:#96909e}@keyframes wrench{to{transform:rotate(-15deg)}}@keyframes blink{50%{opacity:.2}}@keyframes hop{50%{transform:translateY(-5px)}}@keyframes smoke{to{transform:translate(4px,-12px);opacity:0}}@keyframes scan{to{transform:translateY(24px)}}@keyframes shake{50%{transform:translateX(4px)}}@keyframes neon{96%{opacity:1}98%{opacity:.3}}@media(max-width:850px){.bays{grid-template-columns:1fr}.mast{align-items:start}.open-sign{display:none}.scene{max-height:320px}.bay-head h2{font-size:19px}}@media(prefers-reduced-motion:reduce){.shop *{animation:none!important}}
"""

def scene(color, cls):
    return f'''<svg viewBox="0 0 320 180" class="scene {cls}" role="img" aria-label="Pixel mechanic working on a robot customer; state {cls}" shape-rendering="crispEdges">
<defs><pattern id="tiles-{cls}" width="24" height="12" patternUnits="userSpaceOnUse"><path d="M0 12H24M24 0V12" stroke="#343746" fill="none"/></pattern></defs>
<rect width="320" height="180" fill="#232634"/><path d="M0 32H320M32 0V32M90 32V65M160 0V32M250 32V65" stroke="#373949" stroke-width="2"/>
<rect x="15" y="15" width="89" height="22" fill="#151822" stroke="#565b6e"/><text class="neon" x="21" y="30" fill="{color}" font-size="11" font-family="monospace">SPROCKET / 86</text>
<path d="M280 0V55H305V15M290 0V43H315" fill="none" stroke="#555568" stroke-width="7"/>
<rect x="20" y="48" width="55" height="40" fill="#111722" stroke="#555a69" stroke-width="4"/><path class="crt" d="M26 70H32L35 56L39 80L45 62L50 70H67" fill="none" stroke="{color}" stroke-width="2"/>
<path d="M42 90V103M25 103H63" stroke="#6a6978" stroke-width="4"/><rect x="14" y="111" width="65" height="39" fill="#8b514d"/><path d="M18 125H74M18 138H74" stroke="#3d343c" stroke-width="3"/><path d="M40 118H52M40 131H52" stroke="#ccb58e" stroke-width="2"/>
<rect x="0" y="151" width="320" height="29" fill="#171b28"/><rect y="151" width="320" height="29" fill="url(#tiles-{cls})"/>
<g class="mechanic"><path d="M91 64H116V88H91Z" fill="#dca574"/><path d="M87 62H118V69H87M92 55H112V63H92" fill="#352d3b"/><path d="M94 75H100M110 75H116" stroke="#1b1c29" stroke-width="3"/><path d="M99 83H111" stroke="#5b3e45" stroke-width="2"/>
<path d="M86 90H118V129H86Z" fill="#7f8a80"/><path d="M91 92V117H115V92M89 114H117V140H89" fill="#3f6482"/><path d="M90 139V151H100V136M108 136V151H119" fill="#354359" stroke="#354359" stroke-width="4"/><rect x="89" y="150" width="14" height="5" fill="#0c111b"/><rect x="109" y="150" width="15" height="5" fill="#0c111b"/>
<path d="M84 94V121H92" stroke="#dca574" stroke-width="7" fill="none"/><g class="arm"><path d="M116 94L132 107L147 101" stroke="#dca574" stroke-width="7" fill="none"/><path d="M143 111L153 89M149 90L148 82M153 89L160 85" stroke="#b1b5bb" stroke-width="4"/></g>
<path d="M115 82H128" stroke="#e7d6a6" stroke-width="2"/><rect x="128" y="81" width="3" height="2" fill="#ff9068"/><path class="smoke" d="M131 78V72H135V65" stroke="#bcb4b2" stroke-width="2" fill="none"/>
</g><rect x="153" y="127" width="104" height="8" fill="#8f8792"/><path d="M160 135V159M250 135V159" stroke="#5a606f" stroke-width="7"/>
<g class="customer"><rect x="183" y="62" width="47" height="33" rx="3" fill="{color}"/><path d="M205 62V53H215" fill="none" stroke="#aeb9b6" stroke-width="3"/><rect x="189" y="72" width="9" height="8" fill="#242839"/><rect x="214" y="72" width="9" height="8" fill="#242839"/><path d="M198 87H215" stroke="#242839" stroke-width="3"/><rect x="179" y="97" width="55" height="29" fill="#727d89"/><rect x="191" y="102" width="29" height="17" fill="#292c3a"/><path d="M194 110H201L205 105L209 114H216" stroke="{color}" stroke-width="2" fill="none"/><path d="M175 100V120M239 100V120" stroke="#a7adab" stroke-width="7"/><rect x="186" y="124" width="13" height="4" fill="#c7c6af"/><rect x="215" y="124" width="13" height="4" fill="#c7c6af"/></g>
<path class="scanner" d="M174 70H239" stroke="#b7f9d5" stroke-width="2" opacity=".6"/><path class="sparks" d="M160 90L166 85M163 99H172M158 106L165 111" stroke="#ffe2a0" stroke-width="3"/>
<rect x="275" y="131" width="22" height="18" fill="#e0d1ac"/><path d="M297 135H304V144H297" stroke="#e0d1ac" stroke-width="3" fill="none"/><path class="steam" d="M281 127V119H285V113M292 128V119" fill="none" stroke="#9f9eab" stroke-width="2"/>
<text x="16" y="171" fill="#747487" font-size="8" font-family="monospace">AUTHORIZED TOOLS • QUESTIONABLE COFFEE</text></svg>'''


def render(events=None, results=None, live=False, model="offline scripted demo", running=False, error=None):
    events,results=events or [],results or []
    cards=[]
    for index,mode in enumerate(MODES):
        es=[e for e in events if e['mode']==mode]
        last=es[-1] if es else {}
        starts=[e for e in es if e['kind']=='start']
        start=starts[-1] if starts else {}
        job=last.get('job',0)
        actions=[e for e in es if e['kind']=='action' and e['job']==job]
        a=actions[-1] if actions else {}
        finished=[e for e in es if e['kind']=='finish' and e['job']==job]
        done=finished[-1] if finished else None
        kind=last.get('kind','idle')
        cls='thinking' if kind=='thinking' else 'idle'
        quip='Clock in. Try not to become a spare part.'
        if a:
            name=a['action']['name']; op=a['action']['arguments'].get('operation',name)
            cls='inspect' if name=='inspect' else 'active'
            quip={'inspect':'Let’s see what warranty you’ve voided.','test':'Moment of truth. Hide the spare screws.','vent':'A little steam. A lot of drama.','tune':'Percussive maintenance is not a setting.','seal':'Sealed with questionable affection.','reseat_cable':'Have you tried plugging in your personality?','replace_fuse':'New fuse. Same existential dread.'}.get(op,op)
            if a['result'].get('ok') is False: cls='rejected'; quip='Well, that went mechanically sideways.'
        if done:
            cls='passed' if done['passed'] else 'break'
            quip='Test passed. That’ll be tokens, pal.' if done['passed'] else 'Wrench down. Coffee up. Unfinished means unfinished.'
        rs=[r for r in results if r['mode']==mode]
        tokens=sum(r['input']+r['output'] for r in rs)
        memory=[e for e in es if e['kind']=='memory']
        after=memory[-1].get('notes',[]) if memory else []
        working={'job':job or 'waiting','steps_used':last.get('steps',0),'latest_observation':a.get('result',{})}
        tag='PASS' if done and done['passed'] else 'UNFINISHED' if done else 'WORKING' if es else 'OFF DUTY'
        color=['#efb974','#94d7c9','#bdacf1'][index]
        cards.append(f'''<article class="bay" style="--accent:{color}"><div class="bay-head"><div><small>BAY 0{index+1}</small><h2>{LABELS[mode]}</h2></div><span class="tag">{tag}</span></div>{scene(color,cls)}
<div class="hud"><span>CUSTOMER<strong>{esc(last.get('ticket',{}).get('customer','—'))}</strong></span><span>JOB<strong>{job or '—'}/10</strong></span><span>STEPS<strong>{last.get('steps',0)}/12</strong></span></div>
<div class="quip">“{esc(quip)}”</div><div class="hud receipt"><span>{'API TOKEN TILL' if live else 'OFFLINE · NO API BILL'}</span><b>{tokens:,} tokens</b></div>
<details><summary>Working memory · current job</summary><pre>{esc(json.dumps(working,indent=2))}</pre></details>
<details><summary>Memory loaded at job start · exact contents</summary><pre>{esc(json.dumps(start.get('prior',[]),indent=2))}</pre></details>
<details><summary>Memory after maintenance · {'episodic / semantic / procedural' if mode=='structured' else 'raw exchanges' if mode=='notebook' else 'discarded at boundary'}</summary><pre>{esc(json.dumps(after,indent=2))}</pre></details></article>''')
    rows=[]
    for mode in MODES:
        rs=[r for r in results if r['mode']==mode]; passed=[r for r in rs if r['passed']]
        avg=f'{sum(r["steps"] for r in passed)/len(passed):.1f}' if passed else '—'
        rows.append(f'<tr><td>{LABELS[mode]}</td><td>{len(passed)}/{len(rs)}</td><td>{avg}</td><td>{sum(r["input"] for r in rs):,}</td><td>{sum(r["output"] for r in rs):,}</td><td>{sum(r["maintenance"] for r in rs):,}</td></tr>')
    jobs=''.join(f'<tr><td>{r["job"]}</td><td>{LABELS[r["mode"]]}</td><td class="{"good" if r["passed"] else "bad"}">{"PASS" if r["passed"] else "UNFINISHED"}</td><td>{r["steps"]}/12</td><td>{r["input"]+r["output"]:,}</td><td>{esc(r["reason"])} {esc(r.get("warning",""))}</td></tr>' for r in results)
    timeline=''.join(f'<p>#{e["sequence"]:03} · {LABELS[e["mode"]]} · job {e["job"]} · {esc(e["kind"])} {esc(json.dumps(e.get("result",e.get("usage",e.get("warning","")))))}</p>' for e in events[-60:][::-1])
    notice='LIVE OPENAI · '+esc(model) if live else 'OFFLINE SCRIPTED DEMO · NOT MODEL PERFORMANCE'
    return f'''<section class="shop"><header class="mast"><div><div class="eyebrow">A MEMORY EXPERIMENT DISGUISED AS A BAD BUSINESS</div><h1>Groundhog Day<br>Robot Repair Shop<span style="color:#c8ef89">.</span></h1><p>Same mechanic. Same customers. Three ways to remember.<br>Ten peculiar robots, a token till, and absolutely no refunds.</p><div class="subtle">{notice} · {'SHIFT IN PROGRESS' if running else 'READY / SHIFT ENDED'}</div></div><div class="open-sign">OPEN<br>AGAIN.</div></header>
{f'<p class="bad">{esc(error)} Usage may be incomplete. No retry was made.</p>' if error else ''}<div class="bays">{''.join(cards)}</div>
<section class="ledger"><h2>01 / The shift ledger</h2><p class="subtle">Successful-job step averages sit beside completions. Quitting early never counts as efficiency. Maintenance tokens are included in input/output totals.</p><div class="scroll"><table><thead><tr><th>Memory policy</th><th>Completed / attempted</th><th>Mean steps · passes only</th><th>Input tokens</th><th>Output tokens</th><th>Of which maintenance</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><details><summary>Every job · passes and unfinished work</summary><div class="scroll"><table><tr><th>Job</th><th>Policy</th><th>Outcome</th><th>Steps</th><th>Total tokens</th><th>Reason</th></tr>{jobs}</table></div></details></section>
<section class="ledger"><h2>02 / Under the hood</h2><p class="subtle">Animation follows these recorded tool events. Coffee, smoke and terrible jokes consume zero model tokens.</p><div class="timeline">{timeline or 'No events yet. Start the offline shift to meet Sprocket.'}</div></section>
<p class="footnote">FICTIONAL REPAIR RULES · ORIGINAL SVG ART · LOCALHOST ONLY · REDUCED-MOTION PREFERENCES RESPECTED</p></section>'''
