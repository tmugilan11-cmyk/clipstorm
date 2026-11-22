/* Version chips in the clip dialog, so an older take can be pinned back.
 *
 * When a clip is rendered again the old file is kept. The server knows every version of a clip and
 * which one is the keeper. This puts those versions under the re-make button as chips, one per take,
 * each one showing the time it was made. The current take is marked. Pressing a chip asks the server
 * to pin that version, then re-reads the job so the page shows the truth.
 *
 * The block is quiet: it hides itself while there is nothing to choose between, and it stays hidden
 * when the server cannot answer. Nothing here throws into the page.
 */
(() => {
  const P = window.PeakCut;

  P.css("history", `
    .pchist{display:flex;flex-direction:column;gap:9px;min-width:0}
    .pchist .ph-head{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
    .pchist .ph-title{margin:0;font-size:13px;font-weight:600;color:var(--dim)}
    .pchist .ph-note{margin:0;font-size:13px;line-height:1.45;color:var(--faint)}
    .pchist .ph-row{display:flex;flex-wrap:wrap;gap:6px;min-width:0}
    .pchist .pchip{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 11px;
      border:1px solid var(--line-2);border-radius:999px;background:var(--bg);color:var(--dim);
      font:inherit;font-size:13px;font-variant-numeric:tabular-nums;cursor:pointer;
      transition:background .2s ease,border-color .2s ease,color .2s ease}
    .pchist .pchip:hover{border-color:#D4CAC3;background:var(--muted);color:var(--text)}
    .pchist .pchip:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
    .pchist .pchip .pv{font-weight:600;letter-spacing:.01em}
    .pchist .pchip .pt{color:var(--faint);font-variant-numeric:tabular-nums}
    .pchist .pchip.now{border-color:var(--brand-line);background:var(--brand-soft);color:var(--brand-deep)}
    .pchist .pchip.now .pt{color:var(--brand-deep);opacity:.8}
    .pchist .pchip.kept{border-color:transparent;background:var(--good-soft);color:var(--good)}
    .pchist .pchip.kept .pt{color:var(--good);opacity:.8}
    .pchist .pchip.gone{opacity:.6;text-decoration:line-through}
    .pchist .pchip[disabled]{cursor:default;opacity:.55}
    .pchist .pk{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;opacity:.9}
    @media (prefers-reduced-motion: reduce){ .pchist .pchip{transition:none} }
    @media (max-width: 640px){ .pchist .pchip{min-height:44px;padding:0 13px} .pchist .ph-note{display:none} }
  `);

  const OK_ID = /^[A-Za-z0-9_-]+$/;   // the only shape an id may take before it goes into a URL
  const DATA = new Map();             // "jid:cid" -> {versions, current} as the server last told us
  const ASKED = new Set();            // "jid:cid@version" already asked for, so no request per frame
  const DEAD = new Set();             // "jid:cid" the server would not answer for
  const BUSY = new Set();             // "jid:cid" with a pin request in flight right now

  // Every string that came from the server passes through here before it becomes markup.
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const key = (jid, cid) => jid + ":" + cid;
  const okId = v => typeof v === "string" && OK_ID.test(v);

  function say(msg, kind) {
    try { if (P && typeof P.toast === "function") P.toast(msg, kind); } catch {}
  }

  // A version time, in the same shape the rest of the page shows times. Empty when it is not a date.
  function when(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    try {
      return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      const p = d.toISOString();
      return p.slice(5, 10).replace("-", " ") + " " + p.slice(11, 16);
    }
  }

  function size(n) {
    const b = Number(n);
    if (!Number.isFinite(b) || b <= 0) return "";
    return b < 1048576 ? Math.max(1, Math.round(b / 1024)) + " KB" : (b / 1048576).toFixed(1) + " MB";
  }

  // The ids the dialog is showing. `D` is the object drawClipDlg reads, so it is the real source of
  // truth. If it cannot be read, the panel's own copy button carries the same two ids in the markup.
  function target() {
    try {
      if (typeof D !== "undefined" && D && D.jid != null && D.cid != null) {
        const jid = String(D.jid), cid = String(D.cid);
        if (okId(jid) && okId(cid)) return { jid, cid };
      }
    } catch {}
    const hit = document.querySelector('#clipdlg [data-act="copy"][data-j][data-c]');
    if (hit) {
      const jid = String(hit.dataset.j || ""), cid = String(hit.dataset.c || "");
      if (okId(jid) && okId(cid)) return { jid, cid };
    }
    return null;
  }

  function panel() {
    const dlg = document.querySelector("#clipdlg");
    if (!dlg || !dlg.open) return null;
    return dlg.querySelector(".panel");
  }

  // The page ships its own version strip inside #dlgvers, drawn by its inline drawHist(). Two strips
  // saying the same thing is worse than one, so the stronger block takes the slot: while these chips
  // are showing, that strip is hidden. When these chips stand down, the slot is handed back untouched,
  // so the page's own strip can look after itself exactly as before.
  function takeSlot(box, mine) {
    const slot = box.querySelector("#dlgvers");
    if (!slot) return;
    if (mine) slot.hidden = true;
  }

  const vmSig = list => list.map(v => v.n + (v.kept ? "k" : "") + (v.exists === false ? "x" : "") + (v.made_at || "")).join(",");

  function sortVersions(list) {
    return list.filter(v => v && typeof v === "object")
      .map(v => ({ ...v, n: Number(v.v) }))
      .filter(v => Number.isFinite(v.n) && v.n >= 0)
      .sort((a, b) => a.n - b.n);
  }

  function block(jid, cid, h) {
    const vs = sortVersions(h.versions);
    const now = Number(h.current);
    const busy = BUSY.has(key(jid, cid));
    const chips = vs.map(v => {
      const isNow = v.n === now;
      const cls = ["pchip", v.kept ? "kept" : isNow ? "now" : "", v.exists === false ? "gone" : ""].filter(Boolean).join(" ");
      const t = when(v.made_at);
      const tip = ["Version " + v.n, t, size(v.bytes), v.exists === false ? "no longer on disk" : ""].filter(Boolean).join(" · ");
      const mark = v.kept ? `<span class="pk">keeper</span>` : isNow ? `<span class="pk">now</span>` : "";
      return `<button type="button" class="${cls}" data-act="pchistkeep" data-j="${esc(jid)}" data-c="${esc(cid)}" data-v="${v.n}"
        title="${esc(tip)}" aria-current="${isNow ? "true" : "false"}"${busy ? " disabled" : ""}>
        <span class="pv">v${v.n}</span>${t ? `<span class="pt">${esc(t)}</span>` : ""}${mark}</button>`;
    }).join("");
    return `<div class="pchist" data-j="${esc(jid)}" data-c="${esc(cid)}" role="group" aria-label="Versions of this clip">
        <div class="ph-head"><p class="ph-title">Versions</p>
          <p class="ph-note">Every take of this clip, oldest first. Press one to keep it.</p></div>
        <div class="ph-row">${chips}</div>
      </div>`;
  }

  function paint() {
    const box = panel();
    if (!box) return;
    const mine = box.querySelector(":scope > .pchist");
    const t = target();
    const h = t ? DATA.get(key(t.jid, t.cid)) : null;
    const vs = h ? sortVersions(h.versions) : [];
    // One version is not a choice. Nothing to say, so say nothing, and give the slot back.
    if (!t || !h || vs.length < 2 || DEAD.has(key(t.jid, t.cid))) {
      if (mine) mine.remove();
      takeSlot(box, false);
      return;
    }
    const sig = [t.jid, t.cid, vmSig(vs), Number(h.current) || 0, BUSY.has(key(t.jid, t.cid)) ? 1 : 0].join("|");
    if (mine && mine.dataset.sig === sig) return;
    const html = block(t.jid, t.cid, h);
    if (mine) {
      const tpl = document.createElement("template");
      tpl.innerHTML = html;
      const node = tpl.content.firstElementChild;
      node.dataset.sig = sig;
      mine.replaceWith(node);
      return;
    }
    const tpl = document.createElement("template");
    tpl.innerHTML = html;
    const node = tpl.content.firstElementChild;
    node.dataset.sig = sig;
    const anchor = box.querySelector("#dlgvers");
    if (anchor) anchor.after(node);
    else {
      const remake = box.querySelector('[data-act="remake"]');
      if (remake) remake.after(node); else box.append(node);
    }
  }

  // Ask the server once per clip version. A failed read is remembered so it is not retried every frame.
  async function load(jid, cid, version) {
    const k = key(jid, cid), stamp = k + "@" + version;
    if (ASKED.has(stamp) || DEAD.has(k)) return;
    ASKED.add(stamp);
    try {
      const h = await P.api(`/api/jobs/${encodeURIComponent(jid)}/clips/${encodeURIComponent(cid)}/history`);
      if (h && Array.isArray(h.versions)) DATA.set(k, { versions: h.versions, current: Number(h.current) || 0 });
      else DEAD.add(k);
    } catch {
      DEAD.add(k);                       // no history route on this job, or the server said no
    }
    paint();
  }

  // After a pin, read the job back so every other part of the page sees the same clip.
  async function reread(jid) {
    let fresh = null;
    try { fresh = await P.api(`/api/jobs/${encodeURIComponent(jid)}`); } catch { return; }
    if (!fresh || fresh.id == null) return;
    const st = P.state();
    if (!st || !Array.isArray(st.jobs)) return;
    const at = st.jobs.findIndex(j => j && String(j.id) === String(fresh.id));
    if (at >= 0) st.jobs[at] = fresh; else st.jobs.push(fresh);
    try { if (typeof window.render === "function") window.render(); } catch {}
  }

  function clipOf(jid, cid) {
    const st = P.state();
    const j = ((st && st.jobs) || []).find(x => x && String(x.id) === jid);
    const c = j && Array.isArray(j.clips) ? j.clips.find(x => x && String(x.id) === cid) : null;
    return c || null;
  }

  // The hook: after the clip dialog is drawn, make sure the block matches the clip on screen.
  function after(root) {
    try {
      const box = panel();
      if (!box) return;
      const t = target();
      if (!t) return;
      const c = clipOf(t.jid, t.cid);
      if (c) load(t.jid, t.cid, String(c.version == null ? "" : c.version));
      paint();
    } catch {}
  }

  async function keep(el) {
    const jid = String(el.dataset.j || ""), cid = String(el.dataset.c || ""), v = Number(el.dataset.v);
    if (!okId(jid) || !okId(cid) || !Number.isFinite(v)) return;
    const k = key(jid, cid);
    if (BUSY.has(k)) return;
    BUSY.add(k);
    el.disabled = true;
    paint();
    try {
      const r = await P.send(`/api/jobs/${encodeURIComponent(jid)}/clips/${encodeURIComponent(cid)}/history`, { keep: v }, "PATCH");
      if (r && Array.isArray(r.versions)) DATA.set(k, { versions: r.versions, current: Number(r.current) || 0 });
      say(`Pinned version ${r && r.kept != null ? r.kept : v}`, "ok");
      await reread(jid);
    } catch (err) {
      say(String((err && err.message) || err || "Could not pin that version."), "bad");
    } finally {
      BUSY.delete(k);
      paint();
    }
  }

  P.add("history", {
    act: { pchistkeep: el => keep(el) },
    after: { drawClipDlg: root => after(root) },
  });
})();
