from main import Text2SQLPipeline

pipeline = Text2SQLPipeline()

questions = [
    "How many customers are there?",
    "Which 5 customers placed the most orders?",
    "What is the total revenue per product category?",
    "Which employee handled the most orders?",
    "What is the weather in London today?", 
]

for question in questions:
    print(f"\n{'='*60}")
    print(f"Q: {question}")
    result = pipeline.query(question)
    print(f"Success: {result['success']}")
    print(f"SQL: {result['sql']}")
    print(f"Rows: {result['row_count']} | Retries: {result['retries']} | LLM: {result['llm_latency_ms']}ms | Exec: {result['execution_ms']}ms")
    if result['rows']:
        for row in result['rows'][:3]:  
            print(f"  {row}")
    if result['error']:
        print(f"Error: {result['error']}")

print(f"\n{'='*60}")
print("METRICS:")
metrics = pipeline.get_metrics()
for k, v in metrics.items():
    print(f"  {k}: {v}")

pipeline.close()