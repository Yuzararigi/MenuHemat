#!/usr/bin/env python3
"""
MenuHemat v2 — aplikasi web rekomendasi menu termurah harian
berbasis data harga bahan pokok pasar (PIHPS Bank Indonesia).

Fitur: menu termurah (ranking Rp/porsi), info gizi (estimasi),
langkah memasak, pilihan wilayah (provinsi), favorit, pantangan,
perencana mingguan + daftar belanja, kalkulator budget,
mode super hemat, peringatan harga cerdas, akun admin & user.

Jalankan:
    python app.py
Lalu buka: http://127.0.0.1:5000
"""
import os
import sqlite3
import threading
from functools import wraps

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "menuhemat.db")
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
SATUAN_OPSI = ["g", "ml", "sdm", "sdt", "butir", "siung", "buah", "ikat",
               "batang", "lembar", "tongkol", "bungkus", "papan"]
BARIS_BAHAN_FORM = 16  # jumlah baris bahan di form admin resep

app = Flask(__name__)
app.secret_key = os.environ.get("MENUHEMAT_SECRET",
                                "menuhemat-dev-ganti-dengan-yang-acak")

KATEGORI_LABEL = {
    "sarapan": "Sarapan",
    "makan_siang": "Makan Siang",
    "makan_malam": "Makan Malam",
    "camilan": "Camilan",
    "bekal": "Bekal",
}

ASAL_LABEL = ["Jawa", "Sunda", "Sumatera", "Bali", "Sulawesi", "Kalimantan",
              "Western", "Asia", "Timur", "Nusantara"]

URUT_LABEL = {
    "harga": "Harga termurah",
    "kalori-rendah": "Kalori terendah",
    "kalori-tinggi": "Kalori tertinggi",
    "protein": "Protein tertinggi",
    "karbo-rendah": "Karbohidrat terendah",
    "karbo-tinggi": "Karbohidrat tertinggi",
    "lemak-rendah": "Lemak terendah",
    "serat": "Serat tertinggi",
    "natrium": "Natrium terendah",
}


# ---------- util ----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def rupiah(x):
    try:
        return "Rp" + f"{int(round(float(x))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


app.jinja_env.filters["rp"] = rupiah
app.jinja_env.globals["kat_label"] = lambda k: KATEGORI_LABEL.get(k, k)


def sumber_label(sumber):
    """Label sumber data harga yang ramah dibaca."""
    if sumber == "PIHPS":
        return "PIHPS Nasional \u00b7 Bank Indonesia"
    if sumber == "SAMPLE":
        return "Data contoh (mode offline)"
    return sumber or "-"


app.jinja_env.globals["sumber_label"] = sumber_label


def me():
    """User yang sedang login (row) atau None untuk pengunjung."""
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not me():
            flash("Masuk dulu untuk memakai fitur ini.")
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        u = me()
        if not u:
            flash("Masuk sebagai admin untuk membuka halaman ini.")
            return redirect(url_for("login", next=request.path))
        if u["role"] != "admin":
            return render_template("403.html", active=""), 403
        return f(*a, **kw)
    return wrapper


def daftar_wilayah():
    """Daftar wilayah (provinsi) dari data harga. PIHPS hanya level provinsi."""
    rows = get_db().execute(
        "SELECT DISTINCT wilayah FROM harga_harian ORDER BY wilayah").fetchall()
    wils = [r[0] for r in rows]
    # NASIONAL selalu paling depan
    wils = sorted(wils, key=lambda w: (w != "NASIONAL", w))
    return wils


def wilayah_aktif():
    """Wilayah yang dipakai saat ini: akun user, atau session untuk tamu."""
    u = me()
    if u and u["wilayah"]:
        return u["wilayah"]
    return session.get("wilayah", "NASIONAL")


@app.context_processor
def inject_global():
    return {"me": me(), "daftar_wilayah": daftar_wilayah(),
            "wilayah_aktif": wilayah_aktif()}


def harga_terbaru(wilayah):
    """Kembalikan (price_map, tanggal, sumber, wilayah_aktual).

    price_map: komoditas_id -> harga Rp per satuan_harga (kg).
    Jika wilayah tidak ada datanya, fallback ke NASIONAL.
    """
    con = get_db()
    tgl = con.execute(
        "SELECT MAX(tanggal) FROM harga_harian WHERE wilayah = ?", (wilayah,)
    ).fetchone()[0]
    wil = wilayah
    if not tgl:
        wil = "NASIONAL"
        tgl = con.execute(
            "SELECT MAX(tanggal) FROM harga_harian WHERE wilayah = 'NASIONAL'"
        ).fetchone()[0]
    prices, sumber = {}, None
    if tgl:
        for r in con.execute(
            "SELECT komoditas_id, harga_rp, sumber FROM harga_harian "
            "WHERE tanggal = ? AND wilayah = ?", (tgl, wil)
        ):
            prices[r["komoditas_id"]] = r["harga_rp"]
            sumber = r["sumber"]
    return prices, tgl, sumber, wil


def _tabel_konversi(con):
    khusus, umum = {}, {}
    for r in con.execute(
        "SELECT bahan_id, dari_satuan, ke_satuan, faktor FROM konversi_satuan"
    ):
        if r["bahan_id"]:
            khusus[(r["bahan_id"], r["dari_satuan"], r["ke_satuan"])] = r["faktor"]
        else:
            umum[(r["dari_satuan"], r["ke_satuan"])] = r["faktor"]
    return khusus, umum


