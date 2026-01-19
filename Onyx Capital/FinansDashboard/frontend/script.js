const API = "http://127.0.0.1:5000";
let chartInstances = {
    main: null,
    category: null,
    monthly: null
};

// Token'i localStorage'dan güvenli şekilde al
function getToken() {
    return localStorage.getItem("token");
}

// Sayfa açılınca giriş yapılmış mı kontrol et
document.addEventListener("DOMContentLoaded", () => {
    const token = getToken();
    if(token) {
        showDashboard();
    }
});

// --- GİRİŞ & KAYIT ---
function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const msgEl = document.getElementById("msg");
    
    if(!email || !password) {
        msgEl.textContent = "Lütfen e-posta ve şifre girin!";
        return;
    }
    
    msgEl.textContent = "";
    
    fetch(`${API}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    })
    .then(async r => {
        const data = await r.json();
        if(!r.ok) {
            throw new Error(data.error || "Giriş başarısız!");
        }
        return data;
    })
    .then(d => {
        if(d.token) {
            localStorage.setItem("token", d.token);
            localStorage.setItem("userName", d.name || "Kullanıcı");
            localStorage.setItem("userEmail", email);
            console.log("Login successful, token saved");
            showDashboard();
        } else {
            msgEl.textContent = d.error || "Giriş başarısız!";
        }
    })
    .catch(e => {
        console.error("Login error:", e);
        msgEl.textContent = e.message || "Sunucuya bağlanılamadı! Backend çalışıyor mu?";
    });
}

function showRegisterModal() {
    document.getElementById("registerModal").style.display = "block";
    document.getElementById("regMsg").textContent = "";
}

function closeRegisterModal() {
    document.getElementById("registerModal").style.display = "none";
    // Clear form
    document.getElementById("regName").value = "";
    document.getElementById("regEmail").value = "";
    document.getElementById("regPassword").value = "";
    document.getElementById("regPasswordConfirm").value = "";
    document.getElementById("regMsg").textContent = "";
}

function register() {
    const name = document.getElementById("regName").value;
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;
    const passwordConfirm = document.getElementById("regPasswordConfirm").value;
    const msgEl = document.getElementById("regMsg");
    
    if(!name || !email || !password) {
        msgEl.textContent = "Lütfen tüm alanları doldurun!";
        return;
    }
    
    if(password !== passwordConfirm) {
        msgEl.textContent = "Şifreler eşleşmiyor!";
        return;
    }
    
    if(password.length < 4) {
        msgEl.textContent = "Şifre en az 4 karakter olmalıdır!";
        return;
    }
    
    msgEl.textContent = "";
    
    fetch(`${API}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            email: email, 
            password: password,
            full_name: name
        })
    })
    .then(async r => {
        const data = await r.json();
        if(!r.ok) {
            throw new Error(data.error || "Kayıt başarısız!");
        }
        return data;
    })
    .then(d => {
        if(d.message) {
            alert("Kayıt başarılı! Giriş yapabilirsiniz.");
            closeRegisterModal();
            // Auto-fill login form
            document.getElementById("email").value = email;
            document.getElementById("password").value = "";
        }
    })
    .catch(e => {
        console.error("Register error:", e);
        msgEl.textContent = e.message || "Kayıt sırasında hata oluştu!";
    });
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById("registerModal");
    if (event.target == modal) {
        closeRegisterModal();
    }
}

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    localStorage.removeItem("userEmail");
    location.reload();
}

// --- EKRAN YÖNETİMİ ---
function showDashboard() {
    const token = getToken();
    if(!token) {
        showLogin();
        return;
    }
    const loginScreen = document.getElementById("loginScreen");
    const dashboardScreen = document.getElementById("dashboardScreen");
    
    if(loginScreen) loginScreen.style.display = "none";
    if(dashboardScreen) dashboardScreen.style.display = "block";
    
    // Update user info
    const userName = localStorage.getItem("userName") || "Kullanıcı";
    const userEmail = localStorage.getItem("userEmail") || "user@example.com";
    document.getElementById("userName").textContent = userName;
    document.getElementById("userEmail").textContent = userEmail;
    
    loadData();
}

function showLogin() {
    localStorage.removeItem("token");
    const loginScreen = document.getElementById("loginScreen");
    const dashboardScreen = document.getElementById("dashboardScreen");
    
    if(loginScreen) loginScreen.style.display = "flex";
    if(dashboardScreen) dashboardScreen.style.display = "none";
}


