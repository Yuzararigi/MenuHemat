#!/usr/bin/env python3
"""
ekspansi_resep.py — ekspansi katalog MenuHemat dari 15 menjadi 100 resep.

Yang dilakukan (semua IDEMPOTEN, aman dijalankan berulang):
  1. Migrasi: tambah kolom `asal` dan `tag` di tabel resep bila belum ada.
  2. Tambah bahan baru (+ data gizi + konversi satuan) bila nama belum ada.
  3. Isi kolom asal/tag untuk 15 resep lama (id tidak berubah).
  4. Sisipkan 85 resep baru dari resep_baru.py (lewati bila nama sudah ada).

Jalankan SETELAH init_db.py pada database baru:
    python init_db.py && python fetch_harga.py && python ekspansi_resep.py
"""
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "menuhemat.db")

# ---------------------------------------------------------------- bahan baru
# (nama, kategori, komoditas_id, harga_manual_rp, satuan_manual,
#  isi_satuan_manual, satuan_dasar, alergen, (kalori, protein, karbo, lemak, serat, natrium))
# Harga manual = estimasi harga pasar per satuan jual; gizi per 100 g/ml (estimasi TKPI).
BAHAN_BARU = [
    # protein hewani
    ("Daging sapi", "protein_hewani", 9, None, None, None, "g", None, (207, 18.8, 0, 14, 0, 66)),
    ("Ikan kembung", "protein_hewani", None, 30000, "kg", 1000, "g", "ikan", (112, 21.3, 0, 2.4, 0, 65)),
    ("Ikan tongkol", "protein_hewani", None, 28000, "kg", 1000, "g", "ikan", (117, 24, 0, 1.6, 0, 59)),
    ("Ikan cakalang", "protein_hewani", None, 32000, "kg", 1000, "g", "ikan", (110, 24.2, 0, 1.0, 0, 60)),
    ("Ikan patin", "protein_hewani", None, 35000, "kg", 1000, "g", "ikan", (132, 17, 0, 6.6, 0, 60)),
    ("Ikan gabus", "protein_hewani", None, 45000, "kg", 1000, "g", "ikan", (80, 18.5, 0, 1.5, 0, 65)),
    ("Ikan teri kering", "protein_hewani", None, 70000, "kg", 1000, "g", "ikan", (258, 37, 0, 10, 0, 2500)),
    ("Ikan asin", "protein_hewani", None, 40000, "kg", 1000, "g", "ikan", (190, 30, 0, 7, 0, 3500)),
    ("Udang", "protein_hewani", None, 65000, "kg", 1000, "g", "seafood", (91, 21, 0.2, 0.5, 0, 180)),
    # lemak / cairan / olahan
    ("Santan", "lainnya", None, 7000, "bungkus", 200, "ml", None, (230, 2.3, 5.3, 23.6, 0.5, 15)),
    ("Kelapa parut", "lainnya", None, 10000, "buah", 300, "g", None, (354, 3.3, 15.2, 33.5, 9, 20)),
    ("Susu cair", "lainnya", None, 19000, "liter", 1000, "ml", "susu", (61, 3.2, 4.8, 3.1, 0, 43)),
    ("Keju cheddar", "lainnya", None, 16000, "pack", 165, "g", "susu", (416, 25, 1.3, 33, 0, 621)),
    ("Margarin", "minyak", None, 9000, "pack", 200, "g", None, (720, 0.6, 0.7, 80, 0, 750)),
    ("Mayones", "bumbu", None, 13000, "botol", 300, "ml", "telur", (680, 1, 0.6, 75, 0, 635)),
    ("Saus tomat", "bumbu", None, 9000, "botol", 340, "ml", None, (97, 1.2, 25, 0.3, 1.5, 900)),
    ("Kecap asin", "bumbu", None, 10000, "botol", 600, "ml", None, (60, 5.7, 8, 0.1, 0.8, 5500)),
    ("Saus tiram", "bumbu", None, 11000, "botol", 270, "ml", "seafood", (51, 1.3, 11, 0.2, 0.3, 2700)),
    ("Minyak wijen", "minyak", None, 16000, "botol", 100, "ml", None, (884, 0, 0, 100, 0, 0)),
    ("Cuka", "bumbu", None, 6000, "botol", 300, "ml", None, (18, 0, 0.4, 0, 0, 5)),
    # sayur
    ("Bayam", "sayur", None, 3000, "ikat", 200, "g", None, (23, 2.9, 3.6, 0.4, 2.2, 79)),
    ("Sawi hijau", "sayur", None, 4000, "ikat", 250, "g", None, (20, 1.8, 3.4, 0.2, 1.8, 60)),
    ("Tauge", "sayur", None, 10000, "kg", 1000, "g", None, (30, 3.2, 5.9, 0.2, 1.8, 6)),
    ("Daun singkong", "sayur", None, 3000, "ikat", 250, "g", None, (73, 6.8, 8.5, 1.1, 2.4, 30)),
    ("Brokoli", "sayur", None, 24000, "kg", 1000, "g", None, (34, 2.8, 6.6, 0.4, 2.6, 33)),
    ("Jamur tiram", "sayur", None, 16000, "kg", 1000, "g", None, (33, 3.3, 6, 0.4, 2.3, 18)),
    ("Terong", "sayur", None, 9000, "kg", 1000, "g", None, (25, 1, 6, 0.2, 3, 2)),
    ("Oyong", "sayur", None, 10000, "kg", 1000, "g", None, (19, 0.9, 4.2, 0.2, 1.4, 4)),
    ("Labu kuning", "sayur", None, 9000, "kg", 1000, "g", None, (26, 1, 6.5, 0.1, 0.5, 1)),
    ("Nangka muda", "sayur", None, 9000, "kg", 1000, "g", None, (51, 2, 11.5, 0.4, 2.5, 3)),
    ("Timun", "sayur", None, 8000, "kg", 1000, "g", None, (15, 0.7, 3.6, 0.1, 0.5, 2)),
    ("Selada", "sayur", None, 15000, "kg", 1000, "g", None, (15, 1.4, 2.9, 0.2, 1.3, 28)),
    ("Daun kelor", "sayur", None, 3000, "ikat", 100, "g", None, (64, 9.4, 8.3, 1.4, 2, 9)),
    ("Daun pepaya", "sayur", None, 3000, "ikat", 200, "g", None, (60, 5, 8, 1, 3, 10)),
    ("Kelakai", "sayur", None, 5000, "ikat", 200, "g", None, (25, 2.5, 4, 0.3, 2.5, 10)),
    # karbo
    ("Bihun", "karbo", None, 5000, "bungkus", 200, "g", None, (357, 6.5, 80, 0.8, 1.2, 200)),
    ("Kwetiau", "karbo", None, 8000, "bungkus", 400, "g", None, (175, 3.5, 38, 0.5, 1, 250)),
    ("Spaghetti", "karbo", None, 13000, "bungkus", 225, "g", "gluten", (371, 13, 75, 1.5, 3, 6)),
    ("Oat", "karbo", None, 16000, "bungkus", 200, "g", None, (380, 13, 67, 6.5, 10, 2)),
    ("Tepung tapioka", "karbo", None, 11000, "kg", 1000, "g", None, (358, 0.5, 89, 0.3, 0.9, 3)),
    ("Tepung beras", "karbo", None, 13000, "kg", 1000, "g", None, (366, 6, 80, 1.4, 2.4, 2)),
    ("Sagu", "karbo", None, 12000, "kg", 1000, "g", None, (355, 0.2, 88, 0.2, 0.5, 3)),
    ("Ubi jalar", "karbo", None, 9000, "kg", 1000, "g", None, (86, 1.6, 20, 0.1, 3, 55)),
    ("Singkong", "karbo", None, 6000, "kg", 1000, "g", None, (160, 1.4, 38, 0.3, 1.8, 14)),
    ("Roti tawar", "karbo", None, 15000, "pack", 370, "g", "gluten", (265, 9, 49, 3.2, 2.7, 490)),
    ("Roti burger", "karbo", None, 12000, "pack", 240, "g", "gluten", (270, 8, 47, 4, 2, 450)),
    # bumbu & buah
    ("Bawang bombay", "bumbu", None, 32000, "kg", 1000, "g", None, (40, 1.1, 9.3, 0.1, 1.7, 4)),
    ("Kacang tanah", "protein_nabati", None, 26000, "kg", 1000, "g", None, (567, 26, 16, 49, 8.5, 18)),
    ("Kacang hijau", "protein_nabati", None, 24000, "kg", 1000, "g", None, (347, 24, 63, 1.2, 16, 15)),
    ("Kacang merah", "protein_nabati", None, 28000, "kg", 1000, "g", None, (336, 22, 60, 1.4, 15, 12)),
    ("Kluwek", "bumbu", None, 25000, "kg", 1000, "g", None, (320, 8, 12, 28, 4, 10)),
    ("Daun pandan", "bumbu", None, 2000, "ikat", 20, "g", None, (50, 1, 10, 0.5, 2, 5)),
    ("Kemangi", "bumbu", None, 3000, "ikat", 50, "g", None, (23, 3.2, 2.7, 0.6, 1.6, 4)),
    ("Daun pisang", "bumbu", None, 3000, "pack", 100, "g", None, (0, 0, 0, 0, 0, 0)),
    ("Pala bubuk", "bumbu", None, 6000, "sachet", 10, "g", None, (525, 6, 49, 36, 21, 16)),
    ("Pisang kepok", "lainnya", None, 15000, "sisir", 800, "g", None, (89, 1.1, 23, 0.3, 2.6, 1)),
    ("Kencur", "bumbu", None, 25000, "kg", 1000, "g", None, (65, 2, 13, 0.5, 2, 8)),
    ("Kemiri", "bumbu", None, 30000, "kg", 1000, "g", None, (636, 5.8, 13, 63, 3.3, 2)),
]

