CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    generated_sql TEXT,
    success BOOLEAN NOT NULL,
    retries INTEGER DEFAULT 0,
    llm_latency_ms INTEGER,
    execution_ms INTEGER,
    row_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);