me · MD
# Querify
 
**Ask anything about your data in plain English.**
 
Querify is a natural language analytics engine. Upload any CSV — or query the built-in Northwind dataset — and get answers in plain English, backed by real generated SQL, validated, executed, and explained.
 
**Live Demo:** https://text2sql-vm5xiws5uzetxpjgfjbuut.streamlit.app/
 
---
 
## What it does
 
Type a question like *"Which 5 customers placed the most orders?"* — Querify:
 
1. Reads the live database schema (tables, columns, foreign keys, sample data)
2. Generates a PostgreSQL query using an LLM (Groq / Llama 3.3 70B)
3. Validates the SQL — blocks any write operation, checks syntax via AST parsing
4. Executes it against PostgreSQL
5. If it fails, feeds the exact error back to the model and retries (up to 2 times)
6. Returns results, the generated SQL, and execution metrics
7. Optionally generates 3 AI-written business insights from the result
No write access is ever permitted — the system is read-only by design, enforced at two independent layers.
 
---
 
## Demo
 
| Home — Query Interface | Insights — AI Analysis |
|---|---|
| ![Home screenshot](screenshot\home.png) | ![Insights screenshot](screenshot\insights.png) |
 
**Try it yourself:**
- *"Which 5 customers placed the most orders?"*
- *"Total revenue per product category"*
- *"What is the least price of a product?"* (works on uploaded CSVs too)
---
 
## Architecture
 
```
                    ┌─────────────────────┐
                    │   Streamlit UI       │  Home · Insights
                    │  (query + upload)    │
                    └──────────┬───────────┘
                               │ REST
                    ┌──────────▼───────────┐
                    │     FastAPI           │  /query  /upload
                    │                       │  /metrics /logs
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐   ┌─────────▼─────────┐   ┌────────▼────────┐
│ Schema Inspector │   │   LLM Layer        │   │  SQL Validator   │
│ (introspection)  │   │  (Groq / Llama 3.3)│   │  (sqlglot AST)   │
└───────┬─────────┘   └─────────┬──────────┘   └────────┬────────┘
        │                       │                        │
        │              ┌────────▼────────┐               │
        └─────────────►│  Self-Correction │◄──────────────┘
                       │   Retry Loop      │
                       └────────┬──────────┘
                                │
                       ┌────────▼──────────┐
                       │  Query Executor    │  (PostgreSQL)
                       └────────┬──────────┘
                                │
                       ┌────────▼──────────┐
                       │  Metrics Logger    │  query_logs table
                       └───────────────────┘
```
 
**Why it's built this way:**
 
- **Live schema introspection** instead of a hardcoded schema string — the system adapts automatically to schema changes or a newly uploaded CSV, with zero manual updates.
- **Two-layer SQL validation** — a forbidden-keyword filter and an AST-level parser (`sqlglot`) both run independently. The LLM's instructions are a suggestion; the validator is a hard programmatic boundary that can't be prompt-injected.
- **Self-correcting retry loop** — when generated SQL fails (bad column name, syntax slip), the exact database error is fed back to the model for a second attempt, rather than failing silently.
- **Every query is logged** — question, generated SQL, success/failure, retry count, LLM latency, execution time — enabling real measurement of system performance, not just "it works."
---
 
## Tech Stack
 
| Layer | Technology |
|---|---|
| LLM | Groq API — Llama 3.3 70B Versatile |
| Backend | FastAPI, Python 3.10 |
| Database | PostgreSQL |
| SQL Validation | sqlglot (AST-based parsing) |
| Frontend | Streamlit |
| Charts | Plotly |
| Deployment | Render (API + DB), Streamlit Community Cloud (UI) |
 
---
 
## Key Features
 
- **Natural language → SQL** with schema-aware prompting (tables, foreign keys, sample rows injected dynamically)
- **Self-correcting retry loop** — failed queries are automatically fixed using the real database error message
- **Read-only enforcement** — forbidden keyword filter + AST-level statement-type check, defense in depth
- **CSV upload** — query your own data instead of the bundled Northwind dataset, no code changes required
- **AI-generated insights** — a second LLM call turns raw query results into 3 concise, data-grounded business findings
- **Smart auto-visualization** — line charts for time series, bar charts for categorical comparisons, big stat cards for single-value answers
- **Full observability** — every query logged with latency, retry count, and outcome for later analysis
---
 
## Results (measured during testing)
 
| Metric | Value |
|---|---|
| Queries tested | 50+ |
| Success rate (first attempt + retries) | ~80% |
| Avg LLM latency (Groq) | ~900ms |
| Avg DB execution time (Northwind, ~3K rows) | <2ms |
| Queries requiring retry that succeeded on retry | ~67% |
 
The two dominant failure modes observed: genuinely unanswerable questions (correctly rejected by the model rather than hallucinated), and occasional column/join ambiguity that the retry loop resolved on the second attempt.
 
---
 
## Running Locally
 
**Prerequisites:** Python 3.10, PostgreSQL, a free [Groq API key](https://console.groq.com)
 
```bash
# clone
git clone https://github.com/Harkishan-Singh-Gabri/Text2SQL.git
cd Text2SQL
 
# environment
conda create -n querify python=3.10
conda activate querify
pip install -r requirements.txt
```
 
Create a `.env` file:
 
```bash
GROQ_API_KEY=your_groq_key_here
DATABASE_URL=postgresql://postgres:yourpassword@127.0.0.1:5432/northwind
```
 
Load the database:
 
```bash
psql -U postgres -c "CREATE DATABASE northwind;"
psql -U postgres -d northwind -f northwind.sql
psql -U postgres -d northwind -f db/init.sql
```
 
Run the backend:
 
```bash
uvicorn backend.api:app --reload --port 8000
```
 
Run the frontend (new terminal):
 
```bash
streamlit run frontend/Home.py
```
 
Visit `http://localhost:8501` for the app, `http://localhost:8000/docs` for the API.
 
---
 
## Project Structure
 
```
Text2SQL/
├── backend/
│   ├── api.py          # FastAPI routes
│   ├── schema.py       # Live schema introspection + CSV ingestion
│   ├── llm.py           # Prompt construction + self-correction retry loop
│   ├── validator.py     # SQL safety validation (sqlglot AST + keyword filter)
│   ├── executor.py      # Query execution against PostgreSQL
│   └── logger.py        # Query metrics logging
├── frontend/
│   ├── Home.py           # Main query interface
│   └── pages/
│       └── 1_Insights.py # AI-generated insights page
├── db/
│   └── init.sql          # query_logs table definition
├── tests/                # Module-level test scripts
├── main.py                # Pipeline orchestration
└── requirements.txt
```
 
---
 
 
## Author
 
Built by Harkishan Singh Gabri