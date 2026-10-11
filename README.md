# MenuHemat

Aplikasi web untuk merekomendasikan **menu harian termurah** berdasarkan
data harga bahan pokok pasar yang diperbarui setiap hari.

Fitur:
- **Beranda** — ranking resep dari yang termurah (Rp/porsi) memakai harga
  pasar terbaru. Katalog **100 resep** dari 10 daerah (Jawa, Sunda,
  Sumatera, Bali, Sulawesi, Kalimantan, Western, Asia, Timur, Nusantara),
  lengkap dengan filter kategori, **asal daerah**, **label Diet/Gym**,
  **urutan gizi** (kalori, protein, karbohidrat, lemak, serat, natrium),
  batas Rp/porsi, favorit (bintang), dan pengaturan pantangan/alergi.
- **Mode super hemat** — membuang bahan opsional lalu me-ranking ulang.
- **Cek satu hari makan** — pilih hidangan sarapan/siang/malam sendiri
  (tiap pilihan tampil biaya per porsi), atau klik **Isi menu termurah**
  untuk pengisian otomatis; total dibandingkan dengan budget harianmu.
- **Detail resep** — rincian biaya per bahan, total, dan per porsi,
  **kandungan gizi (estimasi)**, dan **langkah memasak**.
- **Rencana mingguan** — atur 7 hari manual atau buatkan otomatis sesuai
  budget, lengkap dengan **daftar belanja agregat** (jumlah + estimasi biaya).
