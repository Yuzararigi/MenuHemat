#!/usr/bin/env python3
"""
init_db.py — membangun database MenuHemat v2 dari nol.

Menjalankan:
    python init_db.py

Isi:
  - tabel inti v1 (komoditas, harga_harian, bahan, konversi_satuan,
    resep + kolom langkah, resep_bahan, users + kolom akun,
    user_favorit_resep, user_pantangan, rencana + kolom user_id)
  - tabel gizi_bahan (kandungan gizi per 100 g/ml bahan — ESTIMASI)
  - 21 komoditas PIHPS, 36 bahan (+data gizi), 15 resep Indonesia
    (+langkah memasak), data harga CONTOH 2 hari (sumber='SAMPLE')
  - akun: admin/admin123 (role admin), user/user123 (role user)
    -> SEGERA GANTI setelah login pertama (lihat README).

Setelah ini jalankan: python fetch_harga.py (data asli PIHPS).
"""
import os
import sqlite3

try:
    from werkzeug.security import generate_password_hash
except ImportError:  # fallback darurat bila werkzeug belum ada
    import hashlib

    def generate_password_hash(pw):
        return "sha256$" + hashlib.sha256(pw.encode()).hexdigest()

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menuhemat.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS gizi_bahan;
DROP TABLE IF EXISTS rencana;
DROP TABLE IF EXISTS user_pantangan;
DROP TABLE IF EXISTS user_favorit_resep;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS resep_bahan;
DROP TABLE IF EXISTS resep;
DROP TABLE IF EXISTS konversi_satuan;
DROP TABLE IF EXISTS bahan;
DROP TABLE IF EXISTS harga_harian;
DROP TABLE IF EXISTS komoditas;

CREATE TABLE komoditas (
  id            INTEGER PRIMARY KEY,
  kode          TEXT UNIQUE NOT NULL,
  nama_pihps    TEXT NOT NULL,
  satuan_harga  TEXT NOT NULL DEFAULT 'kg',
  kategori      TEXT
);

CREATE TABLE harga_harian (
  id            INTEGER PRIMARY KEY,
  komoditas_id  INTEGER NOT NULL REFERENCES komoditas(id),
  tanggal       DATE NOT NULL,
  wilayah       TEXT NOT NULL DEFAULT 'NASIONAL',
  harga_rp      REAL NOT NULL,
  sumber        TEXT NOT NULL DEFAULT 'PIHPS',
  UNIQUE (komoditas_id, tanggal, wilayah)
);
CREATE INDEX idx_harga_cari ON harga_harian (komoditas_id, wilayah, tanggal DESC);

CREATE TABLE bahan (
  id                  INTEGER PRIMARY KEY,
  nama                TEXT UNIQUE NOT NULL,
  kategori            TEXT,
  komoditas_id        INTEGER REFERENCES komoditas(id),
  harga_manual_rp     REAL,
  satuan_manual       TEXT,
  isi_satuan_manual   REAL,
  satuan_dasar        TEXT NOT NULL,
  alergen             TEXT,
  nonhalal            INTEGER DEFAULT 0
);

-- Kandungan gizi per 100 g (atau 100 ml bila satuan_dasar='ml').
-- SEMUA angka adalah ESTIMASI dari tabel komposisi pangan.
CREATE TABLE gizi_bahan (
  bahan_id    INTEGER PRIMARY KEY REFERENCES bahan(id),
  kalori      REAL,   -- kkal
  protein     REAL,   -- g
  karbo       REAL,   -- g
  lemak       REAL,   -- g
  serat       REAL,   -- g
  natrium     REAL    -- mg
);

CREATE TABLE konversi_satuan (
  id            INTEGER PRIMARY KEY,
  bahan_id      INTEGER REFERENCES bahan(id),
  dari_satuan   TEXT NOT NULL,
  ke_satuan     TEXT NOT NULL,
  faktor        REAL NOT NULL
);

