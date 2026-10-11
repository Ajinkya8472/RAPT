from samples import sample_prompt
from pipeline import run

res = run(sample_prompt(), key=b"\x01" * 32, bk=10, mode="budget", assume_p1=True)

print("SANITIZED:", res["sanitized"], "\n")
for row in res["log"]:
    print(row)
print(f"\nbits {res['bits_before']:.1f} -> {res['bits_after']:.1f} "
      f"(budget {res['bmax']:.1f}), D={res['D']:.3f}, Phi={res['phi']:.3f}")

assert round(res["bits_before"], 1) == 115.1
assert abs(res["bits_after"] - 20.4) < 1e-6
assert [r["Span"] for r in res["log"][1:]] == ["Rahul Mehta", "Pune", "City Care Clinic", "17 March 2026"]
assert abs(res["D"] - 0.43) < 1e-6
print("\nALL CHECKS PASSED - matches the paper's worked example")