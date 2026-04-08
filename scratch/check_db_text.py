import sqlite3
import os

db_path = "thesis.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = "SELECT title, results FROM papers WHERE results LIKE '%FUNCTIONALITY%' OR results LIKE '%MEAN%' LIMIT 2;"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    for i, row in enumerate(rows):
        print(f"Paper {i+1}: {row[0]}")
        # Print a snippet of results around the keywords
        results = row[1]
        for kw in ["FUNCTIONALITY", "MEAN", "STANDARD DEVIATION", "INTERPRETATION"]:
            idx = results.upper().find(kw)
            if idx != -1:
                start = max(0, idx - 100)
                end = min(len(results), idx + 300)
                print(f"--- Snippet for {kw} ---")
                print(results[start:end])
                print("-" * 25)
    
    conn.close()
