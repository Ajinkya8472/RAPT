from gliner import GLiNER

model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
text = "Rahul called me yesterday from Infosys in Bengaluru, then Priya Nair from Apollo Hospital in Hubli."
for e in model.predict_entities(text, ["person", "organization", "location"], threshold=0.5):
    print(e["text"], "|", e["label"], "|", round(e["score"], 2), "|", e["start"], e["end"])