def _qty_dasar(khusus, umum, bahan_id, jumlah, satuan, satuan_dasar):
    faktor = khusus.get((bahan_id, satuan, satuan_dasar))
    if faktor is None:
        faktor = umum.get((satuan, satuan_dasar), 1)
    return jumlah * faktor


def biaya_resep(con, resep_id, prices, super_hemat=False):
    """Hitung biaya resep. Kembalikan dict(total, per_porsi, porsi,
    items, dilewati). items: list dict(nama, takaran, harga_label, biaya)."""
    r = con.execute("SELECT * FROM resep WHERE id = ?", (resep_id,)).fetchone()
    if r is None:
        return None
    khusus, umum = _tabel_konversi(con)
    items, total, dilewati = [], 0.0, 0
    for b in con.execute(
        """SELECT b.*, rb.jumlah, rb.satuan, rb.opsional
           FROM resep_bahan rb JOIN bahan b ON b.id = rb.bahan_id
           WHERE rb.resep_id = ? ORDER BY b.nama""", (resep_id,)):
        if super_hemat and b["opsional"]:
            dilewati += 1
            continue
        qty_dasar = _qty_dasar(khusus, umum, b["id"], b["jumlah"],
                               b["satuan"], b["satuan_dasar"])
        if b["komoditas_id"] and b["komoditas_id"] in prices:
            rp_per_dasar = prices[b["komoditas_id"]] / 1000.0
            harga_label = rupiah(prices[b["komoditas_id"]]) + "/kg"
        else:
            rp_per_dasar = (b["harga_manual_rp"] or 0) / (b["isi_satuan_manual"] or 1)
            harga_label = (rupiah(b["harga_manual_rp"]) + "/" +
                           (b["satuan_manual"] or "satuan") + " (estimasi)")
        biaya = qty_dasar * rp_per_dasar
        total += biaya
        items.append({
            "nama": b["nama"],
            "takaran": f"{b['jumlah']:g} {b['satuan']}",
            "harga_label": harga_label,
            "biaya": biaya,
        })
    return {"resep": r, "total": total, "per_porsi": total / (r["porsi"] or 1),
            "porsi": r["porsi"], "items": items, "dilewati": dilewati}


def gizi_resep(con, resep_id):
    """Hitung total gizi resep dari gizi_bahan (per 100 g/ml).
    Kembalikan dict(total, per_porsi, ada). Semua angka ESTIMASI."""
    r = con.execute("SELECT * FROM resep WHERE id = ?", (resep_id,)).fetchone()
    if r is None:
        return None
    khusus, umum = _tabel_konversi(con)
    tot = {"kalori": 0.0, "protein": 0.0, "karbo": 0.0,
           "lemak": 0.0, "serat": 0.0, "natrium": 0.0}
    ada = False
    for b in con.execute(
        """SELECT b.id, b.satuan_dasar, rb.jumlah, rb.satuan,
                  g.kalori, g.protein, g.karbo, g.lemak, g.serat, g.natrium
           FROM resep_bahan rb
           JOIN bahan b ON b.id = rb.bahan_id
           LEFT JOIN gizi_bahan g ON g.bahan_id = b.id
           WHERE rb.resep_id = ?""", (resep_id,)):
        if b["kalori"] is None:
            continue
        ada = True
        qty_dasar = _qty_dasar(khusus, umum, b["id"], b["jumlah"],
                               b["satuan"], b["satuan_dasar"])
        f = qty_dasar / 100.0  # data gizi per 100 g/ml
        tot["kalori"] += f * b["kalori"]
        tot["protein"] += f * b["protein"]
        tot["karbo"] += f * b["karbo"]
        tot["lemak"] += f * b["lemak"]
        tot["serat"] += f * b["serat"]
        tot["natrium"] += f * b["natrium"]
    porsi = r["porsi"] or 1
    per_porsi = {k: v / porsi for k, v in tot.items()}
    return {"total": tot, "per_porsi": per_porsi, "ada": ada, "porsi": porsi}


def pantangan_ids(uid):
    return {r[0] for r in get_db().execute(
        "SELECT bahan_id FROM user_pantangan WHERE user_id = ?", (uid,))}


def favorit_ids(uid):
    return {r[0] for r in get_db().execute(
        "SELECT resep_id FROM user_favorit_resep WHERE user_id = ?", (uid,))}


def mengandung_pantangan(con, resep_id, pant):
    if not pant:
        return False
    rows = con.execute(
        "SELECT bahan_id FROM resep_bahan WHERE resep_id = ?", (resep_id,)).fetchall()
    return any(r[0] in pant for r in rows)


def qty_cantik(qty, dasar):
    if dasar == "g" and qty >= 1000:
        return f"{qty / 1000:.1f} kg"
    if dasar == "ml" and qty >= 1000:
        return f"{qty / 1000:.1f} liter"
    unit = "gram" if dasar == "g" else "ml"
    return f"{qty:.0f} {unit}"


