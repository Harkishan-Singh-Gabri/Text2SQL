import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass, field
from dotenv import load_dotenv
import os
import time

load_dotenv()

@dataclass
class Column:
    name: str
    data_type: str
    is_nullable:bool

@dataclass
class ForeignKey:
    column: str
    references_table: str
    references_column: str

@dataclass
class Table:
    name: str
    columns: list[Column]=field(default_factory=list)
    foreign_keys: list[ForeignKey]=field(default_factory=list)
    sample_rows: list[Column]=field(default_factory=list)

class SchemaInspector:
    def __init__(self):
        self.connection_string=os.getenv("DATABASE_URL")
        self._conn=None

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn=psycopg2.connect(self.connection_string)
        return self._conn
    
    def get_tables(self, exclude: list[str]=None) ->list[str]:
        exclude=exclude or []

        default_exclude=[
            "us_states",
            "customer_demographics",
            "customer_customer_demo",
            "query_logs"
        ]

        exclude=list(set(exclude+default_exclude))

        conn=self._get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                    AND table_type='BASE TABLE'
                    AND table_name != ALL(%s)
                ORDER BY table_name
            """, (exclude,))
            return [row[0] for row in cur.fetchall()]
        

    def get_columns(self, table_name: str) -> list[Column]:
        conn=self._get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema='public'
                        AND table_name=%s
                    ORDER BY ordinal_position
            """, (table_name,))
            return [
                Column(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    is_nullable=row["is_nullable"]=="YES"
                )
                for row in cur.fetchall()
            ]
        
    def get_foreign_keys(self, table_name: str) -> list[ForeignKey]:
        conn=self._get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS references_table,
                    ccu.column_name AS references_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name=kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name=tc.constraint_name
                WHERE tc.constraint_type='FOREIGN KEY'
                    AND tc.table_name=%s
            """, (table_name,))
            return [
                ForeignKey(
                    column=row["column_name"],
                    references_table=row["references_table"],
                    references_column=row["references_column"]
                )
                for row in cur.fetchall()
            ]
        
    def get_sample_rows(self, table_name: str, limit: int=2) -> list[dict]:
        conn=self._get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
            rows=[]
            for row in cur.fetchall():
                clean={}
                for k,v in row.items():
                    if isinstance(v, memoryview):
                        continue
                    clean[k]=str(v)[:50] if v is not None else "null"
                rows.append(clean)
            return rows

    def get_schema(self, exclude: list[str]=None) -> list[Table]:
        tables=self.get_tables(exclude=exclude)
        result=[]
        for table_name in tables:
            result.append(Table(
                name=table_name,
                columns=self.get_columns(table_name),
                foreign_keys=self.get_foreign_keys(table_name),
                sample_rows=self.get_sample_rows(table_name)
            ))
        return result
    
    def _simplify_type(self, data_type:str) -> str:
       mapping = {
        "character varying": "varchar",
        "timestamp without time zone": "timestamp",
        "timestamp with time zone": "timestamptz",
        "double precision": "float",
        "integer": "int",
        "smallint": "int",
        }
       return mapping.get(data_type, data_type) 
    
    def format_for_prompt(self, exclude: list[str]=None) -> tuple[str, int]:
        """
        Returns formatted schema string + token estimate.
        Tuple so caller always knows how much context this is consuming.
        """
        start=time.time()
        schema=self.get_schema(exclude=exclude)
        fetch_ms=round((time.time()-start)*1000)

        lines=[]
        for table in schema:
            lines.append(f"Table: {table.name}")
            for col in table.columns:
                if col.data_type=="bytea":
                    continue
                nullable = ", nullable" if col.is_nullable else ""
                simplified = self._simplify_type(col.data_type)
                lines.append(f"  - {col.name} ({simplified}{nullable})")

            if table.foreign_keys:
                lines.append("  Relationships:")
                for fk in table.foreign_keys:
                    lines.append(f"   {fk.column} -> {fk.references_table}.{fk.references_column}")
            
            if table.sample_rows:
                lines.append("  Sample data:")
                for row in table.sample_rows:
                    clean={
                        k: (str(v)[:50] if v is not None else "null") for k,v in row.items()
                    }
                    lines.append(f"   {clean}")
            
            lines.append("")
        
        schema_str="\n".join(lines)

        #rough token estimate
        token_estimate=len(schema_str)//4
        print(f"Schema fetched in {fetch_ms}ms | "
              f"Tables: {len(schema)} | "
              f"~{token_estimate} tokens")
        return schema_str, token_estimate
    
    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
              