// --- VERİ ÇEKME ---
function loadData() {
    const token = getToken();
    if(!token) {
        console.error("No token found!");
        alert("Giriş yapmanız gerekiyor!");
        logout();
        return;
    }

    fetch(`${API}/dashboard-data`, { 
        headers: { "Authorization": `Bearer ${token}` } 
    })
    .then(async r => {
        if(!r.ok) {
            // Try to get error message from response
            let errorMsg = `HTTP ${r.status}`;
            try {
                const errorData = await r.json();
                errorMsg = errorData.error || errorData.message || errorMsg;
            } catch(e) {
                // Response is not JSON
            }
            throw new Error(errorMsg);
        }
        return r.json();
    })
    .then(d => {
        console.log("Dashboard data loaded from backend:", d);
        updateDashboard(d);
    })
    .catch(e => {
        console.error("Error loading dashboard data:", e);
        const errorMsg = e.message || "Bilinmeyen hata";
        
        if(errorMsg.includes("Failed to fetch") || errorMsg.includes("NetworkError")) {
            alert("Sunucuya bağlanılamadı!\n\n" +
                  "Lütfen kontrol edin:\n" +
                  "1. Backend sunucusu çalışıyor mu? (http://127.0.0.1:5000)\n" +
                  "2. baslat.bat dosyasını çalıştırdınız mı?\n" +
                  "3. Backend penceresi açık mı?");
        } else {
            alert("Veri yüklenemedi: " + errorMsg + "\n\nLütfen backend'in çalıştığından emin olun.");
        }
        
        // Show empty dashboard instead of fake data
        updateDashboard({
            income: 0,
            expense: 0,
            chart_data: [],
            categoryData: {},
            monthlyData: [],
            recentTransactions: [],
            investments: [],
            percentageChanges: {
                income: null,
                expense: null,
                net: null,
                investment: null
            }
        });
    });
}

function updateDashboard(data, isFake = false) {
    // Update statistics
    const income = data.income || 0;
    const expense = data.expense || 0;
    const net = income - expense;
    
    document.getElementById("incomeVal").innerText = formatCurrency(income);
    document.getElementById("expenseVal").innerText = formatCurrency(expense);
    document.getElementById("netVal").innerText = formatCurrency(net);
    
    // Update percentage changes
    const changes = data.percentageChanges || {};
    updatePercentageChange("income", changes.income);
    updatePercentageChange("expense", changes.expense);
    updatePercentageChange("net", changes.net);
    updatePercentageChange("investment", changes.investment);
    
    // Update investments
    const investments = data.investments || [];
    const investTotal = investments.reduce((sum, inv) => sum + (parseFloat(inv.current_value) || 0), 0);
    document.getElementById("investVal").innerText = formatCurrency(investTotal);
    updateInvestments(investments);
    
    // Render charts
    renderMainChart(data.chart_data || []);
    renderCategoryChart(data.categoryData || generateCategoryData(data.chart_data || []));
    renderMonthlyChart(data.monthlyData || []);
    
    // Update recent transactions
    updateRecentTransactions(data.recentTransactions || (data.chart_data || []).slice(-10).reverse());
    
    // Update quick stats
    updateQuickStats(data);
}

function generateCategoryData(chartData) {
    const categoryData = {};
    chartData.filter(d => d.type === 'expense').forEach(d => {
        categoryData[d.category] = (categoryData[d.category] || 0) + (d.amount || 0);
    });
    return categoryData;
}


function formatCurrency(amount) {
    return new Intl.NumberFormat('tr-TR', { 
        style: 'currency', 
        currency: 'TRY',
        minimumFractionDigits: 0 
    }).format(amount);
}

function updatePercentageChange(type, percentage) {
    const elementId = type + "Change";
    const element = document.getElementById(elementId);
    if(!element) return;
    
    if(percentage === null || percentage === undefined) {
        element.textContent = "- bu ay";
        element.className = "stat-change";
        return;
    }
    
    const isPositive = percentage >= 0;
    const sign = isPositive ? "+" : "";
    element.textContent = `${sign}${percentage}% bu ay`;
    element.className = isPositive ? "stat-change positive" : "stat-change negative";
}

