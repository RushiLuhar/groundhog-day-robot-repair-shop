"""Standard-rate estimates, not invoices. No live pricing calls during a run."""
PRICE_DATE = '2026-10-29'
PRICE_URL = 'https://developers.openai.com/api/docs/pricing'
# USD per million tokens; verified from each official model page on PRICE_DATE:
# https://developers.openai.com/api/docs/models/gpt-6-luna
# https://developers.openai.com/api/docs/models/gpt-6-sol
RATES = {'gpt-6-luna': (0.10, 0.50), 'gpt-6-sol': (2.00, 10.00)}
COST_NOTE = ('Uses OpenAI standard text prices checked on 2026-10-29. '
             'Luna costs $0.10 per million input tokens and $0.50 per million output tokens. '
             'GPT-6 Sol costs $2.00 per million input tokens and $10.00 per million output tokens. '
             'Requests above 272,000 input tokens use 2× the input rate and 1.5× the output rate. '
             'The estimate includes memory updates. It does not account for cache discounts, '
             'extra cache-write charges, regional or service-tier adjustments, or taxes. '
             'Your bill may differ. If a request fails, some usage and cost may be missing.')

def estimate(model, input_tokens, output_tokens, live=True):
    if not live:
        return 0.0
    if model not in RATES:
        return None
    incoming, outgoing = RATES[model]
    if input_tokens > 272000:
        incoming *= 2
        outgoing *= 1.5
    return (input_tokens * incoming + output_tokens * outgoing) / 1000000

def total_cost(rows):
    values = [r.get('cost_usd') for r in rows]
    return None if any(v is None for v in values) else sum(values)

def money(value):
    return 'N/A' if value is None else f'${value:.6f}'
