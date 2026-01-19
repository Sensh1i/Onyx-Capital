import psycopg2
from db import get_conn, release_conn

def migrate_data():
    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor()

    print("🔄 Veritabanı yapılandırması başlıyor...")

    # 1. Kullanıcılar Tablosu (Yoksa oluştur)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100)
        );
    """)

    # 2. İşlemler Tablosu (Tek Tablo Yapısı)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            type VARCHAR(10) CHECK (type IN ('income', 'expense')),
            category VARCHAR(50),
            amount DECIMAL(10, 2),
            description TEXT,
            date DATE DEFAULT CURRENT_DATE
        );
    """)

    # 3. Yatırımlar Tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            name VARCHAR(100),
            type VARCHAR(50),
            amount DECIMAL(10, 2),
            current_value DECIMAL(10, 2),
            date DATE DEFAULT CURRENT_DATE
        );
    """)

    # 4. Kredi Kartları
    cur.execute("""
        CREATE TABLE IF NOT EXISTS credit_cards (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            card_name VARCHAR(50),
            limit_amount DECIMAL(10, 2),
            current_debt DECIMAL(10, 2),
            cutoff_date INTEGER
        );
    """)

    # 5. Pasif Gelir
    cur.execute("""
        CREATE TABLE IF NOT EXISTS passive_income (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            source_name VARCHAR(100),
            estimated_monthly DECIMAL(10, 2),
            type VARCHAR(50)
        );
    """)

    try:
        cur.execute("SELECT count(*) FROM transactions")
        count = cur.fetchone()[0]
        if count == 0:
            print("📦 Eski veriler taşınıyor...")
            try:
                cur.execute("INSERT INTO transactions (user_id, type, category, amount, description, date) SELECT user_id, 'income', 'Genel', amount, 'Eski Veri', CURRENT_DATE FROM incomes")
            except: pass
            try:
                cur.execute("INSERT INTO transactions (user_id, type, category, amount, description, date) SELECT user_id, 'expense', 'Genel', amount, 'Eski Veri', CURRENT_DATE FROM expenses")
            except: pass
    except Exception as e:
        print(f"⚠️ Veri taşıma uyarısı: {e}")

    print("✅ Veritabanı hazır.")
    cur.close()
    release_conn(conn)

if __name__ == "__main__":
    migrate_data()