# (nama_bahan, dari_satuan, ke_satuan, faktor)
KONVERSI_BARU = [
    ("Bayam", "ikat", "g", 200), ("Sawi hijau", "ikat", "g", 250),
    ("Daun singkong", "ikat", "g", 250), ("Kemangi", "ikat", "g", 50),
    ("Daun kelor", "ikat", "g", 100), ("Daun pepaya", "ikat", "g", 200),
    ("Kelakai", "ikat", "g", 200), ("Daun pandan", "ikat", "g", 20),
    ("Daun pisang", "lembar", "g", 25), ("Pisang kepok", "buah", "g", 100),
    ("Bawang bombay", "buah", "g", 150), ("Santan", "bungkus", "ml", 200),
    ("Bihun", "bungkus", "g", 200), ("Kwetiau", "bungkus", "g", 400),
    ("Spaghetti", "bungkus", "g", 225), ("Oat", "bungkus", "g", 200),
    ("Cabai merah keriting", "buah", "g", 8),
]

# 15 resep lama: id -> (asal, tag awal; tag final disesuaikan hasil validasi gizi)
RESEP_LAMA = {
    1: ("Jawa", ""), 2: ("Sunda", ""), 3: ("Jawa", ""), 4: ("Sunda", ""),
    5: ("Jawa", ""), 6: ("Jawa", ""), 7: ("Sumatera", ""), 8: ("Jawa", ""),
    9: ("Nusantara", ""), 10: ("Jawa", ""), 11: ("Nusantara", ""),
    12: ("Asia", "diet"), 13: ("Jawa", ""), 14: ("Nusantara", ""),
    15: ("Nusantara", ""),
}


