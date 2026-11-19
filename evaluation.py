"""evaluation.py - mini evaluation of RAPT against two baselines."""
import re
import sys
import pandas as pd

from pipeline import run
from detector import verhoeff_generate
from samples import sample_prompt

KEY = b"\x01" * 32


def aad(prefix):
    """Valid, Verhoeff-correct Aadhaar string built from an 11-digit prefix."""
    n = prefix + verhoeff_generate(prefix)
    return f"{n[:4]} {n[4:8]} {n[8:]}"


def build_tests():
    """(prompt, [(sensitive string, kind)]) where kind is 'direct' or 'quasi'."""
    tests = []

    p = sample_prompt()
    a0 = re.search(r"\d{4} \d{4} \d{4}", p).group()
    tests.append((p, [("Rahul Mehta", "quasi"), ("age 43", "quasi"), ("City Care Clinic", "quasi"),
                      ("Pune", "quasi"), ("17 March 2026", "quasi"),
                      (a0, "direct"), ("+91 98765 43210", "direct")]))

    tests.append(("Mr. Sharma, age 52, works at Apex Technologies in Mumbai. PAN ABCDE1234F, "
                  "phone 9876543210. Draft a loan eligibility summary.",
                  [("Sharma", "quasi"), ("age 52", "quasi"), ("Apex Technologies", "quasi"),
                   ("Mumbai", "quasi"), ("ABCDE1234F", "direct"), ("9876543210", "direct")]))

    tests.append(("Invoice for Shri Anil Kapoor, GSTIN 27ABCDE1234F1Z5, vehicle MH12AB1234, "
                  "email anil.kapoor@gmail.com. Please summarise the payment dispute.",
                  [("Anil Kapoor", "quasi"), ("27ABCDE1234F1Z5", "direct"),
                   ("MH12AB1234", "direct"), ("anil.kapoor@gmail.com", "direct")]))

    tests.append(("Dr. Meera Nair, aged 38, joined Tata Solutions on 05/06/2024. "
                  "Her phone is +91 91234 56789. Write a short bio.",
                  [("Meera Nair", "quasi"), ("aged 38", "quasi"), ("Tata Solutions", "quasi"),
                   ("05/06/2024", "quasi"), ("+91 91234 56789", "direct")]))

    a1 = aad("23456789012")
    tests.append((f"My Aadhaar is {a1} and my PAN is ABCDE1234F. Which form do I need to link them?",
                  [(a1, "direct"), ("ABCDE1234F", "direct")]))

    tests.append(("Explain how photosynthesis works in simple words.", []))

    tests.append(("Rahul called from Infosys in Hubli. His PAN is ABCDE1234F.",
                  [("Rahul", "quasi"), ("Infosys", "quasi"), ("Hubli", "quasi"),
                   ("ABCDE1234F", "direct")]))

    tests.append(("Priya Nair from Apollo Hospital in Chennai emailed priya.nair@gmail.com "
                  "about her appointment on 17 March 2026.",
                  [("Priya Nair", "quasi"), ("Apollo Hospital", "quasi"), ("Chennai", "quasi"),
                   ("priya.nair@gmail.com", "direct"), ("17 March 2026", "quasi")]))

    tests.append(("Sneha Kulkarni and Rohan Mehta from Infosys met in Nagpur. "
                  "Sneha's number is 9876543210.",
                  [("Sneha Kulkarni", "quasi"), ("Rohan Mehta", "quasi"), ("Infosys", "quasi"),
                   ("Nagpur", "quasi"), ("9876543210", "direct")]))

    a2 = aad("34567890123")
    tests.append((f"Patient Anita Desai, 29 years old, lives in Bengaluru. Aadhaar {a2}. "
                  "Email anita.d@outlook.com. Suggest a diet plan.",
                  [("Anita Desai", "quasi"), ("29 years old", "quasi"), ("Bengaluru", "quasi"),
                   (a2, "direct"), ("anita.d@outlook.com", "direct")]))

    tests.append(("Mrs. Kavita Rao reported that her car KA05MN4321 was hit near Mysuru on "
                  "12/08/2025. Phone 8123456789. Help me write an insurance claim.",
                  [("Kavita Rao", "quasi"), ("KA05MN4321", "direct"), ("Mysuru", "quasi"),
                   ("12/08/2025", "quasi"), ("8123456789", "direct")]))

    tests.append(("Ms. Divya Iyer of State Bank in Chennai, PAN FGHIJ5678K, wants a home loan. "
                  "Explain the documents required.",
                  [("Divya Iyer", "quasi"), ("State Bank", "quasi"), ("Chennai", "quasi"),
                   ("FGHIJ5678K", "direct")]))

    tests.append(("Rahul called me yesterday about the invoice.", [("Rahul", "quasi")]))

    tests.append(("The surgery for Mr. Gupta was on March 17, 2026 at Apollo Hospital in Delhi.",
                  [("Gupta", "quasi"), ("March 17, 2026", "quasi"),
                   ("Apollo Hospital", "quasi"), ("Delhi", "quasi")]))

    a3 = aad("45678901234")
    tests.append((f"Customer Vikram Singh, phone 9988776655, email vikram@example.com, "
                  f"Aadhaar {a3}, PAN PQRST1234U, vehicle DL01AB1234 needs a KYC update.",
                  [("Vikram Singh", "quasi"), ("9988776655", "direct"),
                   ("vikram@example.com", "direct"), (a3, "direct"),
                   ("PQRST1234U", "direct"), ("DL01AB1234", "direct")]))

    tests.append(("Meeting with Dr. Rao at Manipal Hospital on 03/04/2026 regarding patient "
                  "Suresh Patil, age 61.",
                  [("Rao", "quasi"), ("Manipal Hospital", "quasi"), ("03/04/2026", "quasi"),
                   ("Suresh Patil", "quasi"), ("age 61", "quasi")]))
    return tests


