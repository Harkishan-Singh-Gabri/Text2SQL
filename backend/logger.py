import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime, timezone
import os

load_dotenv()

class QueryLogger:
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")
        self._conn = None

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.connection_string)
        try:
            self._conn.cursor().execute("SELECT 1")
        except Exception:
            self._conn = psycopg2.connect(self.connection_string)
        return self._conn

    def log(
        self,
        question: str,
        generated_sql: str | None,
        success: bool,
        retries: int = 0,
        llm_latency_ms: int = 0,
        execution_ms: int = 0,
        row_count: int = 0,
        error_message: str | None = None
    ) -> int | None:
        """
        Logs a query attempt to query_logs table.
        Returns the log entry id on success, None on failure.
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO query_logs (
                        question,
                        generated_sql,
                        success,
                        retries,
                        llm_latency_ms,
                        execution_ms,
                        row_count,
                        error_message,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    question,
                    generated_sql,
                    success,
                    retries,
                    llm_latency_ms,
                    execution_ms,
                    row_count,
                    error_message,
                    datetime.now(timezone.utc)
                ))
                log_id = cur.fetchone()[0]
                conn.commit()
                return log_id

        except Exception as e:
            print(f"[logger] failed to log query: {e}")
            return None

    def get_metrics(self) -> dict:
        """
        Aggregate metrics for the Streamlit dashboard.
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*)                                    AS total_queries,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)   AS successful,
                        SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) AS failed,
                        ROUND(AVG(llm_latency_ms))                 AS avg_llm_latency_ms,
                        ROUND(AVG(execution_ms))                   AS avg_execution_ms,
                        SUM(retries)                               AS total_retries,
                        ROUND(
                            100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END)
                            / NULLIF(COUNT(*), 0), 1
                        )                                          AS success_rate_pct
                    FROM query_logs
                """)
                row = cur.fetchone()
                return dict(row) if row else {}

        except Exception as e:
            print(f"[logger] failed to get metrics: {e}")
            return {}

    def get_recent_logs(self, limit: int = 10) -> list[dict]:
        """
        Fetch recent query attempts for the dashboard log panel.
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id,
                        question,
                        generated_sql,
                        success,
                        retries,
                        llm_latency_ms,
                        execution_ms,
                        row_count,
                        error_message,
                        created_at
                    FROM query_logs
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            print(f"[logger] failed to get recent logs: {e}")
            return []

    def get_latency_trend(self, limit: int = 50) -> list[dict]:
        """
        Return last N queries with timestamps and latency.
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        created_at,
                        llm_latency_ms,
                        execution_ms,
                        success
                    FROM query_logs
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                rows = [dict(row) for row in cur.fetchall()]
                
                return rows[::-1]

        except Exception as e:
            print(f"[logger] failed to get latency trend: {e}")
            return []

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()