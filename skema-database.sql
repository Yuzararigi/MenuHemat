-- ================================================================
-- MenuHemat -- Draf Skema Database v0.1 (SQLite)
-- 2026-10-10 - dibuat untuk Ari
--
-- Fondasi database resep bertakaran yang nyambung ke data harga
-- harian (PIHPS BI / Panel Bapanas) untuk fitur:
--   1. "menu termurah hari ini"
--   2. filter alergi / pantangan
--   3. personalisasi favorit
--
-- Kompatibel SQLite -> bisa langsung dipakai di Flask seperti
-- RestoLauncher. Catatan desain ada di bagian paling bawah.
-- ================================================================

-- ---------- 1. KOMODITAS (acuan harga resmi) ----------
-- Satu baris = satu nama persis seperti di PIHPS/Bapanas.
CREATE TABLE komoditas (
  id            INTEGER PRIMARY KEY,
  kode          TEXT UNIQUE NOT NULL,      -- 'cabai_rawit_merah'
  nama_pihps    TEXT NOT NULL,             -- 'Cabai Rawit Merah'
  satuan_harga  TEXT NOT NULL DEFAULT 'kg',
  kategori      TEXT                       -- beras/cabai/bumbu/protein/minyak/gula
);

-- ---------- 2. HARGA HARIAN ----------
-- Diisi cron tiap pagi. PIHPS tidak update saat weekend/libur,
-- jadi query selalu pakai tanggal MAX yang tersedia (lihat contoh).
CREATE TABLE harga_harian (
  id            INTEGER PRIMARY KEY,
  komoditas_id  INTEGER NOT NULL REFERENCES komoditas(id),
  tanggal       DATE NOT NULL,
  wilayah       TEXT NOT NULL DEFAULT 'NASIONAL',  -- samakan dgn label PIHPS
  harga_rp      REAL NOT NULL,            -- per satuan_harga
  sumber        TEXT NOT NULL DEFAULT 'PIHPS',     -- PIHPS/BAPANAS/MANUAL
  UNIQUE (komoditas_id, tanggal, wilayah)
);
CREATE INDEX idx_harga_cari ON harga_harian (komoditas_id, wilayah, tanggal DESC);

-- ---------- 3. BAHAN ----------
-- Setiap bahan WAJIB punya sumber harga: komoditas_id ATAU harga_manual.
CREATE TABLE bahan (
  id                  INTEGER PRIMARY KEY,
  nama                TEXT UNIQUE NOT NULL,
  kategori            TEXT,               -- karbo/protein_hewani/sayur/bumbu/minyak/lainnya
  komoditas_id        INTEGER REFERENCES komoditas(id),  -- NULL = tak ada di PIHPS
  harga_manual_rp     REAL,               -- mis. 5000 (per satuan_manual)
  satuan_manual       TEXT,               -- 'ikat'/'botol'/'sachet'
  isi_satuan_manual   REAL,               -- dalam satuan_dasar, mis. 1 ikat = 250 g
  satuan_dasar        TEXT NOT NULL,      -- 'g' atau 'ml' (dipakai untuk hitung biaya)
  alergen             TEXT,               -- 'seafood'/'kacang'/'telur'/'susu'/'gluten', NULL = aman
  nonhalal            INTEGER DEFAULT 0
);

-- ---------- 4. KONVERSI SATUAN ----------
-- Mengubah takaran resep (sdm, butir, siung...) ke satuan_dasar.
-- Baris khusus bahan (bahan_id terisi) menang atas baris umum (NULL).
CREATE TABLE konversi_satuan (
  id            INTEGER PRIMARY KEY,
  bahan_id      INTEGER REFERENCES bahan(id),  -- NULL = berlaku umum
  dari_satuan   TEXT NOT NULL,    -- 'sdm','sdt','butir','siung','buah','ikat'
  ke_satuan     TEXT NOT NULL,    -- 'g' / 'ml'
  faktor        REAL NOT NULL     -- jumlah ke_satuan per 1 dari_satuan
);