// --- GRAFİKLER ---
function renderMainChart(data) {
    const ctx = document.getElementById('mainChart').getContext('2d');
    if(chartInstances.main) chartInstances.main.destroy();
    
    // If no data, show empty chart
    if(!data || data.length === 0) {
        chartInstances.main = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Gelir',
                        data: [],
                        borderColor: '#00ff99',
                        backgroundColor: 'rgba(0, 255, 153, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Gider',
                        data: [],
                        borderColor: '#ff4d4d',
                        backgroundColor: 'rgba(255, 77, 77, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        labels: { color: '#e0e0e0', font: { size: 12 } },
                        position: 'top'
                    }
                },
                scales: {
                    x: { 
                        ticks: { color: '#999', font: { size: 11 } },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    y: { 
                        ticks: { 
                            color: '#999', 
                            font: { size: 11 },
                            callback: function(value) {
                                return formatCurrency(value);
                            }
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                }
            }
        });
        return;
    }
    
    const labels = data.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' });
    });
    
    const incomeData = data.filter(d => d.type === 'income').map(d => d.amount);
    const expenseData = data.filter(d => d.type === 'expense').map(d => -d.amount);
    
    chartInstances.main = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Gelir',
                    data: data.map(d => d.type === 'income' ? d.amount : null),
                    borderColor: '#00ff99',
                    backgroundColor: 'rgba(0, 255, 153, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Gider',
                    data: data.map(d => d.type === 'expense' ? d.amount : null),
                    borderColor: '#ff4d4d',
                    backgroundColor: 'rgba(255, 77, 77, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    labels: { color: '#e0e0e0', font: { size: 12 } },
                    position: 'top'
                }
            },
            scales: {
                x: { 
                    ticks: { color: '#999', font: { size: 11 } },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                },
                y: { 
                    ticks: { 
                        color: '#999', 
                        font: { size: 11 },
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });
}

function renderCategoryChart(categoryData) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    if(chartInstances.category) chartInstances.category.destroy();
    
    const labels = Object.keys(categoryData);
    const values = Object.values(categoryData);
    const colors = [
        '#00ff99', '#ff4d4d', '#4d94ff', '#ffaa00', 
        '#aa00ff', '#00ffaa', '#ff0066', '#0066ff'
    ];
    
    chartInstances.category = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#1e1e1e'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    labels: { color: '#e0e0e0', font: { size: 11 } },
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': ' + formatCurrency(context.parsed) + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

function renderMonthlyChart(monthlyData) {
    const ctx = document.getElementById('monthlyChart').getContext('2d');
    if(chartInstances.monthly) chartInstances.monthly.destroy();
    
    chartInstances.monthly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: monthlyData.map(d => d.month),
            datasets: [
                {
                    label: 'Gelir',
                    data: monthlyData.map(d => d.income),
                    backgroundColor: 'rgba(0, 255, 153, 0.6)',
                    borderColor: '#00ff99',
                    borderWidth: 2
                },
                {
                    label: 'Gider',
                    data: monthlyData.map(d => d.expense),
                    backgroundColor: 'rgba(255, 77, 77, 0.6)',
                    borderColor: '#ff4d4d',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    labels: { color: '#e0e0e0', font: { size: 12 } },
                    position: 'top'
                }
            },
            scales: {
                x: { 
                    ticks: { color: '#999', font: { size: 11 } },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                },
                y: { 
                    ticks: { 
                        color: '#999', 
                        font: { size: 11 },
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });
}

// --- İŞLEM EKLEME ---
function addTransaction() {
    const token = getToken();
    if(!token) {
        alert("Giriş yapmanız gerekiyor!");
        logout();
        return;
    }
    
    const type = document.getElementById("tType").value;
    const category = document.getElementById("tCat").value;
    const amount = document.getElementById("tAmount").value;
    
    if(!category || !amount) {
        alert("Lütfen kategori ve tutarı girin!");
        return;
    }
    
    fetch(`${API}/transaction`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ type, category, amount })
    })
    .then(async r => {
        if(!r.ok) {
            const errorData = await r.json();
            throw new Error(errorData.error || "İşlem eklenemedi!");
        }
        return r.json();
    })
    .then(d => {
        alert("İşlem başarıyla eklendi!");
        document.getElementById("tCat").value = "";
        document.getElementById("tAmount").value = "";
        // Reload data from backend to show new transaction
        loadData();
    })
    .catch(e => {
        console.error("Error adding transaction:", e);
        alert("İşlem eklenirken hata oluştu: " + e.message);
    });
}

