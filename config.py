import math

n_population = 1.4e9
bn = round(math.log2(n_population), 1)
tau_low = 0.30

KAPPA = {"KEEP": 1.0, "GEN1": 0.85, "GEN2": 0.60, "SUR": 0.80, "SUP": 0.0}

default_u = {"PERSON": 0.9, "AGE": 0.6, "ORG": 0.5, "LOCATION": 0.4, "DATE": 0.5, "AADHAAR": 0.1, "PHONE": 0.1}
default_u_fallback = 0.1

months = ("January|February|March|April|May|June|July|August|"
          "September|October|November|December")

city_state = {
    "Pune": "Maharashtra", "Mumbai": "Maharashtra", "Nagpur": "Maharashtra",
    "Nashik": "Maharashtra", "Bengaluru": "Karnataka", "Bangalore": "Karnataka",
    "Mysuru": "Karnataka", "Chennai": "Tamil Nadu", "Hyderabad": "Telangana",
    "Kolkata": "West Bengal", "Ahmedabad": "Gujarat", "Surat": "Gujarat",
    "Jaipur": "Rajasthan", "Lucknow": "Uttar Pradesh", "Delhi": "Delhi",
} 

def _direct(S, bits):
    return dict(S=S, ladder=[("KEEP", bits), ("SUR", 0.0), ("SUP", 0.0)], allowed=["SUR", "SUP"])

types = {
    "AADHAAR": _direct(1.00, 30.4),
    "PAN":     _direct(0.95, 30.4),
    "PHONE":   _direct(0.90, 30.4),
    "EMAIL":   _direct(0.85, 30.4),
    "VEHICLE": _direct(0.80, 30.4),
    "GSTIN":  dict(S=0.50, ladder=[("KEEP", 20.0), ("SUR", 0.0), ("SUP", 0.0)], allowed=["KEEP","SUR", "SUP"]),
    "PERSON": dict(S=0.70, ladder=[("KEEP", 18.0), ("SUR", 0.0), ("SUP", 0.0)], allowed=["KEEP","SUR", "SUP"]),
    "DATE":   dict(S=0.40, ladder=[("KEEP", 10.0), ("GEN1", 5.1), ("GEN2", 1.6), ("SUP", 0.0)], allowed=["KEEP", "GEN1", "GEN2", "SUP"]),
    "ORG":    dict(S=0.35, ladder=[("KEEP", 10.0), ("GEN1", 4.0), ("SUP", 0.0)], allowed=["KEEP","GEN1", "SUP"]),
    "LOCATION": dict(S=0.30, ladder=[("KEEP", 10.0), ("GEN1", 5.0), ("SUP", 0.0)], allowed=["KEEP","GEN1", "SUP"]),
    "AGE":    dict(S=0.30, ladder=[("KEEP", 6.3), ("GEN1", 4.0), ("GEN2", 3.0), ("SUP", 0.0)], allowed=["KEEP","GEN1","GEN2","SUP"]),
}