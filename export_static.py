#!/usr/bin/env python3
"""Ekspor data menuhemat.db menjadi docs/data.js untuk situs statis GitHub Pages.
Harga yang dipakai: 2026-10-09 (PIHPS). Harga per wilayah yang tidak lengkap
dilengkapi dari NASIONAL per komoditas.
"""
import sqlite3, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
con = sqlite3.connect(os.path.join(BASE, "menuhemat.db"))
con.row_factory = sqlite3.Row

TGL = "2026-10-09"

def rows(q, p=()):
    return [dict(r) for r in con.execute(q, p)]

# --- wilayah: NASIONAL dulu, sisanya alfabetis ---
wilayah = [r["wilayah"] for r in con.execute(
    "SELECT DISTINCT wilayah FROM harga_harian WHERE tanggal=? ORDER BY wilayah", (TGL,))]
wilayah = sorted(wilayah, key=lambda w: (w != "NASIONAL", w))

# --- harga per wilayah, dilengkapi dari NASIONAL per komoditas ---
nas = {r["komoditas_id"]: r["harga_rp"] for r in con.execute(
    "SELECT komoditas_id, harga_rp FROM harga_harian WHERE tanggal=? AND wilayah='NASIONAL'", (TGL,))}
prices = {}
for w in wilayah:
    p = dict(nas)
    for r in con.execute(
        "SELECT komoditas_id, harga_rp FROM harga_harian WHERE tanggal=? AND wilayah=?", (TGL, w)):
        p[r["komoditas_id"]] = r["harga_rp"]
    prices[w] = p

komoditas = rows("SELECT id, nama_pihps AS nama, satuan_harga AS satuan, kategori FROM komoditas ORDER BY id")
bahan = rows("""SELECT id, nama, kategori, komoditas_id, harga_manual_rp, satuan_manual,
                isi_satuan_manual, satuan_dasar, alergen FROM bahan ORDER BY nama""")
konv = rows("SELECT bahan_id, dari_satuan, ke_satuan, faktor FROM konversi_satuan")
gizi = {r["bahan_id"]: [r["kalori"], r["protein"], r["karbo"], r["lemak"], r["serat"], r["natrium"]]
        for r in con.execute("SELECT * FROM gizi_bahan")}
resep_rows = rows("""SELECT id, nama, deskripsi, kategori, porsi, waktu_masak_menit AS waktu,
                     tingkat, tags, langkah, asal, tag FROM resep ORDER BY id""")
resep = []
for r in resep_rows:
    langkah = [s.strip() for s in (r["langkah"] or "").split("\n") if s.strip()]
    # buang penomoran "1. " di depan bila ada
    bersih = []
    for s in langkah:
        if len(s) > 2 and s[0].isdigit() and s[1] in ".)":
            s = s[2:].strip()
        bersih.append(s)
    r["langkah"] = bersih
    resep.append(r)
resep_bahan = [[r["resep_id"], r["bahan_id"], r["jumlah"], r["satuan"], r["opsional"]]
               for r in rows("SELECT resep_id, bahan_id, jumlah, satuan, opsional FROM resep_bahan")]

data = {
    "meta": {
        "tanggal": TGL,
        "tanggalLabel": "9 Okt 2026",
        "sumber": "PIHPS Nasional \u00b7 Bank Indonesia",
        "banner": "Snapshot statis \u2014 data harga per 9 Okt 2026. Versi live dengan harga harian ada di aplikasi penuh.",
    },
    "wilayah": wilayah,
    "komoditas": komoditas,
    "prices": prices,
    "bahan": bahan,
    "konversi": [[c["bahan_id"], c["dari_satuan"], c["ke_satuan"], c["faktor"]] for c in konv],
    "gizi": gizi,
    "resep": resep,
    "resep_bahan": resep_bahan,
}

os.makedirs(os.path.join(BASE, "docs"), exist_ok=True)
out = os.path.join(BASE, "docs", "data.js")
with open(out, "w", encoding="utf-8") as f:
    f.write("// Data MenuHemat — dibuat otomatis dari menuhemat.db (jangan edit manual).\n")
    f.write("// Harga: PIHPS Bank Indonesia, 2026-10-09.\n")
    f.write("const DB = ")
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")

n_resep = len(resep); n_bahan = len(bahan); n_wil = len(wilayah)
print(f"OK -> {out} ({n_resep} resep, {n_bahan} bahan, {n_wil} wilayah)")
# validasi cepat: tiap resep punya bahan & tiap bahan gizi terisi
tanpa_gizi = [b["nama"] for b in bahan if b["id"] not in gizi]
if tanpa_gizi:
    print("PERINGATAN: bahan tanpa data gizi:", tanpa_gizi)
