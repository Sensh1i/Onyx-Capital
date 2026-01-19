import psycopg2
from psycopg2 import pool

# Veritabanı bağlantı havuzu
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1, 20,
        host="127.0.0.1",
        database="finans_db",
        user="postgres",
        password="****"  # <-- BURAYA KENDİ ŞİFRENİZİ YAZIN
    )
except Exception as e:
    print(f"Veritabanı bağlantı hatası: {e}")
    connection_pool = None

def get_conn():
    if connection_pool:
        return connection_pool.getconn()
    else:
        raise Exception("Bağlantı havuzu başlatılamadı.")

def release_conn(conn):
    if connection_pool and conn:
        connection_pool.putconn(conn)



        