# ---------- auth ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if me():
        return redirect(url_for("index"))
    err = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        u = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if u and u["password_hash"] and check_password_hash(u["password_hash"], password):
            session["user_id"] = u["id"]
            flash(f"Selamat datang, {u['nama'] or u['username']}!")
            nxt = request.args.get("next") or request.form.get("next") or url_for("index")
            if not nxt.startswith("/"):
                nxt = url_for("index")
            return redirect(nxt)
        err = "Username atau password salah."
    return render_template("login.html", active="", err=err,
                           next=request.args.get("next", ""))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Kamu sudah keluar.")
    return redirect(url_for("index"))


@app.route("/ganti-password", methods=["GET", "POST"])
@login_required
def ganti_password():
    err = None
    if request.method == "POST":
        lama = request.form.get("lama", "")
        baru = request.form.get("baru", "")
        baru2 = request.form.get("baru2", "")
        u = me()
        if not check_password_hash(u["password_hash"], lama):
            err = "Password lama salah."
        elif len(baru) < 4:
            err = "Password baru minimal 4 karakter."
        elif baru != baru2:
            err = "Konfirmasi password baru tidak sama."
        else:
            get_db().execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(baru), u["id"]))
            get_db().commit()
            flash("Password berhasil diganti.")
            return redirect(url_for("index"))
    return render_template("ganti_password.html", active="", err=err)


@app.route("/wilayah", methods=["POST"])
def set_wilayah():
    wil = request.form.get("wilayah", "NASIONAL")
    valid = daftar_wilayah()
    if wil not in valid:
        wil = "NASIONAL"
    u = me()
    if u:
        get_db().execute("UPDATE users SET wilayah = ? WHERE id = ?",
                         (wil, u["id"]))
        get_db().commit()
    else:
        session["wilayah"] = wil
    return redirect(request.referrer or url_for("index"))


# ---------- beranda ----------

@app.route("/")
def index():
    con = get_db()
    u = me()
    uid = u["id"] if u else None
    prices, tgl, sumber, wil = harga_terbaru(wilayah_aktif())
    pant = pantangan_ids(uid) if uid else set()
    fav = favorit_ids(uid) if uid else set()

    kat = request.args.get("kategori", "")
    asal = request.args.get("asal", "")
    tagf = request.args.get("tag", "")
    urut = request.args.get("urut", "harga")
    if urut not in URUT_LABEL:
        urut = "harga"
    maks = request.args.get("maks", "").strip()
    super_hemat = request.args.get("hemat") == "1"
    budget_txt = request.args.get("budget", "").strip()
    s1 = request.args.get("s1", "").strip()
    s2 = request.args.get("s2", "").strip()
    s3 = request.args.get("s3", "").strip()
    auto = request.args.get("auto") == "1"

    def _kol(row, nama):
        # kolom asal/tag hanya ada setelah migrasi ekspansi_resep.py
        try:
            return row[nama]
        except (IndexError, KeyError):
            return None

    cards, disembunyikan = [], 0
    for r in con.execute("SELECT * FROM resep ORDER BY nama"):
        if mengandung_pantangan(con, r["id"], pant):
            disembunyikan += 1
            continue
        c = biaya_resep(con, r["id"], prices, super_hemat)
        if kat and r["kategori"] != kat:
            continue
        if asal and (_kol(r, "asal") or "") != asal:
            continue
        tag_list = [t.strip() for t in (_kol(r, "tag") or "").split(",")
                    if t.strip()]
        if tagf and tagf not in tag_list:
            continue
        if maks:
            try:
                if c["per_porsi"] > float(maks):
                    continue
            except ValueError:
                pass
        gz = gizi_resep(con, r["id"])
        cards.append({"resep": r, "total": c["total"],
                      "per_porsi": c["per_porsi"],
                      "favorit": r["id"] in fav,
                      "dilewati": c["dilewati"],
                      "asal": _kol(r, "asal"),
                      "tag_list": tag_list,
                      "gizi": gz["per_porsi"],
                      "kkal_porsi": round(gz["per_porsi"]["kalori"]) if gz["ada"] else None})
    if urut == "kalori-rendah":
        cards.sort(key=lambda x: x["gizi"]["kalori"])
    elif urut == "kalori-tinggi":
        cards.sort(key=lambda x: -x["gizi"]["kalori"])
    elif urut == "protein":
        cards.sort(key=lambda x: -x["gizi"]["protein"])
    elif urut == "karbo-rendah":
        cards.sort(key=lambda x: x["gizi"]["karbo"])
    elif urut == "karbo-tinggi":
        cards.sort(key=lambda x: -x["gizi"]["karbo"])
    elif urut == "lemak-rendah":
        cards.sort(key=lambda x: x["gizi"]["lemak"])
    elif urut == "serat":
        cards.sort(key=lambda x: -x["gizi"]["serat"])
    elif urut == "natrium":
        cards.sort(key=lambda x: x["gizi"]["natrium"])
    else:
        cards.sort(key=lambda x: x["per_porsi"])

    # --- cek satu hari makan: mulai kosong, user pilih sendiri ---
    opsi = {"sarapan": [], "makan_siang": [], "makan_malam": []}
    for c in cards:
        kk = c["resep"]["kategori"]
        if kk in opsi:
            opsi[kk].append({"id": c["resep"]["id"], "nama": c["resep"]["nama"],
                            "per_porsi": c["per_porsi"]})

    harian, budget_err = None, None
    if auto or s1 or s2 or s3:
        if auto:
            # isi otomatis dengan hidangan termurah per waktu makan
            for kk, kunci in (("sarapan", "s1"), ("makan_siang", "s2"),
                              ("makan_malam", "s3")):
                best = min(opsi[kk], key=lambda o: o["per_porsi"],
                           default=None)
                val = str(best["id"]) if best else ""
                if kunci == "s1":
                    s1 = val
                elif kunci == "s2":
                    s2 = val
                else:
                    s3 = val
        items = []
        for rid in (s1, s2, s3):
            c = next((c for c in cards if str(c["resep"]["id"]) == rid),
                     None)
            if c:
                items.append(c)
        total = sum(c["total"] for c in items)
        budget, masuk = None, None
        if budget_txt:
            try:
                budget = float(budget_txt)
                masuk = total <= budget
            except ValueError:
                budget_err = "Masukkan angka, contoh: 50000"
        harian = {"items": items, "total": total,
                  "budget": budget, "masuk": masuk}

    semua_bahan, pant_info = [], {}
    if uid:
        semua_bahan = con.execute(
            "SELECT * FROM bahan ORDER BY kategori, nama").fetchall()
        pant_info = {r["bahan_id"]: r["alasan"] for r in con.execute(
            "SELECT bahan_id, alasan FROM user_pantangan WHERE user_id = ?", (uid,))}

    return render_template(
        "index.html", active="home", cards=cards, tgl=tgl, sumber=sumber,
        wilayah_tampil=wil, disembunyikan=disembunyikan, kat=kat,
        kategoris=KATEGORI_LABEL, maks=maks, super_hemat=super_hemat,
        asal=asal, asals=ASAL_LABEL, tagf=tagf, urut=urut, uruts=URUT_LABEL,
        budget_txt=budget_txt, budget_err=budget_err,
        opsi=opsi, s1=s1, s2=s2, s3=s3, harian=harian,
        semua_bahan=semua_bahan, pant_info=pant_info,
        ada_harga=bool(prices))


