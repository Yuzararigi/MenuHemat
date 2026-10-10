@echo off
title MenuHemat
cd /d "%~dp0"
echo ===============================
echo  MenuHemat - sekali klik jalan
echo ===============================
echo.

echo [1/4] Memeriksa database...
if not exist menuhemat.db (
  echo       Database belum ada, membangun dari nol...
  python init_db.py
)

echo [2/4] Memeriksa Flask...
python -c "import flask" 2>nul
if errorlevel 1 (
  echo       Flask belum ada, menginstal...
  pip install flask
)

echo [3/4] Mengambil harga pasar terbaru...
python fetch_harga.py

echo [4/4] Menjalankan server...
start http://127.0.0.1:5000
python app.py

echo.
echo Server berhenti. Tekan tombol apa saja untuk menutup.
pause >nul
