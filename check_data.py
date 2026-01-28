import sqlite3

def check_db():
    conn = sqlite3.connect('thesis.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, abstract FROM papers")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Title: {row[1]}")
        print(f"Author: {row[2]}")
        print(f"Abstract Snippet: {row[3][:300]}...")
        print("-" * 50)
    conn.close()

if __name__ == "__main__":
    check_db()
