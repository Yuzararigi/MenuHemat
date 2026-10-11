#!/usr/bin/env python3
"""
label_kos.py — mode "Anak Kos" untuk katalog MenuHemat.

Yang dilakukan (semua IDEMPOTEN, aman dijalankan berulang):
  1. Tambah resep anak kos baru (RESEP_KOS) bila nama belum ada. Tag diet/gym
     resep baru DIVALIDASI dari gizi terhitung (diet: <=400 kkal & serat
     >=2 g/porsi; gym: protein >=20 g/porsi) — skrip berhenti bila meleset.
  2. Beri token "kos" pada kolom `tag` resep yang jumlah BAHAN INTI-nya <= 5.
     Bahan inti = semua bahan resep SELAIN bumbu dasar (daftar BUMBU_DASAR).
     Token lama (diet/gym) dipertahankan; "kos" ditambahkan di akhir.
     Resep yang sudah punya token "kos" dilewati.

Jalankan setelah ekspansi_resep.py:
    python label_kos.py
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "menuhemat.db")

# Bumbu dasar — TIDAK dihitung sebagai bahan inti (nama disamakan dengan
# entri tabel bahan, perbandingan tidak peka huruf besar/kecil).
BUMBU_DASAR = {
    "garam", "gula pasir", "gula merah", "gula aren",
    "merica bubuk", "merica", "lada bubuk", "lada",
    "kaldu bubuk", "penyedap rasa",
    "minyak goreng", "minyak sayur", "margarin", "air",
    "kecap manis", "kecap asin",
    "saus tiram", "saus sambal", "saus tomat", "cuka",
}

# ------------------------------------------------------------- resep baru
# Format sama dengan resep_baru.py. Semua bahan inti <= 5; bumbu dasar
# (kecap manis, garam, merica, minyak, margarin) tidak dihitung.
RESEP_KOS = [
    {
        "nama": "Ayam Panggang Teflon", "asal": "Nusantara", "tag": "gym",
        "kategori": "makan_malam", "porsi": 4, "waktu": 25,
        "tingkat": "mudah",
        "deskripsi": "Ayam panggang teflon bumbu bawang putih sederhana, "
                     "tinggi protein dan ramah dapur kos.",
        "tags_rasa": "gurih,smoky",
        "bahan": [("Daging ayam", 600, "g", 0), ("Bawang putih", 4, "siung", 0),
                  ("Garam", 1, "sdt", 0), ("Merica bubuk", 1, "sdt", 0),
                  ("Minyak goreng", 1, "sdm", 0)],
        "langkah": [
            "Potong 600 g daging ayam menjadi 8 potong, sayat permukaannya agar bumbu meresap.",
            "Haluskan 4 siung bawang putih, campur dengan 1 sdt garam dan 1 sdt merica bubuk, balurkan ke ayam, lalu diamkan 10 menit.",
            "Panaskan teflon dengan 1 sdm minyak goreng, panggang ayam dengan api sedang.",
            "Balik sesekali dan masak sekitar 15 menit sampai matang kecokelatan.",
            "Angkat dan sajikan hangat.",
        ],
    },
    {
        "nama": "Ayam Suwir Kemangi", "asal": "Sunda", "tag": "gym",
        "kategori": "makan_siang", "porsi": 4, "waktu": 35,
        "tingkat": "mudah",
        "deskripsi": "Ayam suwir pedas wangi kemangi khas Sunda, lauk "
                     "berprotein tinggi dengan bahan seadanya.",
        "tags_rasa": "gurih,pedas_sedang,harum",
        "bahan": [("Daging ayam", 600, "g", 0), ("Bawang merah", 6, "siung", 0),
                  ("Bawang putih", 3, "siung", 0), ("Cabai rawit merah", 5, "buah", 0),
                  ("Kemangi", 1, "ikat", 0), ("Garam", 1, "sdt", 0),
                  ("Gula pasir", 1, "sdt", 0), ("Minyak goreng", 2, "sdm", 0)],
        "langkah": [
            "Rebus 600 g daging ayam sampai matang, angkat, suwir-suwir, dan sisihkan kaldunya.",
            "Haluskan 6 siung bawang merah, 3 siung bawang putih, dan 5 buah cabai rawit merah.",
            "Tumis bumbu halus dengan 2 sdm minyak goreng sampai harum dan matang.",
            "Masukkan ayam suwir, bumbui 1 sdt garam dan 1 sdt gula pasir, tuang sedikit kaldu, lalu masak sampai bumbu meresap dan agak kering.",
            "Masukkan daun kemangi dari 1 ikat, aduk sebentar sampai layu, lalu sajikan.",
        ],
    },
    {
        "nama": "Ikan Kembung Goreng Sambal", "asal": "Sumatera", "tag": "gym",
        "kategori": "makan_malam", "porsi": 4, "waktu": 30,
        "tingkat": "mudah",
        "deskripsi": "Ikan kembung goreng disiram sambal tomat segar, "
                     "protein tinggi khas lauk anak kos.",
        "tags_rasa": "gurih,pedas_sedang,segar",
        "bahan": [("Ikan kembung", 600, "g", 0), ("Cabai merah keriting", 30, "g", 0),
                  ("Bawang merah", 6, "siung", 0), ("Tomat", 150, "g", 0),
                  ("Garam", 1, "sdt", 0), ("Gula pasir", 1, "sdt", 0),
                  ("Minyak goreng", 3, "sdm", 0)],
        "langkah": [
            "Bersihkan 600 g ikan kembung, lumuri sebagian dari 1 sdt garam, lalu diamkan 10 menit.",
            "Goreng ikan dengan 3 sdm minyak goreng sampai matang dan kulitnya kering, angkat dan tiriskan.",
            "Haluskan 30 g cabai merah keriting, 6 siung bawang merah, dan 150 g tomat.",
            "Tumis bumbu halus dengan sisa minyak sampai harum, bumbui sisa garam dan 1 sdt gula pasir.",
            "Siram sambal di atas ikan goreng dan sajikan.",
        ],
    },
    {
        "nama": "Tempe Bakar Teflon", "asal": "Jawa", "tag": "diet,gym",
        "kategori": "makan_siang", "porsi": 4, "waktu": 20,
        "tingkat": "mudah",
        "deskripsi": "Tempe bakar kecap di teflon tanpa goreng rendam minyak, "
                     "rendah kalori tapi tetap tinggi protein.",
        "tags_rasa": "manis,gurih,smoky",
        "bahan": [("Tempe", 500, "g", 0), ("Bawang putih", 3, "siung", 0),
                  ("Kecap manis", 3, "sdm", 0), ("Garam", 1, "sdt", 0),
                  ("Margarin", 1, "sdm", 0)],
        "langkah": [
            "Potong 500 g tempe menjadi 8 irisan tebal.",
            "Haluskan 3 siung bawang putih, campur dengan 3 sdm kecap manis dan 1 sdt garam, lalu rendam tempe 10 menit.",
            "Panaskan teflon dan olesi 1 sdm margarin.",
            "Bakar tempe sambil dibalik sampai kedua sisi kecokelatan dan bumbu meresap, sekitar 8 menit.",
            "Angkat dan sajikan hangat sebagai lauk atau camilan.",
        ],
    },
    {
        "nama": "Tahu Telur", "asal": "Jawa", "tag": "gym",
        "kategori": "makan_malam", "porsi": 4, "waktu": 25,
        "tingkat": "mudah",
        "deskripsi": "Dadar tahu telur tebal khas Jawa Timur, mengenyangkan "
                     "dan kaya protein dari dua bahan utama saja.",
        "tags_rasa": "gurih,lembut",
        "bahan": [("Tahu", 600, "g", 0), ("Telur ayam", 6, "butir", 0),
                  ("Bawang putih", 3, "siung", 0), ("Daun bawang", 1, "ikat", 0),
                  ("Garam", 1, "sdt", 0), ("Merica bubuk", 1, "sdt", 0),
                  ("Minyak goreng", 3, "sdm", 0)],
        "langkah": [
            "Hancurkan kasar 600 g tahu dengan garpu.",
            "Kocok 6 butir telur ayam, campur dengan tahu, 3 siung bawang putih halus, irisan daun bawang dari 1 ikat, 1 sdt garam, dan 1 sdt merica bubuk.",
            "Panaskan 3 sdm minyak goreng di teflon anti lengket.",
            "Tuang adonan, masak dengan api kecil sampai bawahnya kokoh, lalu balik dan masak sisi lainnya sampai matang.",
            "Potong-potong dan sajikan hangat.",
        ],
    },
    {
        "nama": "Roti Lapis Telur Keju", "asal": "Western", "tag": "gym",
        "kategori": "sarapan", "porsi": 4, "waktu": 15,
        "tingkat": "mudah",
        "deskripsi": "Roti lapis orak-arik telur dan keju untuk sarapan cepat "
                     "berprotein tinggi, tanpa perlu banyak bahan.",
        "tags_rasa": "gurih,creamy,segar",
        "bahan": [("Roti tawar", 240, "g", 0), ("Telur ayam", 8, "butir", 0),
                  ("Keju cheddar", 60, "g", 0), ("Selada", 100, "g", 0),
                  ("Margarin", 1, "sdm", 0), ("Garam", 1, "sdt", 0),
                  ("Merica bubuk", 1, "sdt", 0)],
        "langkah": [
            "Kocok 8 butir telur ayam dengan 1 sdt garam dan 1 sdt merica bubuk.",
            "Lelehkan 1 sdm margarin di teflon, buat orak-arik telur sampai matang lembut, lalu angkat.",
            "Panggang 8 lembar roti tawar (240 g) sebentar di teflon yang sama sampai agak renyah.",
            "Susun roti lapis: roti, daun selada dari 100 g dibagi rata, orak-arik telur, dan 60 g keju cheddar, lalu tutup dengan roti.",
            "Potong diagonal dan sajikan.",
        ],
    },
    {
        "nama": "Sup Telur Tomat Wortel", "asal": "Asia", "tag": "diet",
        "kategori": "makan_malam", "porsi": 4, "waktu": 20,
        "tingkat": "mudah",
        "deskripsi": "Sup telur serabut dengan tomat dan wortel ala rumahan "
                     "Tionghoa, ringan dan rendah kalori.",
        "tags_rasa": "segar,berkuah,hangat",
        "bahan": [("Telur ayam", 4, "butir", 0), ("Tomat", 300, "g", 0),
                  ("Wortel", 200, "g", 0), ("Bawang putih", 3, "siung", 0),
                  ("Daun bawang", 1, "ikat", 0), ("Garam", 1, "sdt", 0),
                  ("Merica bubuk", 1, "sdt", 0), ("Minyak goreng", 1, "sdm", 0)],
        "langkah": [
            "Potong 300 g tomat dan 200 g wortel, iris 3 siung bawang putih dan daun bawang dari 1 ikat.",
            "Tumis bawang putih dengan 1 sdm minyak goreng sampai harum, masukkan tomat dan masak sampai layu.",
            "Tuang 1 liter air, masukkan wortel, lalu masak sampai wortel empuk.",
            "Kocok lepas 4 butir telur, tuang perlahan sambil diaduk hingga membentuk serabut.",
            "Bumbui 1 sdt garam dan 1 sdt merica bubuk, taburi daun bawang, lalu sajikan hangat.",
        ],
    },
    {
        "nama": "Nasi Goreng Telur Kos", "asal": "Jawa", "tag": "",
        "kategori": "makan_malam", "porsi": 4, "waktu": 20,
        "tingkat": "mudah",
        "deskripsi": "Nasi goreng telur sederhana lima bahan inti, andalan "
                     "anak kos untuk menghabiskan nasi sisa.",
        "tags_rasa": "gurih,pedas_ringan,manis",
        "bahan": [("Beras", 400, "g", 0), ("Telur ayam", 4, "butir", 0),
                  ("Bawang merah", 5, "siung", 0), ("Bawang putih", 3, "siung", 0),
                  ("Cabai rawit merah", 4, "buah", 0), ("Kecap manis", 3, "sdm", 0),
                  ("Garam", 1, "sdt", 0), ("Minyak goreng", 3, "sdm", 0)],
        "langkah": [
            "Masak 400 g beras menjadi nasi, lalu dinginkan sebentar agar tidak lembek saat digoreng.",
            "Haluskan 5 siung bawang merah, 3 siung bawang putih, dan 4 buah cabai rawit merah.",
            "Panaskan 3 sdm minyak goreng, tumis bumbu halus sampai harum, lalu sisihkan ke tepi wajan.",
            "Masukkan 4 butir telur kocok, buat orak-arik, lalu campur dengan bumbu.",
            "Masukkan nasi, tambahkan 3 sdm kecap manis dan 1 sdt garam, aduk rata dengan api besar sampai matang, lalu sajikan.",
        ],
    },
]


# ---------------------------------------------------------------- util
def token(tag):
    return [t.strip() for t in (tag or "").split(",") if t.strip()]


def bahan_inti(con, resep_id):
    nama = [r[0] for r in con.execute(
        "SELECT b.nama FROM resep_bahan rb JOIN bahan b ON b.id = rb.bahan_id"
        " WHERE rb.resep_id = ?", (resep_id,))]
    return [n for n in nama if n.strip().lower() not in BUMBU_DASAR]


def tabel_konversi(con):
    khusus, umum = {}, {}
    for bid, dari, ke, faktor in con.execute(
            "SELECT bahan_id, dari_satuan, ke_satuan, faktor FROM konversi_satuan"):
        if bid:
            khusus[(bid, dari, ke)] = faktor
        else:
            umum[(dari, ke)] = faktor
    return khusus, umum


def gizi_per_porsi(con, resep_id, khusus, umum):
    """Sama dengan gizi_resep() di app.py: total dari komposisi / porsi."""
    r = con.execute("SELECT porsi FROM resep WHERE id = ?", (resep_id,)).fetchone()
    tot = dict.fromkeys(("kalori", "protein", "karbo", "lemak", "serat", "natrium"), 0.0)
    for bid, dasar, jumlah, satuan, kal, pro, kar, lem, ser, nat in con.execute(
            """SELECT b.id, b.satuan_dasar, rb.jumlah, rb.satuan,
                      g.kalori, g.protein, g.karbo, g.lemak, g.serat, g.natrium
               FROM resep_bahan rb JOIN bahan b ON b.id = rb.bahan_id
               LEFT JOIN gizi_bahan g ON g.bahan_id = b.id
               WHERE rb.resep_id = ?""", (resep_id,)):
        if kal is None:
            continue
        faktor = khusus.get((bid, satuan, dasar), umum.get((satuan, dasar), 1))
        f = jumlah * faktor / 100.0
        tot["kalori"] += f * kal
        tot["protein"] += f * pro
        tot["karbo"] += f * kar
        tot["lemak"] += f * lem
        tot["serat"] += f * ser
        tot["natrium"] += f * nat
    porsi = r[0] or 1
    return {k: v / porsi for k, v in tot.items()}


def hitung_pool(con):
    kos = diet = gym = 0
    for (tag,) in con.execute("SELECT tag FROM resep"):
        tk = token(tag)
        if "kos" in tk:
            kos += 1
            diet += "diet" in tk
            gym += "gym" in tk
    return kos, diet, gym


# ---------------------------------------------------------------- langkah
def tambah_resep_kos(con):
    bahan_id = {r[1]: r[0] for r in con.execute("SELECT id, nama FROM bahan")}
    tidak_dikenal = {n for r in RESEP_KOS for (n, *_x) in r["bahan"]
                     if n not in bahan_id}
    if tidak_dikenal:
        raise SystemExit("BAHAN TIDAK DIKENAL: " + ", ".join(sorted(tidak_dikenal)))
    baru = 0
    for r in RESEP_KOS:
        if con.execute("SELECT id FROM resep WHERE nama = ?",
                       (r["nama"],)).fetchone():
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


def validasi_resep_baru(con, khusus, umum):
    """Tag diet/gym resep baru harus lolos kriteria dari gizi terhitung."""
    gagal = []
    for r in RESEP_KOS:
        row = con.execute("SELECT id FROM resep WHERE nama = ?",
                          (r["nama"],)).fetchone()
        if not row:
            continue
        gz = gizi_per_porsi(con, row[0], khusus, umum)
        inti = bahan_inti(con, row[0])
        if len(inti) > 5:
            gagal.append(f"{r['nama']}: bahan inti {len(inti)} > 5")
        tk = token(r.get("tag"))
        if "diet" in tk and not (gz["kalori"] <= 400 and gz["serat"] >= 2):
            gagal.append(f"{r['nama']}: tag diet tapi {gz['kalori']:.0f} kkal, "
                         f"serat {gz['serat']:.1f} g/porsi")
        if "gym" in tk and gz["protein"] < 20:
            gagal.append(f"{r['nama']}: tag gym tapi protein "
                         f"{gz['protein']:.1f} g/porsi")
        print(f"  - {r['nama']}: inti {len(inti)}, {gz['kalori']:.0f} kkal, "
              f"protein {gz['protein']:.1f} g, serat {gz['serat']:.1f} g /porsi"
              f" | tag={r.get('tag') or '-'}")
    if gagal:
        raise SystemExit("VALIDASI GAGAL:\n  " + "\n  ".join(gagal))


def beri_label_kos(con):
    berubah = 0
    for rid, tag in con.execute("SELECT id, tag FROM resep").fetchall():
        tk = token(tag)
        if "kos" in tk:
            continue
        if len(bahan_inti(con, rid)) <= 5:
            con.execute("UPDATE resep SET tag = ? WHERE id = ?",
                        (",".join(tk + ["kos"]), rid))
            berubah += 1
    return berubah


def main():
    con = sqlite3.connect(DB)
    try:
        khusus, umum = tabel_konversi(con)
        sebelum = hitung_pool(con)
        n_baru = tambah_resep_kos(con)
        print("Validasi resep baru (gizi terhitung dari bahan):")
        validasi_resep_baru(con, khusus, umum)
        n_label = beri_label_kos(con)
        con.commit()
        sesudah = hitung_pool(con)
        total = con.execute("SELECT COUNT(*) FROM resep").fetchone()[0]
    finally:
        con.close()
    print(f"\nOK: +{n_baru} resep baru, {n_label} resep diberi label kos.")
    print(f"Pool kos SEBELUM: total {sebelum[0]}, kos+diet {sebelum[1]}, "
          f"kos+gym {sebelum[2]}")
    print(f"Pool kos SESUDAH: total {sesudah[0]}, kos+diet {sesudah[1]}, "
          f"kos+gym {sesudah[2]} (dari {total} resep)")


if __name__ == "__main__":
    main()
