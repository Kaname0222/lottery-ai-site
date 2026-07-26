import sqlite3

DB_PATH = r'C:\Users\19692\Desktop\test\lottery-ai-site\backend\lottery_ai.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables:', [r[0] for r in cur.fetchall()])
for table in ['matches', 'predictions', 'llm_providers', 'provider_scores', 'scrape_logs']:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(f'{table}:', cur.fetchone()[0])
conn.close()
