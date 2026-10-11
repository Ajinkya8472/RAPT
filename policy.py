from scoring import (allowed_levels, h, kappa, action, total_bits, span_cost)

eps = 1e-9

def select_levels(spans, lam, mu):
    for s in spans:
        s.level = min(allowed_levels(s), key=lambda l: (span_cost(s, l, lam, mu), l))

def next_allowed(s):
    for l in allowed_levels(s):
        if l > s.level:
            return l
    return None

def enforce_budget(spans, bmax):
    log, step = [], 0
    while total_bits(spans) > bmax + eps:
        cands = [s for s in spans if next_allowed(s) is not None and h(s) > 0]
        if not cands:
            break
            
        def omega(s):
            nxt = next_allowed(s)
            saved = h(s) - h(s, nxt)
            lost = s.U * (kappa(s) - kappa(s, nxt))
            return float("inf") if lost < 1e-12 else saved / lost

        best = max(cands, key=omega)
        nxt = next_allowed(best)
        saved = h(best) - h(best, nxt)
        lost = best.U * (kappa(best) - kappa(best, nxt))
        old_action = action(best)
        best.level = nxt
        step += 1
        log.append({
            "Step": step, "Span": best.text,
            "Move": f"{old_action} -> {action(best)}",
            "Bits saved": round(saved, 2), "Utility lost": round(lost, 3),
            "Ratio": round(saved / lost, 1) if lost > 1e-12 else None,
            "B after": round(total_bits(spans), 2),
        })
    return log