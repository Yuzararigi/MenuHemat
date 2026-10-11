/* MenuHemat — situs statis. Seluruh hitungan meniru logika Flask (biaya_resep, gizi_resep). */
(function () {
  "use strict";

  /* ---------- util ---------- */
  const rp = (n) => "Rp " + Math.round(n).toLocaleString("id-ID");
  const num = (n) => String(Number(n));
  const fmt1 = (n) => (Math.round(n * 10) / 10).toLocaleString("id-ID");
  const KAT = { sarapan: "Sarapan", makan_siang: "Makan siang", makan_malam: "Makan malam", camilan: "Camilan" };
  const GIZI_LABEL = [["kalori", "Kalori (kkal)"], ["protein", "Protein (g)"], ["karbo", "Karbohidrat (g)"], ["lemak", "Lemak (g)"], ["serat", "Serat (g)"], ["natrium", "Natrium (mg)"]];

  /* Foto hidangan (file lokal di docs/images/<slug>.jpg). Slug diturunkan
     dari nama resep. Bila file gagal dimuat, <img> menghapus dirinya
     sendiri dan huruf inisial tampil sebagai fallback. */
  const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  const fotoSrc = (r) => "images/" + slugify(r.nama) + ".jpg";
  /* badge label khusus (diet/gym) dari kolom tag resep, mis. "diet,gym" */
  const tagList = (r) => (r.tag || "").split(",").map((t) => t.trim()).filter(Boolean);
  function badgeHTML(r) {
    const tags = tagList(r);
    let h = "";
    if (r.asal) h += '<span class="badge-asal">' + esc(r.asal) + "</span>";
    if (tags.includes("diet")) h += '<span class="badge-khusus diet">Diet</span>';
    if (tags.includes("gym")) h += '<span class="badge-khusus gym">Gym</span>';
    return h ? '<span class="badges">' + h + "</span>" : "";
  }
  function thumbHTML(r, tag, cls) {
    const initial = esc(r.nama.trim().charAt(0).toUpperCase());
    const src = fotoSrc(r);
    const img = src ? '<img src="' + src + '" alt="' + esc(r.nama) + '" loading="lazy" onerror="this.remove()">' : "";
    return "<" + tag + ' class="' + cls + '" aria-hidden="true">' + img +
      '<span class="' + cls + '-initial">' + initial + "</span></" + tag + ">";
  }

  function lsGet(k, fb) {
    try { const v = localStorage.getItem(k); return v === null ? fb : JSON.parse(v); }
    catch (e) { return fb; }
  }
  function lsSet(k, v) {
    try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
  }

  /* ---------- lookup ---------- */
  const resepById = {}, bahanById = {}, komoditasById = {};
  DB.resep.forEach((r) => (resepById[r.id] = r));
  DB.bahan.forEach((b) => (bahanById[b.id] = b));
  DB.komoditas.forEach((k) => (komoditasById[k.id] = k));
  const rbByResep = {};
  DB.resep_bahan.forEach((rb) => {
    (rbByResep[rb[0]] = rbByResep[rb[0]] || []).push(rb);
  });

  const khusus = new Map(), umum = new Map();
  DB.konversi.forEach(([bid, dari, ke, f]) => {
    if (bid) khusus.set(bid + "|" + dari + "|" + ke, f);
    else umum.set(dari + "|" + ke, f);
  });
  function qtyDasar(bahanId, jumlah, satuan, satuanDasar) {
    let f = khusus.get(bahanId + "|" + satuan + "|" + satuanDasar);
    if (f === undefined) f = umum.get(satuan + "|" + satuanDasar);
    if (f === undefined) f = 1;
    return jumlah * f;
  }

  /* ---------- hitungan ---------- */
  function pricesFor(wilayah) {
    return DB.prices[wilayah] || DB.prices["NASIONAL"];
  }
  function pricePerDasar(bahan, wilayah) {
    const p = pricesFor(wilayah);
    if (bahan.komoditas_id && p[bahan.komoditas_id] != null) {
      return { perDasar: p[bahan.komoditas_id] / 1000, label: rp(p[bahan.komoditas_id]) + " / kg" };
    }
    const perDasar = (bahan.harga_manual_rp || 0) / (bahan.isi_satuan_manual || 1);
    return { perDasar, label: rp(bahan.harga_manual_rp || 0) + "/" + (bahan.satuan_manual || "satuan") + " (estimasi)" };
  }
  function biayaResep(resepId, wilayah) {
    const r = resepById[resepId];
    let total = 0;
    const items = [];
    (rbByResep[resepId] || []).forEach(([rid, bid, jumlah, satuan, opsional]) => {
      const b = bahanById[bid];
      const q = qtyDasar(bid, jumlah, satuan, b.satuan_dasar);
      const { perDasar, label } = pricePerDasar(b, wilayah);
      const biaya = q * perDasar;
      total += biaya;
      items.push({ nama: b.nama, takaran: num(jumlah) + " " + satuan, harga: label, biaya });
    });
    items.sort((a, b) => a.nama.localeCompare(b.nama, "id"));
    return { total, perPorsi: total / (r.porsi || 1), items };
  }
  function giziResep(resepId) {
    const r = resepById[resepId];
    const tot = { kalori: 0, protein: 0, karbo: 0, lemak: 0, serat: 0, natrium: 0 };
    let ada = false;
    (rbByResep[resepId] || []).forEach(([rid, bid, jumlah, satuan]) => {
      const g = DB.gizi[bid];
      if (!g) return;
      ada = true;
      const b = bahanById[bid];
      const q = qtyDasar(bid, jumlah, satuan, b.satuan_dasar) / 100;
      tot.kalori += q * g[0]; tot.protein += q * g[1]; tot.karbo += q * g[2];
      tot.lemak += q * g[3]; tot.serat += q * g[4]; tot.natrium += q * g[5];
    });
    const porsi = r.porsi || 1;
    const perPorsi = {};
    Object.keys(tot).forEach((k) => (perPorsi[k] = tot[k] / porsi));
    return { perPorsi, ada };
  }
  function resepAman(resepId, pantangan) {
    if (!pantangan.size) return true;
    return !(rbByResep[resepId] || []).some(([rid, bid]) => pantangan.has(bid));
  }

  /* ---------- state ---------- */
  const state = {
    wilayah: lsGet("mh_wilayah", "NASIONAL"),
    fav: new Set(lsGet("mh_fav", [])),
    pantangan: new Set(lsGet("mh_pantangan", [])),
    favOnly: false,
    kategori: "semua",
    asal: "semua",
    tagF: "semua",
    urut: "harga",
    maxRp: null,
    sehari: new Set(lsGet("mh_sehari", [])),
    rencana: lsGet("mh_rencana", [null, null, null, null, null, null, null]),
  };
  if (!DB.wilayah.includes(state.wilayah)) state.wilayah = "NASIONAL";
  function save() {
    lsSet("mh_wilayah", state.wilayah);
    lsSet("mh_fav", [...state.fav]);
    lsSet("mh_pantangan", [...state.pantangan]);
    lsSet("mh_sehari", [...state.sehari]);
    lsSet("mh_rencana", state.rencana);
  }

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  /* ---------- kartu ---------- */
  function cardHTML(r, opts) {
    const c = biayaResep(r.id, state.wilayah);
    const g = giziResep(r.id);
    const favOn = state.fav.has(r.id) ? " on" : "";
    const sel = opts && opts.selectable && state.sehari.has(r.id) ? " selected" : "";
    const thumb = thumbHTML(r, "span", "thumb");
    return (
      '<button type="button" class="card' + sel + '" data-id="' + r.id + '" data-mode="' + (opts && opts.selectable ? "select" : "detail") + '">' +
      '<span class="check" aria-hidden="true">&#10003;</span>' +
      '<span class="fav' + favOn + '" data-fav="' + r.id + '" role="button" aria-label="Favorit" tabindex="0">&#9733;</span>' +
      thumb +
      '<span class="card-body">' +
      '<span class="kat">#' + r.id + " &middot; " + esc(KAT[r.kategori] || r.kategori) + "</span>" +
      "<h3>" + esc(r.nama) + "</h3>" +
      badgeHTML(r) +
      '<p class="meta">' + rp(c.perPorsi) + "/porsi &middot; &plusmn;" + fmt1(g.perPorsi.kalori) + " kkal estimasi</p>" +
      "</span></button>"
    );
  }

  function visibleResep() {
    return DB.resep.filter((r) => resepAman(r.id, state.pantangan));
  }
  function filteredResep() {
    let list = visibleResep().map((r) => ({ r, c: biayaResep(r.id, state.wilayah), g: giziResep(r.id).perPorsi }));
    if (state.kategori !== "semua") list = list.filter((x) => x.r.kategori === state.kategori);
    if (state.asal !== "semua") list = list.filter((x) => x.r.asal === state.asal);
    if (state.tagF !== "semua") list = list.filter((x) => tagList(x.r).includes(state.tagF));
    if (state.favOnly) list = list.filter((x) => state.fav.has(x.r.id));
    if (state.maxRp != null && !isNaN(state.maxRp)) list = list.filter((x) => x.c.perPorsi <= state.maxRp);
    const U = state.urut;
    const gz = (x, k) => x.g[k] || 0;
    if (U === "kalori-rendah") list.sort((a, b) => gz(a, "kalori") - gz(b, "kalori"));
    else if (U === "kalori-tinggi") list.sort((a, b) => gz(b, "kalori") - gz(a, "kalori"));
    else if (U === "protein") list.sort((a, b) => gz(b, "protein") - gz(a, "protein"));
    else if (U === "karbo-rendah") list.sort((a, b) => gz(a, "karbo") - gz(b, "karbo"));
    else if (U === "karbo-tinggi") list.sort((a, b) => gz(b, "karbo") - gz(a, "karbo"));
    else if (U === "lemak-rendah") list.sort((a, b) => gz(a, "lemak") - gz(b, "lemak"));
    else if (U === "serat") list.sort((a, b) => gz(b, "serat") - gz(a, "serat"));
    else if (U === "natrium") list.sort((a, b) => gz(a, "natrium") - gz(b, "natrium"));
    else list.sort((a, b) => a.c.perPorsi - b.c.perPorsi);
    return list;
  }

  /* ---------- render: beranda ---------- */
  function renderHero() {
    const list = visibleResep().map((r) => ({ r, c: biayaResep(r.id, state.wilayah) }));
    list.sort((a, b) => a.c.perPorsi - b.c.perPorsi);
    const top = list[0];
    if (!top) { $("hero").innerHTML = ""; return; }
    const g = giziResep(top.r.id);
    const gizis = GIZI_LABEL.map(([k, label]) =>
      '<div class="gizi-item"><b>' + fmt1(g.perPorsi[k]) + "</b><span>" + label + "</span></div>"
    ).join("");
    $("hero").innerHTML =
      '<div class="hero">' +
      thumbHTML(top.r, "div", "hero-thumb") +
      '<div class="hero-body">' +
      '<div class="hero-label">Paling hemat hari ini</div>' +
      "<h2>" + esc(top.r.nama) + "</h2>" +
      '<div class="hero-harga">' + rp(top.c.perPorsi) + " <small>/porsi</small></div>" +
      '<div class="hero-meta">' + top.r.waktu + " menit &middot; " + top.r.porsi + " porsi &middot; " + esc(KAT[top.r.kategori] || top.r.kategori) + (top.r.asal ? " &middot; khas " + esc(top.r.asal) : "") + "</div>" +
      '<div class="gizi-grid">' + gizis + "</div>" +
      '<p class="gizi-note">Angka gizi adalah estimasi &mdash; dihitung dari komposisi bahan dibagi jumlah porsi.</p>' +
      '<button type="button" data-detail="' + top.r.id + '">Lihat resep &amp; cara masak</button>' +
      "</div></div>";
  }

  function renderGrid() {
    const list = filteredResep();
    $("grid").innerHTML = list.map((x) => cardHTML(x.r, {})).join("");
    $("grid-info").textContent = "Menampilkan " + list.length + " dari " + DB.resep.length + " resep.";
    $("grid-empty").hidden = list.length > 0;
    document.querySelectorAll("#pant-count").forEach((el) => (el.textContent = state.pantangan.size));
  }

  function renderPantangan() {
    $("pant-list").innerHTML = DB.bahan.map((b) => {
      const checked = state.pantangan.has(b.id) ? " checked" : "";
      const al = b.alergen ? " (" + esc(b.alergen) + ")" : "";
      return '<label><input type="checkbox" data-bahan="' + b.id + '"' + checked + "> " + esc(b.nama) + al + "</label>";
    }).join("");
  }

  /* ---------- render: harga ---------- */
  function renderHarga() {
    const p = pricesFor(state.wilayah);
    $("harga-sumber").textContent =
      "Sumber data: " + DB.meta.sumber + " · data per " + DB.meta.tanggalLabel + " · wilayah " + state.wilayah;
    $("harga-body").innerHTML = DB.komoditas.map((k) => {
      const harga = p[k.id] != null ? rp(p[k.id]) + " / " + k.satuan : "-";
      return "<tr><td>" + esc(k.nama) + '<br><small style="color:#666">' + esc(k.kategori || "") + "</small></td><td>" + harga + "</td></tr>";
    }).join("");
  }

  /* ---------- render: satu hari makan ---------- */
  function renderSehari() {
    const list = visibleResep().map((r) => ({ r, c: biayaResep(r.id, state.wilayah) }));
    list.sort((a, b) => a.c.perPorsi - b.c.perPorsi);
    $("sehari-grid").innerHTML = list.map((x) => cardHTML(x.r, { selectable: true })).join("");
    const sel = [...state.sehari].filter((id) => resepById[id] && resepAman(id, state.pantangan));
    const box = $("sehari-summary");
    if (!sel.length) { box.hidden = true; return; }
    box.hidden = false;
    let total = 0;
    const rows = sel.map((id) => {
      const r = resepById[id], c = biayaResep(id, state.wilayah);
      total += c.perPorsi;
      return "<li>" + esc(r.nama) + " &mdash; " + rp(c.perPorsi) + "/porsi</li>";
    }).join("");
    const budget = parseFloat($("budget").value);
    let sisaHTML = "";
    if (!isNaN(budget) && budget > 0) {
      const sisa = budget - total;
      const cls = sisa >= 0 ? "sisa-ok" : "sisa-lebih";
      const ket = sisa >= 0 ? "MASUK BUDGET" : "LEBIH BUDGET";
      sisaHTML = '<p>Sisa budget: <b class="' + cls + '">' + rp(sisa) + "</b> (" + ket + ")</p>";
    }
    box.innerHTML = "<b>Total " + sel.length + " hidangan: " + rp(total) + "</b><ul>" + rows + "</ul>" + sisaHTML;
  }

  /* ---------- render: rencana ---------- */
  const HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];
  function renderRencana() {
    const opts = visibleResep().map((r) => ({ r, c: biayaResep(r.id, state.wilayah) }));
    opts.sort((a, b) => a.c.perPorsi - b.c.perPorsi);
    $("rencana-rows").innerHTML = HARI.map((h, i) => {
      const cur = state.rencana[i];
      const c = cur ? biayaResep(cur, state.wilayah) : null;
      const options = '<option value="">— pilih hidangan —</option>' + opts.map((x) =>
        '<option value="' + x.r.id + '"' + (x.r.id === cur ? " selected" : "") + ">" +
        esc(x.r.nama) + " (" + rp(x.c.perPorsi) + "/porsi)</option>"
      ).join("");
      return '<div class="rencana-row"><span class="hari">' + h + '</span><span><select data-hari="' + i + '">' + options + "</select>" +
        (c ? '<div class="biaya">' + rp(c.perPorsi) + "/porsi &middot; total " + rp(c.total) + "</div>" : "") + "</span></div>";
    }).join("");
    renderBelanja();
  }
  function renderBelanja() {
    const box = $("belanja");
    const chosen = state.rencana.filter((id) => id && resepById[id] && resepAman(id, state.pantangan));
    if (!chosen.length) { box.innerHTML = '<p class="hint">Belum ada hidangan dipilih.</p>'; return; }
    const agg = {};
    chosen.forEach((rid) => {
      (rbByResep[rid] || []).forEach(([r2, bid, jumlah, satuan]) => {
        const b = bahanById[bid];
        const q = qtyDasar(bid, jumlah, satuan, b.satuan_dasar);
        agg[bid] = agg[bid] || { nama: b.nama, satuan: b.satuan_dasar, qty: 0, bahan: b };
        agg[bid].qty += q;
      });
    });
    let total = 0;
    const rows = Object.values(agg).map((a) => {
      const { perDasar } = pricePerDasar(a.bahan, state.wilayah);
      const biaya = a.qty * perDasar;
      total += biaya;
      return { nama: a.nama, qty: a.qty, satuan: a.satuan, biaya };
    }).sort((a, b) => b.biaya - a.biaya);
    box.innerHTML =
      '<table><thead><tr><th>Bahan</th><th>Jumlah</th><th>Estimasi</th></tr></thead><tbody>' +
      rows.map((r) => "<tr><td>" + esc(r.nama) + "</td><td>" + fmt1(r.qty) + " " + esc(r.satuan) + "</td><td style='text-align:right'>" + rp(r.biaya) + "</td></tr>").join("") +
      '</tbody></table><p><b>Total estimasi belanja: ' + rp(total) + "</b></p>";
  }

  /* ---------- modal detail ---------- */
  function openDetail(id) {
    const r = resepById[id];
    if (!r) return;
    const c = biayaResep(id, state.wilayah);
    const g = giziResep(id);
    const biayaRows = c.items.map((it) =>
      "<tr><td>" + esc(it.nama) + "<br><small style='color:#666'>" + esc(it.takaran) + "</small></td><td style='text-align:right'>" + esc(it.harga) + "</td><td>" + rp(it.biaya) + "</td></tr>"
    ).join("");
    const giziRows = GIZI_LABEL.map(([k, label]) =>
      "<tr><td>" + label + "</td><td style='text-align:right'>" + fmt1(g.perPorsi[k]) + "</td></tr>"
    ).join("");
    const langkah = (r.langkah || []).map((s, i) => "<li>" + esc(s) + "</li>").join("");
    $("modal-body").innerHTML =
      "<h2>" + esc(r.nama) + "</h2>" +
      badgeHTML(r) +
      (fotoSrc(r) ? '<div class="detail-foto"><img src="' + fotoSrc(r) + '" alt="' + esc(r.nama) + '" onerror="this.closest(\'.detail-foto\').remove()"></div>' : "") +
      '<p class="hint">' + esc(KAT[r.kategori] || r.kategori) + " &middot; " + r.waktu + " menit &middot; " + r.porsi + " porsi &middot; " + esc(r.tingkat || "") + (r.asal ? " &middot; khas " + esc(r.asal) : "") + "</p>" +
      (r.deskripsi ? "<p>" + esc(r.deskripsi) + "</p>" : "") +
      "<h3>Rincian biaya (" + esc(state.wilayah) + ")</h3>" +
      '<table class="biaya-table"><thead><tr><th>Bahan</th><th>Harga satuan</th><th>Biaya</th></tr></thead><tbody>' + biayaRows + "</tbody></table>" +
      "<p><b>Total: " + rp(c.total) + "</b> &middot; per porsi: <b>" + rp(c.perPorsi) + "</b></p>" +
      "<h3>Kandungan gizi per porsi (estimasi)</h3>" +
      '<table class="gizi-table"><tbody>' + giziRows + "</tbody></table>" +
      '<p class="gizi-note">Angka gizi adalah estimasi &mdash; dihitung dari komposisi bahan dibagi jumlah porsi, bukan hasil uji lab.</p>' +
      "<h3>Cara memasak</h3>" +
      '<ol class="langkah">' + langkah + "</ol>";
    $("modal").hidden = false;
    document.body.style.overflow = "hidden";
  }
  function closeDetail() {
    $("modal").hidden = true;
    document.body.style.overflow = "";
  }

  /* ---------- tab ---------- */
  function showTab(name) {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".tab").forEach((s) => (s.hidden = s.id !== "tab-" + name));
    if (name === "sehari") renderSehari();
    if (name === "rencana") renderRencana();
    if (name === "harga") renderHarga();
    if (name === "beranda") { renderHero(); renderGrid(); }
  }

  /* ---------- events ---------- */
  function init() {
    // wilayah
    $("wilayah").innerHTML = DB.wilayah.map((w) =>
      '<option value="' + esc(w) + '"' + (w === state.wilayah ? " selected" : "") + ">" + esc(w) + "</option>"
    ).join("");
    $("wilayah").addEventListener("change", (e) => {
      state.wilayah = e.target.value; save();
      renderHero(); renderGrid(); renderHarga(); renderSehari();
    });

    document.querySelectorAll(".tabs button").forEach((b) =>
      b.addEventListener("click", () => showTab(b.dataset.tab))
    );

    // filter beranda
    $("f-kategori").addEventListener("change", (e) => { state.kategori = e.target.value; renderGrid(); });
    $("f-asal").addEventListener("change", (e) => { state.asal = e.target.value; renderGrid(); });
    $("f-tag").addEventListener("change", (e) => { state.tagF = e.target.value; renderGrid(); });
    $("f-urut").addEventListener("change", (e) => { state.urut = e.target.value; renderGrid(); });
    $("f-max").addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      state.maxRp = isNaN(v) || v <= 0 ? null : v;
      renderGrid();
    });
    $("f-fav").addEventListener("click", (e) => {
      state.favOnly = !state.favOnly;
      e.currentTarget.setAttribute("aria-pressed", state.favOnly);
      renderGrid();
    });
    $("f-pant").addEventListener("click", (e) => {
      const panel = $("pant-panel");
      panel.hidden = !panel.hidden;
      e.currentTarget.setAttribute("aria-pressed", !panel.hidden);
    });
    renderPantangan();
    $("pant-list").addEventListener("change", (e) => {
      const bid = parseInt(e.target.dataset.bahan, 10);
      if (e.target.checked) state.pantangan.add(bid); else state.pantangan.delete(bid);
      save(); renderHero(); renderGrid(); renderSehari();
    });

    // klik kartu (delegasi): fav, detail, atau pilih
    document.addEventListener("click", (e) => {
      const favBtn = e.target.closest("[data-fav]");
      if (favBtn) {
        e.stopPropagation();
        const id = parseInt(favBtn.dataset.fav, 10);
        if (state.fav.has(id)) state.fav.delete(id); else state.fav.add(id);
        save();
        document.querySelectorAll('[data-fav="' + id + '"]').forEach((el) => el.classList.toggle("on", state.fav.has(id)));
        if (state.favOnly) renderGrid();
        return;
      }
      const detailBtn = e.target.closest("[data-detail]");
      if (detailBtn) { openDetail(parseInt(detailBtn.dataset.detail, 10)); return; }
      const card = e.target.closest(".card[data-id]");
      if (card) {
        const id = parseInt(card.dataset.id, 10);
        if (card.dataset.mode === "select") {
          if (state.sehari.has(id)) state.sehari.delete(id); else state.sehari.add(id);
          save(); renderSehari();
        } else {
          openDetail(id);
        }
      }
    });
    // keyboard: fav via Enter/Space
    document.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches("[data-fav]")) {
        e.preventDefault(); e.target.click();
      }
    });

    // modal
    document.querySelector(".modal-close").addEventListener("click", closeDetail);
    $("modal").addEventListener("click", (e) => { if (e.target === $("modal")) closeDetail(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("modal").hidden) closeDetail(); });

    // sehari
    $("budget").addEventListener("input", renderSehari);
    $("auto-sehari").addEventListener("click", () => {
      const list = visibleResep().map((r) => ({ id: r.id, c: biayaResep(r.id, state.wilayah) }));
      list.sort((a, b) => a.c.perPorsi - b.c.perPorsi);
      state.sehari = new Set(list.slice(0, 3).map((x) => x.id));
      save(); renderSehari();
    });
    $("clear-sehari").addEventListener("click", () => {
      state.sehari = new Set(); save(); renderSehari();
    });

    // rencana
    $("rencana-rows").addEventListener("change", (e) => {
      const i = parseInt(e.target.dataset.hari, 10);
      state.rencana[i] = e.target.value ? parseInt(e.target.value, 10) : null;
      save(); renderRencana();
    });
    $("auto-rencana").addEventListener("click", () => {
      const list = visibleResep().map((r) => ({ id: r.id, c: biayaResep(r.id, state.wilayah) }));
      list.sort((a, b) => a.c.perPorsi - b.c.perPorsi);
      state.rencana = [0, 1, 2, 3, 4, 5, 6].map((i) => (list[i] ? list[i].id : null));
      save(); renderRencana();
    });

    renderHero(); renderGrid(); renderSehari();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  // ekspor untuk pengujian
  window.__mh = { biayaResep, giziResep, state, DB };
})();
