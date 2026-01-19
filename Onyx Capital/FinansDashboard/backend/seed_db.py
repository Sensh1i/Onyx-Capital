import psycopg2
from db import get_conn, release_conn
from datetime import date, timedelta
import random

def seed_database():
    print("🌱 Örnek veriler ekleniyor...")
    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # 1. Test Kullanıcıları Oluştur
        print("👤 Kullanıcılar oluşturuluyor...")
        
        users_data = [
            ('test@test.com', '1234', 'Demo Kullanıcı'),
            ('user1@example.com', '1234', 'Ahmet Yılmaz'),
            ('user2@example.com', '1234', 'Ayşe Demir')
        ]
        
        user_ids = {}
        for email, password, name in users_data:
            cur.execute("""
                INSERT INTO users (email, password_hash, full_name) 
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
                RETURNING user_id;
            """, (email, password, name))
            
            row = cur.fetchone()
            if row:
                user_id = row[0]
            else:
                cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                user_id = cur.fetchone()[0]
            
            user_ids[email] = user_id
            print(f"  ✓ {email} - ID: {user_id}")

        # Ana kullanıcı için detaylı veri
        main_user_id = user_ids['test@test.com']
        
        # 2. Son 3 ay için çeşitli işlemler ekle (yüzde hesaplaması için)
        print("💰 Gelirler ekleniyor (son 3 ay)...")
        
        income_categories = ['Maaş', 'Freelance', 'Yatırım Getirisi', 'Kira Geliri', 'Bonus']
        income_amounts = {
            'Maaş': [40000, 45000, 50000],
            'Freelance': [5000, 8000, 12000, 15000],
            'Yatırım Getirisi': [2000, 3500, 5000],
            'Kira Geliri': [10000, 12000],
            'Bonus': [5000, 10000]
        }
        
        # Son 3 ay için aylık maaşlar (her ayın 1'i)
        for month_offset in range(3):
            # Her ayın başında maaş
            if month_offset == 0:
                # Bu ay
                month_date = date.today().replace(day=1)
            else:
                # Geçmiş aylar
                month_date = (date.today().replace(day=1) - timedelta(days=32 * month_offset)).replace(day=1)
            
            amount = random.choice(income_amounts['Maaş'])
            # Bu ay biraz daha fazla olsun (yüzde artışı için)
            if month_offset == 0:
                amount = int(amount * 1.1)  # %10 artış
            
            cur.execute("""
                INSERT INTO transactions (user_id, type, category, amount, description, date) 
                VALUES (%s, 'income', 'Maaş', %s, 'Aylık Maaş', %s)
            """, (main_user_id, amount, month_date))
        
        # Diğer gelirler (son 90 gün boyunca rastgele)
        for i in range(20):
            days_ago = random.randint(1, 90)
            trans_date = date.today() - timedelta(days=days_ago)
            category = random.choice(income_categories)
            if category == 'Maaş':
                continue  # Maaşları zaten ekledik
            amount = random.choice(income_amounts.get(category, [5000]))
            cur.execute("""
                INSERT INTO transactions (user_id, type, category, amount, description, date) 
                VALUES (%s, 'income', %s, %s, %s, %s)
            """, (main_user_id, category, amount, f'{category} Geliri', trans_date))

        print("💸 Giderler ekleniyor (son 3 ay)...")
        
        expense_categories = {
            'Kira': [15000, 18000, 20000],
            'Market': [2000, 3500, 5000, 6000],
            'Fatura': [800, 1200, 1500, 2000],
            'Ulaşım': [500, 800, 1200, 2000],
            'Eğlence': [1000, 2000, 3000, 5000],
            'Sağlık': [500, 1000, 2000, 4000],
            'Eğitim': [2000, 5000, 8000],
            'Giyim': [1000, 2000, 4000],
            'Restoran': [300, 500, 800, 1500],
            'Teknoloji': [2000, 5000, 10000]
        }
        
        # Her kategori için çeşitli giderler (son 90 gün)
        for category, amounts in expense_categories.items():
            # Her kategori için 4-10 arası işlem
            num_transactions = random.randint(4, 10)
            for _ in range(num_transactions):
                days_ago = random.randint(1, 90)
                trans_date = date.today() - timedelta(days=days_ago)
                amount = random.choice(amounts)
                
                # Bu ay için biraz daha az gider olsun (yüzde azalışı için)
                if days_ago <= 30:
                    amount = int(amount * 0.95)  # %5 azalış
                
                descriptions = {
                    'Kira': 'Ev Kirası',
                    'Market': 'Market Alışverişi',
                    'Fatura': 'Elektrik & Su Faturası',
                    'Ulaşım': 'Ulaşım Gideri',
                    'Eğlence': 'Eğlence & Aktivite',
                    'Sağlık': 'Sağlık Gideri',
                    'Eğitim': 'Eğitim & Kurs',
                    'Giyim': 'Giyim & Aksesuar',
                    'Restoran': 'Restoran & Yemek',
                    'Teknoloji': 'Teknoloji & Elektronik'
                }
                cur.execute("""
                    INSERT INTO transactions (user_id, type, category, amount, description, date) 
                    VALUES (%s, 'expense', %s, %s, %s, %s)
                """, (main_user_id, category, amount, descriptions[category], trans_date))

        # 3. Yatırımlar Ekle
        print("📈 Yatırımlar ekleniyor...")
        
        investments_data = [
            ('Gram Altın', 'Altın', 50, 125000),
            ('Apple Hisse', 'Borsa', 15, 97500),
            ('Bitcoin', 'Kripto', 0.5, 125000),
            ('Ethereum', 'Kripto', 2, 45000),
            ('Tesla Hisse', 'Borsa', 5, 85000),
            ('Döviz (USD)', 'Döviz', 5000, 150000)
        ]
        
        for name, inv_type, amount, value in investments_data:
            cur.execute("""
                INSERT INTO investments (user_id, name, type, amount, current_value, date) 
                VALUES (%s, %s, %s, %s, %s, CURRENT_DATE - %s)
                ON CONFLICT DO NOTHING
            """, (main_user_id, name, inv_type, amount, value, random.randint(0, 90)))

        # 4. Kredi Kartı Borcu
        print("💳 Kredi kartı bilgileri ekleniyor...")
        cur.execute("""
            INSERT INTO credit_cards (user_id, card_name, limit_amount, current_debt, cutoff_date) 
            VALUES (%s, 'Garanti Bonus', 150000, 24500, 15)
            ON CONFLICT DO NOTHING
        """, (main_user_id,))

        # 5. Pasif Gelir
        print("🏠 Pasif gelir ekleniyor...")
        cur.execute("""
            INSERT INTO passive_income (user_id, source_name, estimated_monthly, type) 
            VALUES (%s, 'Ofis Kirası', 7500, 'Kira')
            ON CONFLICT DO NOTHING
        """, (main_user_id,))

        # Diğer kullanıcılar için basit veri
        for email, user_id in user_ids.items():
            if email != 'test@test.com':
                print(f"📊 {email} için örnek veri ekleniyor...")
                
                # Birkaç işlem
                cur.execute("""
                    INSERT INTO transactions (user_id, type, category, amount, description, date) 
                    VALUES (%s, 'income', 'Maaş', 35000, 'Aylık Maaş', CURRENT_DATE - 5)
                """, (user_id,))
                
                cur.execute("""
                    INSERT INTO transactions (user_id, type, category, amount, description, date) 
                    VALUES (%s, 'expense', 'Market', 2500, 'Market Alışverişi', CURRENT_DATE - 2)
                """, (user_id,))
                
                cur.execute("""
                    INSERT INTO transactions (user_id, type, category, amount, description, date) 
                    VALUES (%s, 'expense', 'Kira', 12000, 'Ev Kirası', CURRENT_DATE - 1)
                """, (user_id,))

        print("\n✅ Veritabanı başarıyla dolduruldu!")
        print("\n📋 Giriş Bilgileri:")
        print("   Email: test@test.com")
        print("   Şifre: 1234")
        print("\n   Email: user1@example.com")
        print("   Şifre: 1234")
        print("\n   Email: user2@example.com")
        print("   Şifre: 1234")
        print("\n🚀 Backend'i başlatıp giriş yapabilirsiniz!")

    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cur.close()
        release_conn(conn)

if __name__ == "__main__":
    seed_database()
