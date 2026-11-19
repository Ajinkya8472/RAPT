import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
SYSTEM = "You are a helpful assistant. Answer concisely."


def mock_llm(sanitized: str) -> str:
    return (
        "**[Mock LLM — no real model was called]**\n\n"
        "Based on the text you provided:\n\n"
        f"> {sanitized}\n\n"
        "This is a placeholder reply."
    )


def ollama_llm(text: str, model: str = "llama3.2:3b", timeout: int = 180) -> str:
    payload = {"model": model, "stream": False,
               "messages": [{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": text}]}
    r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()["message"]["content"]


def call_llm(text: str, backend: str = "mock", model: str = "llama3.2:3b") -> str:
    if backend == "mock":
        return mock_llm(text)
    if backend == "ollama":
        return ollama_llm(text, model)
    raise ValueError(f"unknown backend {backend}")