-- ---------- 5. RESEP ----------
CREATE TABLE resep (
  id                INTEGER PRIMARY KEY,
  nama              TEXT NOT NULL,
  deskripsi         TEXT,
  kategori          TEXT,             -- sarapan/makan_siang/makan_malam/camilan/bekal
  porsi             INTEGER NOT NULL DEFAULT 4,
  waktu_masak_menit INTEGER,
  tingkat           TEXT DEFAULT 'mudah',   -- mudah/sedang/sulit
  tags              TEXT,             -- 'pedas,berkuah' (comma-separated utk MVP)
  cocok_diet        TEXT,             -- 'rendah_garam,tinggi_protein,mpasi'
  created_at        TEXT DEFAULT (datetime('now'))
);

-- ---------- 6. KOMPOSISI RESEP (takaran bahan) ----------
CREATE TABLE resep_bahan (
  resep_id  INTEGER NOT NULL REFERENCES resep(id),
  bahan_id  INTEGER NOT NULL REFERENCES bahan(id),
  jumlah    REAL NOT NULL,        -- mis. 250 (gram), 3 (sdm), 4 (butir)
  satuan    TEXT NOT NULL,        -- 'g','ml','sdm','sdt','butir','siung','buah','ikat'
  opsional  INTEGER DEFAULT 0,    -- 1 = boleh di-skip untuk versi super hemat
  catatan   TEXT,
  PRIMARY KEY (resep_id, bahan_id)
);

-- ---------- 7. USER, FAVORIT, PANTANGAN ----------
CREATE TABLE users (
  id                INTEGER PRIMARY KEY,
  nama              TEXT,
  wilayah           TEXT DEFAULT 'JAWA BARAT',  -- harga ikut wilayah user
  budget_harian_rp  REAL                        -- opsional: target budget
);

CREATE TABLE user_favorit_resep (
  user_id   INTEGER REFERENCES users(id),
  resep_id  INTEGER REFERENCES resep(id),
  PRIMARY KEY (user_id, resep_id)
);

-- Pantangan dicek di level BAHAN (lebih akurat daripada level resep).
CREATE TABLE user_pantangan (
  user_id   INTEGER REFERENCES users(id),
  bahan_id  INTEGER REFERENCES bahan(id),
  alasan    TEXT,                 -- 'alergi'/'tidak_suka'/'agama'/'diet'
  PRIMARY KEY (user_id, bahan_id)
);


-- ================================================================
-- DATA CONTOH (dummy, untuk testing logika)
-- Harga di bawah ini CONTOH, bukan data resmi.
-- ================================================================

INSERT INTO komoditas (id, kode, nama_pihps, kategori) VALUES
  (1, 'beras_medium',       'Beras Kualitas Medium I',     'beras'),
  (2, 'cabai_rawit_merah',  'Cabai Rawit Merah',           'cabai'),
  (3, 'cabai_merah_keriting','Cabai Merah Keriting',       'cabai'),
  (4, 'bawang_merah',       'Bawang Merah Ukuran Sedang',  'bumbu'),
  (5, 'bawang_putih',       'Bawang Putih Ukuran Sedang',  'bumbu'),
  (6, 'telur_ayam',         'Telur Ayam Ras Segar',        'protein'),
  (7, 'ayam_ras',           'Daging Ayam Ras Segar',       'protein'),
  (8, 'minyak_kemasan',     'Minyak Goreng Kemasan Bermerek 1','minyak'),
  (9, 'gula_lokal',         'Gula Pasir Lokal',            'gula');

-- Harga contoh 2026-10-09, wilayah JAWA BARAT (DUMMY)
INSERT INTO harga_harian (komoditas_id, tanggal, wilayah, harga_rp) VALUES
  (1,'2026-10-09','JAWA BARAT',16500),
  (2,'2026-10-09','JAWA BARAT',100000),
  (3,'2026-10-09','JAWA BARAT',82000),
  (4,'2026-10-09','JAWA BARAT',36500),
  (5,'2026-10-09','JAWA BARAT',38700),
  (6,'2026-10-09','JAWA BARAT',29200),
  (7,'2026-10-09','JAWA BARAT',41000),
  (8,'2026-10-09','JAWA BARAT',24400),
  (9,'2026-10-09','JAWA BARAT',19200);

