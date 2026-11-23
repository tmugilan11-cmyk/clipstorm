/* The toolbar on a project's page: order the clips, narrow them by score, length, kind and decision, switch between a grid
 * and a list, and pick everything that is showing.
 *
 * The clips are drawn by index.html (clipHtml). Each one carries data-score, data-len, data-at, data-cat and data-rv, so
 * this file never asks the server for anything: it hides the clips that do not match and, for "Order in the video", sets a
 * CSS order. The default stays best score first, which is how byScore() hands them over. The choices are remembered in this
 * browser, and a browser that will not remember them just starts from the defaults again. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  const KEY = "peakcut_project_tools";
  const DEFAULTS = { sort: "best", min: "0", len: "any", cat: "all", show: "all", view: "grid" };
  const load = () => {
    try { const v = JSON.parse(localStorage.getItem(KEY) || "{}"); return { ...DEFAULTS, ...(v && typeof v === "object" ? v : {}) }; }
    catch (e) { return { ...DEFAULTS }; }
  };
  let T = load();
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(T)); } catch (e) { /* it simply forgets */ } };

  P.css("project-tools", `
    .pt-bar{display:grid;gap:10px;margin:0 0 18px;padding:12px 14px;border:1px solid var(--line);border-radius:var(--r);background:var(--muted)}
    .pt-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px}
    .pt-grp{display:inline-flex;gap:4px;padding:3px;border-radius:10px;background:var(--bg)}
    .pt-grp button{height:28px;padding:0 11px;border:0;border-radius:7px;background:transparent;color:var(--dim);font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;transition:background-color .15s ease,color .15s ease}
    .pt-grp button:hover,.pt-grp button:focus-visible{background:var(--brand-soft);color:var(--text)}
    .pt-grp button[aria-pressed=true]{background:var(--brand-soft);color:var(--brand-deep)}
    .pt-lab{font-size:12px;font-weight:600;color:var(--faint)}
    .pt-sel{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:var(--faint)}
    .pt-sel select{height:34px;border-radius:10px;border:1px solid var(--line-2);background:var(--bg);color:var(--text);padding:0 10px;font-size:13px}
    .pt-count{font-size:13px;color:var(--dim);margin-right:auto}
    .pt-count b{color:var(--text);font-variant-numeric:tabular-nums}
    .pt-row .btn.sm{height:30px}
    .pt-view{margin-left:auto}
    #view:has(#projbar) .pcf-bar{display:none}
    .pcf-search #pf_q{padding-left:34px}
    .job .pt-none{padding:28px 0;color:var(--dim)}
    /* list view: one clip per row, with the reason in full */
    #jobs.pt-list .grid{grid-template-columns:1fr;gap:10px}
    #jobs.pt-list .clip{flex-direction:row;align-items:stretch}
    #jobs.pt-list .clip .shot{width:112px;flex:none;aspect-ratio:9/16}
    #jobs.pt-list .clip .shot .veil{left:6px;bottom:6px}
    #jobs.pt-list .clip .shot .veil span{width:28px;height:28px}
    #jobs.pt-list .clip-body{padding:12px 16px;gap:6px;justify-content:flex-start}
    #jobs.pt-list .clip .hook{font-size:15px}
    #jobs.pt-list .clip .why{white-space:normal;overflow:visible;font-size:13px;color:var(--dim);max-width:78ch}
    #jobs.pt-list .clip .ttl{font-size:13px}
    #jobs.pt-list .clip-foot{margin-top:auto}
    #jobs.pt-list .clip-acts{flex-wrap:wrap}
    #jobs.pt-list .clip-acts .btn,#jobs.pt-list .clip-rv .btn,#jobs.pt-list .pcpeek .btn{flex:0 0 auto;width:auto}
    #jobs.pt-list .clip-acts .btn .lbl{display:inline}
    #jobs.pt-list .clip-acts,#jobs.pt-list .clip-rv,#jobs.pt-list .pcpeek,#jobs.pt-list .clip-foot{width:auto;align-self:flex-start}
    #jobs.pt-list .clip-foot{gap:10px}
    @media (max-width:640px){
      .pt-view{margin-left:0}
      .pt-grp{flex-wrap:wrap;max-width:100%}
      .pt-row .btn.sm{white-space:normal;height:auto;min-height:30px}
      .pt-count{flex:1 1 100%}
      #jobs.pt-list .clip .shot{width:88px}
      #jobs.pt-list .clip .shot .badge.r{display:none}
    }
  `);

  const SORTS = [["best", "Best first"], ["video", "Order in the video"]];
  const MINS = [["0", "Any score"], ["90", "90 and up"], ["80", "80 and up"], ["70", "70 and up"]];
  const LENS = [["any", "Any length"], ["short", "Under 30 s"], ["mid", "30 to 60 s"], ["long", "Over 60 s"]];
  const SHOWS = [["all", "All clips"], ["open", "Not decided yet"], ["approved", "Kept"], ["rejected", "Skipped"]];
  const grp = (k, label, list) => `<div class="pt-grp" role="group" aria-label="${esc(label)}">${list.map(([v, l]) =>
    `<button type="button" data-act="ptset" data-k="${k}" data-v="${esc(v)}" aria-pressed="${String(T[k]) === String(v)}">${esc(l)}</button>`).join("")}</div>`;

  const kindWord = (k) => String(k || "").replace(/[_-]+/g, " ").replace(/^./, (m) => m.toUpperCase());
  const lenOk = (n) => T.len === "any" || (T.len === "short" ? n < 30 : T.len === "mid" ? n >= 30 && n <= 60 : n > 60);
  const showOk = (rv) => T.show === "all" || (T.show === "open" ? !rv : rv === T.show);

  function clips(root) { return Array.from(root.querySelectorAll("article.clip")); }

  function kinds(list) {
    const seen = new Map();
    for (const el of list) { const k = el.dataset.cat || ""; if (k) seen.set(k, (seen.get(k) || 0) + 1); }
    return Array.from(seen.entries()).sort((a, b) => b[1] - a[1]);
  }

  function bar(list) {
    const ks = kinds(list);
    if (T.cat !== "all" && !ks.some(([k]) => k === T.cat)) T.cat = "all";
    const kindSel = ks.length > 1 ? `<label class="pt-sel">Kind<select data-pt="cat" aria-label="Kind of moment"><option value="all">All kinds</option>${ks.map(([k, n]) =>
      `<option value="${esc(k)}"${T.cat === k ? " selected" : ""}>${esc(kindWord(k))} (${n})</option>`).join("")}</select></label>` : "";
    return `<div class="pt-bar" role="region" aria-label="Narrow down the clips">
      <div class="pt-row">${grp("sort", "Order", SORTS)}${grp("min", "Score", MINS)}${grp("len", "Length", LENS)}
        <div class="pt-grp pt-view" role="group" aria-label="How the clips are shown">
          <button type="button" data-act="ptset" data-k="view" data-v="grid" aria-pressed="${T.view === "grid"}">Grid</button>
          <button type="button" data-act="ptset" data-k="view" data-v="list" aria-pressed="${T.view === "list"}">List</button></div></div>
      <div class="pt-row">${kindSel}<label class="pt-sel">Show<select data-pt="show" aria-label="Which clips to show">${SHOWS.map(([v, l]) =>
        `<option value="${v}"${T.show === v ? " selected" : ""}>${l}</option>`).join("")}</select></label>
        <span class="pt-count" id="pt_count" role="status"></span>
        <button type="button" class="btn sm" data-act="ptpick">Select what is showing</button>
        <button type="button" class="btn sm ghost" data-act="ptreset">Clear choices</button></div></div>`;
  }

  // Hide what does not match and order the rest. Idempotent: it only touches what differs, so the repaint loop stays cheap.
  function apply() {
    const host = document.getElementById("projbar"), jobs = document.getElementById("jobs");
    if (!host || !jobs) return;
    const list = clips(jobs);
    // Rebuild the bar when the set of kinds changed or the first time; leave it alone while a select is open.
    const sig = T.sort + T.min + T.len + T.cat + T.show + T.view + "|" + kinds(list).map(([k, n]) => k + n).join(",");
    if (host.dataset.sig !== sig && !host.contains(document.activeElement && document.activeElement.tagName === "SELECT" ? document.activeElement : null)) {
      host.innerHTML = bar(list); host.dataset.sig = sig;
    }
    jobs.classList.toggle("pt-list", T.view === "list");
    const min = Number(T.min) || 0;
    const byTime = list.slice().sort((a, b) => (Number(a.dataset.at) || 0) - (Number(b.dataset.at) || 0));
    byTime.forEach((el, i) => { const want = T.sort === "video" ? String(i) : ""; if (el.style.order !== want) el.style.order = want; });
    let shown = 0;
    for (const el of list) {
      const ok = (Number(el.dataset.score) || 0) >= min && lenOk(Number(el.dataset.len) || 0)
        && (T.cat === "all" || el.dataset.cat === T.cat) && showOk(el.dataset.rv || "");
      if (el.hidden === ok) el.hidden = !ok;
      if (ok) shown++;
    }
    const n = document.getElementById("pt_count");
    if (n) { const t = list.length ? `Showing ${shown} of ${list.length} clips` : "No clips yet"; if (n.dataset.t !== t) { n.dataset.t = t; n.innerHTML = list.length ? `Showing <b>${shown}</b> of ${list.length} clips` : "No clips yet"; } }
    // Say so when the choices hide everything, so an empty page never looks like a broken one.
    const grid = jobs.querySelector(".grid");
    let none = jobs.querySelector(".pt-none");
    if (grid && list.length && !shown) {
      if (!none) { none = document.createElement("p"); none.className = "pt-none"; none.textContent = "No clip matches those choices. Press Clear choices to see them all."; grid.after(none); }
    } else if (none) none.remove();
  }

  document.addEventListener("change", (e) => {
    const k = e.target && e.target.dataset && e.target.dataset.pt;
    if (!k) return;
    T[k] = e.target.value; save(); const host = document.getElementById("projbar"); if (host) host.dataset.sig = ""; apply();
  });

  P.add("project-tools", {
    label: "Project page toolbar",
    after: { drawJobs() { apply(); } },
    act: {
      ptset(el) { T[el.dataset.k] = el.dataset.v; save(); const h = document.getElementById("projbar"); if (h) h.dataset.sig = ""; apply(); },
      ptreset() { T = { ...DEFAULTS }; save(); const h = document.getElementById("projbar"); if (h) h.dataset.sig = ""; apply(); },
      ptpick() {
        const jobs = document.getElementById("jobs"); if (!jobs) return;
        let n = 0;
        for (const el of clips(jobs)) {
          if (el.hidden) continue;
          const box = el.querySelector("[data-sel]");
          if (box && typeof sel === "function") { sel().add(box.dataset.sel); n++; }
        }
        if (!n) { P.toast("Nothing is showing to select. Ready clips only can be selected.", "bad"); return; }
        if (typeof render === "function") render();
        P.toast(`Selected ${n} clip${n === 1 ? "" : "s"}. Post or download them from the bar at the bottom.`, "ok");
      },
    },
  });
})();
