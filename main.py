from backend.schema import SchemaInspector
from backend.llm import generate_sql_with_retry
from backend.validator import validate_sql, explain_validation_error
from backend.executor import QueryExecutor
from backend.logger import QueryLogger
import time

class Text2SQLPipeline:
    def __init__(self):
        self.schema_inspector=SchemaInspector()
        self.executor=QueryExecutor()
        self.logger=QueryLogger()
        self._schema_cache=None
        self._schema_cache_time=0

        #cache schema for 5 minutes
        self._schema_ttl=300

    def _get_schema(self) ->tuple[str, int]:
        """
        Returns cached schema if fresh, else re-fetches.
        """
        now=time.time()
        if self._schema_cache is None or (now - self._schema_cache_time)>self._schema_ttl:
            self._schema_cache=self.schema_inspector.format_for_prompt()
            self._schema_cache_time=now
            print("[pipeline] schema cache refreshed")
        return self._schema_cache
    
    def query(self, question: str) ->dict:
        """
        Full pipeline: question -> SQL -> execute -> log -> return result.

        Returns:
        {
            success: bool,
            question: str,
            sql: str | None,
            rows: list[dict] | None,
            columns: list[str] | None,
            retries: int,
            llm_latency_ms: int,
            execution_ms: int,
            row_count: int,
            truncated: bool,
            error: str | None,
            log_id: int | None
        }
        """
        print(f"\n[pipeline] question: {question}")

        #step-1 : get schema
        schema_str, token_count=self._get_schema()
        print(f"[pipeline] schema tokens: {token_count}")

        #step-2: generate sql with retry loop
        def execute_fn(sql: str):
            valid, error = validate_sql(sql)
            if not valid:
                return None, explain_validation_error(error)
            rows, err=self.executor.execute_safe(sql)
            return rows, err
        
        llm_result=generate_sql_with_retry(
            question=question,
            schema=schema_str,
            execute_fn=execute_fn
        )

        # get execution metadata if successful
        execution_ms=0
        row_count=0
        columns=[]
        rows=llm_result.get("rows")
        truncated=False

        if llm_result["success"] and llm_result["sql"]:
            result_rows, columns, meta = self.executor.execute(llm_result["sql"])
            execution_ms=meta["execution_ms"]
            row_count=meta["row_count"]
            truncated=meta["truncated"]
            rows=result_rows

        # log everything
        log_id= self.logger.log(
            question=question,
            generated_sql=llm_result.get("sql"),
            success=llm_result["success"],
            retries=llm_result["retries"],
            llm_latency_ms=llm_result["latency_ms"],
            execution_ms=execution_ms,
            row_count=row_count,
            error_message=llm_result.get("error")
        )

        print(f"[pipeline] success={llm_result['success']} | "
              f"retries={llm_result['retries']} | "
              f"llm={llm_result['latency_ms']}ms | "
              f"exec={execution_ms}ms | "
              f"rows={row_count}")

        return {
            "success": llm_result["success"],
            "question": question,
            "sql": llm_result.get("sql"),
            "rows": rows,
            "columns": columns,
            "retries": llm_result["retries"],
            "llm_latency_ms": llm_result["latency_ms"],
            "execution_ms": execution_ms,
            "row_count": row_count,
            "truncated": truncated,
            "error": llm_result.get("error"),
            "log_id": log_id
        }
    
    def get_metrics(self) ->dict:
        return self.logger.get_metrics()
    
    def get_recent_logs(self, limit: int=10) ->list[dict]:
        return self.logger.get_recent_logs(limit=limit)
    
    def get_latency_trend(self, limit: int=50) -> list[dict]:
        return self.logger.get_latency_trend(limit=limit)
    
    def close(self):
        self.schema_inspector.close()
        self.executor.close()
        self.logger.close()