# ---------------- helpers ----------------
def overlap(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def mask_all(prompt, spans):
    out, pos = [], 0
    for s in sorted(spans, key=lambda s: s.start):
        out.append(prompt[pos:s.start])
        out.append(f"[{s.type}]")
        pos = s.end
    out.append(prompt[pos:])
    return "".join(out)


def words(t):
    return set(re.findall(r"[A-Za-z0-9]+", t.lower()))


def word_retention(orig, new):
    o = words(orig)
    return len(o & words(new)) / len(o) if o else 1.0


def leaked(text, gold, kind=None):
    return sum(1 for g, k in gold if (kind is None or k == kind) and g in text)


# ---------------- main evaluation ----------------
def evaluate(use_model=False, bk=10, mode="budget", assume_p1=True):
    names = ("No protection", "Mask everything", "RAPT")
    acc = {n: dict(bits=[], phi=[], words=[], leak=0, dleak=0) for n in names}
    rows = []
    total_gold = total_direct = found_all = det_all = tp_all = within = 0
    missed_leak = kept_leak = 0

    tests = build_tests()
    for idx, (prompt, gold) in enumerate(tests, 1):
        res = run(prompt, KEY, bk=bk, mode=mode, assume_p1=assume_p1, use_model=use_model)
        spans = res["spans"]

        # detection quality
        pos = [(g, k, prompt.find(g)) for g, k in gold]
        found = sum(any(overlap(i, i + len(g), s.start, s.end) for s in spans)
                    for g, k, i in pos if i >= 0)
        tp = sum(any(overlap(i, i + len(g), s.start, s.end) for g, k, i in pos if i >= 0)
                 for s in spans)
        found_all += found
        det_all += len(spans)
        tp_all += tp
        total_gold += len(gold)
        total_direct += sum(1 for _, k in gold if k == "direct")

        ok = res["bits_after"] <= res["bmax"] + 1e-9
        within += ok

        texts = {"No protection": prompt,
                 "Mask everything": mask_all(prompt, spans),
                 "RAPT": res["sanitized"]}
        bits = {"No protection": res["bits_before"], "Mask everything": 0.0,
                "RAPT": res["bits_after"]}
        phi = {"No protection": 1.0, "Mask everything": 0.0 if spans else 1.0,
               "RAPT": res["phi"]}
        for n in names:
            a = acc[n]
            a["bits"].append(bits[n])
            a["phi"].append(phi[n])
            a["words"].append(word_retention(prompt, texts[n]))
            a["leak"] += leaked(texts[n], gold)
            a["dleak"] += leaked(texts[n], gold, "direct")

        for g, k in gold:
            i = prompt.find(g)
            if i >= 0 and g in texts["RAPT"]:
                hit = any(overlap(i, i + len(g), s.start, s.end) for s in spans)
                if hit:
                    kept_leak += 1
                else:
                    missed_leak += 1

        rows.append({"#": idx, "Gold": len(gold), "Found": found, "Detected": len(spans),
                     "Bits before": round(res["bits_before"], 1),
                     "Bits after": round(res["bits_after"], 1),
                     "Within budget": "yes" if ok else "NO",
                     "Utility Φ %": round(res["phi"] * 100),
                     "Gold leaked (RAPT)": leaked(texts["RAPT"], gold),
                     "Direct leaked (RAPT)": leaked(texts["RAPT"], gold, "direct"),
                     "Prompt": prompt[:60] + ("…" if len(prompt) > 60 else "")})

    n = len(tests)
    mean = lambda xs: sum(xs) / len(xs)
    pct = lambda a, b: 100 * a / b if b else 0.0
    cmp_df = pd.DataFrame([{
        "Strategy": s,
        "Avg bits left (detected)": round(mean(acc[s]["bits"]), 1),
        "Model utility Φ %": round(100 * mean(acc[s]["phi"]), 1),
        "Words kept %": round(100 * mean(acc[s]["words"]), 1),
        "Sensitive items leaked %": round(pct(acc[s]["leak"], total_gold), 1),
        "Direct IDs leaked %": round(pct(acc[s]["dleak"], total_direct), 1),
    } for s in names])

    det = {"recall": pct(found_all, total_gold), "precision": pct(tp_all, det_all),
           "within": pct(within, n), "n": n, "gold": total_gold,
           "missed": missed_leak, "kept": kept_leak}
    return pd.DataFrame(rows), cmp_df, det


def frontier(prompt, use_model=False, mode="budget", bks=range(0, 27, 2)):
    """Privacy-utility curve: sweep the anonymity margin b_k."""
    out = []
    for bk in bks:
        r = run(prompt, KEY, bk=bk, mode=mode, assume_p1=True, use_model=use_model)
        out.append({"b_k": bk, "Budget": round(r["bmax"], 1),
                    "Bits sent": round(r["bits_after"], 1),
                    "Utility %": round(r["phi"] * 100, 1)})
    return pd.DataFrame(out)


if __name__ == "__main__":
    use_model = "--gliner" in sys.argv
    per, cmp_df, det = evaluate(use_model=use_model)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    print(f"\n=== RAPT evaluation (GLiNER {'ON' if use_model else 'OFF'}) ===\n")
    print(per.to_string(index=False))
    print("\n--- Strategy comparison ---")
    print(cmp_df.to_string(index=False))
    print(f"\nDetection recall    : {det['recall']:.1f}%  ({det['gold']} labelled items)")
    print(f"Detection precision : {det['precision']:.1f}%")
    print(f"Within budget       : {det['within']:.0f}% of {det['n']} prompts")
    print("\n--- Privacy-utility curve (paper sample) ---")
    print(frontier(sample_prompt(), use_model=use_model).to_string(index=False))
    per.to_csv("eval_results.csv", index=False)
    print("\nSaved per-prompt results to eval_results.csv")
    print(f"RAPT leaks: {det['missed']} undetected + {det['kept']} deliberately kept (within budget)")