@app.route("/favorit/<int:resep_id>", methods=["POST"])
@login_required
def toggle_favorit(resep_id):
    con = get_db()
    uid = me()["id"]
    ada = con.execute(
        "SELECT 1 FROM user_favorit_resep WHERE user_id = ? AND resep_id = ?",
        (uid, resep_id)).fetchone()
    if ada:
        con.execute(
            "DELETE FROM user_favorit_resep WHERE user_id = ? AND resep_id = ?",
            (uid, resep_id))
    else:
        con.execute(
            "INSERT INTO user_favorit_resep (user_id, resep_id) VALUES (?, ?)",
            (uid, resep_id))
    con.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/pantangan", methods=["POST"])
@login_required
def simpan_pantangan():
    con = get_db()
    uid = me()["id"]
    dipilih = request.form.getlist("bahan")
    con.execute("DELETE FROM user_pantangan WHERE user_id = ?", (uid,))
    for bid in dipilih:
        try:
            con.execute(
                "INSERT INTO user_pantangan (user_id, bahan_id, alasan) VALUES (?, ?, 'pantangan')",
                (uid, int(bid)))
        except ValueError:
            continue
    con.commit()
    return redirect(url_for("index") + "#pantangan")


# ---------- detail resep ----------

@app.route("/resep/<int:resep_id>")
def detail_resep(resep_id):
    con = get_db()
    prices, tgl, sumber, wil = harga_terbaru(wilayah_aktif())
    normal = biaya_resep(con, resep_id, prices, super_hemat=False)
    if normal is None:
        return "Resep tidak ditemukan", 404
    hemat = biaya_resep(con, resep_id, prices, super_hemat=True)
    gz = gizi_resep(con, resep_id)
    langkah = [s for s in (normal["resep"]["langkah"] or "").split("\n") if s.strip()]
    u = me()
    fav = u and resep_id in favorit_ids(u["id"])
    return render_template("resep.html", active="home", normal=normal,
                           hemat=hemat, gizi=gz, langkah=langkah,
                           tgl=tgl, sumber=sumber,
                           wilayah_tampil=wil, favorit=fav)


# ---------- perencana mingguan ----------

def _rencana_tersimpan(con, uid):
    return {r["hari"]: r["resep_id"] for r in
            con.execute("SELECT hari, resep_id FROM rencana WHERE user_id = ?",
                        (uid,))}


