import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.connect() as conn:
        await conn.execute(text('ATTACH DATABASE "./test.db" AS user_db'))
        await conn.execute(text('CREATE TABLE IF NOT EXISTS user_db.t1 (id INT)'))
        await conn.execute(text('INSERT INTO user_db.t1 VALUES (1)'))
        
        user_tables_result = await conn.execute(text("SELECT name FROM user_db.sqlite_master WHERE type='table'"))
        for (t_name,) in user_tables_result.all():
            await conn.execute(text(f'CREATE TEMP VIEW IF NOT EXISTS {t_name} AS SELECT * FROM user_db.{t_name}'))
            
        res = await conn.execute(text('SELECT * FROM t1'))
        print(res.all())

asyncio.run(test())