- **Harga pasar** — tabel harga 21 komoditas + indikator naik/turun vs hari
  sebelumnya + **peringatan harga cerdas** (mis. "cabai naik — ini resep
  yang tidak pakai cabai").
- **Pilihan wilayah (provinsi)** — semua harga mengikuti provinsi yang
  dipilih. Catatan jujur: PIHPS hanya menyediakan data level provinsi
  (34 provinsi + nasional), bukan per kota.
- **Akun** — pengunjung bisa browsing tanpa login (wilayah default
  NASIONAL); masuk untuk favorit, pantangan, dan perencana. Admin punya
  panel CRUD resep & bahan, daftar pengguna, dan tombol update harga.

## Akun bawaan

| Username | Password   | Peran |
|----------|------------|-------|
| `admin`  | `admin123` | admin — panel `/admin`: kelola resep, bahan (+harga & gizi), lihat pengguna, update harga |
| `user`   | `user123`  | user — favorit, pantangan, wilayah tersimpan, perencana mingguan |

> **PENTING:** segera ganti password bawaan setelah masuk, lewat menu
> **Ganti password** di kanan atas (tersedia untuk semua akun yang login).
> Password disimpan sebagai hash (werkzeug), bukan teks polos.

## Catatan gizi

Angka gizi (kalori, protein, karbohidrat, lemak, serat, natrium) dihitung
dari tabel `gizi_bahan` berisi komposisi per 100 g/ml bahan — **semuanya
estimasi** dari tabel komposisi pangan umum, bukan hasil uji laboratorium.
Ditampilkan dengan label "estimasi" di aplikasi. Kalori per porsi juga
muncul sebagai badge di kartu resep beranda.

Data harga: **PIHPS Bank Indonesia** (Pusat Informasi Harga Pangan Strategis),
diambil otomatis setiap hari. Tanpa internet, aplikasi tetap jalan memakai
data contoh bawaan.

## Cara menjalankan (macOS)

**Cara termudah:** double-click `Jalankan-Mac.command`. Terminal akan
terbuka, browser terbuka otomatis di http://127.0.0.1:5000.

> **Catatan Gatekeeper:** saat pertama kali membuka file `.command` hasil
> unduhan, macOS bisa menolaknya ("cannot be opened because it is from an
> unidentified developer"). Solusinya: **klik kanan** file-nya → **Open** →
> klik **Open** pada dialog konfirmasi. Setelah itu double-click biasa
> akan jalan normal.

**Cara manual** (via Terminal):

```
cd folder-menuhemat
python3 -m pip install flask
python3 fetch_harga.py
python3 app.py
```

Lalu buka http://127.0.0.1:5000 di browser.

## Cara menjalankan (Windows)

**Cara termudah:** double-click `Jalankan.bat`. Browser akan terbuka
otomatis di http://127.0.0.1:5000.

> **Catatan SmartScreen:** saat pertama kali menjalankan file `.bat` hasil
> unduhan, Windows SmartScreen bisa memblokirnya. Solusinya: klik kanan
> `Jalankan.bat` → **Properties** → centang **Unblock** → OK. Setelah itu
> double-click seperti biasa.

**Cara manual** (jika sudah biasa pakai terminal):

```
cd folder-menuhemat
pip install flask
python fetch_harga.py
python app.py
```

Lalu buka http://127.0.0.1:5000 di browser.

## Cara update harga harian

```
python fetch_harga.py
```

Jalankan setiap pagi (data PIHPS diperbarui tiap hari kerja sekitar
pukul 05.30 WIB; akhir pekan dan hari libur tidak ada data baru sehingga
aplikasi otomatis memakai tanggal terakhir yang tersedia).

Untuk otomatisasi di Windows, bisa memakai **Task Scheduler** dengan
perintah `pythonw.exe` menunjuk ke `fetch_harga.py` setiap jam 07.00.
Di macOS, bisa memakai `cron` atau `launchd` dengan perintah
`python3 /path/ke/fetch_harga.py`.

## Catatan data harga

- `fetch_harga.py` mengambil data dari endpoint yang dipakai oleh halaman
  web PIHPS sendiri (`bi.go.id/hargapangan`). Endpoint ini **tidak
  didokumentasikan resmi** oleh BI — ditemukan dengan membaca JavaScript
  halaman tersebut (Oktober 2026). Jika suatu hari script gagal, kemungkinan
  BI mengubah struktur situsnya.
- Harga yang disimpan adalah **rata-rata pasar tradisional per provinsi**
  plus rata-rata nasional. Harga di pasar/warung spesifik bisa berbeda
  ±2–5%.
- Jika `fetch_harga.py` gagal (mis. tidak ada internet), aplikasi tetap
  berjalan memakai data contoh (`sumber='SAMPLE'`) yang tertanam saat
  `init_db.py` dijalankan. Data asli (`sumber='PIHPS'`) selalu menimpa
  data contoh pada tanggal yang sama.

## Struktur file

```
app.py              aplikasi web (Flask)
fetch_harga.py      pengambil data harga harian PIHPS
init_db.py          membangun database dari nol (15 resep, 36 bahan + gizi,
                    langkah memasak, akun admin & user demo)
ekspansi_resep.py   ekspansi katalog 15 -> 100 resep (migrasi kolom asal/tag,
                    +58 bahan, +85 resep dari resep_baru.py; idempoten)
resep_baru.py       data 85 resep baru (10 daerah x 10 resep)
label_kos.py        mode Anak Kos: +8 resep sederhana & label "kos" untuk resep
                    berbahan inti <= 5 (bumbu dasar tidak dihitung; idempoten)
export_static.py    ekspor menuhemat.db menjadi docs/data.js (situs statis)
docs/               situs statis untuk GitHub Pages (termasuk foto 108 resep)
menuhemat.db        database SQLite (dibuat oleh init_db.py)
skema-database.sql  draf skema awal (dokumentasi)
templates/          halaman HTML (server-rendered, termasuk templates/admin/)
static/style.css    tampilan mobile-first
Jalankan.bat        peluncur sekali klik untuk Windows
Jalankan-Mac.command peluncur sekali klik untuk macOS
README.md           file ini
```

## Membangun ulang database

```
python init_db.py        # hapus dan buat ulang menuhemat.db dari nol
python fetch_harga.py    # isi dengan data harga asli PIHPS
python ekspansi_resep.py # perluas katalog menjadi 100 resep + 94 bahan
python label_kos.py      # +8 resep anak kos & label "kos" (total 108 resep)
python export_static.py  # (opsional) bangun ulang situs statis di docs/
```

Urutan ini penting: `init_db.py` membuat skema baru (tabel gizi, kolom
langkah, kolom akun) + seed, lalu `fetch_harga.py` menimpa harga SAMPLE
dengan data asli PIHPS per provinsi. `ekspansi_resep.py` menambahkan kolom
`asal`/`tag` pada resep, 58 bahan baru, dan 85 resep baru — aman dijalankan
berulang (idempoten).

Label **Diet** (≤400 kkal & serat ≥2 g/porsi) dan **Gym** (protein ≥20 g/porsi)
dihitung dari komposisi bahan tiap resep, bukan klaim manual.

Label **Anak Kos** (token `kos` pada kolom `tag`, diatur `label_kos.py`)
diberikan pada resep dengan bahan inti ≤5. Bahan inti = semua bahan resep
selain bumbu dasar (garam, gula, merica/lada, kaldu bubuk, minyak, margarin,
air, kecap, saus-saus, cuka — tidak dihitung). Label ini bisa dikombinasikan
dengan Diet/Gym lewat filter di beranda.

## Batasan yang diketahui

- Endpoint PIHPS tidak resmi (lihat "Catatan data harga") — kalau BI
  mengubah situsnya, `fetch_harga.py` bisa gagal; aplikasi fallback ke
  data SAMPLE.
- Harga bahan non-PIHPS (tahu, tempe, sayur, dll.) adalah estimasi wajar
  berlabel "(estimasi)" — kalibrasi ke pasar setempat saat pilot.
- Angka gizi adalah estimasi tabel komposisi pangan, bukan uji lab.
- PIHPS hanya level provinsi — tidak ada pilihan per kota.
- Single-server Flask tanpa HTTPS; cocok untuk pemakaian pribadi/lokal,
  belum untuk publik skala besar.
