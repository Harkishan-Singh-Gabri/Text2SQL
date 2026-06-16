from backend.executor import QueryExecutor

executor = QueryExecutor()

# test 1 - simple query
print("Test 1: Simple count")
rows, columns, meta = executor.execute("SELECT COUNT(*) as total FROM customers")
print(f"Rows: {rows}")
print(f"Columns: {columns}")
print(f"Meta: {meta}")

# test 2 - join query
print("\nTest 2: Join query")
rows, columns, meta = executor.execute("""
    SELECT c.company_name, COUNT(o.order_id) AS order_count
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.company_name
    ORDER BY order_count DESC
    LIMIT 5
""")
print(f"Columns: {columns}")
for row in rows:
    print(f"  {row}")
print(f"Execution time: {meta['execution_ms']}ms")

# test 3 - bad SQL reaches DB
print("\nTest 3: Bad SQL")
rows, columns, meta = executor.execute("SELECT * FROM nonexistent_table")
print(f"Rows: {rows}")
print(f"Error: {meta['error']}")

# test 4 - execute_safe interface (for retry loop)
print("\nTest 4: execute_safe interface")
rows, error = executor.execute_safe("SELECT COUNT(*) as total FROM orders")
print(f"Rows: {rows}")
print(f"Error: {error}")

executor.close()