@app.route("/rencana", methods=["GET", "POST"])
@login_required
def rencana():
    con = get_db()
    uid = me()["id"]
    prices, tgl, sumber, wil = harga_terbaru(wilayah_aktif())
    pant = pantangan_ids(uid)
    pesan = None

    if request.method == "POST":
        aksi = request.form.get("aksi", "manual")
        if aksi == "manual":
            for h in HARI:
                rid = request.form.get("hari_" + h, "").strip()
                if rid:
                    con.execute(
                        "INSERT OR REPLACE INTO rencana (user_id, hari, resep_id)"
                        " VALUES (?, ?, ?)", (uid, h, int(rid)))
                else:
                    con.execute("DELETE FROM rencana WHERE user_id = ? AND hari = ?",
                                (uid, h))
            con.commit()
            pesan = "Rencana mingguan disimpan."
        elif aksi == "otomatis":
            try:
                budget = float(request.form.get("budget_mingguan", "350000") or 0)
            except ValueError:
                budget = 0
            hasil = rencana_otomatis(con, prices, pant, budget)
            for h, rid in zip(HARI, hasil["pilihan"]):
                con.execute(
                    "INSERT OR REPLACE INTO rencana (user_id, hari, resep_id)"
                    " VALUES (?, ?, ?)", (uid, h, rid))
            con.commit()
            if hasil["masuk"]:
                pesan = (f"Rencana otomatis dibuat: estimasi {rupiah(hasil['total'])} "
                         f"untuk 7 hari (budget {rupiah(budget)}).")
            else:
                pesan = (f"Resep termurah pun butuh {rupiah(hasil['total'])} untuk 7 hari, "
                         f"melebihi budget {rupiah(budget)}. Naikkan budget atau aktifkan mode hemat.")

    tersimpan = _rencana_tersimpan(con, uid)
    semua_resep = con.execute("SELECT id, nama, kategori FROM resep ORDER BY nama").fetchall()

    # susun tampilan + daftar belanja agregat
    baris, belanja, total = [], {}, 0.0
    khusus, umum = _tabel_konversi(con)
    for h in HARI:
        rid = tersimpan.get(h)
        if not rid:
            baris.append({"hari": h, "resep": None})
            continue
        c = biaya_resep(con, rid, prices)
        baris.append({"hari": h, "resep": c["resep"], "total": c["total"],
                      "per_porsi": c["per_porsi"]})
        total += c["total"]
        for b in con.execute(
            """SELECT b.id, b.nama, b.satuan_dasar, b.komoditas_id,
                      b.harga_manual_rp, b.isi_satuan_manual,
                      rb.jumlah, rb.satuan
               FROM resep_bahan rb JOIN bahan b ON b.id = rb.bahan_id
               WHERE rb.resep_id = ?""", (rid,)):
            qty = _qty_dasar(khusus, umum, b["id"], b["jumlah"],
                             b["satuan"], b["satuan_dasar"])
            if b["komoditas_id"] and b["komoditas_id"] in prices:
                rpd = prices[b["komoditas_id"]] / 1000.0
            else:
                rpd = (b["harga_manual_rp"] or 0) / (b["isi_satuan_manual"] or 1)
            key = b["id"]
            if key not in belanja:
                belanja[key] = {"nama": b["nama"], "qty": 0.0,
                                "dasar": b["satuan_dasar"], "biaya": 0.0}
            belanja[key]["qty"] += qty
            belanja[key]["biaya"] += qty * rpd

    daftar_belanja = sorted(belanja.values(), key=lambda x: x["nama"])
    total_belanja = sum(x["biaya"] for x in daftar_belanja)

    return render_template("rencana.html", active="rencana", hari_list=HARI,
                           tersimpan=tersimpan, semua_resep=semua_resep,
                           baris=baris, daftar_belanja=daftar_belanja,
                           total=total, total_belanja=total_belanja,
                           pesan=pesan, tgl=tgl, sumber=sumber,
                           wilayah_tampil=wil, qty_cantik=qty_cantik)


def rencana_otomatis(con, prices, pant, budget):
    """Isi 7 hari dengan resep termurah (boleh berulang, tidak berurutan sama)."""
    kandidat = []
    for r in con.execute("SELECT * FROM resep"):
        if mengandung_pantangan(con, r["id"], pant):
            continue
        c = biaya_resep(con, r["id"], prices)
        kandidat.append((c["total"], r["id"]))
    kandidat.sort()
    if not kandidat:
        return {"pilihan": [], "total": 0, "masuk": False}
    pilihan, total, terakhir = [], 0.0, None
    i = 0
    while len(pilihan) < 7:
        tot, rid = kandidat[i % len(kandidat)]
        if rid == terakhir and len(kandidat) > 1:
            i += 1
            continue
        pilihan.append(rid)
        total += tot
        terakhir = rid
        i += 1
    return {"pilihan": pilihan, "total": total, "masuk": total <= budget}


# ---------- harga pasar ----------

@app.route("/harga")
def harga():
    con = get_db()
    wil = wilayah_aktif()

    tgllist = [r[0] for r in con.execute(
        "SELECT DISTINCT tanggal FROM harga_harian WHERE wilayah='NASIONAL' "
        "ORDER BY tanggal DESC LIMIT 2")]
    if not tgllist:
        return render_template("harga.html", active="harga", ada_data=False)

    tgl_now, tgl_prev = tgllist[0], (tgllist[1] if len(tgllist) > 1 else None)

    def peta(tgl, wilayah):
        return {r["komoditas_id"]: (r["harga_rp"], r["sumber"]) for r in con.execute(
            "SELECT komoditas_id, harga_rp, sumber FROM harga_harian "
            "WHERE tanggal = ? AND wilayah = ?", (tgl, wilayah))}

    now_nas, now_wil = peta(tgl_now, "NASIONAL"), peta(tgl_now, wil)
    prev_nas = peta(tgl_prev, "NASIONAL") if tgl_prev else {}

    baris = []
    for k in con.execute("SELECT * FROM komoditas ORDER BY id"):
        kid = k["id"]
        h_nas = now_nas.get(kid)
        h_wil = now_wil.get(kid)
        pct = None
        if h_nas and kid in prev_nas and prev_nas[kid][0]:
            pct = (h_nas[0] - prev_nas[kid][0]) / prev_nas[kid][0] * 100
        baris.append({"nama": k["nama_pihps"], "kategori": k["kategori"],
                      "satuan": k["satuan_harga"],
                      "nas": h_nas[0] if h_nas else None,
                      "wil": h_wil[0] if h_wil else None,
                      "sumber": h_nas[1] if h_nas else None, "pct": pct,
                      "komoditas_id": kid})

    alerts = susun_peringatan(con, baris, wil)

    return render_template("harga.html", active="harga", ada_data=True,
                           baris=baris, tgl_now=tgl_now, tgl_prev=tgl_prev,
                           wilayah=wil, alerts=alerts)


