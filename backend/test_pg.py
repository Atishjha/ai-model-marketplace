import asyncio, asyncpg
async def main():
    conn = await asyncpg.connect(user="postgres", password="postgres", database="marketplace", host="localhost", port=5433)
    print(await conn.fetchval("SELECT 1"))
    await conn.close()
asyncio.run(main())