CREATE TABLE resep (
  id                INTEGER PRIMARY KEY,
  nama              TEXT NOT NULL,
  deskripsi         TEXT,
  kategori          TEXT,
  porsi             INTEGER NOT NULL DEFAULT 4,
  waktu_masak_menit INTEGER,
  tingkat           TEXT DEFAULT 'mudah',
  tags              TEXT,
  cocok_diet        TEXT,
  langkah           TEXT,   -- langkah memasak, satu langkah per baris
  created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE resep_bahan (
  resep_id  INTEGER NOT NULL REFERENCES resep(id),
  bahan_id  INTEGER NOT NULL REFERENCES bahan(id),
  jumlah    REAL NOT NULL,
  satuan    TEXT NOT NULL,
  opsional  INTEGER DEFAULT 0,
  catatan   TEXT,
  PRIMARY KEY (resep_id, bahan_id)
);

CREATE TABLE users (
  id                INTEGER PRIMARY KEY,
  username          TEXT UNIQUE,
  password_hash     TEXT,
  role              TEXT DEFAULT 'user',   -- 'admin' / 'user'
  nama              TEXT,
  wilayah           TEXT DEFAULT 'NASIONAL',
  budget_harian_rp  REAL
);

CREATE TABLE user_favorit_resep (
  user_id   INTEGER REFERENCES users(id),
  resep_id  INTEGER REFERENCES resep(id),
  PRIMARY KEY (user_id, resep_id)
);

CREATE TABLE user_pantangan (
  user_id   INTEGER REFERENCES users(id),
  bahan_id  INTEGER REFERENCES bahan(id),
  alasan    TEXT,
  PRIMARY KEY (user_id, bahan_id)
);

CREATE TABLE rencana (
  id        INTEGER PRIMARY KEY,
  user_id   INTEGER REFERENCES users(id),
  hari      TEXT NOT NULL,
  resep_id  INTEGER REFERENCES resep(id),
  UNIQUE (user_id, hari)
);
"""

# (tree_id_pihps, kode, nama_pihps, kategori)
KOMODITAS = [
    ("1_1",  "beras_bawah1",   "Beras Kualitas Bawah I",          "beras"),
    ("1_2",  "beras_bawah2",   "Beras Kualitas Bawah II",         "beras"),
    ("1_3",  "beras_medium1",  "Beras Kualitas Medium I",         "beras"),
    ("1_4",  "beras_medium2",  "Beras Kualitas Medium II",        "beras"),
    ("1_5",  "beras_super1",   "Beras Kualitas Super I",          "beras"),
    ("1_6",  "beras_super2",   "Beras Kualitas Super II",         "beras"),
    ("2_7",  "ayam_ras",       "Daging Ayam Ras Segar",           "protein"),
    ("3_8",  "sapi_k1",        "Daging Sapi Kualitas 1",          "protein"),
    ("3_9",  "sapi_k2",        "Daging Sapi Kualitas 2",          "protein"),
    ("4_10", "telur",          "Telur Ayam Ras Segar",            "protein"),
    ("5_11", "bamer",          "Bawang Merah Ukuran Sedang",      "bumbu"),
    ("6_12", "baput",          "Bawang Putih Ukuran Sedang",      "bumbu"),
    ("7_13", "cabe_besar",     "Cabai Merah Besar",               "cabai"),
    ("7_14", "cabe_keriting",  "Cabai Merah Keriting",            "cabai"),
    ("8_15", "rawit_hijau",    "Cabai Rawit Hijau",               "cabai"),
    ("8_16", "rawit_merah",    "Cabai Rawit Merah",               "cabai"),
    ("9_17", "migor_curah",    "Minyak Goreng Curah",             "minyak"),
    ("9_18", "migor_kemasan1", "Minyak Goreng Kemasan Bermerk 1", "minyak"),
    ("9_19", "migor_kemasan2", "Minyak Goreng Kemasan Bermerk 2", "minyak"),
    ("10_20", "gula_premium",  "Gula Pasir Kualitas Premium",     "gula"),
    ("10_21", "gula_lokal",    "Gula Pasir Lokal",                "gula"),
]

# (nama, kategori, kode_komoditas|None, harga_manual, satuan_manual,
#  isi_satuan_manual, satuan_dasar, alergen)
BAHAN = [
    ("Beras",              "karbo",          "beras_medium1",  None,  None,      None, "g",  None),
    ("Cabai rawit merah",  "cabai",          "rawit_merah",    None,  None,      None, "g",  None),
    ("Cabai merah keriting","cabai",         "cabe_keriting",  None,  None,      None, "g",  None),
    ("Bawang merah",       "bumbu",          "bamer",          None,  None,      None, "g",  None),
    ("Bawang putih",       "bumbu",          "baput",          None,  None,      None, "g",  None),
    ("Telur ayam",         "protein_hewani", "telur",          None,  None,      None, "g",  "telur"),
    ("Daging ayam",        "protein_hewani", "ayam_ras",       None,  None,      None, "g",  None),
    ("Minyak goreng",      "minyak",         "migor_kemasan1", None,  None,      None, "ml", None),
    ("Gula pasir",         "lainnya",        "gula_lokal",     None,  None,      None, "g",  None),
    ("Garam",              "bumbu",          None, 5000,  "bungkus", 500,  "g",  None),
    ("Kecap manis",        "bumbu",          None, 18000, "botol",   600,  "ml", None),
    ("Kangkung",           "sayur",          None, 5000,  "ikat",    250,  "g",  None),
    ("Terasi",             "bumbu",          None, 2500,  "sachet",  20,   "g",  "seafood"),
    ("Tahu",               "protein_nabati", None, 5000,  "bungkus", 500,  "g",  None),
    ("Tempe",              "protein_nabati", None, 5000,  "papan",   400,  "g",  None),
    ("Wortel",             "sayur",          None, 12000, "kg",      1000, "g",  None),
    ("Kol",                "sayur",          None, 10000, "kg",      1000, "g",  None),
    ("Buncis",             "sayur",          None, 14000, "kg",      1000, "g",  None),
    ("Kentang",            "karbo",          None, 16000, "kg",      1000, "g",  None),
    ("Tomat",              "sayur",          None, 12000, "kg",      1000, "g",  None),
    ("Labu siam",          "sayur",          None, 4000,  "buah",    300,  "g",  None),
    ("Jagung manis",       "karbo",          None, 5000,  "tongkol", 250,  "g",  None),
    ("Kacang panjang",     "sayur",          None, 10000, "ikat",    250,  "g",  None),
    ("Asam jawa",          "bumbu",          None, 3000,  "bungkus", 50,   "g",  None),
    ("Gula merah",         "lainnya",        None, 16000, "kg",      1000, "g",  None),
    ("Tepung terigu",      "karbo",          None, 12000, "kg",      1000, "g",  "gluten"),
    ("Ketumbar bubuk",     "bumbu",          None, 4000,  "sachet",  15,   "g",  None),
    ("Kunyit",             "bumbu",          None, 8000,  "kg",      1000, "g",  None),
    ("Jahe",               "bumbu",          None, 30000, "kg",      1000, "g",  None),
    ("Lengkuas",           "bumbu",          None, 12000, "kg",      1000, "g",  None),
    ("Serai",              "bumbu",          None, 2000,  "batang",  20,   "g",  None),
    ("Daun salam",         "bumbu",          None, 2000,  "ikat",    20,   "g",  None),
    ("Daun jeruk",         "bumbu",          None, 2000,  "ikat",    15,   "g",  None),
    ("Merica bubuk",       "bumbu",          None, 8000,  "sachet",  25,   "g",  None),
    ("Mie telur",          "karbo",          None, 5000,  "bungkus", 200,  "g",  "telur,gluten"),
    ("Daun bawang",        "sayur",          None, 4000,  "ikat",    100,  "g",  None),
]

# Kandungan gizi per 100 g (atau 100 ml) — ESTIMASI dari tabel komposisi pangan.
# Format: nama -> (kalori kkal, protein g, karbo g, lemak g, serat g, natrium mg)
GIZI = {
    "Beras":              (360, 6.6, 78.9, 0.6, 0.8, 5),
    "Cabai rawit merah":  (40, 2.0, 9.5, 0.5, 2.5, 30),
    "Cabai merah keriting": (40, 1.9, 9.4, 0.4, 2.6, 28),
    "Bawang merah":       (40, 1.5, 9.3, 0.2, 1.2, 10),
    "Bawang putih":       (149, 6.4, 33.0, 0.5, 2.1, 17),
    "Telur ayam":         (155, 12.6, 1.1, 10.6, 0.0, 140),
    "Daging ayam":        (120, 22.0, 0.0, 3.0, 0.0, 70),
    "Minyak goreng":      (884, 0.0, 0.0, 100.0, 0.0, 0),
    "Gula pasir":         (387, 0.0, 100.0, 0.0, 0.0, 2),
    "Garam":              (0, 0.0, 0.0, 0.0, 0.0, 38700),
    "Kecap manis":        (130, 4.0, 28.0, 0.2, 0.5, 5500),
    "Kangkung":           (25, 2.5, 4.5, 0.3, 2.0, 60),
    "Terasi":             (150, 25.0, 10.0, 2.0, 0.0, 4000),
    "Tahu":               (80, 8.0, 2.0, 4.5, 0.5, 10),
    "Tempe":              (190, 18.0, 9.0, 10.0, 3.0, 10),
    "Wortel":             (41, 0.9, 10.0, 0.2, 2.8, 70),
    "Kol":                (25, 1.3, 5.8, 0.1, 2.5, 18),
    "Buncis":             (31, 1.8, 7.0, 0.2, 2.7, 6),
    "Kentang":            (77, 2.0, 17.0, 0.1, 2.2, 6),
    "Tomat":              (18, 0.9, 3.9, 0.2, 1.2, 5),
    "Labu siam":          (19, 0.8, 4.5, 0.1, 1.7, 2),
    "Jagung manis":       (96, 3.4, 21.0, 1.5, 2.4, 15),
    "Kacang panjang":     (47, 2.8, 8.4, 0.2, 3.5, 4),
    "Asam jawa":          (240, 2.8, 62.0, 0.6, 5.0, 30),
    "Gula merah":         (380, 0.5, 95.0, 0.2, 0.0, 40),
    "Tepung terigu":      (364, 10.0, 76.0, 1.0, 2.7, 2),
    "Ketumbar bubuk":     (300, 12.0, 55.0, 17.0, 40.0, 35),
    "Kunyit":             (350, 9.7, 65.0, 10.0, 22.0, 40),
    "Jahe":               (80, 1.8, 17.8, 0.8, 2.0, 13),
    "Lengkuas":           (70, 1.5, 15.0, 0.6, 2.0, 10),
    "Serai":              (99, 1.8, 25.0, 0.5, 5.0, 6),
    "Daun salam":         (60, 2.0, 12.0, 1.0, 4.0, 20),
    "Daun jeruk":         (60, 2.0, 12.0, 1.0, 4.0, 20),
    "Merica bubuk":       (250, 10.0, 64.0, 3.0, 25.0, 20),
    "Mie telur":          (350, 12.0, 70.0, 2.0, 3.0, 500),
    "Daun bawang":        (32, 1.8, 7.3, 0.2, 2.6, 16),
}

# (bahan_nama|None=umum, dari, ke, faktor)
KONVERSI = [
    (None, "sdm", "ml", 15),
    (None, "sdt", "ml", 5),
    (None, "sdm", "g", 15),
    (None, "sdt", "g", 5),
    ("Telur ayam", "butir", "g", 60),
    ("Bawang merah", "siung", "g", 5),
    ("Bawang putih", "siung", "g", 4),
    ("Cabai rawit merah", "buah", "g", 3),
    ("Kangkung", "ikat", "g", 250),
    ("Tahu", "bungkus", "g", 500),
    ("Tempe", "papan", "g", 400),
    ("Wortel", "buah", "g", 100),
    ("Kentang", "buah", "g", 150),
    ("Tomat", "buah", "g", 100),
    ("Labu siam", "buah", "g", 300),
    ("Jagung manis", "tongkol", "g", 250),
    ("Kacang panjang", "ikat", "g", 250),
    ("Serai", "batang", "g", 20),
    ("Daun salam", "lembar", "g", 1),
    ("Daun salam", "ikat", "g", 20),
    ("Daun jeruk", "lembar", "g", 1),
    ("Daun jeruk", "ikat", "g", 15),
    ("Mie telur", "bungkus", "g", 200),
    ("Daun bawang", "ikat", "g", 100),
]

# (id, nama, deskripsi, kategori, porsi, menit, tingkat, tags)
RESEP = [
    (1, "Nasi Goreng Jawa", "Nasi goreng kampung dengan suwiran ayam dan telur.",
     "makan_malam", 4, 30, "mudah", "gurih,pedas_sedang"),
    (2, "Tumis Kangkung Terasi", "Tumis kangkung cepat dengan terasi bakar.",
     "makan_siang", 4, 15, "mudah", "gurih,pedas"),
    (3, "Ayam Kecap", "Ayam dimasak kecap manis sampai meresap.",
     "makan_malam", 4, 40, "mudah", "manis,gurih,anak_suka"),
    (4, "Sayur Asem", "Sayur asem segar isi labu siam, jagung, dan kacang panjang.",
     "makan_siang", 4, 35, "mudah", "segar,berkuah"),
    (5, "Tempe Goreng Tepung", "Tempe goreng renyah berbalut tepung bumbu.",
     "camilan", 4, 25, "mudah", "renyah,gurih"),
    (6, "Tahu Bacem", "Tahu dimasak bacem manis gurih sampai meresap.",
     "makan_malam", 4, 45, "mudah", "manis,gurih"),
    (7, "Telur Balado", "Telur rebus dibalut sambal balado merah.",
     "makan_siang", 4, 30, "mudah", "pedas,gurih"),
    (8, "Soto Ayam", "Soto ayam kuning hangat dengan kol dan soun ala rumahan.",
     "makan_malam", 4, 50, "sedang", "berkuah,hangat"),
    (9, "Sayur Sop", "Sop sayuran bening isi wortel, kentang, buncis, dan kol.",
     "makan_siang", 4, 30, "mudah", "berkuah,sehat"),
    (10, "Orek Tempe", "Orek tempe kecap manis, lauk bekal favorit.",
     "sarapan", 4, 20, "mudah", "manis,gurih,bekal"),
    (11, "Perkedel Kentang", "Perkedel kentang gurih, cocok untuk camilan atau lauk.",
     "camilan", 4, 40, "sedang", "gurih,renyah"),
    (12, "Capcay", "Capcay sayuran warna-warni dimasak cepat.",
     "makan_malam", 4, 20, "mudah", "sehat,warnawarni"),
    (13, "Mie Goreng Jawa", "Mie goreng tek-tek ala kaki lima dengan kol dan telur.",
     "sarapan", 4, 25, "mudah", "gurih,pedas_sedang"),
    (14, "Tumis Buncis Tahu", "Tumis buncis dan tahu, cepat dan bergizi.",
     "makan_siang", 4, 20, "mudah", "sehat,gurih"),
    (15, "Semur Telur Kentang", "Semur telur dan kentang dengan kuah kecap pekat.",
     "makan_malam", 4, 40, "mudah", "manis,gurih,anak_suka"),
]

# Langkah memasak per resep (id -> list langkah). Takaran konsisten dgn RESEP_BAHAN.
LANGKAH = {
    1: [
        "Masak 600 g beras menjadi nasi, lalu dinginkan agar tidak lembek saat digoreng.",
        "Kocok 4 butir telur, buat orak-arik di wajan dengan 1 sdm minyak, sisihkan.",
        "Haluskan 6 siung bawang merah, 4 siung bawang putih, dan 8 buah cabai rawit; tumis dengan 2 sdm minyak hingga harum.",
        "Masukkan 250 g daging ayam (potong dadu kecil), masak hingga berubah warna.",
        "Masukkan nasi, aduk rata dengan bumbu.",
        "Tambahkan 3 sdm kecap manis, 1 sdt garam, dan 1 sdt gula; aduk hingga warna merata.",
        "Masukkan telur orak-arik, aduk sebentar, koreksi rasa, angkat dan sajikan.",
    ],
    2: [
        "Petiki 2 ikat kangkung, cuci bersih, tiriskan.",
        "Bakar 1 sdt terasi sebentar agar aromanya keluar.",
        "Iris 5 siung bawang merah, 3 siung bawang putih, dan 6 buah cabai rawit.",
        "Panaskan 2 sdm minyak, tumis irisan bumbu dan terasi hingga harum.",
        "Masukkan kangkung, aduk cepat dengan api besar.",
        "Tambahkan 1 sdt garam dan 1 sdt gula, aduk hingga kangkung layu tapi tetap hijau.",
        "Angkat dan sajikan selagi panas.",
    ],
    3: [
        "Potong 800 g ayam sesuai selera, cuci bersih, lumuri sedikit garam.",
        "Iris 8 siung bawang merah dan 5 siung bawang putih.",
        "Panaskan 3 sdm minyak, tumis bawang hingga harum dan layu.",
        "Masukkan ayam, aduk hingga berubah warna dan setengah matang.",
        "Tuang 5 sdm kecap manis, tambahkan 1 sdm gula pasir dan 1 sdt garam; aduk rata.",
        "Tambahkan sedikit air (±200 ml), masak dengan api kecil hingga kuah menyusut dan meresap (±25 menit).",
        "Koreksi rasa, angkat, sajikan.",
    ],
    4: [
        "Potong 2 buah labu siam, 2 tongkol jagung (±4 cm), dan 1 ikat kacang panjang (±5 cm); cuci bersih.",
        "Larutkan 10 g asam jawa dengan sedikit air hangat, saring.",
        "Haluskan 4 siung bawang merah, 2 siung bawang putih, 5 buah cabai rawit, dan 1 sdt terasi.",
        "Didihkan ±1,5 liter air, masukkan jagung dan bumbu halus.",
        "Setelah jagung setengah empuk, masukkan labu siam dan kacang panjang.",
        "Tuang air asam jawa, tambahkan 1 sdt garam dan 1 sdt gula.",
        "Masak hingga semua sayuran empuk, koreksi rasa asam-garam, angkat.",
    ],
    5: [
        "Iris 1 papan tempe tipis-tipis (±0,5 cm).",
        "Haluskan 3 siung bawang putih dengan 1 sdt garam dan 1 sdt ketumbar bubuk.",
        "Campur 100 g tepung terigu dengan bumbu halus dan air secukupnya hingga menjadi adonan kental.",
        "Panaskan 200 ml minyak dengan api sedang.",
        "Celupkan irisan tempe ke adonan, goreng hingga kuning keemasan.",
        "Angkat, tiriskan, sajikan selagi renyah.",
    ],
    6: [
        "Potong 1 bungkus tahu menjadi 8–10 bagian, goreng setengah matang, tiriskan.",
        "Haluskan 4 siung bawang merah, 3 siung bawang putih, dan 1 sdt ketumbar bubuk.",
        "Tumis bumbu halus dengan 2 sdm minyak hingga harum.",
        "Masukkan tahu, 100 g gula merah, 3 sdm kecap manis, 2 lembar daun salam, dan 1 sdt garam.",
        "Tuang air hingga tahu terendam, masak dengan api kecil hingga air menyusut dan bumbu meresap.",
        "Koreksi rasa manis-gurih, angkat. Opsional: goreng sebentar sebelum disajikan.",
    ],
    7: [
        "Rebus 8 butir telur hingga matang (±10 menit), kupas kulitnya.",
        "Goreng telur rebus sebentar hingga berkulit tipis, tiriskan.",
        "Haluskan 100 g cabai merah keriting, 6 siung bawang merah, 3 siung bawang putih, dan 2 buah tomat.",
        "Panaskan 4 sdm minyak, tumis bumbu halus hingga harum dan minyaknya keluar.",
        "Masukkan telur, tambahkan 1 sdt garam dan 1 sdt gula.",
        "Aduk rata hingga bumbu membalut telur, masak ±5 menit.",
        "Koreksi rasa, angkat, sajikan.",
    ],
    8: [
        "Rebus 500 g ayam hingga empuk, saring kaldunya (±1,5 liter), suwir-suwir daging ayam.",
        "Haluskan 6 siung bawang merah, 4 siung bawang putih, 20 g kunyit, 20 g jahe, dan 20 g lengkuas.",
        "Tumis bumbu halus dengan 3 sdm minyak; masukkan 2 batang serai (geprek) dan 3 lembar daun jeruk hingga harum.",
        "Masukkan tumisan bumbu ke dalam kaldu, didihkan kembali.",
        "Tambahkan 1 sdt garam dan 1 sdt merica bubuk, koreksi rasa.",
        "Iris 200 g kol tipis; rebus 2 butir telur lalu belah dua.",
        "Tata di mangkuk: kol, suwiran ayam, dan telur; siram kuah panas dan taburi 1 ikat daun bawang iris. Sajikan.",
    ],
    9: [
        "Potong 2 buah wortel, 2 buah kentang, 100 g buncis, dan 200 g kol sesuai selera; cuci bersih.",
        "Didihkan ±1,5 liter air.",
        "Masukkan wortel dan kentang terlebih dahulu, masak hingga setengah empuk.",
        "Tumis 3 siung bawang putih cincang dengan 1 sdm minyak hingga harum, masukkan ke panci.",
        "Masukkan buncis dan kol, tambahkan 1 sdt garam dan 1 sdt merica bubuk.",
        "Masak hingga semua sayuran empuk, taburi ½ ikat daun bawang iris.",
        "Koreksi rasa, angkat, sajikan hangat.",
    ],
    10: [
        "Iris 1 papan tempe tipis memanjang seperti korek api.",
        "Goreng tempe hingga setengah kering, tiriskan.",
        "Iris 5 siung bawang merah, 3 siung bawang putih, dan 5 buah cabai rawit.",
        "Tumis irisan bumbu dengan 3 sdm minyak hingga harum.",
        "Masukkan tempe goreng, 4 sdm kecap manis, 1 sdt gula, dan ½ sdt garam.",
        "Aduk rata hingga kecap meresap dan tempe kering berbumbu.",
        "Koreksi rasa, angkat. Cocok untuk bekal.",
    ],
    11: [
        "Kupas 500 g kentang, potong-potong, goreng hingga empuk, tiriskan.",
        "Haluskan kentang selagi panas.",
        "Goreng 4 siung bawang merah iris hingga kering, campurkan ke kentang.",
        "Tambahkan 1 sdt merica bubuk, 1 sdt garam, dan 1 butir telur; aduk rata.",
        "Bentuk bulat pipih sesuai selera.",
        "Kocok 1 butir telur sisa; celupkan perkedel lalu goreng dengan 200 ml minyak panas hingga keemasan.",
        "Angkat, tiriskan, sajikan.",
    ],
    12: [
        "Iris 1 buah wortel serong tipis; potong 200 g kol dan 100 g buncis; cuci bersih.",
        "Cincang 4 siung bawang putih.",
        "Panaskan 2 sdm minyak, tumis bawang putih hingga harum.",
        "Masukkan wortel dan buncis terlebih dahulu, aduk ±2 menit.",
        "Masukkan kol, tambahkan sedikit air (±100 ml).",
        "Bumbui dengan 1 sdt garam, 1 sdt merica bubuk, dan 1 sdt gula.",
        "Masak cepat hingga sayuran matang tapi tetap renyah, angkat, sajikan.",
    ],
    13: [
        "Rebus 2 bungkus mie telur hingga setengah matang, tiriskan, beri sedikit minyak agar tidak lengket.",
        "Iris 200 g kol dan 1 buah wortel; kocok 2 butir telur.",
        "Haluskan 5 siung bawang merah dan 3 siung bawang putih.",
        "Panaskan 3 sdm minyak, buat orak-arik telur, sisihkan di pinggir wajan.",
        "Tumis bumbu halus hingga harum, masukkan wortel dan kol.",
        "Masukkan mie, 3 sdm kecap manis, 1 sdt merica bubuk, dan 1 sdt garam; aduk rata.",
        "Campurkan telur orak-arik, koreksi rasa, angkat, sajikan.",
    ],
    14: [
        "Potong 250 g buncis serong ±4 cm; potong dadu 250 g tahu lalu goreng setengah matang.",
        "Iris 4 siung bawang putih dan 4 buah cabai rawit.",
        "Panaskan 2 sdm minyak, tumis bawang putih dan cabai hingga harum.",
        "Masukkan buncis, aduk dengan api besar ±3 menit.",
        "Masukkan tahu goreng, 1 sdm kecap manis, 1 sdt garam, dan ½ sdt gula.",
        "Aduk rata hingga bumbu meresap, koreksi rasa.",
        "Angkat dan sajikan selagi hangat.",
    ],
    15: [
        "Rebus 6 butir telur hingga matang, kupas kulitnya.",
        "Kupas 400 g kentang, potong dadu besar, goreng setengah matang.",
        "Haluskan 6 siung bawang merah dan 4 siung bawang putih.",
        "Tumis bumbu halus dengan 3 sdm minyak hingga harum.",
        "Masukkan telur dan kentang, tuang 4 sdm kecap manis.",
        "Tambahkan air secukupnya, 1 sdt merica bubuk, 1 sdt gula, dan 1 sdt garam.",
        "Masak dengan api kecil hingga kuah mengental dan meresap (±20 menit), koreksi rasa, angkat.",
    ],
}

# (resep_id, bahan_nama, jumlah, satuan, opsional)
RESEP_BAHAN = [
    (1, "Beras", 600, "g", 0), (1, "Telur ayam", 4, "butir", 0),
    (1, "Daging ayam", 250, "g", 0), (1, "Bawang merah", 6, "siung", 0),
    (1, "Bawang putih", 4, "siung", 0), (1, "Cabai rawit merah", 8, "buah", 1),
    (1, "Kecap manis", 3, "sdm", 0), (1, "Minyak goreng", 3, "sdm", 0),
    (1, "Garam", 1, "sdt", 0), (1, "Gula pasir", 1, "sdt", 1),
    (2, "Kangkung", 2, "ikat", 0), (2, "Bawang merah", 5, "siung", 0),
    (2, "Bawang putih", 3, "siung", 0), (2, "Cabai rawit merah", 6, "buah", 1),
    (2, "Terasi", 1, "sdt", 0), (2, "Minyak goreng", 2, "sdm", 0),
    (2, "Garam", 1, "sdt", 0), (2, "Gula pasir", 1, "sdt", 1),
    (3, "Daging ayam", 800, "g", 0), (3, "Bawang merah", 8, "siung", 0),
    (3, "Bawang putih", 5, "siung", 0), (3, "Kecap manis", 5, "sdm", 0),
    (3, "Minyak goreng", 3, "sdm", 0), (3, "Gula pasir", 1, "sdm", 0),
    (3, "Garam", 1, "sdt", 0),
    (4, "Labu siam", 2, "buah", 0), (4, "Jagung manis", 2, "tongkol", 0),
    (4, "Kacang panjang", 1, "ikat", 0), (4, "Bawang merah", 4, "siung", 0),
    (4, "Bawang putih", 2, "siung", 0), (4, "Cabai rawit merah", 5, "buah", 1),
    (4, "Terasi", 1, "sdt", 0), (4, "Asam jawa", 10, "g", 0),
    (4, "Garam", 1, "sdt", 0), (4, "Gula pasir", 1, "sdt", 1),
    (5, "Tempe", 1, "papan", 0), (5, "Tepung terigu", 100, "g", 0),
    (5, "Bawang putih", 3, "siung", 0), (5, "Ketumbar bubuk", 1, "sdt", 0),
    (5, "Garam", 1, "sdt", 0), (5, "Minyak goreng", 200, "ml", 0),
    (6, "Tahu", 1, "bungkus", 0), (6, "Gula merah", 100, "g", 0),
    (6, "Kecap manis", 3, "sdm", 0), (6, "Bawang merah", 4, "siung", 0),
    (6, "Bawang putih", 3, "siung", 0), (6, "Ketumbar bubuk", 1, "sdt", 0),
    (6, "Daun salam", 2, "lembar", 0), (6, "Garam", 1, "sdt", 0),
    (6, "Minyak goreng", 2, "sdm", 0),
    (7, "Telur ayam", 8, "butir", 0), (7, "Cabai merah keriting", 100, "g", 0),
    (7, "Bawang merah", 6, "siung", 0), (7, "Bawang putih", 3, "siung", 0),
    (7, "Tomat", 2, "buah", 0), (7, "Gula pasir", 1, "sdt", 0),
    (7, "Garam", 1, "sdt", 0), (7, "Minyak goreng", 4, "sdm", 0),
    (8, "Daging ayam", 500, "g", 0), (8, "Bawang merah", 6, "siung", 0),
    (8, "Bawang putih", 4, "siung", 0), (8, "Kunyit", 20, "g", 0),
    (8, "Jahe", 20, "g", 0), (8, "Lengkuas", 20, "g", 0),
    (8, "Serai", 2, "batang", 0), (8, "Daun jeruk", 3, "lembar", 0),
    (8, "Kol", 200, "g", 1), (8, "Telur ayam", 2, "butir", 1),
    (8, "Minyak goreng", 3, "sdm", 0), (8, "Garam", 1, "sdt", 0),
    (8, "Merica bubuk", 1, "sdt", 0), (8, "Daun bawang", 1, "ikat", 1),
    (9, "Wortel", 2, "buah", 0), (9, "Kentang", 2, "buah", 0),
    (9, "Buncis", 100, "g", 0), (9, "Kol", 200, "g", 0),
    (9, "Bawang putih", 3, "siung", 0), (9, "Merica bubuk", 1, "sdt", 0),
    (9, "Garam", 1, "sdt", 0), (9, "Minyak goreng", 1, "sdm", 0),
    (9, "Daun bawang", 0.5, "ikat", 1),
    (10, "Tempe", 1, "papan", 0), (10, "Kecap manis", 4, "sdm", 0),
    (10, "Bawang merah", 5, "siung", 0), (10, "Bawang putih", 3, "siung", 0),
    (10, "Cabai rawit merah", 5, "buah", 1), (10, "Gula pasir", 1, "sdt", 0),
    (10, "Garam", 0.5, "sdt", 0), (10, "Minyak goreng", 3, "sdm", 0),
    (11, "Kentang", 500, "g", 0), (11, "Telur ayam", 2, "butir", 0),
    (11, "Bawang merah", 4, "siung", 0), (11, "Merica bubuk", 1, "sdt", 0),
    (11, "Garam", 1, "sdt", 0), (11, "Minyak goreng", 200, "ml", 0),
    (12, "Wortel", 1, "buah", 0), (12, "Kol", 200, "g", 0),
    (12, "Buncis", 100, "g", 0), (12, "Bawang putih", 4, "siung", 0),
    (12, "Merica bubuk", 1, "sdt", 0), (12, "Garam", 1, "sdt", 0),
    (12, "Gula pasir", 1, "sdt", 1), (12, "Minyak goreng", 2, "sdm", 0),
    (13, "Mie telur", 2, "bungkus", 0), (13, "Kol", 200, "g", 0),
    (13, "Wortel", 1, "buah", 0), (13, "Telur ayam", 2, "butir", 0),
    (13, "Bawang merah", 5, "siung", 0), (13, "Bawang putih", 3, "siung", 0),
    (13, "Kecap manis", 3, "sdm", 0), (13, "Merica bubuk", 1, "sdt", 0),
    (13, "Garam", 1, "sdt", 0), (13, "Minyak goreng", 3, "sdm", 0),
    (14, "Buncis", 250, "g", 0), (14, "Tahu", 250, "g", 0),
    (14, "Bawang putih", 4, "siung", 0), (14, "Cabai rawit merah", 4, "buah", 1),
    (14, "Kecap manis", 1, "sdm", 1), (14, "Garam", 1, "sdt", 0),
    (14, "Gula pasir", 0.5, "sdt", 1), (14, "Minyak goreng", 2, "sdm", 0),
    (15, "Telur ayam", 6, "butir", 0), (15, "Kentang", 400, "g", 0),
    (15, "Kecap manis", 4, "sdm", 0), (15, "Bawang merah", 6, "siung", 0),
    (15, "Bawang putih", 4, "siung", 0), (15, "Merica bubuk", 1, "sdt", 0),
    (15, "Gula pasir", 1, "sdt", 0), (15, "Garam", 1, "sdt", 0),
    (15, "Minyak goreng", 3, "sdm", 0),
]

# Harga CONTOH (Rp/kg) — DITANDAI sumber='SAMPLE', bukan data resmi.
# Format: kode -> (nas_08, nas_09, jabar_08, jabar_09)
SAMPLE_HARGA = {
    "beras_bawah1":   (14900, 14900, 14500, 14500),
    "beras_bawah2":   (14750, 14750, 14300, 14300),
    "beras_medium1":  (16600, 16650, 15750, 15800),
    "beras_medium2":  (16400, 16400, 15300, 15300),
    "beras_super1":   (17950, 17950, 17000, 17000),
    "beras_super2":   (17400, 17400, 16500, 16500),
    "ayam_ras":       (41750, 41050, 39500, 39000),
    "sapi_k1":        (152350, 152650, 148000, 148000),
    "sapi_k2":        (143000, 145900, 140000, 141000),
    "telur":          (29500, 29200, 28000, 27800),
    "bamer":          (36650, 36500, 34000, 33800),
    "baput":          (39350, 38700, 37000, 36800),
    "cabe_besar":     (67600, 69650, 60000, 62000),
    "cabe_keriting":  (81750, 82050, 74000, 74500),
    "rawit_hijau":    (76900, 76100, 70000, 69500),
    "rawit_merah":    (100800, 101350, 92000, 93500),
    "migor_curah":    (20600, 20350, 20000, 19800),
    "migor_kemasan1": (24400, 24450, 24000, 24000),
    "migor_kemasan2": (23650, 23800, 23200, 23300),
    "gula_premium":   (20100, 20450, 19800, 20000),
    "gula_lokal":     (19300, 19200, 18800, 18700),
}


def main():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    kode_ke_id = {}
    for tree_id, kode, nama, kat in KOMODITAS:
        cur = con.execute(
            "INSERT INTO komoditas (kode, nama_pihps, kategori) VALUES (?,?,?)",
            (kode, nama, kat))
        kode_ke_id[kode] = cur.lastrowid

    nama_ke_id = {}
    for nama, kat, kode_kom, hm, sm, isi, dasar, alergen in BAHAN:
        kom_id = kode_ke_id.get(kode_kom) if kode_kom else None
        cur = con.execute(
            """INSERT INTO bahan (nama, kategori, komoditas_id, harga_manual_rp,
                                  satuan_manual, isi_satuan_manual, satuan_dasar, alergen)
               VALUES (?,?,?,?,?,?,?,?)""",
            (nama, kat, kom_id, hm, sm, isi, dasar, alergen))
        nama_ke_id[nama] = cur.lastrowid

    for nama, (kal, pro, kar, lem, ser, nat) in GIZI.items():
        con.execute(
            "INSERT INTO gizi_bahan (bahan_id, kalori, protein, karbo, lemak, serat, natrium)"
            " VALUES (?,?,?,?,?,?,?)",
            (nama_ke_id[nama], kal, pro, kar, lem, ser, nat))

    for bnama, dari, ke, faktor in KONVERSI:
        bid = nama_ke_id.get(bnama) if bnama else None
        con.execute(
            "INSERT INTO konversi_satuan (bahan_id, dari_satuan, ke_satuan, faktor) VALUES (?,?,?,?)",
            (bid, dari, ke, faktor))

    for rid, nama, desk, kat, porsi, menit, ting, tags in RESEP:
        langkah = "\n".join(LANGKAH[rid])
        con.execute(
            """INSERT INTO resep (id, nama, deskripsi, kategori, porsi,
                                  waktu_masak_menit, tingkat, tags, langkah)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (rid, nama, desk, kat, porsi, menit, ting, tags, langkah))

    for rid, bnama, jml, satuan, ops in RESEP_BAHAN:
        con.execute(
            "INSERT INTO resep_bahan (resep_id, bahan_id, jumlah, satuan, opsional) VALUES (?,?,?,?,?)",
            (rid, nama_ke_id[bnama], jml, satuan, ops))

    # Akun: admin + user demo. GANTI password setelah login pertama!
    con.execute(
        "INSERT INTO users (username, password_hash, role, nama, wilayah) VALUES (?,?,?,?,?)",
        ("admin", generate_password_hash("admin123"), "admin", "Administrator", "NASIONAL"))
    cur = con.execute(
        "INSERT INTO users (username, password_hash, role, nama, wilayah, budget_harian_rp)"
        " VALUES (?,?,?,?,?,?)",
        ("user", generate_password_hash("user123"), "user", "Pengguna Demo", "JAWA BARAT", 50000))
    uid = cur.lastrowid
    con.execute("INSERT INTO user_pantangan (user_id, bahan_id, alasan) VALUES (?, ?, 'alergi')",
                (uid, nama_ke_id["Terasi"]))
    con.execute("INSERT INTO user_favorit_resep (user_id, resep_id) VALUES (?, 1)", (uid,))

    # Harga contoh 2 hari (supaya indikator naik/turun & peringatan bisa jalan offline)
    for kode, (n8, n9, j8, j9) in SAMPLE_HARGA.items():
        kid = kode_ke_id[kode]
        for tgl, wil, hr in [("2026-10-08", "NASIONAL", n8), ("2026-10-09", "NASIONAL", n9),
                             ("2026-10-08", "JAWA BARAT", j8), ("2026-10-09", "JAWA BARAT", j9)]:
            con.execute(
                """INSERT OR REPLACE INTO harga_harian
                   (komoditas_id, tanggal, wilayah, harga_rp, sumber)
                   VALUES (?,?,?,?, 'SAMPLE')""",
                (kid, tgl, wil, hr))

    con.commit()
    n_r = con.execute("SELECT COUNT(*) FROM resep").fetchone()[0]
    n_b = con.execute("SELECT COUNT(*) FROM bahan").fetchone()[0]
    n_g = con.execute("SELECT COUNT(*) FROM gizi_bahan").fetchone()[0]
    n_h = con.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0]
    n_u = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    con.close()
    print(f"OK: {DB}")
    print(f"  resep={n_r}, bahan={n_b}, gizi={n_g}, users={n_u}, harga_harian={n_h} (SAMPLE)")


if __name__ == "__main__":
    main()