def migrasi(con):
    kolom = {r[1] for r in con.execute("PRAGMA table_info(resep)")}
    if "asal" not in kolom:
        con.execute("ALTER TABLE resep ADD COLUMN asal TEXT")
    if "tag" not in kolom:
        con.execute("ALTER TABLE resep ADD COLUMN tag TEXT")


def tambah_bahan(con):
    baru = 0
    for (nama, kat, kom, harga, sat, isi, dasar, alergen, gizi) in BAHAN_BARU:
        cur = con.execute(
            "INSERT OR IGNORE INTO bahan (nama, kategori, komoditas_id,"
            " harga_manual_rp, satuan_manual, isi_satuan_manual, satuan_dasar,"
            " alergen, nonhalal) VALUES (?,?,?,?,?,?,?,?,0)",
            (nama, kat, kom, harga, sat, isi, dasar, alergen))
        if cur.rowcount:
            baru += 1
        bid = con.execute("SELECT id FROM bahan WHERE nama = ?", (nama,)).fetchone()[0]
        con.execute(
            "INSERT OR IGNORE INTO gizi_bahan (bahan_id, kalori, protein,"
            " karbo, lemak, serat, natrium) VALUES (?,?,?,?,?,?,?)",
            (bid,) + gizi)
    for (nama, dari, ke, faktor) in KONVERSI_BARU:
        bid = con.execute("SELECT id FROM bahan WHERE nama = ?", (nama,)).fetchone()[0]
        sudah = con.execute(
            "SELECT 1 FROM konversi_satuan WHERE bahan_id = ? AND"
            " dari_satuan = ? AND ke_satuan = ?", (bid, dari, ke)).fetchone()
        if not sudah:
            con.execute(
                "INSERT INTO konversi_satuan (bahan_id, dari_satuan,"
                " ke_satuan, faktor) VALUES (?,?,?,?)", (bid, dari, ke, faktor))
    return baru


def isi_resep_lama(con):
    for rid, (asal, tag) in RESEP_LAMA.items():
        con.execute("UPDATE resep SET asal = ?, tag = ? WHERE id = ?",
                    (asal, tag, rid))


