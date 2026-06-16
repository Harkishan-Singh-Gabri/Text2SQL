# tests/test_llm.py

from backend.schema import SchemaInspector
from backend.llm import generate_sql

inspector = SchemaInspector()
schema, tokens = inspector.format_for_prompt()

# test 1 - simple query
print("=== Test 1: Simple query ===")
result = generate_sql("How many customers are there?", schema)
print(f"SQL: {result['sql']}")
print(f"Success: {result['success']}")
print(f"Retries: {result['retries']}")
print(f"Latency: {result['latency_ms']}ms")

# test 2 - join query
print("\n=== Test 2: Join query ===")
result = generate_sql("Which 5 customers placed the most orders?", schema)
print(f"SQL: {result['sql']}")
print(f"Latency: {result['latency_ms']}ms")

# test 3 - unanswerable query
print("\n=== Test 3: Unanswerable ===")
result = generate_sql("What is the weather in London today?", schema)
print(f"Success: {result['success']}")
print(f"Error: {result['error']}")

inspector.close()