def susun_peringatan(con, baris, wil):
    """Peringatan harga cerdas: kenaikan/penurunan terbesar + saran resep."""
    alerts = []
    ber_pct = [b for b in baris if b["pct"] is not None]
    if not ber_pct:
        return alerts

    def resep_tanpa(kom_id):
        bids = {b["id"] for b in con.execute(
            "SELECT id FROM bahan WHERE komoditas_id = ?", (kom_id,))}
        out = []
        for r in con.execute("SELECT id, nama FROM resep"):
            punya = {x[0] for x in con.execute(
                "SELECT bahan_id FROM resep_bahan WHERE resep_id = ?", (r["id"],))}
            if not (punya & bids):
                out.append(r["nama"])
        return out

    def resep_dengan(kom_id):
        bids = {b["id"] for b in con.execute(
            "SELECT id FROM bahan WHERE komoditas_id = ?", (kom_id,))}
        out = []
        for r in con.execute("SELECT id, nama FROM resep"):
            punya = {x[0] for x in con.execute(
                "SELECT bahan_id FROM resep_bahan WHERE resep_id = ?", (r["id"],))}
            if punya & bids:
                out.append(r["nama"])
        return out

    naik = max(ber_pct, key=lambda b: b["pct"])
    if naik["pct"] >= 3:
        tanpa = resep_tanpa(naik["komoditas_id"])
        alerts.append({
            "jenis": "naik",
            "judul": f"{naik['nama']} naik {naik['pct']:.1f}% ke {rupiah(naik['nas'])}/kg",
            "isi": (f"Ada {len(tanpa)} resep yang tidak memakai bahan ini. "
                    f"Contoh: {', '.join(tanpa[:5])}." if tanpa
                    else "Semua resep memakai bahan ini — pertimbangkan mode super hemat."),
        })
    turun = min(ber_pct, key=lambda b: b["pct"])
    if turun["pct"] <= -3:
        dengan = resep_dengan(turun["komoditas_id"])
        alerts.append({
            "jenis": "turun",
            "judul": f"{turun['nama']} turun {abs(turun['pct']):.1f}% ke {rupiah(turun['nas'])}/kg",
            "isi": (f"Waktunya stok. {len(dengan)} resep memakai bahan ini, "
                    f"contoh: {', '.join(dengan[:5])}." if dengan else ""),
        })
    return alerts


# ---------- panel admin ----------

def _bahan_form_data(con):
    return con.execute("SELECT * FROM bahan ORDER BY nama").fetchall()


def _komoditas_opts(con):
    return con.execute("SELECT * FROM komoditas ORDER BY id").fetchall()


@app.route("/admin")
@admin_required
def admin_index():
    con = get_db()
    stats = {
        "resep": con.execute("SELECT COUNT(*) FROM resep").fetchone()[0],
        "bahan": con.execute("SELECT COUNT(*) FROM bahan").fetchone()[0],
        "users": con.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "harga": con.execute(
            "SELECT COUNT(*), MAX(tanggal) FROM harga_harian WHERE sumber='PIHPS'").fetchone(),
    }
    return render_template("admin/index.html", active="admin", stats=stats)


@app.route("/admin/resep")
@admin_required
def admin_resep_list():
    con = get_db()
    rows = con.execute("SELECT * FROM resep ORDER BY nama").fetchall()
    return render_template("admin/resep_list.html", active="admin", rows=rows)


def _parse_bahan_form(con):
    """Baca baris-baris bahan dari form admin. Kembalikan list dict atau (None, err)."""
    out = []
    for i in range(BARIS_BAHAN_FORM):
        bid = request.form.get(f"bahan_{i}", "").strip()
        jml = request.form.get(f"jumlah_{i}", "").strip()
        if not bid or not jml:
            continue
        try:
            out.append({
                "bahan_id": int(bid),
                "jumlah": float(jml),
                "satuan": request.form.get(f"satuan_{i}", "g"),
                "opsional": 1 if request.form.get(f"ops_{i}") else 0,
            })
        except ValueError:
            return None, f"Baris bahan ke-{i + 1}: jumlah harus angka."
    if not out:
        return None, "Resep harus punya minimal 1 bahan."
    return out, None


