import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Querify — Insights", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 3rem 2rem; max-width: 780px; }

.page-title {
    font-size: 1.4rem; font-weight: 700; color: #0f172a;
    letter-spacing: -0.03em; margin-bottom: 0.2rem;
}
.page-sub { font-size: 0.875rem; color: #94a3b8; margin-bottom: 2rem; }

.insight-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.insight-number {
    font-size: 0.7rem; font-weight: 700; color: #6366f1;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
}
.insight-text {
    font-size: 0.925rem; color: #1e293b; line-height: 1.6;
}
.section-label {
    font-size: 0.7rem; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: #94a3b8; margin: 1.5rem 0 0.5rem 0;
}
.no-data {
    text-align: center; padding: 4rem 2rem;
    color: #cbd5e1; font-size: 0.9rem;
}
hr { border-color: #f1f5f9; }
</style>
""", unsafe_allow_html=True)


def generate_insights(question: str, rows: list, columns: list) -> list[str]:
    """Call Groq to generate business insights from query results."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # limit data sent to LLM — top 30 rows is enough for insight generation
    data_sample = rows[:30]

    prompt = f"""You are a senior business analyst. A user asked this question about their database:
"{question}"

The query returned this data:
{json.dumps(data_sample, indent=2, default=str)}

Generate exactly 3 concise, specific business insights from this data.

Rules:
- Reference specific numbers and values from the data
- Each insight should be 1-2 sentences maximum
- No bullet points, no numbering — just the insight text
- Do not speculate beyond what the data shows
- Separate each insight with the delimiter: ---INSIGHT---

Return only the 3 insights separated by ---INSIGHT--- and nothing else."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400
    )

    raw = response.choices[0].message.content.strip()
    insights = [i.strip() for i in raw.split("---INSIGHT---") if i.strip()]
    return insights[:3]


def smart_chart(df: pd.DataFrame):
    cols = df.columns.tolist()
    if len(cols) < 2:
        return
    x_col, y_col = cols[0], cols[1]

    raw_df = df.copy()
    for col in raw_df.columns:
        raw_df[col] = pd.to_numeric(
            raw_df[col].astype(str).str.replace('[$,]', '', regex=True),
            errors='ignore'
        )

    if not pd.api.types.is_numeric_dtype(raw_df[y_col]):
        return

    if any(k in x_col.lower() for k in ["date", "month", "year", "time"]):
        fig = px.area(raw_df, x=x_col, y=y_col, color_discrete_sequence=["#6366f1"])
    elif len(raw_df) > 6 or raw_df[x_col].astype(str).str.len().max() > 12:
        fig = px.bar(raw_df, x=y_col, y=x_col, orientation='h',
                     color_discrete_sequence=["#6366f1"])
    else:
        fig = px.bar(raw_df, x=x_col, y=y_col, color_discrete_sequence=["#6366f1"])

    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter", size=12, color="#475569"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#f8fafc", title=""),
        margin=dict(t=10, b=10, l=0, r=0),
        height=320
    )
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)


# --- page ---
st.markdown("""
<div>
    <p class="page-title">Insights</p>
    <p class="page-sub">AI-generated analysis of your last query result</p>
</div>
""", unsafe_allow_html=True)

result = st.session_state.get("last_result")

if not result or not result.get("success") or not result.get("rows"):
    st.markdown("""
    <div class="no-data">
        Run a query on the Home page first — insights will appear here automatically.
    </div>
    """, unsafe_allow_html=True)

else:
    rows = result["rows"]
    columns = result.get("columns", [])
    question = result.get("question", "")
    df = pd.DataFrame(rows)

    # question context
    st.markdown(f"""
    <p style="font-size:0.8rem;color:#94a3b8;margin-bottom:1.5rem">
        Analysing results for: <b style="color:#475569">{question}</b>
        &nbsp;·&nbsp; {len(rows)} rows
    </p>
    """, unsafe_allow_html=True)

    # generate insights
    with st.spinner("Generating insights..."):
        try:
            insights = generate_insights(question, rows, columns)
        except Exception as e:
            insights = []
            st.error(f"Could not generate insights: {e}")

    if insights:
        st.markdown('<p class="section-label">Key Findings</p>', unsafe_allow_html=True)
        labels = ["Finding 01", "Finding 02", "Finding 03"]
        for i, insight in enumerate(insights):
            label = labels[i] if i < len(labels) else f"Finding 0{i+1}"
            st.markdown(f"""
            <div class="insight-card">
                <div class="insight-number">{label}</div>
                <div class="insight-text">{insight}</div>
            </div>
            """, unsafe_allow_html=True)

    # chart
    if df.shape[1] >= 2:
        st.markdown('<p class="section-label">Visualization</p>', unsafe_allow_html=True)
        smart_chart(df)

    # data table
    st.markdown('<p class="section-label">Data</p>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 height=min(350, 60 + len(df) * 35))