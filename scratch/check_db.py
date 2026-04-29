import sqlite3

conn = sqlite3.connect('thesis.db')
c = conn.cursor()
c.execute("""
    SELECT id, title, abstract, keywords, methods, results, discussion, introduction
    FROM papers 
    WHERE deleted_at IS NULL AND status='Approved' 
    LIMIT 5
""")
rows = c.fetchall()
for r in rows:
    print(f"ID:{r[0]} | Title:{r[1][:60]}")
    print(f"  Kw:{(r[3] or '')[:50]}")
    print(f"  Has Methods:{bool(r[4])} | Has Results:{bool(r[5])} | Has Disc:{bool(r[6])} | Has Intro:{bool(r[7])}")
    print()

c.execute("SELECT COUNT(*) FROM papers WHERE deleted_at IS NULL AND status='Approved'")
print(f"TOTAL APPROVED: {c.fetchone()[0]}")
conn.close()