def _simpan_resep(con, rid=None):
    nama = request.form.get("nama", "").strip()
    if not nama:
        return None, "Nama resep wajib diisi."
    bahan_rows, err = _parse_bahan_form(con)
    if err:
        return None, err
    try:
        porsi = int(request.form.get("porsi", 4) or 4)
    except ValueError:
        return None, "Porsi harus angka."
    try:
        menit = int(request.form.get("menit", 0) or 0)
    except ValueError:
        menit = 0
    data = (nama, request.form.get("deskripsi", "").strip(),
            request.form.get("kategori", "makan_malam"), porsi, menit,
            request.form.get("tingkat", "mudah"), request.form.get("tags", "").strip(),
            request.form.get("langkah", "").strip(),
            request.form.get("asal", "").strip() or None,
            request.form.get("tag", "").strip() or None)
    if rid is None:
        cur = con.execute(
            """INSERT INTO resep (nama, deskripsi, kategori, porsi, waktu_masak_menit,
                                  tingkat, tags, langkah, asal, tag) VALUES (?,?,?,?,?,?,?,?,?,?)""", data)
        rid = cur.lastrowid
    else:
        con.execute(
            """UPDATE resep SET nama=?, deskripsi=?, kategori=?, porsi=?,
                              waktu_masak_menit=?, tingkat=?, tags=?, langkah=?,
                              asal=?, tag=?
               WHERE id=?""", data + (rid,))
        con.execute("DELETE FROM resep_bahan WHERE resep_id = ?", (rid,))
    for b in bahan_rows:
        con.execute(
            "INSERT INTO resep_bahan (resep_id, bahan_id, jumlah, satuan, opsional)"
            " VALUES (?,?,?,?,?)",
            (rid, b["bahan_id"], b["jumlah"], b["satuan"], b["opsional"]))
    con.commit()
    return rid, None


@app.route("/admin/resep/baru", methods=["GET", "POST"])
@admin_required
def admin_resep_baru():
    con = get_db()
    err = None
    if request.method == "POST":
        rid, err = _simpan_resep(con)
        if not err:
            flash("Resep berhasil ditambahkan.")
            return redirect(url_for("admin_resep_list"))
    return render_template("admin/resep_form.html", active="admin", err=err,
                           resep=None, komposisi=[],
                           bahans=_bahan_form_data(con),
                           kategoris=KATEGORI_LABEL, satuan_opsi=SATUAN_OPSI,
                           n_baris=BARIS_BAHAN_FORM, form=request.form)


@app.route("/admin/resep/<int:rid>/edit", methods=["GET", "POST"])
@admin_required
def admin_resep_edit(rid):
    con = get_db()
    resep = con.execute("SELECT * FROM resep WHERE id = ?", (rid,)).fetchone()
    if not resep:
        return "Resep tidak ditemukan", 404
    err = None
    if request.method == "POST":
        _, err = _simpan_resep(con, rid)
        if not err:
            flash("Resep berhasil diperbarui.")
            return redirect(url_for("admin_resep_list"))
    komposisi = con.execute(
        """SELECT rb.*, b.nama FROM resep_bahan rb JOIN bahan b ON b.id = rb.bahan_id
           WHERE rb.resep_id = ?""", (rid,)).fetchall()
    return render_template("admin/resep_form.html", active="admin", err=err,
                           resep=resep, komposisi=komposisi,
                           bahans=_bahan_form_data(con),
                           kategoris=KATEGORI_LABEL, satuan_opsi=SATUAN_OPSI,
                           n_baris=BARIS_BAHAN_FORM, form=request.form)


@app.route("/admin/resep/<int:rid>/hapus", methods=["POST"])
@admin_required
def admin_resep_hapus(rid):
    con = get_db()
    con.execute("DELETE FROM resep_bahan WHERE resep_id = ?", (rid,))
    con.execute("DELETE FROM user_favorit_resep WHERE resep_id = ?", (rid,))
    con.execute("DELETE FROM rencana WHERE resep_id = ?", (rid,))
    con.execute("DELETE FROM resep WHERE id = ?", (rid,))
    con.commit()
    flash("Resep dihapus.")
    return redirect(url_for("admin_resep_list"))


@app.route("/admin/bahan")
@admin_required
def admin_bahan_list():
    con = get_db()
    rows = con.execute(
        """SELECT b.*, k.nama_pihps AS komoditas_nama,
                  (g.bahan_id IS NOT NULL) AS ada_gizi
           FROM bahan b
           LEFT JOIN komoditas k ON k.id = b.komoditas_id
           LEFT JOIN gizi_bahan g ON g.bahan_id = b.id
           ORDER BY b.nama""").fetchall()
    return render_template("admin/bahan_list.html", active="admin", rows=rows)


