from backend.schema import SchemaInspector
inspector=SchemaInspector()

#test-1 - tables
tables=inspector.get_tables()
print("Tables:", tables)
print("Count:",len(tables))

#test-2 - columns on orders
print("\n Order columns")
for col in inspector.get_columns("orders"):
    print(f"  {col.name} | {col.data_type} | nullable={col.is_nullable}")

#test-3 - foreign keys
print("\n Order_FKs")
for fk in inspector.get_foreign_keys("order_details"):
    print(f"   {fk.column} -> {fk.references_table} | {fk.references_column}")
    
#test-4 - full prompt format
print("\n Formatted schema (first 800 chars):")
schema_str, tokens= inspector.format_for_prompt()
print(schema_str[:800])
print(f"\n Total token estimate: {tokens}")

inspector.close()