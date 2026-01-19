from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from db import get_conn, release_conn
import pandas as pd
import io
from datetime import timedelta, datetime
from collections import defaultdict

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "gizli-super-anahtar"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
jwt = JWTManager(app)

# JWT error handlers for better error messages
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token süresi dolmuş. Lütfen tekrar giriş yapın."}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"error": f"Geçersiz token: {str(error)}"}), 422

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"error": "Token bulunamadı. Lütfen giriş yapın."}), 401


def execute_query(query, params=(), fetch_one=False, fetch_all=False, commit=False):
    conn = get_conn()
    cur = conn.cursor()
    result = None
    try:
        cur.execute(query, params)
        if commit:
            conn.commit()
        if fetch_one:
            result = cur.fetchone()
        if fetch_all:
            result = cur.fetchall()
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        cur.close()
        release_conn(conn)
    return result


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    try:
        execute_query(
            "INSERT INTO users (email, password_hash, full_name) VALUES (%s, %s, %s)", 
            (data['email'], data['password'], data.get('full_name', 'Kullanıcı')), 
            commit=True
        )
        return jsonify({"message": "Kayıt başarılı!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = execute_query(
        "SELECT user_id, full_name FROM users WHERE email=%s AND password_hash=%s",
        (data.get("email"), data.get("password")),
        fetch_one=True
    )

    if user:
        # JWT identity must be a string
        token = create_access_token(identity=str(user[0]))
        return jsonify({"token": token, "user_id": user[0], "name": user[1]})
    else:
        return jsonify({"error": "Hatalı bilgi!"}), 401

@app.route("/dashboard-data", methods=["GET"])
@jwt_required()
def dashboard_data():
    try:
        # Convert string identity back to integer
        user_id = int(get_jwt_identity())
        
        # İşlem toplamlarını çek
        totals_raw = execute_query(
            "SELECT type, COALESCE(SUM(amount), 0) FROM transactions WHERE user_id=%s GROUP BY type", 
            (user_id,), fetch_all=True
        )
        totals = {row[0]: float(row[1]) for row in (totals_raw or [])}
        
        # Bu ay ve geçen ay toplamlarını hesapla (yüzde değişim için)
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Bu ay toplamları
        this_month_totals_raw = execute_query(
            """SELECT type, COALESCE(SUM(amount), 0) 
               FROM transactions 
               WHERE user_id=%s 
               AND EXTRACT(MONTH FROM date) = %s 
               AND EXTRACT(YEAR FROM date) = %s
               GROUP BY type""",
            (user_id, current_month, current_year), fetch_all=True
        )
        this_month_totals = {row[0]: float(row[1]) for row in (this_month_totals_raw or [])}
        
        # Geçen ay toplamları
        last_month = current_month - 1
        last_month_year = current_year
        if last_month == 0:
            last_month = 12
            last_month_year = current_year - 1
        
        last_month_totals_raw = execute_query(
            """SELECT type, COALESCE(SUM(amount), 0) 
               FROM transactions 
               WHERE user_id=%s 
               AND EXTRACT(MONTH FROM date) = %s 
               AND EXTRACT(YEAR FROM date) = %s
               GROUP BY type""",
            (user_id, last_month, last_month_year), fetch_all=True
        )
        last_month_totals = {row[0]: float(row[1]) for row in (last_month_totals_raw or [])}
        
        # Yüzde değişimleri hesapla
        def calculate_percentage_change(current, previous):
            if previous == 0:
                return None if current == 0 else 100.0
            return round(((current - previous) / previous) * 100, 1)
        
        income_change = calculate_percentage_change(
            this_month_totals.get('income', 0),
            last_month_totals.get('income', 0)
        )
        expense_change = calculate_percentage_change(
            this_month_totals.get('expense', 0),
            last_month_totals.get('expense', 0)
        )
        
        # Net gelir değişimi
        this_month_net = this_month_totals.get('income', 0) - this_month_totals.get('expense', 0)
        last_month_net = last_month_totals.get('income', 0) - last_month_totals.get('expense', 0)
        net_change = calculate_percentage_change(this_month_net, last_month_net)
        
        # Yatırım değişimi için basit bir tahmin (gerçek uygulamada geçmiş değerler saklanmalı)
        # Şimdilik pozitif bir değer göster (gerçek uygulamada geçmiş değerlerle karşılaştırılmalı)
        invest_change = 15.3  # Varsayılan, gerçek uygulamada hesaplanmalı

        # Tüm transaction verilerini çek (category dahil)
        chart_raw = execute_query(
            "SELECT date, type, category, amount FROM transactions WHERE user_id=%s ORDER BY date ASC", 
            (user_id,), fetch_all=True
        )
        chart_data = [
            {
                "date": str(r[0]),
                "type": r[1],
                "category": r[2] or "Genel",
                "amount": float(r[3])
            } 
            for r in (chart_raw or [])
        ]
        
        # Kategori dağılımı (sadece expense için)
        category_data = {}
        for trans in chart_data:
            if trans["type"] == "expense" and trans["category"]:
                category = trans["category"]
                category_data[category] = category_data.get(category, 0) + trans["amount"]
        
        # Aylık veriler (son 6 ay) - tüm transaction verilerinden hesapla
        months_tr = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                     "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        
        monthly_dict = {}
        current_month = datetime.now().month
        
        # Chart data'dan aylık toplamları hesapla
        for trans in chart_data:
            try:
                trans_date = datetime.strptime(trans["date"], "%Y-%m-%d")
                month_num = trans_date.month
                month_name = months_tr[month_num - 1]
                
                if month_name not in monthly_dict:
                    monthly_dict[month_name] = {"month": month_name, "income": 0, "expense": 0}
                
                if trans["type"] == "income":
                    monthly_dict[month_name]["income"] += trans["amount"]
                else:
                    monthly_dict[month_name]["expense"] += trans["amount"]
            except:
                continue
        
        # Son 6 ayı al (sıralı)
        monthly_data = []
        for i in range(6):
            month_idx = (current_month - 6 + i) % 12
            if month_idx < 0:
                month_idx += 12
            month_name = months_tr[month_idx]
            monthly_data.append(monthly_dict.get(month_name, {
                "month": month_name,
                "income": 0,
                "expense": 0
            }))
        
        # Son 10 işlem
        recent_raw = execute_query(
            "SELECT date, type, category, amount FROM transactions WHERE user_id=%s ORDER BY date DESC, id DESC LIMIT 10",
            (user_id,), fetch_all=True
        )
        recent_transactions = [
            {
                "date": str(r[0]),
                "type": r[1],
                "category": r[2] or "Genel",
                "amount": float(r[3])
            }
            for r in (recent_raw or [])
        ]
        
        # Yatırımları çek
        investments_raw = execute_query(
            "SELECT name, amount, current_value FROM investments WHERE user_id=%s",
            (user_id,), fetch_all=True
        )
        investments = [
            {
                "name": r[0],
                "amount": float(r[1]),
                "current_value": float(r[2])
            } 
            for r in (investments_raw or [])
        ]
        
        return jsonify({
            "income": float(totals.get('income', 0)),
            "expense": float(totals.get('expense', 0)),
            "chart_data": chart_data,
            "categoryData": category_data,
            "monthlyData": monthly_data,
            "recentTransactions": recent_transactions,
            "investments": investments,
            "percentageChanges": {
                "income": income_change,
                "expense": expense_change,
                "net": net_change,
                "investment": invest_change
            }
        })
    except Exception as e:
        print(f"Error in dashboard_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Veri yüklenirken hata: {str(e)}"}), 500

