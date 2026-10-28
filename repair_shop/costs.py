"""Standard-rate estimates, not invoices. No live pricing calls during a run."""
PRICE_DATE = '2026-10-28'
PRICE_URL = 'https://developers.openai.com/api/docs/models/gpt-6-luna'
# USD per million tokens; verified from the official model page on PRICE_DATE.
RATES = {'gpt-6-luna': (0.10, 0.50)}
COST_NOTE = ('Estimated USD at standard uncached text rates checked 2026-10-28. '
             'Luna: $0.10 input / $0.50 output per million tokens; above 272K input, 2x input and 1.5x output. '
             'Includes memory calls; excludes cache discounts, cache-write premiums, '
             'regional/service-tier adjustments and taxes. Not a billing invoice. '
             'Unknown models show N/A; errors can leave usage/cost incomplete.')

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
