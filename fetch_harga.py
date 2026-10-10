#!/usr/bin/env python3
"""
fetch_harga.py — mengambil harga pangan harian dari PIHPS Bank Indonesia
(https://www.bi.go.id/hargapangan) lalu menyimpannya ke tabel harga_harian.

Cara pakai:
    python fetch_harga.py

Cara kerja:
  1. Mengambil daftar komoditas dari endpoint GetCommoditiesTree.
  2. Untuk tiap komoditas, memanggil GetGridData1 (endpoint yang dipakai
     halaman web PIHPS sendiri untuk mengisi tabel harga) dengan tipe
     harga pasar tradisional (eceran).
  3. Menyimpan harga per provinsi + rata-rata nasional (wilayah='NASIONAL')
     dengan sumber='PIHPS' (INSERT OR REPLACE — menimpa data SAMPLE
     pada tanggal yang sama).

Catatan jujur:
  - Endpoint ini TIDAK didokumentasikan resmi oleh BI; ditemukan dengan
    membaca JavaScript halaman web PIHPS pada 2026-10-10. Jika suatu hari
    gagal, kemungkinan BI mengubah struktur situsnya — lihat README
    bagian "Data harga".
  - PIHPS tidak memperbarui data pada akhir pekan/hari libur; server
    otomatis mengembalikan tanggal terakhir yang tersedia.
  - Dibutuhkan koneksi internet. Jika gagal, aplikasi tetap jalan
    memakai data SAMPLE bawaan init_db.py.
"""
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://www.bi.go.id/hargapangan/WebSite/Home"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MenuHemat/1.0"}
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menuhemat.db")

BULAN_ID = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Mei": 5, "Jun": 6,
            "Jul": 7, "Agu": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Des": 12}


def http_get(url, params=None, timeout=25, retries=3):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001 - jaringan memang flaky
            last_err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Gagal mengambil {url}: {last_err}")


def parse_tanggal(s):
    # "09 Okt 26" -> "2026-10-09"
    parts = s.strip().split()
    d, m, y = int(parts[0]), BULAN_ID[parts[1]], int(parts[2])
    y += 2000 if y < 100 else 0
    return f"{y:04d}-{m:02d}-{d:02d}"


def main():
    if not os.path.exists(DB):
        print(f"Database {DB} tidak ada. Jalankan dulu: python init_db.py")
        sys.exit(1)

    print("Mengambil daftar komoditas PIHPS ...")
    tree = json.loads(http_get(BASE + "/GetCommoditiesTree"))["data"]
    komoditas = [(t["TreeID"], t["TreeName"].strip())
                 for t in tree if t["ParentID"] is not None]
    print(f"  {len(komoditas)} komoditas ditemukan.")

    con = sqlite3.connect(DB)
    nama_ke_id = {r[0].strip(): r[1]
                  for r in con.execute("SELECT nama_pihps, id FROM komoditas")}
    hilang = [nama for _, nama in komoditas if nama not in nama_ke_id]
    if hilang:
        print("  PERINGATAN: komoditas berikut tidak ada di database, dilewati:")
        for h in hilang:
            print("   -", h)

    today = date.today()
    # format tanggal seperti yang dikirim halaman web PIHPS, mis. "Oct 10, 2026"
    tgl_param = today.strftime("%b %d, %Y")

    total = 0
    gagal = []
    for tree_id, nama in komoditas:
        if nama not in nama_ke_id:
            continue
        kid = nama_ke_id[nama]
        params = {"tanggal": tgl_param, "commodity": tree_id, "priceType": 1,
                  "isPasokan": 0, "jenis": 1, "periode": 1, "provId": 0}
        try:
            data = json.loads(http_get(BASE + "/GetGridData1", params))["data"]
        except Exception as e:  # noqa: BLE001
            gagal.append((nama, str(e)))
            continue
        if not data:
            gagal.append((nama, "data kosong"))
            continue
        tgl = parse_tanggal(data[0]["Tanggal"])
        rows = []
        for r in data:
            wil = r["Provinsi"].strip().upper()
            rows.append((kid, tgl, wil, float(r["Nilai"]), "PIHPS"))
        # rata-rata nasional dari kolom SemuaProvinsi
        rows.append((kid, tgl, "NASIONAL", float(data[0]["SemuaProvinsi"]), "PIHPS"))
        con.executemany(
            """INSERT OR REPLACE INTO harga_harian
               (komoditas_id, tanggal, wilayah, harga_rp, sumber)
               VALUES (?,?,?,?,?)""",
            rows)
        total += len(rows)
        print(f"  OK {nama}: {len(data)} provinsi, tgl {tgl}")
        time.sleep(0.7)  # sopan ke server BI

    con.commit()
    con.close()
    print(f"\nSelesai: {total} baris harga disimpan (sumber=PIHPS).")
    if gagal:
        print(f"{len(gagal)} komoditas gagal:")
        for n, e in gagal:
            print(f"  - {n}: {e}")
        print("Data SAMPLE lama tetap dipakai untuk yang gagal.")


if __name__ == "__main__":
    main()