@app.route("/transaction", methods=["POST"])
@jwt_required()
def add_transaction():
    try:
        # Convert string identity back to integer
        user_id = int(get_jwt_identity())
        d = request.get_json()
        
        if not d.get('type') or not d.get('amount'):
            return jsonify({"error": "Type ve amount gerekli!"}), 400
        
        execute_query(
            "INSERT INTO transactions (user_id, type, category, amount, description, date) VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)",
            (user_id, d['type'], d.get('category'), d['amount'], d.get('description', 'Web')),
            commit=True
        )
        return jsonify({"msg": "Eklendi"})
    except Exception as e:
        print(f"Error adding transaction: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/investment", methods=["POST"])
@jwt_required()
def add_investment():
    try:
        # Convert string identity back to integer
        user_id = int(get_jwt_identity())
        d = request.get_json()
        
        if not d.get('name') or not d.get('current_value'):
            return jsonify({"error": "Name ve current_value gerekli!"}), 400
        
        execute_query(
            "INSERT INTO investments (user_id, name, amount, current_value, date) VALUES (%s, %s, %s, %s, CURRENT_DATE)",
            (user_id, d['name'], d.get('amount', 0), d['current_value']),
            commit=True
        )
        return jsonify({"message": "Yatırım eklendi", "id": True})
    except Exception as e:
        print(f"Error adding investment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/export", methods=["GET"])