def tambah_resep(con):
    sys.path.insert(0, BASE)
    from resep_baru import RECIPES
    bahan_id = {r[1]: r[0] for r in con.execute("SELECT id, nama FROM bahan")}
    tidak_dikenal = set()
    for r in RECIPES:
        for (nama_b, *_rest) in r["bahan"]:
            if nama_b not in bahan_id:
                tidak_dikenal.add(nama_b)
    if tidak_dikenal:
        raise SystemExit("BAHAN TIDAK DIKENAL: " + ", ".join(sorted(tidak_dikenal)))
    baru = 0
    for r in RECIPES:
        ada = con.execute("SELECT id FROM resep WHERE nama = ?", (r["nama"],)).fetchone()
        if ada:
            continue
        cur = con.execute(
            "INSERT INTO resep (nama, deskripsi, kategori, porsi,"
            " waktu_masak_menit, tingkat, tags, langkah, asal, tag)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (r["nama"], r.get("deskripsi"), r["kategori"], r.get("porsi", 4),
             r.get("waktu"), r.get("tingkat", "mudah"), r.get("tags_rasa"),
             "\n".join(r["langkah"]), r.get("asal"), r.get("tag") or None))
        rid = cur.lastrowid
        for (nama_b, jumlah, satuan, opsional) in r["bahan"]:
            con.execute(
                "INSERT INTO resep_bahan (resep_id, bahan_id, jumlah, satuan,"
                " opsional) VALUES (?,?,?,?,?)",
                (rid, bahan_id[nama_b], jumlah, satuan, opsional))
        baru += 1
    return baru


# Penyesuaian tag final berdasarkan gizi TERHITUNG dari komposisi bahan
# (diet: <=400 kkal & serat >=2 g/porsi; gym: protein >=20 g/porsi).
# Hanya hidangan yang masuk akal secara kuliner yang ditag: gorengan dan
# camilan manis tidak ditag diet walau angkanya lolos, dst.
TAG_FINAL = {
    # resep lama
    "Nasi Goreng Jawa": "gym", "Tumis Kangkung Terasi": "diet",
    "Ayam Kecap": "gym", "Sayur Asem": "diet", "Soto Ayam": "diet,gym",
    "Sayur Sop": "diet", "Orek Tempe": "diet", "Tumis Buncis Tahu": "diet",
    "Semur Telur Kentang": "diet",
    # resep baru yang lolos kriteria di luar tag awalnya
    "Pepes Ayam Kemangi": "diet,gym", "Ayam Goreng Lengkuas": "gym",
    "Gulai Ikan Tongkol": "gym", "Mie Aceh": "gym",
    "Pempek Palembang": "gym", "Ikan Asam Padeh": "diet,gym",
    "Ayam Tangkap": "gym", "Ikan Sambal Matah": "gym",
    "Tum Ikan Tongkol": "diet,gym", "Sup Ikan Bali": "diet,gym",
    "Sop Konro": "gym", "Ikan Bakar Rica-Rica": "diet,gym",
    "Cakalang Fufu Rica": "gym", "Soto Banjar": "gym",
    "Ketupat Kandangan": "gym", "Pais Patin": "diet,gym",
    "Gangan Asam Patin": "diet,gym", "Sup Krim Ayam Jagung": "diet,gym",
    "Fish and Chips": "gym", "Bibimbap Hemat": "gym",
    "Kwetiau Goreng": "gym", "Pad Thai": "gym", "Kare Ayam Jepang": "gym",
    "Ikan Bakar Colo-Colo": "gym", "Ikan Kuah Pala Banda": "gym",
    "Ikan Kuah Asam Manado": "diet,gym", "Pancake Oat Pisang": "diet",
    "Jagung Bose": "diet",
}


def sesuaikan_tag(con):
    for nama, tag in TAG_FINAL.items():
        con.execute("UPDATE resep SET tag = ? WHERE nama = ?", (tag, nama))


def main():
    con = sqlite3.connect(DB)
    try:
        migrasi(con)
        n_bahan = tambah_bahan(con)
        isi_resep_lama(con)
        n_resep = tambah_resep(con)
        sesuaikan_tag(con)
        con.commit()
    finally:
        total_r = con.execute("SELECT COUNT(*) FROM resep").fetchone()[0]
        total_b = con.execute("SELECT COUNT(*) FROM bahan").fetchone()[0]
        con.close()
    print(f"OK: +{n_bahan} bahan baru, +{n_resep} resep baru. "
          f"Total sekarang: {total_r} resep, {total_b} bahan.")


if __name__ == "__main__":
    main()