def _simpan_bahan(con, bid=None):
    nama = request.form.get("nama", "").strip()
    if not nama:
        return None, "Nama bahan wajib diisi."
    dasar = request.form.get("satuan_dasar", "g")
    kom_id = request.form.get("komoditas_id", "").strip() or None
    hm = request.form.get("harga_manual_rp", "").strip() or None
    isi = request.form.get("isi_satuan_manual", "").strip() or None
    if not kom_id and not (hm and isi):
        return None, "Isi komoditas PIHPS ATAU harga manual + isi kemasan."
    try:
        hm_v = float(hm) if hm else None
        isi_v = float(isi) if isi else None
    except ValueError:
        return None, "Harga manual dan isi kemasan harus angka."
    data = (nama, request.form.get("kategori", "lainnya"),
            int(kom_id) if kom_id else None, hm_v,
            request.form.get("satuan_manual", "").strip() or None,
            isi_v, dasar, request.form.get("alergen", "").strip() or None)
    if bid is None:
        try:
            cur = con.execute(
                """INSERT INTO bahan (nama, kategori, komoditas_id, harga_manual_rp,
                                      satuan_manual, isi_satuan_manual, satuan_dasar, alergen)
                   VALUES (?,?,?,?,?,?,?,?)""", data)
        except sqlite3.IntegrityError:
            return None, "Nama bahan sudah ada."
        bid = cur.lastrowid
    else:
        try:
            con.execute(
                """UPDATE bahan SET nama=?, kategori=?, komoditas_id=?, harga_manual_rp=?,
                                  satuan_manual=?, isi_satuan_manual=?, satuan_dasar=?, alergen=?
                   WHERE id=?""", data + (bid,))
        except sqlite3.IntegrityError:
            return None, "Nama bahan sudah ada."
    # data gizi (opsional)
    gvals = {}
    for k in ["kalori", "protein", "karbo", "lemak", "serat", "natrium"]:
        v = request.form.get("g_" + k, "").strip()
        gvals[k] = float(v) if v else None
    if any(v is not None for v in gvals.values()):
        con.execute("DELETE FROM gizi_bahan WHERE bahan_id = ?", (bid,))
        con.execute(
            """INSERT INTO gizi_bahan (bahan_id, kalori, protein, karbo, lemak, serat, natrium)
               VALUES (?,?,?,?,?,?,?)""",
            (bid, gvals["kalori"], gvals["protein"], gvals["karbo"],
             gvals["lemak"], gvals["serat"], gvals["natrium"]))
    con.commit()
    return bid, None


@app.route("/admin/bahan/baru", methods=["GET", "POST"])
@admin_required
def admin_bahan_baru():
    con = get_db()
    err = None
    if request.method == "POST":
        _, err = _simpan_bahan(con)
        if not err:
            flash("Bahan berhasil ditambahkan.")
            return redirect(url_for("admin_bahan_list"))
    return render_template("admin/bahan_form.html", active="admin", err=err,
                           bahan=None, gizi=None,
                           komoditas=_komoditas_opts(con), form=request.form)


@app.route("/admin/bahan/<int:bid>/edit", methods=["GET", "POST"])
@admin_required
def admin_bahan_edit(bid):
    con = get_db()
    bahan = con.execute("SELECT * FROM bahan WHERE id = ?", (bid,)).fetchone()
    if not bahan:
        return "Bahan tidak ditemukan", 404
    gizi = con.execute("SELECT * FROM gizi_bahan WHERE bahan_id = ?",
                       (bid,)).fetchone()
    err = None
    if request.method == "POST":
        _, err = _simpan_bahan(con, bid)
        if not err:
            flash("Bahan berhasil diperbarui.")
            return redirect(url_for("admin_bahan_list"))
    return render_template("admin/bahan_form.html", active="admin", err=err,
                           bahan=bahan, gizi=gizi,
                           komoditas=_komoditas_opts(con), form=request.form)


@app.route("/admin/bahan/<int:bid>/hapus", methods=["POST"])
@admin_required
def admin_bahan_hapus(bid):
    con = get_db()
    dipakai = con.execute(
        "SELECT COUNT(*) FROM resep_bahan WHERE bahan_id = ?", (bid,)).fetchone()[0]
    if dipakai:
        flash(f"Bahan tidak bisa dihapus: dipakai di {dipakai} resep.")
        return redirect(url_for("admin_bahan_list"))
    con.execute("DELETE FROM gizi_bahan WHERE bahan_id = ?", (bid,))
    con.execute("DELETE FROM konversi_satuan WHERE bahan_id = ?", (bid,))
    con.execute("DELETE FROM user_pantangan WHERE bahan_id = ?", (bid,))
    con.execute("DELETE FROM bahan WHERE id = ?", (bid,))
    con.commit()
    flash("Bahan dihapus.")
    return redirect(url_for("admin_bahan_list"))


@app.route("/admin/users")
@admin_required
def admin_users():
    con = get_db()
    rows = con.execute(
        "SELECT id, username, role, nama, wilayah FROM users ORDER BY id").fetchall()
    return render_template("admin/users.html", active="admin", rows=rows)


def _fetch_background():
    try:
        import fetch_harga
        fetch_harga.main()
    except BaseException as e:  # noqa: BLE001
        print("Update harga background gagal:", e)


@app.route("/admin/harga/update", methods=["POST"])
@admin_required
def admin_update_harga():
    t = threading.Thread(target=_fetch_background, daemon=True)
    t.start()
    flash("Pengambilan harga PIHPS dimulai di background (butuh beberapa menit). "
          "Buka halaman Harga lagi nanti untuk melihat hasilnya.")
    return redirect(url_for("admin_index"))


@app.route("/ping")
def ping():
    return "ok"


if __name__ == "__main__":
    if not os.path.exists(DB):
        print("Database belum ada. Jalankan dulu: python init_db.py")
    else:
        print("MenuHemat berjalan di http://127.0.0.1:5000")
        app.run(host="127.0.0.1", port=5000, debug=False)
