/* How far people watched one video. The Content tab lists every video in the range; this card sits
 * under that list, offers the same videos in a picker, and draws the audience-retention curve for the
 * one picked: one line, share still watching against position through the video.
 *
 * The table draws no video id anywhere and this file does not own the table, so the ids come from the
 * route the table itself reads. The titles the table is showing decide which of those ids the picker
 * offers, and in what order, so the two stay in step.
 */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-retention", `
    .an-ret{margin-top:16px}
    .an-ret .rttl{display:flex;align-items:center;gap:8px}
    .an-ret .rttl svg{flex:none;width:16px;height:16px;color:var(--brand)}
    .an-ret .card-head .help{margin:4px 0 0;max-width:58ch}
    .an-ret .rpick{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--dim)}
    .an-ret .rpick select{height:34px;max-width:300px;padding:0 10px;border:1px solid var(--line-2);
      border-radius:var(--r-sm);background:var(--bg);font-size:13px;color:var(--text)}
    .an-ret .rpick select:disabled{color:var(--faint)}
    .an-ret .rwrap{position:relative;padding:6px 4px 0;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--bg)}
    .an-ret .rwrap:focus{outline:none}
    .an-ret .rwrap:focus-visible{outline:2px solid var(--brand-line);outline-offset:2px}
    .an-ret .rsvg{display:block;width:100%;height:auto;color:var(--brand-deep);cursor:crosshair;touch-action:pan-y}
    .an-ret .rg{stroke:var(--line);stroke-width:1;shape-rendering:crispEdges}
    .an-ret .rbase{stroke:var(--line-2);stroke-width:1;shape-rendering:crispEdges}
    .an-ret .rt{font-size:11px;fill:var(--faint);font-variant-numeric:tabular-nums}
    .an-ret .rcap{font-size:11px;fill:var(--dim)}
    .an-ret .rarea{fill:currentColor;stroke:none;opacity:.06}
    .an-ret .rline{fill:none;stroke:currentColor;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
    .an-ret .rcursor{stroke:var(--faint);stroke-width:1;stroke-dasharray:3 3;opacity:0}
    .an-ret .rcursor.on{opacity:.85}
    .an-ret .rdot{fill:#fff;stroke:currentColor;stroke-width:2.4;opacity:0}
    .an-ret .rdot.on{opacity:1}
    .an-ret .rtip{position:absolute;z-index:6;min-width:150px;padding:8px 10px 9px;border:1px solid var(--line-2);
      border-radius:var(--r-sm);background:var(--bg);font-size:12px;color:var(--dim);pointer-events:none;
      opacity:0;transform:translate(-50%,-100%);transition:opacity .1s ease}
    .an-ret .rtip.on{opacity:1}
    .an-ret .rtip .d{display:block;margin-bottom:4px;font-size:11px;font-weight:600;color:var(--text)}
    .an-ret .rtip .rr{display:flex;justify-content:space-between;gap:16px;line-height:1.6}
    .an-ret .rtip .rr b{font-weight:600;color:var(--text);font-variant-numeric:tabular-nums}
    .an-ret .rmsg{margin:0;padding:16px 2px;font-size:13px;color:var(--dim)}
    .an-ret .rnote{margin:10px 0 0;font-size:12px;color:var(--faint)}
    .an-ret .rerr{margin:0;padding:12px 14px;border-radius:var(--r-sm);background:var(--bad-soft);color:var(--bad);font-size:13px}
    .an-ret .rerr button{margin-left:8px;border:0;background:none;color:var(--bad);font:inherit;font-weight:600;text-decoration:underline;cursor:pointer}
    .an-ret .rerr a{color:inherit;font-weight:600;text-decoration:underline}
    @media (max-width:700px){.an-ret .rpick,.an-ret .rpick select{width:100%;max-width:none}}
    @media (prefers-reduced-motion:reduce){.an-ret .rtip{transition:none}}
  `);

  const LIST = "/api/analytics/videos", CURVE = "/api/analytics/retention";
  const W = 640, H = 210, PL = 46, PR = 16, PT = 26, PB = 34;
  const PW = W - PL - PR, PH = H - PT - PB, MID = PL + PW / 2, BASE = H - PB;
  const PICK = "Pick a video to see how far people watched.";
  const TICKS = [0, 25, 50, 75, 100];
  const nf1 = new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const obj = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : null);
  const num = (v) => {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const say = (err) => String((err && err.message) || err || "The server did not answer.");
  /* The curve comes from YouTube, so the no-channel error asks for a channel. When the server's
     sentence names Connected apps, those words get a link, the way the other cards do it. */
  const linked = (t) => {
    const e = esc(t);
    return e.includes("Connected apps") ? e.replace("Connected apps", '<a href="/app/apps">Connected apps</a>') : e;
  };
  const clamp = (n) => Math.max(0, Math.min(100, n));
  const pct = (n) => (Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : nf1.format(n));
  const xOf = (at) => PL + (clamp(at) / 100) * PW;
  const yOf = (w) => PT + (1 - clamp(w) / 100) * PH;

  function mmss(s) {
    const t = Math.max(0, Math.round(Number(s) || 0));
    const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), r = t % 60;
    return h ? h + ":" + String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0")
      : m + ":" + String(r).padStart(2, "0");
  }

  async function get(path) {
    if (typeof P.api === "function") return P.api(path);
    const r = await fetch(path);
    if (!r.ok) {
      let d = r.statusText;
      try { d = (await r.json()).detail || d; } catch { /* a plain-text answer keeps the status text */ }
      throw new Error(d || "The request failed.");
    }
    return r.json();
  }

  /* The videos the table is showing right now: its title cells, in the order it drew them. The table
   * owns its own markup, so this reads the page rather than any state of its own. */
  function visible() {
    try {
      const cells = document.querySelectorAll("#an_table .ant-name");
      return Array.prototype.map.call(cells, (el) => String(el.textContent || "").replace(/\s+/g, " ").trim());
    } catch { return []; }
  }

  // A YouTube id is 11 characters, reached either bare or inside a link. Nothing else is offered: the
  // retention route only answers for a video YouTube knows.
  function idOf(row) {
    const raw = String((row && (row.id || row.video || row.video_id)) || "").trim();
    const hit = raw.match(/(?:v=|youtu\.be\/|shorts\/|embed\/)([\w-]{11})/);
    const id = hit ? hit[1] : raw;
    return /^[\w-]{11}$/.test(id) ? id : "";
  }

  function dedupe(raw) {
    const seen = new Set(), out = [];
    for (const row of Array.isArray(raw) ? raw : []) {
      const o = obj(row) || {}, id = idOf(o);
      if (!id || seen.has(id)) continue;
      seen.add(id);
      const secs = num(o.seconds);
      out.push({ id, title: String(o.title || o.video_title || id).trim() || id, secs: secs && secs > 0 ? secs : null });
    }
    return out;
  }

  /* The table can be filtered or re-sorted at any time, and it does that without telling this file,
   * so the picker is put in the table's order again on every draw, not only when the list arrives. */
  function arrange(all, keepId) {
    const out = all || [];
    const order = new Map(visible().map((t, i) => [t, i]));
    if (!order.size) return out;
    const shown = out.filter((r) => order.has(r.title));
    if (!shown.length) return out;
    shown.sort((a, b) => order.get(a.title) - order.get(b.title));
    const kept = keepId && out.find((r) => r.id === keepId);
    if (kept && !shown.some((r) => r.id === keepId)) shown.push(kept);   // a filter must not drop the pick
    return shown;
  }

  /* The range the shell is showing, as days. The videos route takes days, so a range with real dates
   * is counted into days; the retention route is not date bound, so it needs none of this. */
  function winKey() {
    const A = obj(window.PeakCutAnalytics) || {};
    const day = (v) => (/^\d{4}-\d{2}-\d{2}/.test(String(v || "")) ? String(v).slice(0, 10) : "");
    const s = day(A.start), e = day(A.end);
    let days = num(A.days);
    if ((!days || days < 1) && s && e) days = Math.round((Date.parse(e + "T00:00:00") - Date.parse(s + "T00:00:00")) / 864e5) + 1;
    if (!days || days < 1) days = 28;
    days = Math.max(1, Math.min(3650, Math.round(days)));
    return { key: s && e ? s + "|" + e : "days|" + days, days };
  }

  function shape(st) {
    const raw = st.curve && Array.isArray(st.curve.points) ? st.curve.points : [];
    const pts = [];
    for (const p of raw) {
      const at = num(p && p.at), w = num(p && p.watching);
      if (at === null || w === null) continue;
      pts.push({ at: clamp(at), watching: clamp(w) });
    }
    pts.sort((a, b) => a.at - b.at);
    return pts;
  }

  function tipHtml(p, secs) {
    const head = secs ? mmss(secs * p.at / 100) + " into the video" : pct(p.at) + "% into the video";
    const rows = [`<span class="rr"><span>Still watching</span><b>${esc(pct(p.watching))}%</b></span>`];
    if (secs) rows.push(`<span class="rr"><span>Through the video</span><b>${esc(pct(p.at))}%</b></span>`);
    return `<span class="d">${esc(head)}</span>${rows.join("")}`;
  }

  function chartHtml(st, pts, secs) {
    const first = pts[0], last = pts[pts.length - 1];
    const grid = TICKS.map((v) => `<line class="rg" x1="${PL}" y1="${yOf(v).toFixed(1)}" x2="${W - PR}" y2="${yOf(v).toFixed(1)}"/>`).join("");
    const yTicks = TICKS.map((v) => `<text class="rt" x="${PL - 8}" y="${(yOf(v) + 3.6).toFixed(1)}" text-anchor="end">${v}%</text>`).join("");
    const xTicks = TICKS.map((v) => `<text class="rt" x="${xOf(v).toFixed(1)}" y="${BASE + 15}" text-anchor="middle">${v}%</text>`).join("");
    const line = pts.map((p) => `${xOf(p.at).toFixed(1)},${yOf(p.watching).toFixed(1)}`).join(" ");
    const area = "M " + xOf(first.at).toFixed(1) + " " + yOf(0).toFixed(1) + " L "
      + pts.map((p) => `${xOf(p.at).toFixed(1)} ${yOf(p.watching).toFixed(1)}`).join(" L ")
      + " L " + xOf(last.at).toFixed(1) + " " + yOf(0).toFixed(1) + " Z";
    const label = `Retention curve for ${st.title || "this video"}: ${pts.length} points, from `
      + `${pct(first.watching)} percent watching at ${pct(first.at)} percent through the video, to `
      + `${pct(last.watching)} percent watching at ${pct(last.at)} percent through.`;
    const note = [];
    if (st.curve && String(st.curve.note || "").trim()) note.push(String(st.curve.note).trim());
    note.push(secs
      ? "The second in the box is the share of the video just read, taken from the " + mmss(secs) + " length the video list sent."
      : "The video list did not send a length for this video, so the box names the share of the video instead of a second.");
    note.push("The curve covers every day YouTube holds for this video; the response does not name those dates, so none are shown here.");
    return `<div class="rwrap" tabindex="0" role="group" aria-label="Retention curve. Use the left and right arrow keys to read the points.">
        <svg class="rsvg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">
          ${grid}
          <line class="rbase" x1="${PL}" y1="${BASE}" x2="${W - PR}" y2="${BASE}"/>
          ${yTicks}${xTicks}
          <text class="rcap" x="${W - PR}" y="13" text-anchor="end">Still watching</text>
          <text class="rcap" x="${MID}" y="${H - 5}" text-anchor="middle">Position through the video</text>
          <path class="rarea" d="${area}"/>
          <polyline class="rline" points="${line}"/>
          <line class="rcursor" data-ar="cursor" x1="${PL}" y1="${PT}" x2="${PL}" y2="${BASE}"/>
          <circle class="rdot" data-ar="dot" cx="${PL}" cy="${BASE}" r="3.6"/>
        </svg>
        <div class="rtip" data-ar="tip" role="status"></div>
      </div>
      <p class="rnote">${esc(note.join(" "))}</p>`;
  }

  function bodyHtml(st, cur) {
    const secs = cur ? cur.secs : null;
    if (st.listErr) {
      return `<p class="rerr">Could not read the list of videos. ${esc(st.listErr)}`
        + ` <button type="button" data-ar="retry" data-ar-what="list">Try again</button></p>`;
    }
    if (st.loadingList && !(st.rows || []).length) return `<p class="rmsg">Reading the list of videos.</p>`;
    if (!(st.rows || []).length) return `<p class="rmsg">${esc(PICK)}</p><p class="rnote">No videos in this range yet, so the picker is empty.</p>`;
    if (!st.vid) return `<p class="rmsg">${esc(PICK)}</p>`;
    if (st.curveErr) {
      return `<p class="rerr">Could not read the retention curve for this video. ${linked(st.curveErr)}`
        + ` <button type="button" data-ar="retry" data-ar-what="curve">Try again</button></p>`;
    }
    if (st.loadingCurve || !st.curve) return `<p class="rmsg">Reading the retention curve for this video.</p>`;
    if (st.pts.length < 2) return `<p class="rmsg">This video has no retention curve to draw yet.</p>`;
    return chartHtml(st, st.pts, secs);
  }

  function paint(root) {
    const st = root.__ar;
    if (!st) return;
    const rows = arrange(st.rows, st.vid);
    st.pts = shape(st);
    const cur = rows.find((r) => r.id === st.vid) || null;
    if (cur) st.title = cur.title;
    const sig = [st.key, st.listErr, !!st.loadingList, rows.map((r) => r.id + ":" + r.title).join("\u0001"),
      st.vid || "", st.curveErr, !!st.loadingCurve, st.pts.length,
      st.pts.length ? st.pts[0].watching + "/" + st.pts[st.pts.length - 1].watching : "", cur ? cur.secs : ""].join("\u0002");
    if (st.sig === sig) return;
    st.sig = sig;

    const opts = rows.map((r) => `<option value="${esc(r.id)}"${r.id === st.vid ? " selected" : ""}>${esc(r.title)}</option>`).join("");
    root.innerHTML = `<div class="card-head">
        <div>
          <div class="rttl">${ic("chart")}<h2>How far people watched</h2></div>
          <p class="help">One video, from its first second to its last. The list is the same videos the table above is showing.</p>
        </div>
        <label class="rpick"><span>Video</span>
          <select data-ar="pick" aria-label="Video to draw the retention curve for"${rows.length ? "" : " disabled"}>
            <option value=""${st.vid ? "" : " selected"}>Pick a video</option>${opts}
          </select></label>
      </div>
      <div data-ar="body">${bodyHtml(st, cur)}</div>`;

    const wrap = root.querySelector(".rwrap");
    if (wrap) wire(wrap, st, st.pts, cur ? cur.secs : null);
  }

  /* Hover and arrow keys read the same curve: the box names the second and the share still watching,
   * and a thin line marks where that point sits. */
  function wire(wrap, st, pts, secs) {
    const svg = wrap.querySelector(".rsvg"), tip = wrap.querySelector('[data-ar="tip"]');
    const cursor = wrap.querySelector('[data-ar="cursor"]'), dot = wrap.querySelector('[data-ar="dot"]');
    if (!svg || !tip || !cursor || !dot || pts.length < 2) return;
    let at = -1;

    function hide() {
      at = -1;
      tip.classList.remove("on");
      tip.textContent = "";
      cursor.classList.remove("on");
      dot.classList.remove("on");
    }

    function show(i) {
      at = Math.max(0, Math.min(pts.length - 1, i));
      const p = pts[at], r = svg.getBoundingClientRect(), box = wrap.getBoundingClientRect();
      cursor.setAttribute("x1", xOf(p.at).toFixed(1));
      cursor.setAttribute("x2", xOf(p.at).toFixed(1));
      dot.setAttribute("cx", xOf(p.at).toFixed(1));
      dot.setAttribute("cy", yOf(p.watching).toFixed(1));
      cursor.classList.add("on");
      dot.classList.add("on");
      tip.innerHTML = tipHtml(p, secs);
      tip.classList.add("on");
      if (!r.width || !box.width) return;
      const k = r.width / W;
      const left = (r.left - box.left) + xOf(p.at) * k;
      const top = (r.top - box.top) + yOf(p.watching) * k;
      const half = (tip.offsetWidth || 160) / 2;
      tip.style.left = Math.round(Math.max(half + 4, Math.min(box.width - half - 4, left))) + "px";
      tip.style.top = Math.round(Math.max(tip.offsetHeight + 6, top - 10)) + "px";
    }

    svg.addEventListener("pointermove", (e) => {
      const r = svg.getBoundingClientRect();
      if (!r.width) return;
      const vx = (e.clientX - r.left) * (W / r.width);
      const want = (vx - PL) / PW * 100;
      let best = 0, gap = Infinity;
      for (let i = 0; i < pts.length; i += 1) {
        const d = Math.abs(pts[i].at - want);
        if (d < gap) { gap = d; best = i; }
      }
      show(best);
    });
    wrap.addEventListener("pointerleave", hide);
    wrap.addEventListener("focusout", hide);
    wrap.addEventListener("keydown", (e) => {
      const k = e.key;
      if (k === "ArrowRight" || k === "ArrowDown") { show(at < 0 ? 0 : at + 1); e.preventDefault(); }
      else if (k === "ArrowLeft" || k === "ArrowUp") { show(at < 0 ? pts.length - 1 : at - 1); e.preventDefault(); }
      else if (k === "Home") { show(0); e.preventDefault(); }
      else if (k === "End") { show(pts.length - 1); e.preventDefault(); }
      else if (k === "Escape") hide();
    });
  }

  function bind(root) {
    if (root.dataset.bound === "1") return;
    root.dataset.bound = "1";
    root.addEventListener("change", (e) => {
      const pick = e.target && e.target.closest ? e.target.closest("[data-ar=pick]") : null;
      if (!pick) return;
      const st = root.__ar;
      st.vid = String(pick.value || "");
      st.curve = null;
      st.curveErr = "";
      st.pts = [];
      st.seq = (st.seq || 0) + 1;
      st.loadingCurve = false;
      st.sig = "";
      paint(root);
      fill(root);
    });
    root.addEventListener("click", (e) => {
      const b = e.target && e.target.closest ? e.target.closest("[data-ar=retry]") : null;
      if (!b) return;
      const st = root.__ar;
      if (b.dataset.arWhat === "list") { st.rows = null; st.listErr = ""; }
      else { st.curve = null; st.curveErr = ""; st.seq = (st.seq || 0) + 1; st.loadingCurve = false; }
      st.sig = "";
      paint(root);
      fill(root);
    });
  }

  async function readList(root, w) {
    const st = root.__ar;
    const seq = (st.lseq = (st.lseq || 0) + 1);
    st.loadingList = true;
    paint(root);
    try {
      /* The whole list is kept, not just the part the table is showing, so clearing the table's
       * filter brings those videos back into the picker without another request. */
      const rows = dedupe(rowsOf(await get(LIST + "?days=" + w.days + "&limit=200")));
      if (!root.isConnected || st.lseq !== seq) return;
      st.rows = rows;
      st.listErr = "";
      if (st.vid && !rows.some((r) => r.id === st.vid)) { st.vid = ""; st.curve = null; st.pts = []; }
    } catch (err) {
      if (!root.isConnected || st.lseq !== seq) return;
      st.rows = [];
      st.listErr = say(err);
    } finally {
      if (st.lseq === seq) st.loadingList = false;
    }
    if (root.isConnected && st.lseq === seq) paint(root);
  }

  async function readCurve(root) {
    const st = root.__ar;
    if (st.loadingList || st.loadingCurve) return;
    const vid = st.vid, seq = (st.seq = (st.seq || 0) + 1);
    st.loadingCurve = true;
    paint(root);
    try {
      const got = obj(await get(CURVE + "?video=" + encodeURIComponent(vid)));
      if (!root.isConnected || st.seq !== seq) return;
      st.curve = got || { points: [] };
      st.curveErr = "";
    } catch (err) {
      if (!root.isConnected || st.seq !== seq) return;
      st.curve = null;
      st.curveErr = say(err);
    } finally {
      if (st.seq === seq) st.loadingCurve = false;
    }
    if (root.isConnected && st.seq === seq) paint(root);
  }

  function rowsOf(data) {
    const o = obj(data);
    const list = Array.isArray(data) ? data : o && (o.rows || o.videos || o.items);
    return Array.isArray(list) ? list : [];
  }

  async function fill(root) {
    const st = root.__ar;
    if (!st) return;
    const w = winKey();
    if (st.key !== w.key) {
      st.key = w.key;
      st.rows = null;
      st.listErr = "";
      st.loadingList = false;
      st.lseq = (st.lseq || 0) + 1;
    }
    if (!st.rows && !st.loadingList && !st.listErr) await readList(root, w);
    if (st.vid && !st.loadingCurve && !st.curve && !st.curveErr) await readCurve(root);
    if (root.isConnected) paint(root);
  }

  /* The card lives in the Content panel, under the table it borrows its videos from. The shell redraws
   * that panel on a tab change, so this looks again rather than holding on to an element. */
  function mount() {
    const panel = document.querySelector('[data-an-panel="content"]');
    if (!panel) return;
    let root = panel.querySelector('[data-ar="root"]');
    if (!root) {
      root = document.createElement("div");
      root.className = "an-ret card";
      root.setAttribute("data-ar", "root");
      const table = panel.querySelector("#an_table");
      if (table && table.parentNode === panel) panel.insertBefore(root, table.nextSibling);
      else panel.append(root);
    }
    if (!root.__ar) {
      root.__ar = {
        key: "", rows: null, listErr: "", loadingList: false, lseq: 0,
        vid: "", title: "", curve: null, curveErr: "", loadingCurve: false, seq: 0, pts: [], sig: ""
      };
    }
    bind(root);
    fill(root);
  }

  let queued = false;
  function draw() {
    queued = false;
    try { mount(); } catch (err) { try { console.warn("[PeakCut] analytics-retention:", err); } catch (e) { /* nothing left to say */ } }
  }
  function look() {
    if (queued) return;
    queued = true;
    // Once the page has settled, so the table around this card has drawn already. A tab in the
    // background does not run animation frames, so a timer draws it there too; either one runs once.
    try { requestAnimationFrame(draw); } catch (err) { /* older engine: the timer below still draws */ }
    setTimeout(() => { if (queued) draw(); }, 250);
  }

  P.add("analytics-retention", { label: "Retention curve", load() { look(); } });

  try {
    new MutationObserver(look).observe(document.getElementById("view") || document.body, { childList: true, subtree: true });
  } catch (err) { /* without an observer the look below and the render event still draw the card */ }
  document.addEventListener("peakcut:render", look);
  look();
})();
