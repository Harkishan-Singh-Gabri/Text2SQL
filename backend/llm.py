# backend/llm.py

import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 2


def _build_system_prompt() -> str:
    """
    System prompt defines LLM behavior globally.
    Separated from user prompt so it doesn't get buried in conversation history.
    """
    return """You are an expert PostgreSQL query writer.

Your job is to convert natural language questions into valid PostgreSQL SQL queries.

Rules you must follow:
1. Return ONLY the SQL query — no explanation, no markdown, no code blocks
2. Use only the tables and columns provided in the schema
3. Always use table aliases for clarity in joins
4. Use LIMIT 100 by default unless the question specifies a number
5. Never use DROP, DELETE, UPDATE, INSERT or any write operations
6. If the question cannot be answered from the schema, return: UNABLE_TO_ANSWER
"""


def _build_user_prompt(question: str, schema: str) -> str:
    """
    User prompt carries the actual question + schema context.
    Schema is injected here, not in system prompt, because it changes
    per database — system prompt should be static behavior rules only.
    """
    return f"""Database Schema:
{schema}

Question: {question}

Write a PostgreSQL query to answer this question."""


def _build_retry_prompt(question: str, schema: str, bad_sql: str, error: str) -> str:
    """
    Retry prompt includes the previous failed attempt + error message.
    This is the key insight — LLMs self-correct much better when they
    see exactly what went wrong rather than just being asked again.
    """
    return f"""Database Schema:
{schema}

Question: {question}

Your previous SQL query failed:
{bad_sql}

Error:
{error}

Fix the SQL query. Return only the corrected SQL, nothing else."""


def _clean_sql(raw: str) -> str:
    """
    Strip markdown formatting LLMs sometimes add despite instructions.
    Belt-and-suspenders approach — prompt says no markdown, this removes
    it anyway in case the model slips.
    """
    raw = raw.strip()

    # remove ```sql ... ``` or ``` ... ```
    if raw.startswith("```"):
        lines = raw.split("\n")
        # drop first line (```sql) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()

    return raw


def generate_sql(question: str, schema: str) -> dict:
    """
    Main entry point. Returns a result dict with:
    - sql: the generated SQL string
    - success: bool
    - retries: how many retry attempts were made
    - latency_ms: total time including retries
    - error: error message if all retries failed
    """
    start = time.time()
    attempts = []
    last_error = None
    last_sql = None

    for attempt in range(MAX_RETRIES + 1):  # 0, 1, 2
        try:
            # first attempt uses clean prompt
            # subsequent attempts use retry prompt with error context
            if attempt == 0:
                user_prompt = _build_user_prompt(question, schema)
            else:
                user_prompt = _build_retry_prompt(
                    question, schema, last_sql, last_error
                )

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": _build_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=1000
            )

            raw_sql = response.choices[0].message.content.strip()
            clean = _clean_sql(raw_sql)

            if clean == "UNABLE_TO_ANSWER":
                return {
                    "sql": None,
                    "success": False,
                    "retries": attempt,
                    "latency_ms": round((time.time() - start) * 1000),
                    "error": "Question cannot be answered from the available schema"
                }

            attempts.append(clean)
            last_sql = clean

            return {
                "sql": clean,
                "success": True,
                "retries": attempt,
                "latency_ms": round((time.time() - start) * 1000),
                "error": None
            }

        except Exception as e:
            last_error = str(e)
            print(f"[llm] attempt {attempt + 1} failed: {last_error}")
            continue

    # all retries exhausted
    return {
        "sql": None,
        "success": False,
        "retries": MAX_RETRIES,
        "latency_ms": round((time.time() - start) * 1000),
        "error": last_error
    }


def generate_sql_with_retry(question: str, schema: str, execute_fn) -> dict:
    """
    Full retry loop that actually executes SQL and retries on DB errors.
    This is the real self-correction loop — generate → execute → if fails
    → send error back to LLM → regenerate → execute again.

    execute_fn: callable that takes SQL string and returns (rows, error)
    """
    start = time.time()
    last_sql = None
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        # generate SQL
        if attempt == 0:
            user_prompt = _build_user_prompt(question, schema)
        else:
            user_prompt = _build_retry_prompt(
                question, schema, last_sql, last_error
            )

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": _build_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=1000
            )

            raw_sql = response.choices[0].message.content.strip()
            sql = _clean_sql(raw_sql)

            if sql == "UNABLE_TO_ANSWER":
                return {
                    "sql": None,
                    "rows": None,
                    "success": False,
                    "retries": attempt,
                    "latency_ms": round((time.time() - start) * 1000),
                    "error": "Question cannot be answered from the available schema"
                }

            last_sql = sql

            # execute and check for DB errors
            rows, error = execute_fn(sql)

            if error is None:
                # success
                return {
                    "sql": sql,
                    "rows": rows,
                    "success": True,
                    "retries": attempt,
                    "latency_ms": round((time.time() - start) * 1000),
                    "error": None
                }
            else:
                # DB returned an error — feed it back for retry
                last_error = error
                print(f"[llm] attempt {attempt + 1} DB error: {error}")

        except Exception as e:
            last_error = str(e)
            print(f"[llm] attempt {attempt + 1} API error: {last_error}")

    return {
        "sql": last_sql,
        "rows": None,
        "success": False,
        "retries": MAX_RETRIES,
        "latency_ms": round((time.time() - start) * 1000),
        "error": last_error
    }