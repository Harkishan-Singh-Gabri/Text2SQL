import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Querify",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 4rem 2rem 2rem 2rem;
    max-width: 780px;
}

/* hero */
.hero {
    text-align: center;
    padding: 3rem 0 2.5rem 0;
}
.hero-logo {
    font-size: 2.4rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.04em;
    margin-bottom: 0.4rem;
}
.hero-logo span { color: #6366f1; }
.hero-sub {
    font-size: 1rem;
    color: #94a3b8;
    font-weight: 400;
    margin: 0;
}

/* search box */
.stTextInput > div > div > input {
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.85rem 1.1rem;
    font-size: 1rem;
    color: #0f172a;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}
.stTextInput > div > div > input::placeholder { color: #cbd5e1; }

/* run button */
div[data-testid="stHorizontalBlock"] .stButton > button {
    border-radius: 10px;
    font-size: 0.9rem;
    font-weight: 500;
    height: 2.6rem;
    border: 1.5px solid #e2e8f0;
    background: white;
    color: #475569;
    transition: all 0.15s;
}
div[data-testid="stHorizontalBlock"] .stButton > button:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
}

/* primary button */
.stButton > button[kind="primary"] {
    background: #6366f1 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.6rem 1.5rem !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.25) !important;
    transition: all 0.15s !important;
}
.stButton > button[kind="primary"]:hover {
    background: #4f46e5 !important;
    box-shadow: 0 4px 12px rgba(99,102,241,0.35) !important;
}

/* example chips */
.chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: center;
    margin: 1.2rem 0 2rem 0;
}
.chip {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 0.35rem 0.85rem;
    font-size: 0.8rem;
    color: #475569;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
}
.chip:hover {
    background: #ede9fe;
    border-color: #a5b4fc;
    color: #4f46e5;
}

/* result card */
.result-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

/* status pills */
.pill-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}
.pill {
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 500;
}
.pill-success { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.pill-failed  { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.pill-neutral { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
.pill-warn    { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }

/* sql block label */
.section-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 1.25rem 0 0.4rem 0;
}

/* stat card for single value */
.stat-card {
    text-align: center;
    padding: 2rem;
    background: #fafafa;
    border-radius: 12px;
    border: 1px solid #f1f5f9;
    margin: 1rem 0;
}
.stat-value {
    font-size: 3rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.03em;
}
.stat-label {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-top: 0.3rem;
}

/* history sidebar */
.history-item {
    padding: 0.6rem 0.75rem;
    border-radius: 8px;
    font-size: 0.8rem;
    color: #475569;
    cursor: pointer;
    border: 1px solid transparent;
    margin-bottom: 0.3rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.history-item:hover {
    background: #f8fafc;
    border-color: #e2e8f0;
}

hr { border-color: #f1f5f9; margin: 1.25rem 0; }

/* hide index col */
.dataframe { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# --- helpers ---
def query_api(question: str) -> dict:
    try:
        r = requests.post(f"{API_BASE}/query", json={"question": question}, timeout=60)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e), "rows": None, "sql": None,
                "retries": 0, "llm_latency_ms": 0, "execution_ms": 0, "row_count": 0,
                "truncated": False, "log_id": None, "columns": []}


def fmt(value):
    """Smart number formatter for display."""
    if isinstance(value, float):
        if value > 1000:
            return f"${value:,.2f}"
        return f"{value:.2f}"
    return value


def format_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply smart formatting to dataframe columns."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            if any(k in col.lower() for k in ["revenue", "price", "total", "amount", "freight", "cost"]):
                df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
            else:
                df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
        elif pd.api.types.is_integer_dtype(df[col]):
            df[col] = df[col].apply(lambda x: f"{x:,}" if pd.notna(x) else "")
    return df


def smart_chart(df: pd.DataFrame):
    """Render the most appropriate chart for the data shape."""
    if df.shape[1] < 2:
        return

    cols = df.columns.tolist()
    x_col = cols[0]
    y_col = cols[1]

    # detect numeric column for charting
    raw_df = df.copy()
    for col in raw_df.columns:
        raw_df[col] = pd.to_numeric(
            raw_df[col].astype(str).str.replace('[$,]', '', regex=True),
            errors='ignore'
        )

    if not pd.api.types.is_numeric_dtype(raw_df[y_col]):
        return

    # time series — line chart
    if any(k in x_col.lower() for k in ["date", "month", "year", "time", "period"]):
        fig = px.line(raw_df, x=x_col, y=y_col,
                      markers=True, color_discrete_sequence=["#6366f1"])
        chart_type = "line"
    # many categories or long labels — horizontal bar
    elif len(raw_df) > 6 or raw_df[x_col].astype(str).str.len().max() > 12:
        fig = px.bar(raw_df, x=y_col, y=x_col,
                     orientation='h', color_discrete_sequence=["#6366f1"])
        chart_type = "hbar"
    # few categories — vertical bar
    else:
        fig = px.bar(raw_df, x=x_col, y=y_col,
                     color_discrete_sequence=["#6366f1"])
        chart_type = "bar"

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter", size=12, color="#475569"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#f8fafc", title=""),
        margin=dict(t=10, b=10, l=0, r=0),
        height=300
    )
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)


# --- session state ---
for key, default in [
    ("question_input", ""),
    ("last_result", None),
    ("query_history", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# --- sidebar — query history ---
with st.sidebar:
    st.markdown("""
    <p style="font-size:0.75rem;font-weight:600;color:#94a3b8;
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem">
    Query History</p>
    """, unsafe_allow_html=True)

    if not st.session_state.query_history:
        st.markdown('<p style="font-size:0.8rem;color:#cbd5e1">No queries yet</p>',
                    unsafe_allow_html=True)
    else:
        for i, item in enumerate(reversed(st.session_state.query_history[-15:])):
            label = item["question"][:42] + ("..." if len(item["question"]) > 42 else "")
            icon = "+" if item["success"] else "-"
            if st.button(f"{icon}  {label}", key=f"hist_{i}", use_container_width=True):
                st.session_state.question_input = item["question"]
                st.session_state.last_result = item["result"]
                st.rerun()

    if st.session_state.query_history:
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("Clear history", use_container_width=True):
            st.session_state.query_history = []
            st.session_state.last_result = None
            st.session_state.question_input = ""
            st.rerun()


# --- hero ---
st.markdown("""
<div class="hero">
    <div class="hero-logo">Quer<span>ify</span></div>
    <p class="hero-sub">Ask anything about your data in plain English</p>
</div>
""", unsafe_allow_html=True)


# --- example chips (rendered as buttons, styled as chips) ---
examples = [
    "Which 5 customers placed the most orders?",
    "Total revenue per product category",
    "Top 10 products by units sold",
    "Average order value by country",
    "Orders shipped to Germany in 1997",
    "Which employee handled the most orders?",
]

cols = st.columns(3)
for i, example in enumerate(examples):
    if cols[i % 3].button(example, key=f"chip_{i}", use_container_width=True):
        st.session_state.question_input = example
        st.rerun()

st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

# --- search input ---
question = st.text_input(
    label="question",
    value=st.session_state.question_input,
    placeholder="Ask anything — e.g. What are the top selling products this year?",
    label_visibility="collapsed",
    key="question_field"
)
st.session_state.question_input = question

run_col, clear_col = st.columns([5, 1])
run = run_col.button("Run", type="primary", use_container_width=True)
clear = clear_col.button("Clear", use_container_width=True)

if clear:
    st.session_state.question_input = ""
    st.session_state.last_result = None
    st.rerun()

# --- run query ---
if run and question.strip():
    status_placeholder = st.empty()

    status_placeholder.markdown("""
    <div style="text-align:center;padding:1rem;color:#94a3b8;font-size:0.85rem">
        Fetching schema...
    </div>""", unsafe_allow_html=True)

    import time
    time.sleep(0.3)

    status_placeholder.markdown("""
    <div style="text-align:center;padding:1rem;color:#94a3b8;font-size:0.85rem">
        Generating SQL...
    </div>""", unsafe_allow_html=True)

    result = query_api(question)

    status_placeholder.markdown("""
    <div style="text-align:center;padding:1rem;color:#94a3b8;font-size:0.85rem">
        Executing query...
    </div>""", unsafe_allow_html=True)

    time.sleep(0.2)
    status_placeholder.empty()

    st.session_state.last_result = result
    st.session_state.query_history.append({
        "question": question,
        "success": result.get("success", False),
        "result": result
    })
    st.rerun()


# --- results ---
result = st.session_state.last_result

if result:
    with st.container():
        st.markdown('<div class="result-card">', unsafe_allow_html=True)

        # status pills
        status_cls = "pill-success" if result.get("success") else "pill-failed"
        status_txt = "Success" if result.get("success") else "Failed"
        retries = result.get("retries", 0)
        retry_html = f'<span class="pill pill-warn">{retries} retr{"y" if retries==1 else "ies"}</span>' if retries > 0 else ""

        st.markdown(f"""
        <div class="pill-row">
            <span class="pill {status_cls}">{status_txt}</span>
            <span class="pill pill-neutral">LLM {result.get('llm_latency_ms',0)}ms</span>
            <span class="pill pill-neutral">DB {result.get('execution_ms',0)}ms</span>
            <span class="pill pill-neutral">{result.get('row_count',0)} rows</span>
            {retry_html}
        </div>
        """, unsafe_allow_html=True)

        # error state
        if not result.get("success"):
            st.markdown(f"""
            <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;
            padding:0.75rem 1rem;color:#991b1b;font-size:0.875rem">
                {result.get('error', 'Unknown error')}
            </div>
            """, unsafe_allow_html=True)

        else:
            rows = result.get("rows", [])
            df_raw = pd.DataFrame(rows) if rows else pd.DataFrame()

            # single value — big stat card
            if df_raw.shape == (1, 1):
                val = list(rows[0].values())[0]
                col_name = list(rows[0].keys())[0]
                display_val = f"{int(val):,}" if isinstance(val, (int, float)) and val == int(val) else fmt(val)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{display_val}</div>
                    <div class="stat-label">{col_name.replace('_',' ').title()}</div>
                </div>
                """, unsafe_allow_html=True)

            else:
                # generated SQL
                st.markdown('<p class="section-label">Generated SQL</p>', unsafe_allow_html=True)
                st.code(result.get("sql", ""), language="sql")

                if result.get("truncated"):
                    st.warning("Results limited to 500 rows.")

                # formatted results table
                st.markdown('<p class="section-label">Results</p>', unsafe_allow_html=True)
                df_display = format_df(df_raw)
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    height=min(380, 60 + len(df_display) * 35)
                )

                # smart chart
                if df_raw.shape[1] == 2:
                    st.markdown('<p class="section-label">Chart</p>', unsafe_allow_html=True)
                    smart_chart(df_raw)

            # insights link
            if rows and len(rows) > 0:
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("""
                <p style="font-size:0.8rem;color:#94a3b8;text-align:center">
                    Go to <b>Insights</b> in the sidebar for AI-generated analysis of this result
                </p>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)