@jwt_required()
def export():
    # Convert string identity back to integer
    user_id = int(get_jwt_identity())
    conn = get_conn()
    try:
        query = """
            SELECT type, category, amount, date, description 
            FROM transactions 
            WHERE user_id=%s 
            ORDER BY date DESC
        """
        df = pd.read_sql(query, conn, params=(user_id,))
        
        if df.empty:
            return jsonify({"error": "Dışa aktarılacak veri yok"}), 400
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # İşlemler sayfası
            df.to_excel(writer, sheet_name='İşlemler', index=False)
            
            # Özet sayfası
            summary_data = {
                'Kategori': ['Toplam Gelir', 'Toplam Gider', 'Net Gelir'],
                'Tutar': [
                    float(df[df['type'] == 'income']['amount'].sum()),
                    float(df[df['type'] == 'expense']['amount'].sum()),
                    float(df[df['type'] == 'income']['amount'].sum() - df[df['type'] == 'expense']['amount'].sum())
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Özet', index=False)
        
        output.seek(0)
        return send_file(
            output, 
            download_name=f"finans_raporu_{datetime.now().strftime('%Y%m%d')}.xlsx", 
            as_attachment=True, 
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print(f"Error exporting: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_conn(conn)

@app.route("/api/analytics/advanced", methods=["GET"])
@jwt_required()
def advanced_analytics():
    """
    Advanced Analytics endpoint with 5 complex SQL queries:
    1. MoM Growth (CTE & Window Function)
    2. Category Ranking (Dense Rank)
    3. Anomaly Detection (Subquery & Having)
    4. Gap Analysis (Left Join)
    5. Running Total (Window Function)
    """
    conn = None
    try:
        # Convert string identity back to integer
        user_id = int(get_jwt_identity())
        conn = get_conn()
        cur = conn.cursor()
        
        results = {}
        
        # 1. MoM Growth (CTE & Window Function)
        # Calculate month-over-month growth percentage of net cashflow
        query1 = """
        WITH monthly_totals AS (
            SELECT 
                DATE_TRUNC('month', date) as month,
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense,
                SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) as net_cashflow
            FROM transactions
            WHERE user_id = %s
            GROUP BY DATE_TRUNC('month', date)
        ),
        monthly_with_lag AS (
            SELECT 
                month,
                net_cashflow,
                LAG(net_cashflow) OVER (ORDER BY month) as previous_month_cashflow
            FROM monthly_totals
        )
        SELECT 
            TO_CHAR(month, 'YYYY-MM') as month,
            net_cashflow,
            previous_month_cashflow,
            CASE 
                WHEN previous_month_cashflow > 0 
                THEN ROUND(((net_cashflow - previous_month_cashflow) / previous_month_cashflow * 100)::numeric, 2)
                ELSE NULL
            END as growth_percentage
        FROM monthly_with_lag
        ORDER BY month DESC
        LIMIT 12;
        """
        
        cur.execute(query1, (user_id,))
        mom_results = cur.fetchall()
        results["growth_analysis"] = [
            {
                "month": row[0],
                "net_cashflow": float(row[1]) if row[1] else 0,
                "previous_month_cashflow": float(row[2]) if row[2] else 0,
                "growth_percentage": float(row[3]) if row[3] else None
            }
            for row in mom_results
        ]
        
        # 2. Category Ranking (Dense Rank)
        # Top spending category for each month using DENSE_RANK()
        query2 = """
        WITH monthly_category_totals AS (
            SELECT 
                DATE_TRUNC('month', date) as month,
                category,
                SUM(amount) as total_spent
            FROM transactions
            WHERE user_id = %s AND type = 'expense' AND category IS NOT NULL
            GROUP BY DATE_TRUNC('month', date), category
        ),
        ranked_categories AS (
            SELECT 
                TO_CHAR(month, 'YYYY-MM') as month,
                category,
                total_spent,
                DENSE_RANK() OVER (PARTITION BY month ORDER BY total_spent DESC) as rank
            FROM monthly_category_totals
        )
        SELECT month, category, total_spent, rank
        FROM ranked_categories
        WHERE rank = 1
        ORDER BY month DESC
        LIMIT 12;
        """
        
        cur.execute(query2, (user_id,))
        ranking_results = cur.fetchall()
        results["category_rankings"] = [
            {
                "month": row[0],
                "top_category": row[1] or "Genel",
                "total_spent": float(row[2]),
                "rank": int(row[3])
            }
            for row in ranking_results
        ]
        
        # 3. Anomaly Detection (Subquery & Having)
        # Categories where total spending is 50% higher than daily average
        query3 = """
        WITH daily_avg AS (
            SELECT AVG(daily_total) as avg_daily_spending
            FROM (
                SELECT date, SUM(amount) as daily_total
                FROM transactions
                WHERE user_id = %s AND type = 'expense'
                GROUP BY date
            ) daily_totals
        ),
        category_totals AS (
            SELECT 
                category,
                SUM(amount) as category_total,
                COUNT(DISTINCT date) as days_with_spending
            FROM transactions
            WHERE user_id = %s AND type = 'expense' AND category IS NOT NULL
            GROUP BY category
        ),
        category_analysis AS (
            SELECT 
                ct.category,
                ct.category_total,
                ROUND((ct.category_total / NULLIF(ct.days_with_spending, 0))::numeric, 2) as avg_daily_per_category,
                ROUND(da.avg_daily_spending::numeric, 2) as overall_avg_daily,
                ROUND(((ct.category_total / NULLIF(ct.days_with_spending, 0)) / NULLIF(da.avg_daily_spending, 1) * 100)::numeric, 2) as percentage_of_avg
            FROM category_totals ct
            CROSS JOIN daily_avg da
        )
        SELECT 
            category,
            category_total,
            avg_daily_per_category,
            overall_avg_daily,
            percentage_of_avg
        FROM category_analysis
        WHERE avg_daily_per_category > (overall_avg_daily * 1.5)
        ORDER BY category_total DESC;
        """
        
        cur.execute(query3, (user_id, user_id))
        anomaly_results = cur.fetchall()
        results["anomalies"] = [
            {
                "category": row[0] or "Genel",
                "category_total": float(row[1]),
                "avg_daily_per_category": float(row[2]) if row[2] else 0,
                "overall_avg_daily": float(row[3]) if row[3] else 0,
                "percentage_of_avg": float(row[4]) if row[4] else 0
            }
            for row in anomaly_results
        ]
        
        # 4. Gap Analysis (Left Join)
        # Users with high income (>50,000) but NO investments
        query4 = """
        WITH user_income_totals AS (
            SELECT 
                u.user_id,
                u.email,
                u.full_name,
                COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) as total_income
            FROM users u
            LEFT JOIN transactions t ON u.user_id = t.user_id
            WHERE u.user_id = %s
            GROUP BY u.user_id, u.email, u.full_name
        )
        SELECT 
            uit.user_id,
            uit.email,
            uit.full_name,
            uit.total_income,
            CASE WHEN i.id IS NULL THEN true ELSE false END as has_no_investments
        FROM user_income_totals uit
        LEFT JOIN investments i ON uit.user_id = i.user_id
        WHERE uit.total_income > 50000 AND i.id IS NULL;
        """
        
        cur.execute(query4, (user_id,))
        gap_results = cur.fetchall()
        results["gap_analysis"] = [
            {
                "user_id": row[0],
                "email": row[1],
                "full_name": row[2] or "Kullanıcı",
                "total_income": float(row[3]),
                "has_no_investments": row[4],
                "recommendation": "Yüksek gelire sahipsiniz ancak yatırım yapmıyorsunuz. Yatırım yapmayı düşünebilirsiniz."
            }
            for row in gap_results
        ]
        
        # 5. Running Total
        # Cumulative balance over time using window function
        query5 = """
        SELECT 
            date,
            type,
            category,
            amount,
            SUM(CASE 
                WHEN type = 'income' THEN amount 
                ELSE -amount 
            END) OVER (ORDER BY date, id) as running_balance
        FROM transactions
        WHERE user_id = %s
        ORDER BY date ASC, id ASC
        LIMIT 100;
        """
        
        cur.execute(query5, (user_id,))
        running_total_results = cur.fetchall()
        results["running_total"] = [
            {
                "date": str(row[0]),
                "type": row[1],
                "category": row[2] or "Genel",
                "amount": float(row[3]),
                "running_balance": float(row[4])
            }
            for row in running_total_results
        ]
        
        cur.close()
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "analytics": results,
            "summary": {
                "growth_periods": len(results["growth_analysis"]),
                "top_categories_found": len(results["category_rankings"]),
                "anomalies_detected": len(results["anomalies"]),
                "gap_analysis_count": len(results["gap_analysis"]),
                "running_total_records": len(results["running_total"])
            }
        })
        
    except Exception as e:
        print(f"Error in advanced_analytics: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": f"Analytics hesaplanırken hata: {str(e)}"
        }), 500
    finally:
        if conn:
            cur.close()
            release_conn(conn)

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Backend çalışıyor"})

if __name__ == "__main__":
    print("🚀 Finans Dashboard Backend başlatılıyor...")
    print("📍 API: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
