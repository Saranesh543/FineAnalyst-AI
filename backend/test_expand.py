import sqlglot
from sqlglot import exp

class Col:
    def __init__(self, name):
        self.name = name

class Tab:
    def __init__(self, name, cols):
        self.name = name
        self.columns = [Col(c) for c in cols]

class Schema:
    def __init__(self):
        self.dialect = 'sqlite'
        self.tables = [Tab('orders', ['id', 'total', 'customer_id']), Tab('customers', ['id', 'name'])]

def _expand_wildcards(sql: str, schema) -> str:
    try:
        ast = sqlglot.parse_one(sql, dialect=schema.dialect)
    except Exception:
        return sql
    
    schema_tables = {t.name.lower(): [c.name for c in t.columns] for t in schema.tables}

    for select in ast.find_all(exp.Select):
        table_aliases = {}
        for table in select.find_all(exp.Table):
            alias = table.alias.lower() if table.alias else table.name.lower()
            table_aliases[alias] = table.name.lower()
            
        new_exprs = []
        for projection in select.expressions:
            if isinstance(projection, exp.Star):
                for alias, table_name in table_aliases.items():
                    cols = schema_tables.get(table_name, [])
                    for col in cols:
                        # sqlglot needs string or Identifier
                        new_exprs.append(exp.column(col, table=alias))
            elif isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star):
                prefix = projection.args.get("table").name.lower()
                table_name = table_aliases.get(prefix, prefix)
                cols = schema_tables.get(table_name, [])
                if cols:
                    for col in cols:
                        new_exprs.append(exp.column(col, table=prefix))
                else:
                    new_exprs.append(projection)
            else:
                new_exprs.append(projection)
        select.set("expressions", new_exprs)
        
    return ast.sql(dialect=schema.dialect)

schema = Schema()
print(_expand_wildcards("SELECT * FROM orders", schema))
print(_expand_wildcards("SELECT orders.*, c.name FROM orders JOIN customers c ON c.id = orders.customer_id", schema))
