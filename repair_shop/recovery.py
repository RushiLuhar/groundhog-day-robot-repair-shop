"""Read-only recovery of incomplete reports; never resumes or retries a request."""
from copy import deepcopy
from .costs import total_cost


def attempt_key(value):
    return (value.get('repetition', 1), value['mode'], value.get('job', value.get('ticket', {}).get('job')))


def recover_report(report, reason='Execution was interrupted; this report contains the last saved evidence.', uncertain=True):
    data = deepcopy(report)
    data['completed'] = False
    data['interrupted'] = True
    data['stop_reason'] = data.get('stop_reason') or reason
    data['usage_complete'] = data.get('usage_complete', True) and not uncertain
    pending = data.get('active_request')
    if pending:
        pending['status'] = 'unknown' if uncertain else 'interrupted'
    ended = {attempt_key(r) for r in data['results']}
    active = data.get('active_attempt')
    # Legacy checkpoints did not store active_attempt. Only infer from recorded events.
    if not active:
        for event in data.get('events', []):
            if event['kind'] == 'start' and attempt_key(event) not in ended:
                active = deepcopy(event)
        if active:
            for event in data.get('events', []):
                if attempt_key(event) == attempt_key(active):
                    for key in ('steps', 'passed', 'reason', 'memory_audit'):
                        if key in event:
                            active[key] = deepcopy(event[key])
    if active and attempt_key(active) not in ended:
        key = attempt_key(active)
        cfg = next(m for m in data['configuration']['mechanics'] if m['bay_id'] == active['mode'])
        calls = [c for c in data.get('calls', []) if attempt_key(c) == key]
        passed = bool(active.get('passed', False))
        data['results'].append({
            'mode': active['mode'], 'model': calls[-1]['model'] if calls else cfg['model'],
            'repetition': key[0], 'job': key[2], 'memory_policy': cfg['memory'],
            'memory_update_policy': cfg.get('memory_update_policy', 'replace_v1'),
            'reasoning': cfg['reasoning'], 'step_limit': cfg['step_limit'],
            'passed': passed, 'steps': active.get('steps', 0), 'interrupted': True,
            'reason': 'passed test' if passed else reason,
            'warning': reason if passed else '', 'memory_audit': active.get('memory_audit', {}),
            'memory_update': {}, 'task_metrics': active.get('task_metrics', {}),
            'input': sum(c['input'] for c in calls), 'output': sum(c['output'] for c in calls),
            'maintenance': sum(c['input'] + c['output'] for c in calls if c['kind'] == 'memory'),
            'calls': len(calls), 'cost_usd': total_cost(calls),
        })
    data['active_attempt'] = None
    return data
