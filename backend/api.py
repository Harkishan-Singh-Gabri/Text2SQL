# backend/api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import Text2SQLPipeline
from fastapi import UploadFile, File
import io
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Text2SQL API",
    description="Natural language to SQL query engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = Text2SQLPipeline()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    success: bool
    question: str
    sql: str | None
    rows: list[dict] | None
    columns: list[str] | None
    retries: int
    llm_latency_ms: int
    execution_ms: int
    row_count: int
    truncated: bool
    error: str | None
    log_id: int | None

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    contents = await file.read()
    table_name, row_count, columns = pipeline.schema_inspector.load_csv(
        io.BytesIO(contents)
    )
    pipeline._schema_cache = None 
    return {
        "table_name": table_name,
        "row_count": row_count,
        "columns": columns
    }

@app.get("/health")
def health():
    """Quick check that the API is running."""
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Main endpoint. Takes a natural language question,
    returns SQL + results + execution metadata.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = pipeline.query(request.question)
    return result


@app.get("/metrics")
def metrics():
    """
    Aggregated metrics for the dashboard.
    Total queries, success rate, avg latency, retry count.
    """
    return pipeline.get_metrics()


@app.get("/logs")
def logs(limit: int = 10):
    """
    Recent query log for the dashboard history panel.
    limit: number of recent entries to return (default 10, max 50)
    """
    if limit > 50:
        limit = 50
    return pipeline.get_recent_logs(limit=limit)


@app.get("/latency")
def latency(limit: int = 50):
    """
    Latency trend data for the line chart.
    Returns last N queries with timestamps and latency values.
    """
    return pipeline.get_latency_trend(limit=limit)