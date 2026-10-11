_model = None
labels = {"person": "PERSON", "organization": "ORG", "location": "LOCATION"}


def load():
    """Load GLiNER once (first call downloads the weights)."""
    global _model
    if _model is None:
        from gliner import GLiNER
        _model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
    return _model


def model_spans(text, threshold=0.5):
    out = []
    for e in load().predict_entities(text, list(labels), threshold=threshold):
        out.append((e["start"], e["end"], e["text"], labels[e["label"]], float(e["score"])))
    return out