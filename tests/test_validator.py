from backend.validator import validate_sql, explain_validation_error

# test 1 - valid SELECT
sql = "SELECT COUNT(*) FROM customers"
valid, error = validate_sql(sql)
print(f"Test 1 - Valid SELECT: {valid} | {error}")

# test 2 - syntax error
sql = "SELCT COUNT(*) FROM customers"
valid, error = validate_sql(sql)
print(f"Test 2 - Bad syntax: {valid} | {error}")

# test 3 - forbidden operation
sql = "DROP TABLE customers"
valid, error = validate_sql(sql)
print(f"Test 3 - DROP: {valid} | {error}")

# test 4 - multiple statements
sql = "SELECT * FROM customers; DROP TABLE orders"
valid, error = validate_sql(sql)
print(f"Test 4 - Multiple statements: {valid} | {error}")

# test 5 - complex valid join
sql = """
    SELECT c.company_name, COUNT(o.order_id) AS order_count
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.company_name
    ORDER BY order_count DESC
    LIMIT 5
"""
valid, error = validate_sql(sql)
print(f"Test 5 - Complex JOIN: {valid} | {error}")

# test 6 - error explanation
print(f"\nExplained error: {explain_validation_error('SQL syntax error: line 1')}")