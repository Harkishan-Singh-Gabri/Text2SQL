import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
import time

load_dotenv()

MAX_ROWS = 500
QUERY_TIMEOUT_MS = 10000  # 10 seconds


class QueryExecutor:
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")
        self._conn = None

    def _get_connection(self):
        
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.connection_string)
        try:
            # ping the connection 
            self._conn.cursor().execute("SELECT 1")
        except Exception:
            # connection died - reconnect
            self._conn = psycopg2.connect(self.connection_string)
        return self._conn

    def execute(self, sql: str) -> tuple[list[dict] | None, list[str] | None, dict]:
        """
        Executes validated SQL and returns:
        - rows: list of dicts (column_name -> value) or None on error
        - columns: list of column names or None on error
        - meta: execution metadata (timing, row count, truncated flag)
        """
        meta = {
            "execution_ms": 0,
            "row_count": 0,
            "truncated": False,
            "error": None
        }

        try:
            conn = self._get_connection()

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                cur.execute(f"SET statement_timeout = {QUERY_TIMEOUT_MS}")

                start = time.time()
                cur.execute(sql)
                meta["execution_ms"] = round((time.time() - start) * 1000)

                rows = cur.fetchmany(MAX_ROWS + 1) 

                # check if there were more rows than the limit
                if len(rows) > MAX_ROWS:
                    rows = rows[:MAX_ROWS]
                    meta["truncated"] = True

                meta["row_count"] = len(rows)

                # convert to plain dicts
                result_rows = [dict(row) for row in rows]

                # extract column names from first row if available
                columns = list(result_rows[0].keys()) if result_rows else []

                return result_rows, columns, meta

        except psycopg2.errors.QueryCanceled:
            # statement_timeout triggered
            meta["error"] = f"Query exceeded {QUERY_TIMEOUT_MS // 1000}s timeout"
            conn.rollback()  # must rollback after error
            return None, None, meta

        except psycopg2.Error as e:
            # catch all other postgres errors
            # extract clean message 
            meta["error"] = e.pgerror.strip() if e.pgerror else str(e)
            try:
                conn.rollback()
            except Exception:
                pass
            return None, None, meta

        except Exception as e:
            meta["error"] = str(e)
            return None, None, meta

    def execute_safe(self, sql: str) -> tuple[list[dict] | None, str | None]:
        """
        Simplified interface for the LLM retry loop.
        Returns (rows, error) - what generate_sql_with_retry expects.
        """
        rows, columns, meta = self.execute(sql)
        if meta["error"]:
            return None, meta["error"]
        return rows, None

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()