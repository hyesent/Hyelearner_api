# test_db.py
import psycopg2

try:
    conn = psycopg2.connect(
        host="db.prygcgagxayxijdlnovd.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="syl.hyesent001"
    )
    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")