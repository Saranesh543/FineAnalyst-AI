import asyncio
import logging
from app.services.schema_service import schema_service
from app.services.sql_generator_service import sql_generator_service
from app.services.sql_executor_service import sql_executor_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def run_query(q):
    print(f"\n=====================================")
    print(f"QUERY: {q}")
    print(f"=====================================")
    try:
        schema = await schema_service.get_schema()
        sql_res = await sql_generator_service.generate(q, schema)
        print("GENERATED SQL:", sql_res.sql)
        
        exec_res = await sql_executor_service.execute_sql(sql_res.sql)
        print("SUCCESS! Rows:", exec_res.row_count)
    except Exception as e:
        print("EXCEPTION:", type(e), str(e))
        import traceback
        traceback.print_exc()

async def main():
    queries = [
        "Top 5 companies by revenue",
        "Top 5 countries by net revenue",
        "Average order value by country"
    ]
    for q in queries:
        await run_query(q)

if __name__ == "__main__":
    asyncio.run(main())