INSERT INTO bahan (id, nama, kategori, komoditas_id, harga_manual_rp, satuan_manual, isi_satuan_manual, satuan_dasar, alergen) VALUES
  (1,  'Beras',             'karbo',          1,    NULL,  NULL,     NULL, 'g',  NULL),
  (2,  'Cabai rawit merah', 'bumbu',          2,    NULL,  NULL,     NULL, 'g',  NULL),
  (3,  'Cabai merah keriting','bumbu',        3,    NULL,  NULL,     NULL, 'g',  NULL),
  (4,  'Bawang merah',      'bumbu',          4,    NULL,  NULL,     NULL, 'g',  NULL),
  (5,  'Bawang putih',      'bumbu',          5,    NULL,  NULL,     NULL, 'g',  NULL),
  (6,  'Telur ayam',        'protein_hewani', 6,    NULL,  NULL,     NULL, 'g',  'telur'),
  (7,  'Daging ayam',       'protein_hewani', 7,    NULL,  NULL,     NULL, 'g',  NULL),
  (8,  'Minyak goreng',     'minyak',         8,    NULL,  NULL,     NULL, 'ml', NULL),
  (9,  'Gula pasir',        'lainnya',        9,    NULL,  NULL,     NULL, 'g',  NULL),
  (10, 'Garam',             'bumbu',          NULL, 5000,  'bungkus',500,  'g',  NULL),
  (11, 'Kecap manis',       'bumbu',          NULL, 18000, 'botol',  600,  'ml', NULL),
  (12, 'Kangkung',          'sayur',          NULL, 5000,  'ikat',   250,  'g',  NULL),
  (13, 'Terasi',            'bumbu',          NULL, 2500,  'sachet', 20,   'g',  'seafood');

INSERT INTO konversi_satuan (bahan_id, dari_satuan, ke_satuan, faktor) VALUES
  (NULL, 'sdm', 'ml', 15),
  (NULL, 'sdt', 'ml', 5),
  (NULL, 'sdm', 'g',  15),   -- asumsi: untuk gula/garam kasar
  (NULL, 'sdt', 'g',  5),
  (6, 'butir', 'g', 60),     -- 1 butir telur = 60 g
  (4, 'siung', 'g', 5),
  (5, 'siung', 'g', 4),
  (2, 'buah',  'g', 3),
  (12, 'ikat', 'g', 250);

INSERT INTO resep (id, nama, deskripsi, kategori, porsi, waktu_masak_menit, tingkat, tags) VALUES
  (1, 'Nasi Goreng Jawa', 'Nasi goreng kampung dengan suwiran ayam dan telur.',
      'makan_malam', 4, 30, 'mudah', 'gurih,pedas_sedang'),
  (2, 'Tumis Kangkung Terasi', 'Tumis kangkung cepat dengan terasi bakar.',
      'makan_siang', 4, 15, 'mudah', 'gurih,pedas'),
  (3, 'Ayam Kecap', 'Ayam dimasak kecap manis sampai meresap.',
      'makan_malam', 4, 40, 'mudah', 'manis,gurih,anak_suka');

INSERT INTO resep_bahan (resep_id, bahan_id, jumlah, satuan, opsional) VALUES
  -- Nasi Goreng Jawa
  (1, 1, 600, 'g', 0), (1, 6, 4, 'butir', 0), (1, 7, 250, 'g', 0),
  (1, 4, 6, 'siung', 0), (1, 5, 4, 'siung', 0), (1, 2, 8, 'buah', 1),
  (1, 11, 3, 'sdm', 0), (1, 8, 3, 'sdm', 0), (1, 10, 1, 'sdt', 0),
  (1, 9, 1, 'sdt', 1),
  -- Tumis Kangkung Terasi
  (2, 12, 2, 'ikat', 0), (2, 4, 5, 'siung', 0), (2, 5, 3, 'siung', 0),
  (2, 2, 6, 'buah', 1), (2, 13, 1, 'sdt', 0), (2, 8, 2, 'sdm', 0),
  (2, 10, 1, 'sdt', 0), (2, 9, 1, 'sdt', 1),
  -- Ayam Kecap
  (3, 7, 800, 'g', 0), (3, 4, 8, 'siung', 0), (3, 5, 5, 'siung', 0),
  (3, 11, 5, 'sdm', 0), (3, 8, 3, 'sdm', 0), (3, 9, 1, 'sdm', 0),
  (3, 10, 1, 'sdt', 0);

