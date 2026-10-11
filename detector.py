import re
from dataclasses import dataclass 
from config import tau_low, city_state, months

_d = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
      [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
      [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
      [9,8,7,6,5,4,3,2,1,0]]
_p = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
      [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
      [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]
_inv = [0,4,3,2,1,5,6,7,8,9]

def verhoeff_valid(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _d[c][_p[i % 8][int(ch)]]
    return c == 0

def verhoeff_generate(prefix: str) -> str:
    c = 0 
    for i, ch in enumerate(reversed(prefix)):
        c = _d[c][_p[(i + 1) % 8][int(ch)]]
    return str(_inv[c])

@dataclass
class Span:
    start: int
    end: int
    text: str
    type: str
    p: float
    source: str = "rule"
    level: int = 0
    U: float = 0.1
    R: float = 0.0
    I: float = 0.0
    C: float = 0.0

_priority = {"checksum": 0, "rule": 1, "model": 2}

rules = [  # (type, regex, detection prob)
    ("GSTIN", r"(?<![A-Z0-9])\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Z0-9])", 0.95),
    ("PAN", r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])", 0.95),
    ("EMAIL", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", 0.90),
    ("PHONE", r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)", 0.90),
    ("VEHICLE", r"\b[A-Z]{2}[\s-]?\d{2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b", 0.90),
    ("DATE", rf"\b\d{{1,2}}\s(?:{months})\s\d{{4}}\b", 0.90),
    ("DATE", r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", 0.90),
    ("AGE", r"\b(?:aged?\s+\d{1,3}|\d{1,3}[- ]years?[- ]old)\b", 0.90),
]

# hardcoded stand-ins for the GLiNER span model
person_re = r"\b(?:Patient|Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Shri|Smt\.?)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
org_re = (r"\b(?:[A-Z][A-Za-z&]*\s){1,3}"
          r"(?:Clinic|Hospital|Bank|University|Institute|Technologies|Solutions|Pvt\.?\s?Ltd|Ltd)\b")
city_re = r"\b(?:" + "|".join(city_state) + r")\b"   

def detect(text: str, use_model: bool = False):
    spans = []

    for m in re.finditer(r"(?<!\d)[2-9]\d{3}\s?\d{4}\s?\d{4}(?!\d)", text):
        digits = re.sub(r"\s", "", m.group())
        ok = verhoeff_valid(digits)
        spans.append(Span(m.start(), m.end(), m.group(), "AADHAAR",
                          0.99 if ok else 0.55, "checksum" if ok else "rule"))

    for typ, pat, p in rules:
        for m in re.finditer(pat, text):
            spans.append(Span(m.start(), m.end(), m.group(), typ, p, "rule"))

    for m in re.finditer(person_re, text):
        spans.append(Span(m.start(1), m.end(1), m.group(1), "PERSON", 0.85, "model"))
    for m in re.finditer(org_re, text):
        spans.append(Span(m.start(), m.end(), m.group(), "ORG", 0.80, "model"))
    for m in re.finditer(city_re, text):
        spans.append(Span(m.start(), m.end(), m.group(), "LOCATION", 0.85, "model"))

    if use_model:
        from detector_model import model_spans
        for st, en, tx, ty, sc in model_spans(text):
            spans.append(Span(st, en, tx, ty, sc, "model"))
    else:
        for m in re.finditer(person_re, text):
            spans.append(Span(m.start(1), m.end(1), m.group(1), "PERSON", 0.85, "model"))
        for m in re.finditer(org_re, text):
            spans.append(Span(m.start(), m.end(), m.group(), "ORG", 0.80, "model"))
        for m in re.finditer(city_re, text):
            spans.append(Span(m.start(), m.end(), m.group(), "LOCATION", 0.85, "model"))

    # overlap resolution: priority, then confidence, then length
    spans.sort(key=lambda s: (_priority[s.source], -s.p, -(s.end - s.start)))
    kept = []
    for s in spans:
        if all(s.end <= k.start or s.start >= k.end for k in kept):
            kept.append(s)

    kept = [s for s in kept if s.p >= tau_low]   # below tau_low: not transformed
    return sorted(kept, key=lambda s: s.start)