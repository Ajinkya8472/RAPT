import hmac, hashlib, re
from config import city_state, months
from detector import verhoeff_valid
from scoring import action

first = ["Arjun", "Priya", "Rohan", "Neha", "Vikram", "Anita", "Karan", "Meera", "Sanjay", "Divya"]
last = ["Joshi", "Kulkarni", "Rao", "Nair", "Singh", "Patil", "Iyer", "Desai", "Gupta", "Bose"]

def _stream(key: bytes, t: str, v: str, c: int = 0):
    msg = f"{t}|{v}" + (f"|{c}" if c else "")
    seed = hmac.new(key, msg.encode(), hashlib.sha256).digest()
    n = 0
    while True:
        for b in hashlib.sha256(seed + n.to_bytes(4, "big")).digest():
            yield b
        n += 1

def _fp(value, st):
    out = []
    for ch in value:
        if  ch.isdigit():  out.append(str(next(st) % 10))
        elif ch.isupper(): out.append(chr(65 + next(st) % 26))
        elif ch.islower(): out.append(chr(97 + next(st) % 26))
        else:              out.append(ch)
    return "".join(out)

def _surrogate(span, key, c=0):
    t = span.type
    norm = re.sub(r"\s+",  " ", span.text.strip().lower())
    st = _stream(key, t, norm, c)

    if t == "PERSON":
        return f"{first[next(st) % len(first)]} {last[next(st) % len(last)]}"

    if t == "AADHAAR":
        chars = list(_fp(span.text, st))
        pos = [i for i, ch in enumerate(chars) if ch.isdigit()]
        chars[pos[0]] = str(2 + next(st) % 8)
        while verhoeff_valid("".join(chars[i] for i in pos)):
            chars[pos[-1]] = str((int(chars[pos[-1]]) + 1) % 10)
        return "".join(chars)

    if t == "PHONE":
        m = re.match(r"(\+91[\s-]?|0)?(.*)", span.text, re.S)
        rest = list(_fp(m.group(2), st))
        rest[0] = str(6 + next(st) % 4)
        return (m.group(1) or "") + "".join(rest)
    
    if t == "EMAIL":
        local = span.text.split("@")[0]
        return f"{_fp(local, st)}@example.com"

    return _fp(span.text, st)

def _org_descriptor(txt):
    for kw, d in [("Clinic", "a private clinic"), ("Hospital", "a hospital"), ("Bank", "a bank"), ("University", "a university"), ("Institute", "an institute")]:
        if kw in txt:
            return d
    return "a company"

def _generalize(span, act):
    t, txt = span.type, span.text
    if t == "DATE":
        m = re.search(rf"({months})\s(\d{{4}})", txt)
        if m:
            return f"{m.group(1)} {m.group(2)}" if act == "GEN1" else m.group(2)
        m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", txt)
        if m:
            return f"{m.group(2)}/{m.group(3)}" if act == "GEN1" else m.group(3)
    if t == "LOCATION":
        return city_state.get(txt, "India")
    if t == "ORG":
        return _org_descriptor(txt)
    if t == "AGE":
        n = int(re.search(r"\d+", txt).group())
        band = f"{n//5*5}-{n//5*5+4}" if act == "GEN1" else f"{n//10*10}s"
        return re.sub(r"\d+", band, txt, count=1)
    return f"[{t}]"

def transform(prompt, spans, key):
    pieces, ledger, pos = [], {}, 0
    for s in sorted(spans, key=lambda s: s.start):
        pieces.append((prompt[pos:s.start], None))
        act = action(s)
        if act == "KEEP":
            new = s.text
        elif act in ("GEN1", "GEN2"):
            new = _generalize(s, act)
        elif act == "SUR":
            c = 0
            while True:
                new = _surrogate(s, key, c)
                if ledger.get(new, s.text) == s.text:
                    break
                c += 1
            ledger[new] = s.text
        else:
            new = f"[{s.type}]"
        pieces.append((new, act))
        pos = s.end
    pieces.append((prompt[pos:], None))
    return "".join(p for p, _ in pieces), pieces, ledger

def restore(text, ledger):
    for sur in sorted(ledger, key=len, reverse=True):
        text = text.replace(sur, ledger[sur])
    return text    