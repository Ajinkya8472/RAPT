from config import types, bn, KAPPA

def ladder(s):
    return types[s.type]["ladder"]
def action(s, level=None):
    return ladder(s)[s.level if level is None else level][0]
def h(s, level=None):
    return ladder(s)[s.level if level is None else level][1]
def h0(s): 
    return ladder(s)[0][1]
def kappa(s, level=None): 
    return KAPPA[action(s, level)]

def allowed_levels(s):
    allowed = types[s.type]["allowed"]
    return [i for i, (a, _) in enumerate(ladder(s)) if a in allowed]

def total_bits(spans):
    return sum(h(s) for s in spans)

def compute_risk(spans, alpha = 1.0, beta = 1.0, gamma = 1.0):
    T = total_bits(spans)
    for s in spans:
        S = types[s.type]["S"]
        s.I = min(1.0, h0(s) / bn)
        s.C = min(1.0, (T - h(s)) / bn)
        Q = 1 - ((1 - S) ** alpha) * ((1 - s.I) ** beta) * ((1 - s.C) ** gamma)
        s.R = s.p * Q

def utility_retention(spans):
    tot = sum(s.U for s in spans)
    return sum(s.U * kappa(s) for s in spans) / tot if tot else 1.0

def utility_loss(spans):
    return sum(s.U * (1 - kappa(s)) for s in spans)

def span_cost(s, level, lam, mu):
    rho = h(s, level) / h0(s)
    return lam * s.R * rho + mu * s.U * (1 - kappa(s, level))

    