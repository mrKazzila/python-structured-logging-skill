import json


def render_total(amount_cents):
    print(json.dumps({'amount_cents': amount_cents}))
