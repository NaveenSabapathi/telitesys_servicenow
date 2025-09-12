import psycopg2

try:
    conn = psycopg2.connect(
        dbname="neondb",
        user="neondb_owner",
        password="npg_9doPOBkLnMY8",
        host="ep-hidden-wind-a8o3vno9-pooler.eastus2.azure.neon.tech",
        port=5432,
        sslmode="require",
        channel_binding="require"
    )
    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:")
    print(e)
