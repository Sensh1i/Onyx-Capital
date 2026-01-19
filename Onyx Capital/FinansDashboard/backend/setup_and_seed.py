"""
Database Setup and Seeding Script
This script will:
1. Create all necessary tables (migrate)
2. Seed the database with sample data
"""

import sys
from migrate_db import migrate_data
from seed_db import seed_database

def main():
    print("=" * 60)
    print("🚀 Finans Dashboard - Veritabanı Kurulumu")
    print("=" * 60)
    
    try:
        # Step 1: Migrate database (create tables)
        print("\n📦 Adım 1: Veritabanı tabloları oluşturuluyor...")
        migrate_data()
        print("✅ Tablolar başarıyla oluşturuldu!\n")
        
        # Step 2: Seed database (add sample data)
        print("📊 Adım 2: Örnek veriler ekleniyor...")
        seed_database()
        print("\n✅ Kurulum tamamlandı!\n")
        
        print("=" * 60)
        print("🎉 Başarılı! Artık backend'i başlatabilirsiniz:")
        print("   python backend/server.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
