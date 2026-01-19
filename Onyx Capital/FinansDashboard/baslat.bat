@echo off
chcp 65001 >nul
title Finans Dashboard Baslatici
color 0A

echo ===================================================
echo   FINANS DASHBOARD BASLATILIYOR 
echo ===================================================
echo.

:: --- 1. Veritabani Kontrolu ---
echo [1/4] Veritabani kontrol ediliyor...
set PG_FOUND=0

if exist "C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" (
    set "PG_CTL=C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe"
    set "PG_DATA=C:\Program Files\PostgreSQL\17\data"
    set PG_FOUND=1
) else if exist "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" (
    set "PG_CTL=C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"
    set "PG_DATA=C:\Program Files\PostgreSQL\16\data"
    set PG_FOUND=1
) else if exist "C:\Program Files\PostgreSQL\15\bin\pg_ctl.exe" (
    set "PG_CTL=C:\Program Files\PostgreSQL\15\bin\pg_ctl.exe"
    set "PG_DATA=C:\Program Files\PostgreSQL\15\data"
    set PG_FOUND=1
) else if exist "C:\Program Files\PostgreSQL\14\bin\pg_ctl.exe" (
    set "PG_CTL=C:\Program Files\PostgreSQL\14\bin\pg_ctl.exe"
    set "PG_DATA=C:\Program Files\PostgreSQL\14\data"
    set PG_FOUND=1
)

if %PG_FOUND%==1 (
    echo       - PostgreSQL bulundu, kontrol ediliyor...
    "%PG_CTL%" -D "%PG_DATA%" status >nul 2>&1
    if errorlevel 1 (
        echo       - Veritabani baslatiliyor...
        "%PG_CTL%" -D "%PG_DATA%" start >nul 2>&1
        timeout /t 2 /nobreak >nul
    ) else (
        echo       - Veritabani zaten calisiyor.
    )
) else (
    echo       - PostgreSQL bulunamadi. Lutfen manuel olarak baslatin.
)
echo.

:: --- 2. Veritabani Kurulumu ---
echo [2/4] Veritabani kurulumu kontrol ediliyor...
cd backend
if exist "..\db_initialized.flag" (
    echo       - Veritabani zaten kurulu.
) else (
    echo       - Veritabani kuruluuyor ve ornek veriler ekleniyor...
    python setup_and_seed.py
    if not errorlevel 1 (
        echo. > ..\db_initialized.flag
        echo       - Veritabani basariyla kuruldu!
    ) else (
        echo       - UYARI: Veritabani kurulumunda hata olabilir.
    )
)
cd ..
echo.

:: --- 3. Backend Sunucusu ---
echo [3/4] Backend sunucusu baslatiliyor...
cd backend

if exist "venv\Scripts\activate.bat" (
    echo       - Sanal ortam aktive ediliyor...
    start "Finans Backend Server" cmd /k "call venv\Scripts\activate.bat ^&^& python server.py"
) else (
    echo       - Global Python kullaniliyor...
    start "Finans Backend Server" cmd /k "python server.py"
)
cd ..
echo       - Backend baslatildi. Lutfen 5 saniye bekleyin...
timeout /t 5 /nobreak >nul
echo.

:: --- 4. Frontend ---
echo [4/4] Frontend aciliyor...
cd frontend
start "" index.html
cd ..

echo.
echo ===================================================
echo   SISTEM HAZIR!
echo ===================================================
echo.
echo   ONEMLI:
echo   - Acilan siyah server penceresini KAPATMAYIN
echo   - Backend: http://127.0.0.1:5000
echo   - Frontend: Tarayicida acilacak
echo.
echo   Giris Bilgileri:
echo   - Email: test@test.com
echo   - Sifre: 1234
echo.
echo ===================================================
pause
