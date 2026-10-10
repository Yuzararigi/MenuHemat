#!/bin/bash
# MenuHemat — peluncur macOS (double-click file ini untuk jalan)
cd "$(dirname "$0")"

echo "==============================="
echo " MenuHemat - sekali klik jalan"
echo "==============================="
echo

# 1. Cek python3
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 belum terinstal di Mac ini."
  echo "Instal dulu dari https://www.python.org/downloads/"
  echo "lalu double-click file ini lagi."
  read -p "Tekan Enter untuk menutup... " dummy
  exit 1
fi

# 1. Bangun database bila belum ada (penting untuk clone baru)
if [ ! -f "menuhemat.db" ]; then
  echo "[1/4] Database belum ada, membangun dari nol..."
  python3 init_db.py
fi

# 2. Cek Flask
echo "[2/4] Memeriksa Flask..."
if ! python3 -c "import flask" 2>/dev/null; then
  echo "      Flask belum ada, menginstal..."
  python3 -m pip install flask
fi

# 3. Ambil harga pasar terbaru (gagal = pakai data bawaan, tidak masalah)
echo "[3/4] Mengambil harga pasar terbaru..."
python3 fetch_harga.py || echo "      (lanjut pakai data bawaan)"

# 4. Jalankan server + buka browser
echo "[4/4] Menjalankan server..."
(sleep 2 && open "http://127.0.0.1:5000") &
python3 app.py

echo
echo "Server berhenti."
read -p "Tekan Enter untuk menutup... " dummy
