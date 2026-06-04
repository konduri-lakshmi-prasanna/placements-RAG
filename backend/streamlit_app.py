"""
streamlit_app.py — PlacementIQ Streamlit Frontend

Replaces the React frontend entirely.
Tabs:
  1. Ask PlacementIQ  — chat interface with confidence bar
  2. Eligibility Filter — CGPA/backlog/bond filter
  3. Hiring Charts     — bar charts by role
  4. Evaluation Suite  — run eval and see results

Deploy on Streamlit Cloud:
  1. Push this file to GitHub root of backend/
  2. Go to share.streamlit.io → New app → select repo → main file: streamlit_app.py
  3. Add GROQ_API_KEY in Secrets
"""

import os
import sys
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PlacementIQ — SVECW",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Backend URL ───────────────────────────────────────────────────────────
# When running locally: http://localhost:8000
# When deployed: set BACKEND_URL in Streamlit secrets or environment
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Custom CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme tweaks */
    .stApp { background-color: #09090b; color: #f4f4f5; }
    .stTextInput > div > div > input { background: #18181b; border: 1px solid #3f3f46; color: #f4f4f5; border-radius: 12px; }
    .stButton > button { border-radius: 10px; font-weight: 600; }
    .stTabs [data-baseweb="tab"] { font-size: 14px; }
    .stSlider > div { color: #a1a1aa; }

    /* Chat bubbles */
    .user-bubble {
        background: #7c3aed;
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 4px 0;
        max-width: 80%;
        margin-left: auto;
        font-size: 15px;
        line-height: 1.6;
    }
    .bot-bubble {
        background: #18181b;
        border: 1px solid #3f3f46;
        color: #f4f4f5;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 4px 0;
        max-width: 80%;
        font-size: 15px;
        line-height: 1.6;
    }
    .query-badge {
        display: inline-block;
        font-size: 11px;
        padding: 2px 10px;
        border-radius: 999px;
        font-family: monospace;
        margin-bottom: 6px;
        border: 1px solid;
    }
    .badge-web_search          { background: rgba(59,130,246,0.15); color: #93c5fd; border-color: rgba(59,130,246,0.3); }
    .badge-student_eligibility { background: rgba(20,184,166,0.15); color: #5eead4; border-color: rgba(20,184,166,0.3); }
    .badge-threshold_filter    { background: rgba(14,165,233,0.15); color: #7dd3fc; border-color: rgba(14,165,233,0.3); }
    .badge-direct_lookup       { background: rgba(16,185,129,0.15); color: #6ee7b7; border-color: rgba(16,185,129,0.3); }
    .badge-temporal            { background: rgba(245,158,11,0.15); color: #fcd34d; border-color: rgba(245,158,11,0.3); }
    .badge-conflict            { background: rgba(239,68,68,0.15);  color: #fca5a5; border-color: rgba(239,68,68,0.3);  }
    .badge-out_of_corpus       { background: rgba(113,113,122,0.15);color: #a1a1aa; border-color: rgba(113,113,122,0.3);}
    .badge-general             { background: rgba(113,113,122,0.15);color: #a1a1aa; border-color: rgba(113,113,122,0.3);}
    .hallucination-warning {
        background: rgba(153,27,27,0.2);
        border: 1px solid rgba(239,68,68,0.3);
        border-radius: 10px;
        padding: 10px 14px;
        color: #fca5a5;
        font-size: 13px;
        margin-top: 6px;
    }
    .company-card {
        background: #18181b;
        border: 1px solid #3f3f46;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .company-card:hover { border-color: rgba(124,58,237,0.4); }
</style>
""", unsafe_allow_html=True)

# ── Helper: call backend ──────────────────────────────────────────────────
def query_backend(question: str) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/query",
            json={"question": question, "use_agent": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"answer": "⚠️ Backend is offline. Please start uvicorn first.", "query_type": "error",
                "sources": [], "conflict_warning": None, "multihop_steps": [],
                "confidence": 0.0, "lookback_ratio": 0.0, "hallucination_warning": None}
    except Exception as e:
        return {"answer": f"⚠️ Error: {str(e)}", "query_type": "error",
                "sources": [], "conflict_warning": None, "multihop_steps": [],
                "confidence": 0.0, "lookback_ratio": 0.0, "hallucination_warning": None}

def check_health() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

# ── Confidence bar ────────────────────────────────────────────────────────
def show_confidence(confidence: float, lookback: float):
    if confidence == 1.0 and lookback == 1.0:
        return   # tool answer, skip
    if confidence == 0.0 and lookback == 0.0:
        return   # out of corpus, skip

    pct = int(confidence * 100)
    if confidence >= 0.75:
        color, label = "#10b981", "🟢 High confidence"
    elif confidence >= 0.5:
        color, label = "#f59e0b", "🟡 Medium confidence"
    else:
        color, label = "#ef4444", "🔴 Low confidence"

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-top:6px;">
        <div style="flex:1;height:6px;background:#3f3f46;border-radius:999px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:999px;"></div>
        </div>
        <span style="font-size:12px;color:{color};font-family:monospace;">{pct}% · {label}</span>
    </div>
    """, unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────
COMPANIES = [
    {"name":"TCS",          "min_cgpa":7.5,"max_backlogs":0,"package_lpa":4.1, "bond_years":0,"tech_focus":"System Design"},
    {"name":"Infosys",      "min_cgpa":8.0,"max_backlogs":0,"package_lpa":42.9,"bond_years":0,"tech_focus":"Java"},
    {"name":"Deloitte",     "min_cgpa":7.7,"max_backlogs":1,"package_lpa":9.6, "bond_years":1,"tech_focus":"System Design"},
    {"name":"Accenture",    "min_cgpa":8.2,"max_backlogs":0,"package_lpa":17.3,"bond_years":2,"tech_focus":"System Design"},
    {"name":"Amazon",       "min_cgpa":6.4,"max_backlogs":1,"package_lpa":28.6,"bond_years":2,"tech_focus":"C++"},
    {"name":"Flipkart",     "min_cgpa":7.8,"max_backlogs":2,"package_lpa":25.3,"bond_years":2,"tech_focus":"Python"},
    {"name":"Google",       "min_cgpa":7.4,"max_backlogs":0,"package_lpa":42.0,"bond_years":1,"tech_focus":"Python"},
    {"name":"Microsoft",    "min_cgpa":6.1,"max_backlogs":1,"package_lpa":21.4,"bond_years":0,"tech_focus":"C++"},
    {"name":"Wipro",        "min_cgpa":6.7,"max_backlogs":1,"package_lpa":26.1,"bond_years":1,"tech_focus":"System Design"},
    {"name":"Cognizant",    "min_cgpa":8.4,"max_backlogs":0,"package_lpa":42.3,"bond_years":2,"tech_focus":"Java"},
    {"name":"Capgemini",    "min_cgpa":7.1,"max_backlogs":0,"package_lpa":38.3,"bond_years":2,"tech_focus":"C++"},
    {"name":"IBM",          "min_cgpa":7.5,"max_backlogs":2,"package_lpa":27.5,"bond_years":0,"tech_focus":"C++"},
    {"name":"Adobe",        "min_cgpa":7.5,"max_backlogs":0,"package_lpa":18.3,"bond_years":1,"tech_focus":"System Design"},
    {"name":"Oracle",       "min_cgpa":7.7,"max_backlogs":0,"package_lpa":17.3,"bond_years":2,"tech_focus":"Python"},
    {"name":"SAP",          "min_cgpa":8.4,"max_backlogs":0,"package_lpa":20.7,"bond_years":2,"tech_focus":"C++"},
    {"name":"HCL",          "min_cgpa":8.4,"max_backlogs":1,"package_lpa":28.1,"bond_years":2,"tech_focus":"Cloud"},
    {"name":"Tech Mahindra","min_cgpa":8.1,"max_backlogs":2,"package_lpa":35.9,"bond_years":1,"tech_focus":"System Design"},
    {"name":"Qualcomm",     "min_cgpa":7.2,"max_backlogs":2,"package_lpa":41.3,"bond_years":1,"tech_focus":"Cloud"},
    {"name":"Intel",        "min_cgpa":7.0,"max_backlogs":0,"package_lpa":41.4,"bond_years":0,"tech_focus":"Python"},
    {"name":"Samsung R&D",  "min_cgpa":6.3,"max_backlogs":2,"package_lpa":7.6, "bond_years":2,"tech_focus":"Java"},
]

HIRING_DATA = [
    {"company":"TCS",          "SDE":88, "Analyst":42,"Officer":70,"Intern":44},
    {"company":"Infosys",      "SDE":30, "Analyst":68,"Officer":62,"Intern":22},
    {"company":"Deloitte",     "SDE":42, "Analyst":85,"Officer":62,"Intern":44},
    {"company":"Accenture",    "SDE":25, "Analyst":22,"Officer":52,"Intern":68},
    {"company":"Amazon",       "SDE":42, "Analyst":36,"Officer":40,"Intern":82},
    {"company":"Flipkart",     "SDE":58, "Analyst":55,"Officer":50,"Intern":32},
    {"company":"Google",       "SDE":30, "Analyst":92,"Officer":46,"Intern":30},
    {"company":"Microsoft",    "SDE":58, "Analyst":58,"Officer":36,"Intern":68},
    {"company":"Wipro",        "SDE":42, "Analyst":92,"Officer":40,"Intern":82},
    {"company":"Cognizant",    "SDE":48, "Analyst":28,"Officer":82,"Intern":34},
    {"company":"Capgemini",    "SDE":68, "Analyst":38,"Officer":50,"Intern":58},
    {"company":"IBM",          "SDE":58, "Analyst":38,"Officer":78,"Intern":68},
    {"company":"Adobe",        "SDE":42, "Analyst":80,"Officer":62,"Intern":48},
    {"company":"Oracle",       "SDE":35, "Analyst":92,"Officer":62,"Intern":95},
    {"company":"SAP",          "SDE":48, "Analyst":42,"Officer":28,"Intern":38},
    {"company":"HCL",          "SDE":48, "Analyst":42,"Officer":38,"Intern":32},
    {"company":"Tech Mahindra","SDE":58, "Analyst":28,"Officer":58,"Intern":30},
    {"company":"Qualcomm",     "SDE":25, "Analyst":38,"Officer":82,"Intern":78},
    {"company":"Intel",        "SDE":48, "Analyst":48,"Officer":42,"Intern":48},
    {"company":"Samsung R&D",  "SDE":42, "Analyst":80,"Officer":42,"Intern":38},
]

SUGGESTED = [
    "What is Amazon's CGPA requirement?",
    "Which companies allow 2 backlogs?",
    "Is roll no 21A91A0501 eligible for TCS and who is the CEO?",
    "What is TCS package and their stock price today?",
    "Which company's package grew most from 2021 to 2024?",
    "ceo of infosys",
]

# ── Session state ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "text": "Hello! I'm PlacementIQ — your SVECW placement intelligence assistant.\n\nAsk me about eligibility, packages, interviews, or multi-tool queries like:\n\"Is roll no 21A91A0501 eligible for TCS and who is the CEO?\"",
        "query_type": None, "sources": [], "conflict_warning": None,
        "multihop_steps": [], "confidence": None,
        "lookback_ratio": None, "hallucination_warning": None,
    }]

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 PlacementIQ")
    st.markdown("<p style='color:#71717a;font-size:12px;font-family:monospace;'>SVECW · RAG-ATHON 24</p>", unsafe_allow_html=True)
    st.divider()

    # Health check
    online = check_health()
    status_color = "#10b981" if online else "#ef4444"
    status_text  = "online" if online else "offline"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <div style="width:8px;height:8px;border-radius:50%;background:{status_color};"></div>
        <span style="font-size:12px;color:{status_color};font-family:monospace;">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)

    if not online:
        st.warning("Backend offline. Run:\n```\nuvicorn main:app --reload\n```")

    st.markdown("<p style='color:#52525b;font-size:11px;font-family:monospace;'>SYSTEM INFO</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#71717a;font-size:12px;'>Model: LLaMA 3.3 70B</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#71717a;font-size:12px;'>Vector DB: ChromaDB</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#71717a;font-size:12px;'>Companies: 19</p>", unsafe_allow_html=True)
    st.divider()

    st.markdown("<p style='color:#52525b;font-size:11px;font-family:monospace;'>TOOLS AVAILABLE</p>", unsafe_allow_html=True)
    st.markdown("🌐 Web Search (live info)")
    st.markdown("🗄️ MySQL DB (student data)")
    st.markdown("🧮 Calculator (arithmetic)")
    st.markdown("📄 PDF RAG (placement dataset)")

# ── Main tabs ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Ask PlacementIQ",
    "🎯 Eligibility Filter",
    "📊 Hiring Charts",
    "🧪 Evaluation Suite",
])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("#### Ask PlacementIQ")
    st.markdown("<p style='color:#71717a;font-size:13px;'>Multi-hop RAG · Conflict detection · Web search · MySQL DB</p>", unsafe_allow_html=True)

    # Suggested queries (only on first load)
    if len(st.session_state.messages) == 1:
        st.markdown("<p style='color:#52525b;font-size:11px;font-family:monospace;margin-bottom:8px;'>TRY ASKING</p>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, s in enumerate(SUGGESTED):
            if cols[i % 3].button(s[:45] + ("…" if len(s) > 45 else ""), key=f"sugg_{i}"):
                st.session_state.pending_query = s
                st.rerun()

    # Render messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-bubble">{msg["text"]}</div>', unsafe_allow_html=True)
        else:
            # Query type badge
            if msg.get("query_type") and msg["query_type"] not in (None, "error"):
                badge_class = f"badge-{msg['query_type']}"
                badge_text  = msg["query_type"].replace("_", " ")
                st.markdown(f'<span class="query-badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)

            st.markdown(f'<div class="bot-bubble">{msg["text"]}</div>', unsafe_allow_html=True)

            # Confidence bar
            if msg.get("confidence") is not None:
                show_confidence(msg["confidence"], msg.get("lookback_ratio", 0))

            # Hallucination warning
            if msg.get("hallucination_warning"):
                st.markdown(f'<div class="hallucination-warning">⚠️ {msg["hallucination_warning"]}</div>', unsafe_allow_html=True)

            # Conflict warning
            if msg.get("conflict_warning"):
                st.warning(f"🔴 Conflict: {msg['conflict_warning']}")

            # Multi-hop steps
            if msg.get("multihop_steps"):
                with st.expander("🔗 Reasoning chain"):
                    for i, step in enumerate(msg["multihop_steps"], 1):
                        st.markdown(f"`{i}.` {step}")

            # Sources
            if msg.get("sources"):
                with st.expander(f"📎 {len(msg['sources'])} source(s)"):
                    for s in msg["sources"]:
                        company = f" · {s['company']}" if s.get('company') and s['company'] != 'ALL' else ''
                        st.markdown(f"`{s.get('section','')}{company}`")

    # Input
    st.markdown("<br>", unsafe_allow_html=True)
    col_input, col_btn = st.columns([6, 1])
    with col_input:
        user_input = st.text_input(
            "Ask a question",
            placeholder="Ask about eligibility, packages, interviews, CEO names…",
            label_visibility="collapsed",
            key="chat_input",
        )
    with col_btn:
        send_clicked = st.button("Send ➤", use_container_width=True, type="primary")

    # Handle pending query from suggested buttons
    if "pending_query" in st.session_state:
        user_input   = st.session_state.pending_query
        send_clicked = True
        del st.session_state.pending_query

    if send_clicked and user_input.strip():
        q = user_input.strip()
        st.session_state.messages.append({
            "role": "user", "text": q,
            "query_type": None, "sources": [], "conflict_warning": None,
            "multihop_steps": [], "confidence": None, "lookback_ratio": None,
            "hallucination_warning": None,
        })

        with st.spinner("Thinking…"):
            data = query_backend(q)

        st.session_state.messages.append({
            "role":                "assistant",
            "text":                data.get("answer", ""),
            "query_type":          data.get("query_type"),
            "sources":             data.get("sources", []),
            "conflict_warning":    data.get("conflict_warning"),
            "multihop_steps":      data.get("multihop_steps", []),
            "confidence":          data.get("confidence"),
            "lookback_ratio":      data.get("lookback_ratio"),
            "hallucination_warning": data.get("hallucination_warning"),
        })
        st.rerun()

    if st.button("🗑️ Clear chat", key="clear"):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — ELIGIBILITY FILTER
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("#### Eligibility Filter")
    st.markdown("<p style='color:#71717a;font-size:13px;'>Real-time filter across all 19 companies</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        cgpa = st.slider("Your CGPA", 5.0, 10.0, 7.5, 0.1)
    with col2:
        backlogs = st.selectbox("Backlogs", [0, 1, 2])
    with col3:
        bond_free = st.checkbox("Bond-free only")

    sort_by = st.radio("Sort by", ["Package (High→Low)", "CGPA cutoff (Low→High)"], horizontal=True)

    # Filter
    eligible   = [c for c in COMPANIES if cgpa >= c["min_cgpa"] and backlogs <= c["max_backlogs"] and (not bond_free or c["bond_years"] == 0)]
    ineligible = [c for c in COMPANIES if c not in eligible]

    if sort_by == "Package (High→Low)":
        eligible.sort(key=lambda c: -c["package_lpa"])
    else:
        eligible.sort(key=lambda c: c["min_cgpa"])

    st.markdown(f"**✅ {len(eligible)} eligible** · ❌ {len(ineligible)} not eligible")
    st.divider()

    if not eligible:
        st.info("No companies match your criteria. Try lowering your CGPA slider.")
    else:
        for i, c in enumerate(eligible):
            pkg_color = "#10b981" if c["package_lpa"] >= 40 else "#0ea5e9" if c["package_lpa"] >= 25 else "#f59e0b" if c["package_lpa"] >= 15 else "#71717a"
            bond_text = "No bond" if c["bond_years"] == 0 else f"{c['bond_years']}yr bond"
            st.markdown(f"""
            <div class="company-card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-size:15px;font-weight:600;color:#f4f4f5;">{i+1}. {c['name']}</span>
                        <span style="font-size:12px;color:#71717a;font-family:monospace;margin-left:10px;">
                            min {c['min_cgpa']} CGPA · {c['max_backlogs']} backlogs · {bond_text} · {c['tech_focus']}
                        </span>
                    </div>
                    <span style="font-size:16px;font-weight:700;color:{pkg_color};font-family:monospace;">
                        ₹{c['package_lpa']} LPA
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    if ineligible:
        st.markdown("<p style='color:#52525b;font-size:12px;margin-top:16px;'>NOT ELIGIBLE</p>", unsafe_allow_html=True)
        st.markdown(" ".join([f"`{c['name']}`" for c in ineligible]))

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — HIRING CHARTS
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### Hiring Distribution by Role")
    st.markdown("<p style='color:#71717a;font-size:13px;'>Section 3 — Hiring data across 20 companies</p>", unsafe_allow_html=True)

    df = pd.DataFrame(HIRING_DATA)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        roles = st.multiselect("Roles", ["SDE", "Analyst", "Officer", "Intern"], default=["SDE", "Analyst", "Officer", "Intern"])
    with col_b:
        chart_type = st.radio("Chart type", ["Grouped", "Stacked"], horizontal=True)
    with col_c:
        top_n = st.selectbox("Show", ["Top 10", "All 20"])

    n      = 10 if top_n == "Top 10" else 20
    df_top = df.head(n)

    colors = {"SDE": "#7c3aed", "Analyst": "#0ea5e9", "Officer": "#10b981", "Intern": "#f59e0b"}
    barmode = "group" if chart_type == "Grouped" else "stack"

    fig = go.Figure()
    for role in roles:
        if role in df_top.columns:
            fig.add_trace(go.Bar(
                name=role, x=df_top["company"], y=df_top[role],
                marker_color=colors.get(role, "#7c3aed"),
            ))

    fig.update_layout(
        barmode=barmode,
        plot_bgcolor="#09090b", paper_bgcolor="#09090b",
        font=dict(color="#a1a1aa", size=11),
        xaxis=dict(tickangle=-40, gridcolor="#27272a"),
        yaxis=dict(gridcolor="#27272a"),
        legend=dict(bgcolor="#18181b", bordercolor="#3f3f46"),
        margin=dict(t=20, b=80),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary cards
    st.markdown("**Top hiring company per role:**")
    cols = st.columns(4)
    for i, role in enumerate(["SDE", "Analyst", "Officer", "Intern"]):
        max_row = df.loc[df[role].idxmax()]
        cols[i].metric(f"{role}", max_row["company"], f"{max_row[role]} hires")

# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — EVALUATION SUITE
# ══════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### Evaluation Suite")
    st.markdown("<p style='color:#71717a;font-size:13px;'>Test PlacementIQ across all query types</p>", unsafe_allow_html=True)

    eval_queries = [
        ("direct_lookup",       "What is TCS's bond period?"),
        ("threshold_filter",    "Which companies require a CGPA above 8.0?"),
        ("eligibility_package", "I have CGPA 7.6 and 1 backlog. What is the highest package I can get?"),
        ("temporal",            "Which company's package grew most from 2021 to 2024?"),
        ("conflict",            "Is Amazon's CGPA cutoff 6.4 or 7.0?"),
        ("web_search",          "Who is the CEO of TCS?"),
        ("student_eligibility", "Is roll no 21A91A0501 eligible for TCS?"),
        ("out_of_corpus",       "What is the salary in the USA?"),
    ]

    if st.button("▶ Run Evaluation (8 queries)", type="primary"):
        results = []
        progress = st.progress(0)
        for i, (qtype, question) in enumerate(eval_queries):
            with st.spinner(f"Running: {question[:50]}…"):
                data = query_backend(question)
                results.append({
                    "Type":       qtype,
                    "Question":   question,
                    "Answer":     data.get("answer", "")[:100] + "…",
                    "Confidence": f"{int(data.get('confidence', 0) * 100)}%",
                    "Routed To":  "Tool Agent" if qtype in ("web_search", "student_eligibility") else "RAG Chain",
                })
            progress.progress((i + 1) / len(eval_queries))

        st.success("✅ Evaluation complete!")
        st.dataframe(pd.DataFrame(results), use_container_width=True)

    else:
        st.info("Click **Run Evaluation** to test all query types automatically.")
        st.markdown("**Query types being tested:**")
        for qtype, question in eval_queries:
            st.markdown(f"- `{qtype}` — {question}")