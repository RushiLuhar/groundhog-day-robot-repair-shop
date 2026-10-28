"""Factual rendering only: no model, diagnosis, arithmetic, or hidden state."""
import json
from copy import deepcopy
from .config import LOG_VERSION

def tokens(value):
    import tiktoken
    return len(tiktoken.get_encoding('o200k_base').encode(json.dumps(value,sort_keys=True,separators=(',',':')),disallowed_special=()))

def observation(entry_id,job,action,result):
    allowed={'inspect','sample_sensor','probe','power','operate','calibrate','test'}
    if action.get('name') not in allowed or not isinstance(result,dict):raise ValueError('Unsupported observation schema.')
    schemas={
        'inspect':[{'chassis','component','revision','origin','installed_gain','installed_bias','indicated_temperature','power','visible_work'}],
        'sample_sensor':[{'level','reference_temperature','raw_reading'}],
        'probe':[{'airflow','reference_temperature'},{'continuity'},{'alignment_interlock','vent_interlock'}],
        'power':[{'ok','power'}], 'operate':[{'ok','operation'},{'ok','operation','visible_work'}],
        'calibrate':[{'ok','installed_gain','installed_bias'}], 'test':[{'pass','observation'}]}
    if set(result) not in schemas[action['name']]+[{'ok','observation'}]:raise ValueError('Unsupported tool result schema.')
    if len(json.dumps(result))>2048 or len(json.dumps(action))>1024:raise ValueError('Observation exceeds literal log length bound.')
    raw={'entry_id':entry_id,'job':job,'action':deepcopy(action),'result':deepcopy(result)}
    # Only status fields actually returned by the tool; never inspect the world here.
    status={k:result[k] for k in ('ok','pass','power','panel') if k in result}
    text=(f'Observation {entry_id} for ticket {job}.\n'
          f'Action: {json.dumps(action,sort_keys=True)}\n'
          f'Observed result: {json.dumps(result,sort_keys=True)}\n'
          f'Explicit visible status: {json.dumps(status,sort_keys=True) if status else "not reported by this tool"}.')
    return {**raw,'text':text,'log_version':LOG_VERSION}

def supplied(entries):return [{'entry_id':e['entry_id'],'text':e['text']} for e in entries]

def decode(entry):
    """Offline policy parses exactly the same log text supplied to a live agent."""
    lines=entry['text'].splitlines()
    return {'action':json.loads(lines[1].removeprefix('Action: ')),
            'result':json.loads(lines[2].removeprefix('Observed result: '))}
