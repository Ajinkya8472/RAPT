from detector import verhoeff_generate


def sample_prompt() -> str:
    prefix = "23456789012"
    n = prefix + verhoeff_generate(prefix)
    return (
        "Patient Rahul Mehta, age 43, visited City Care Clinic in Pune on 17 March 2026. "
        f"Aadhaar {n[:4]} {n[4:8]} {n[8:]}, phone +91 98765 43210. Summarise the visit."
    )