import sqlite3
import os

db_path = r'c:\Users\19692\Desktop\test\lottery-ai-site\lottery_ai.db'
print('检查项目根目录数据库:', db_path)
if not os.path.exists(db_path):
    print('数据库文件不存在')
else:
    print('数据库存在，大小:', os.path.getsize(db_path), 'bytes')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print('表:', [r[0] for r in cur.fetchall()])
    conn.close()
