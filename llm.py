def mock_llm(sanitized: str) -> str:
    return (
        "**[Mock LLM — no real model was called]**\n\n"
        "Based on the text you provided:\n\n"
        f"> {sanitized}\n\n"
        "This is a placeholder reply. Surrogate values appear above exactly as "
        "the cloud saw them, so the gateway can swap the real ones back in."
    )


def call_llm(sanitized: str, backend: str = "mock") -> str:
    if backend == "mock":
        return mock_llm(sanitized)
    # later: elif backend == "openai": ... / "anthropic": ... / "ollama": ...
    raise ValueError(f"unknown backend {backend}")