// --- EXCEL ---
function exportData() {
    const token = getToken();
    if(!token) {
        alert("Giriş yapmanız gerekiyor!");
        logout();
        return;
    }
    
    fetch(`${API}/export`, { headers: { "Authorization": `Bearer ${token}` } })
    .then(r => {
        if(!r.ok) {
            throw new Error("Dosya indirilemedi!");
        }
        return r.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "finans_raporu.xlsx";
        a.click();
        window.URL.revokeObjectURL(url);
    })
    .catch(e => {
        console.error("Error exporting:", e);
        alert("Excel dosyası indirilemedi: " + e.message);
    });
}

// --- YATIRIM İŞLEMLERİ ---
function addInvestment() {
    const token = getToken();
    if(!token) {
        alert("Giriş yapmanız gerekiyor!");
        logout();
        return;
    }
    
    const name = document.getElementById("invName").value;
    const amount = document.getElementById("invAmount").value;
    const value = document.getElementById("invValue").value;
    
    if(!name || !amount || !value) {
        alert("Lütfen tüm alanları doldurun!");
        return;
    }
    
    fetch(`${API}/investment`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ name, amount, current_value: value })
    })
    .then(async r => {
        if(!r.ok) {
            const errorData = await r.json();
            throw new Error(errorData.error || "Yatırım eklenemedi!");
        }
        return r.json();
    })
    .then(d => {
        if(d.message || d.id) {
            alert("Yatırım başarıyla eklendi!");
            document.getElementById("invName").value = "";
            document.getElementById("invAmount").value = "";
            document.getElementById("invValue").value = "";
            // Reload data from backend to show new investment
            loadData();
        } else {
            alert("Hata: " + (d.error || "Yatırım eklenemedi"));
        }
    })
    .catch(e => {
        console.error("Error adding investment:", e);
        alert("Yatırım eklenirken hata oluştu: " + e.message);
    });
}

function updateInvestments(investments) {
    const listEl = document.getElementById("investList");
    if(!listEl) return;
    
    if(!investments || investments.length === 0) {
        listEl.innerHTML = "<li style='color: #999;'>Henüz yatırım yok</li>";
        return;
    }
    
    listEl.innerHTML = investments.map(inv => 
        `<li>
            <div>
                <strong>${inv.name}</strong>
                <span style="color: #999; font-size: 12px;">${inv.amount || 0} adet</span>
            </div>
            <span class="stat-value">${formatCurrency(inv.current_value || 0)}</span>
        </li>`
    ).join("");
}

function updateRecentTransactions(transactions) {
    const listEl = document.getElementById("recentTransactions");
    if(!listEl) return;
    
    if(!transactions || transactions.length === 0) {
        listEl.innerHTML = "<li style='color: #999;'>Henüz işlem yok</li>";
        return;
    }
    
    listEl.innerHTML = transactions.map(t => {
        const isIncome = t.type === 'income';
        const date = new Date(t.date);
        return `<li class="${isIncome ? 'income-item' : ''}">
            <div>
                <strong>${t.category || 'Genel'}</strong>
                <span style="color: #999; font-size: 11px;">${date.toLocaleDateString('tr-TR')}</span>
            </div>
            <span class="${isIncome ? 'green' : 'red'}">${isIncome ? '+' : '-'}${formatCurrency(t.amount || 0)}</span>
        </li>`;
    }).join("");
}

function updateQuickStats(data) {
    const income = data.income || 0;
    const expense = data.expense || 0;
    const chartData = data.chart_data || [];
    
    // Average daily income
    const incomeDays = chartData.filter(d => d.type === 'income').length || 1;
    const avgDailyIncome = income / incomeDays;
    document.getElementById("avgDailyIncome").textContent = formatCurrency(avgDailyIncome);
    
    // Top category
    const categoryData = data.categoryData || generateCategoryData(chartData);
    const topCategory = Object.keys(categoryData).reduce((a, b) => 
        categoryData[a] > categoryData[b] ? a : b, Object.keys(categoryData)[0] || '-'
    );
    document.getElementById("topCategory").textContent = topCategory || '-';
    
    // Monthly transactions
    const thisMonth = new Date().getMonth();
    const monthlyCount = chartData.filter(d => {
        const date = new Date(d.date);
        return date.getMonth() === thisMonth;
    }).length;
    document.getElementById("monthlyTransactions").textContent = monthlyCount;
    
    // Savings rate
    const savingsRate = income > 0 ? ((income - expense) / income * 100).toFixed(1) : 0;
    document.getElementById("savingsRate").textContent = savingsRate + '%';
}
