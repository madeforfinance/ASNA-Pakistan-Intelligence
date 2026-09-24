import sqlite3

DB_PATH = "data/intelligence.db"

db = sqlite3.connect(DB_PATH)

print("=" * 70)
print("DATABASE INSPECTION")
print("=" * 70)

print("\n=== TABLES ===")

tables = db.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

for table in tables:
    print(f"  - {table[0]}")

print("\n=== ARTICLES TABLE ===")

try:
    columns = db.execute("PRAGMA table_info(articles)").fetchall()

    for column in columns:
        print(
            f"  {column[1]:25} "
            f"type={column[2]:15} "
            f"notnull={column[3]} "
            f"default={column[4]} "
            f"pk={column[5]}"
        )

except Exception as e:
    print("Could not inspect articles:", e)

print("\n=== SOURCES TABLE ===")

try:
    columns = db.execute("PRAGMA table_info(sources)").fetchall()

    for column in columns:
        print(
            f"  {column[1]:25} "
            f"type={column[2]:15} "
            f"notnull={column[3]} "
            f"default={column[4]} "
            f"pk={column[5]}"
        )

except Exception as e:
    print("Could not inspect sources:", e)

print("\n=== EXISTING SOURCE RECORDS ===")

try:
    rows = db.execute("""
        SELECT *
        FROM sources
        LIMIT 20
    """).fetchall()

    for row in rows:
        print(row)

except Exception as e:
    print("Could not read sources:", e)

print("\n" + "=" * 70)

db.close()