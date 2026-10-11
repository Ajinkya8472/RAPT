import os, html
import pandas as pd
import streamlit as st

from pipeline import run
from samples import sample_prompt
from transformer import restore
from llm import call_llm
from config import bn
from scoring import action, h, h0, kappa

st.set_page_config(page_title="RAPT", page_icon="🛡️", layout="wide")
st.title("🛡️ RAPT: Risk-Adaptive Prompt Transformation")
st.caption("A local privacy gateway: sanitize → cloud LLM → restore")

COLORS = {"KEEP": "#9be7a0", "GEN1": "#ffd54f", "GEN2": "#ffd54f",
          "SUR": "#7cc4ff", "SUP": "#ff8a8a"}

if "key" not in st.session_state:
    st.session_state.key = os.urandom(32)       # per-session secret key


def mark(text, act):
    t = html.escape(text)
    if act is None:
        return t
    return (f'<span style="background:{COLORS[act]};color:#111;font-weight:600;'
            f'padding:2px 6px;border-radius:4px">{t}</span>')


def box(inner):
    return f'<div style="white-space:pre-wrap;line-height:1.9">{inner}</div>'


# ---------------- sidebar ----------------
with st.sidebar:
    st.header("Controls")
    bk = st.slider("Anonymity margin b_k (bits)", 0, 25, 10)
    st.caption(f"B_N = {bn} bits  →  budget B_max = {bn - bk:.1f} bits")
    mode_label = st.radio("Policy mode",
                          ["Budget only (paper's worked example)",
                           "Full (per-span cost + budget)"])
    mode = "budget" if mode_label.startswith("Budget") else "full"
    lam = st.slider("λ privacy weight", 0.1, 5.0, 1.0, 0.1, disabled=(mode == "budget"))
    mu = st.slider("μ utility weight", 0.1, 5.0, 1.0, 0.1, disabled=(mode == "budget"))
    p1 = st.checkbox("Assume perfect detection (p = 1)", True)
    use_model = st.checkbox("Use GLiNER span model (slower first run)", False)
    st.markdown("**Legend**")
    for k, lbl in [("KEEP", "kept"), ("GEN1", "generalized"), ("SUR", "surrogate"), ("SUP", "suppressed")]:
        st.markdown(f'<span style="background:{COLORS[k]};color:#111;font-weight:600;'
                f'padding:2px 8px;border-radius:4px">{lbl}</span>',
                unsafe_allow_html=True)

# ---------------- input ----------------
prompt = st.text_area("Your prompt", value=sample_prompt(), height=130)
if st.button("🛡️ Run RAPT", type="primary"):
    st.session_state.res = run(prompt, st.session_state.key, bk, mode, lam, mu, p1, use_model=use_model)
    st.session_state.prompt = prompt

res = st.session_state.get("res")
if not res:
    st.info("Press **Run RAPT** to sanitize the prompt.")
    st.stop()

spans, prompt = res["spans"], st.session_state.prompt

# ---------------- metrics ----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Identifying bits (original)", f"{res['bits_before']:.1f}")
c2.metric("Identifying bits (sent)", f"{res['bits_after']:.1f}",
          delta=f"{res['bits_after'] - res['bits_before']:.1f}", delta_color="inverse")
c3.metric("Budget B_max", f"{res['bmax']:.1f}")
c4.metric("Utility retained Φ", f"{res['phi'] * 100:.0f}%")

used = min(res["bits_after"] / res["bmax"], 1.0) if res["bmax"] > 0 else 0.0
st.progress(used, text=f"Budget used: {res['bits_after']:.1f} / {res['bmax']:.1f} bits"
                       + ("  ✅ within budget" if res["bits_after"] <= res["bmax"] + 1e-9 else "  ⚠️ over budget"))

# ---------------- tabs ----------------
t1, t2, t3, t4, t5 = st.tabs(["Side by side", "Span table", "Escalation log",
                              "Comparison", "Cloud & restore"])

with t1:
    a, b = st.columns(2)
    # original, highlighted by the action chosen for each span
    orig, pos = "", 0
    for s in spans:
        orig += mark(prompt[pos:s.start], None) + mark(s.text, action(s))
        pos = s.end
    orig += mark(prompt[pos:], None)
    a.subheader("Original (stays local)")
    a.markdown(box(orig), unsafe_allow_html=True)
    b.subheader("Sanitized (sent to cloud)")
    b.markdown(box("".join(mark(t, act) for t, act in res["pieces"])), unsafe_allow_html=True)

with t2:
    rows = [{"Text": s.text, "Type": s.type, "p": round(s.p, 2), "Action": action(s),
             "Bits (orig)": h0(s), "Bits (left)": h(s),
             "Identifiability I": round(s.I, 2), "Exposure C": round(s.C, 2),
             "Risk R": round(s.R, 2), "Importance U": s.U, "κ": kappa(s)} for s in spans]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with t3:
    st.dataframe(pd.DataFrame(res["log"]), use_container_width=True, hide_index=True)
    st.caption("Each step escalates the span with the highest bits-saved per utility-lost ratio.")

with t4:
    cmp_df = pd.DataFrame([
        {"Strategy": "No protection", "Bits left": res["bits_before"], "Utility %": 100.0},
        {"Strategy": "Mask everything", "Bits left": 0.0, "Utility %": 0.0},
        {"Strategy": "RAPT", "Bits left": round(res["bits_after"], 1), "Utility %": round(res["phi"] * 100, 1)},
    ])
    st.dataframe(cmp_df, use_container_width=True, hide_index=True)
    x, y = st.columns(2)
    x.caption("Identifying bits left (lower = more private)")
    x.bar_chart(cmp_df.set_index("Strategy")["Bits left"])
    y.caption("Utility retained % (higher = more useful)")
    y.bar_chart(cmp_df.set_index("Strategy")["Utility %"])

with t5:
    st.subheader("What the cloud received")
    st.code(res["sanitized"], language=None)
    reply = call_llm(res["sanitized"], backend="mock")
    st.subheader("Raw cloud reply (contains surrogates)")
    st.markdown(reply)
    st.subheader("Restored reply (shown to you)")
    st.markdown(restore(reply, res["ledger"]))
    with st.expander("Ledger (local only, never sent)"):
        st.json(res["ledger"])