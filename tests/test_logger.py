from backend.logger import QueryLogger

logger = QueryLogger()

# test 1 - log a successful query
print("Test 1: Log successful query")
log_id = logger.log(
    question="How many customers are there?",
    generated_sql="SELECT COUNT(*) FROM customers",
    success=True,
    retries=0,
    llm_latency_ms=947,
    execution_ms=2,
    row_count=1
)
print(f"Log ID: {log_id}")

# test 2 - log a failed query
print("\nTest 2: Log failed query")
log_id = logger.log(
    question="What is the weather today?",
    generated_sql=None,
    success=False,
    retries=2,
    llm_latency_ms=1800,
    execution_ms=0,
    row_count=0,
    error_message="Question cannot be answered from the available schema"
)
print(f"Log ID: {log_id}")

# test 3 - log a retry success
print("\nTest 3: Log retry success")
log_id = logger.log(
    question="Top 5 products by revenue",
    generated_sql="SELECT p.product_name, SUM(od.unit_price * od.quantity) AS revenue FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY revenue DESC LIMIT 5",
    success=True,
    retries=1,
    llm_latency_ms=2100,
    execution_ms=5,
    row_count=5
)
print(f"Log ID: {log_id}")

# test 4 - get metrics
print("\nTest 4: Metrics")
metrics = logger.get_metrics()
for k, v in metrics.items():
    print(f"  {k}: {v}")

# test 5 - recent logs
print("\nTest 5: Recent logs")
logs = logger.get_recent_logs(limit=3)
for log in logs:
    print(f"  [{log['id']}] success={log['success']} | retries={log['retries']} | q={log['question'][:40]}")

logger.close()