INSERT INTO users (id, nama, wilayah, budget_harian_rp) VALUES
  (1, 'Ari', 'JAWA BARAT', 50000);

-- Contoh: Ari alergi seafood (terasi) dan tidak suka pedas berlebihan
INSERT INTO user_pantangan (user_id, bahan_id, alasan) VALUES
  (1, 13, 'alergi');
INSERT INTO user_favorit_resep (user_id, resep_id) VALUES
  (1, 1);


-- ================================================================
-- CONTOH QUERY
-- ================================================================

-- Q1. MENU TERMURAH HARI INI (per porsi), ikut wilayah user.
--     Otomatis pakai tanggal harga terbaru (fallback saat weekend).
WITH harga_aktif AS (
  SELECT komoditas_id, harga_rp / 1000.0 AS rp_per_dasar
  FROM harga_harian
  WHERE wilayah = (SELECT wilayah FROM users WHERE id = 1)
    AND tanggal = (SELECT MAX(tanggal) FROM harga_harian
                   WHERE wilayah = (SELECT wilayah FROM users WHERE id = 1))
),
biaya AS (
  SELECT rb.resep_id,
         SUM(rb.jumlah
             * COALESCE(ksb.faktor, ksg.faktor, 1)   -- ke satuan dasar
             * COALESCE(h.rp_per_dasar,              -- harga PIHPS per g/ml
                        b.harga_manual_rp / NULLIF(b.isi_satuan_manual, 0))
         ) AS total_rp
  FROM resep_bahan rb
  JOIN bahan b ON b.id = rb.bahan_id
  LEFT JOIN konversi_satuan ksb
    ON ksb.bahan_id = b.id AND ksb.dari_satuan = rb.satuan
   AND ksb.ke_satuan = b.satuan_dasar
  LEFT JOIN konversi_satuan ksg
    ON ksg.bahan_id IS NULL AND ksg.dari_satuan = rb.satuan
   AND ksg.ke_satuan = b.satuan_dasar
  LEFT JOIN harga_aktif h ON h.komoditas_id = b.komoditas_id
  GROUP BY rb.resep_id
)
SELECT r.nama, r.porsi,
       ROUND(b.total_rp) AS total_rp,
       ROUND(b.total_rp / r.porsi) AS rp_per_porsi
FROM biaya b JOIN resep r ON r.id = b.resep_id
ORDER BY rp_per_porsi ASC;

-- Q2. RESEP AMAN UNTUK USER (lewati semua bahan yang dipantang)
SELECT r.nama
FROM resep r
WHERE NOT EXISTS (
  SELECT 1 FROM resep_bahan rb
  JOIN user_pantangan up ON up.bahan_id = rb.bahan_id
  WHERE rb.resep_id = r.id AND up.user_id = 1
);

-- Q3. VALIDASI: bahan yang belum punya sumber harga (wajib diperbaiki
--     sebelum Q1 bisa dipercaya — SUM mengabaikan NULL)
SELECT nama FROM bahan
WHERE komoditas_id IS NULL
  AND (harga_manual_rp IS NULL OR isi_satuan_manual IS NULL);


-- ================================================================
-- CATATAN DESAIN (asumsi yang disadari)
-- ================================================================
-- 1. Harga PIHPS per kg -> dibagi 1000 = per gram. Untuk minyak yang
--    satuan_dasarnya 'ml', dipakai asumsi densitas ~1 (cukup utk MVP).
-- 2. Weekend/libur: PIHPS tidak update -> query Q1 otomatis memakai
--    tanggal terbaru yang ada (fallback, bukan error).
-- 3. Wilayah: harga mengikuti wilayah user. MVP cukup satu wilayah;
--    nanti bisa tambah fallback NASIONAL bila data kota kosong.
-- 4. Alergi dicek di level BAHAN (terasi = seafood), bukan level resep
--    -> tidak ada resep "aman" yang diam-diam mengandung pemicu.
-- 5. Kolom 'opsional' di resep_bahan = bahan yang boleh di-skip untuk
--    mode "super hemat" (mis. cabai saat harganya Rp100rb/kg).
-- 6. Skala berikutnya tanpa ubah struktur inti: tambah tabel nutrisi
--    (kalori/protein per 100g bahan), tabel harga_manual riwayat,
--    dan kolom skor AI di resep.
-- ================================================================
