from time import sleep
from config import bn, default_u, default_u_fallback
from detector import detect
from scoring import (allowed_levels, h0, total_bits, compute_risk, utility_retention, utility_loss)
from policy import select_levels, enforce_budget
from transformer import transform

def run(prompt, key, bk=10, mode="budget", lam=1.0, mu=1.0, assume_p1=True, use_model=False):
    spans = detect(prompt, use_model)
    for s in spans:
        s.U = default_u.get(s.type, default_u_fallback)
        if assume_p1:
            s.p = 1.0
        s.level = allowed_levels(s)[0]

    bits_before = sum(h0(s) for s in spans)
    bmax = bn - bk

    if mode == "full":
        for _ in range(3):
            compute_risk(spans)
            before = [s.level for s in spans]
            select_levels(spans, lam, mu)
            if [s.level for s in spans] == before:
                break

    bits_init = total_bits(spans)
    log = enforce_budget(spans, bmax)
    compute_risk(spans)

    log.insert(0, {"Step": 0, "Span": "-", "Move": "initial levels" + (" (direct IDs forced to SUR)" if mode == "budget" else ""),
                   "Bits saved": None, "Utility lost": None, "Ratio": None,
                   "B after": round(bits_init, 2)})

    sanitized, pieces, ledger = transform(prompt, spans, key)
    return dict(spans=spans, bits_before=bits_before, bits_after=total_bits(spans),
                bmax=bmax, phi=utility_retention(spans), D=utility_loss(spans),
                log=log, sanitized=sanitized, pieces=pieces, ledger=ledger) 