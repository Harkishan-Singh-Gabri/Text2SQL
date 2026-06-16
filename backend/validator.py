import sqlglot
import sqlglot.errors

FORBIDDEN_KEYWORDS={"DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"}

def validate_sql(sql: str) -> tuple[bool, str| None]:
    """
    Validates SQL before execution.
    Returns (is_valid, error_message)
    - (True, None) means safe to execute
    - (False, "reason") means reject and retry
    """
    if not sql or not sql.strip():
        return False, "Empty SQL returned by model"
    sql_upper=sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper:
            return False, f"Forbidden operations detected: {keyword}"
        
    # Syntax Validation via sqlglot
    try:
        statements=sqlglot.parse(sql, dialect="postgres")
        if not statements:
            return False, "No valid SQL statement found"
        
        if len(statements)>1:
            return False, "Multiple statements not allowed"
        
        statement=statements[0]

        if not isinstance(statement, sqlglot.exp.Select):
            return False, f"Only SELECT statements allowed, got: {type(statement).__name__}"
        
        return True, None
    
    except sqlglot.errors.ParseError as e:
        error_msg=str(e).split("\n")[0]
        return False, f"SQL syntax error: {error_msg}"
    
    except Exception as e:
        return False, f"Validation error: {str(e)}"
    

def explain_validation_error(error:str) -> str:
    """
    Makes validation errors more actionable for the retry prompt.
    """
    if "Forbidden operation" in error:
        return f"{error}. Rewrite as a SELECT query only."
    if "syntax error" in error.lower():
        return f"{error}. Check for missing commas, unclosed parentheses, or misspelled keywords."
    if "Multiple statements" in error:
        return "Return only a single SQL SELECT statement, no semicolons separating multiple queries."
    return error