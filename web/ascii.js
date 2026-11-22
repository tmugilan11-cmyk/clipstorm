/* PeakCut ASCII field: a soft colour cloud with loose clusters of small characters that fade in and out as it drifts.
   Smooth: every character keeps its own glyph and only its opacity moves, and the cloud is drawn small and scaled up
   (a cheap, natural blur), so it can run at full frame rate.
   Usage: PeakAscii(canvasElement, {strength: 1}). Pauses off screen and when the tab is hidden; still for reduced motion. */
(function () {
  const GLYPHS = "-=+xX+x=";
  const CLOUD = [[255, 206, 166], [255, 228, 198], [255, 192, 146], [255, 238, 220]];
  const INK = "214,120,52";

  const P = new Uint8Array(512);
  (function () { const p = []; for (let i = 0; i < 256; i++) p[i] = i;
    let s = 7; for (let i = 255; i > 0; i--) { s = (s * 16807) % 2147483647; const j = s % (i + 1); [p[i], p[j]] = [p[j], p[i]]; }
    for (let i = 0; i < 512; i++) P[i] = p[i & 255]; })();
  const ease = t => t * t * (3 - 2 * t);
  function vnoise(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y), u = ease(x - xi), v = ease(y - yi);
    const h = (a, b) => P[(P[a & 255] + b) & 511] / 255;
    const a = h(xi, yi), b = h(xi + 1, yi), c = h(xi, yi + 1), d = h(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  const noise = (x, y) => vnoise(x, y) * .65 + vnoise(x * 2.1 + 17, y * 2.1 + 5) * .35;
  const smooth = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

  function PeakAscii(canvas, opts) {
    opts = Object.assign({cell: 11, line: 17, strength: 1}, opts || {});
    const ctx = canvas.getContext("2d");
    const cloud = document.createElement("canvas"), cctx = cloud.getContext("2d");
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w = 0, h = 0, raf = 0, visible = true, cells = [];
    const t0 = performance.now();

    const band = y => { const v = y / h; return smooth(.12, .5, v) * smooth(1.04, .84, v); };

    function size() {
      const r = canvas.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
      w = Math.max(1, Math.round(r.width)); h = Math.max(1, Math.round(r.height));
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cloud.width = Math.max(8, Math.round(w / 10)); cloud.height = Math.max(8, Math.round(h / 10));
      cells = [];                                         // every character keeps its glyph; only opacity changes
      for (let y = 4, row = 0; y < h; y += opts.line, row++) {
        const m = band(y);
        if (m < .03) continue;
        for (let x = (row % 2) * opts.cell * .5; x < w; x += opts.cell) {
          const k = P[(P[(x / opts.cell) & 255] + row) & 511];
          cells.push({x, y, m, g: GLYPHS[k % GLYPHS.length], o: (k % 7) / 7});
        }
      }
    }

    function draw(now) {
      const t = (now - t0) / 1000;
      // the cloud, drawn at a tenth of the size and stretched: soft without an expensive blur
      const cw = cloud.width, ch = cloud.height;
      cctx.clearRect(0, 0, cw, ch);
      CLOUD.forEach((c, i) => {
        const bx = (.15 + i * .24 + Math.sin(t * .09 + i * 1.9) * .07) * cw;
        const by = (.68 + Math.cos(t * .07 + i * 1.3) * .08) * ch;
        const r = (.38 + (i % 2) * .1) * Math.max(cw, ch * 1.6);
        const g = cctx.createRadialGradient(bx, by, 0, bx, by, r);
        g.addColorStop(0, `rgba(${c},.62)`); g.addColorStop(.55, `rgba(${c},.25)`); g.addColorStop(1, `rgba(${c},0)`);
        cctx.fillStyle = g; cctx.fillRect(0, 0, cw, ch);
      });
      ctx.clearRect(0, 0, w, h);
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
      ctx.drawImage(cloud, 0, 0, w, h);
      const top = ctx.createLinearGradient(0, 0, 0, h * .5);
      top.addColorStop(0, "#fff"); top.addColorStop(.6, "rgba(255,255,255,.75)"); top.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = top; ctx.fillRect(0, 0, w, h * .5);

      // the characters: each one fades in and out with the drifting noise
      ctx.font = `400 ${opts.line - 5}px ui-monospace, "Cascadia Mono", Consolas, monospace`;
      ctx.textBaseline = "top";
      const sx = t * .045, sy = t * .028;
      for (const c of cells) {
        const n = noise(c.x * .012 + sx, c.y * .03 - sy) + c.o * .06;
        const a = smooth(.5, .78, n) * c.m * opts.strength * .5;
        if (a < .02) continue;
        ctx.fillStyle = `rgba(${INK},${a.toFixed(3)})`;
        ctx.fillText(c.g, c.x, c.y);
      }
    }

    function loop(now) {
      raf = 0;
      if (!visible || document.hidden) return;
      draw(now);
      raf = requestAnimationFrame(loop);
    }
    const start = () => { if (!raf && !still) raf = requestAnimationFrame(loop); };
    size(); draw(performance.now());
    new ResizeObserver(() => { size(); draw(performance.now()); }).observe(canvas);
    try { new IntersectionObserver(es => { visible = es[0].isIntersecting; if (visible) start(); }).observe(canvas); } catch {}
    document.addEventListener("visibilitychange", start);
    start();
  }
  window.PeakAscii = PeakAscii;
})();

/* PeakCut clip tools: the small fetch wrappers the app page calls for clip work, plus the clipping-rules badge.
   Every call resolves - {ok:true, ...} or {ok:false, error:"a sentence a person can read"} - and none of them ever
   rejects, so a dead network, a route that is not there yet or an answer that is not JSON can only become a message.
   Nothing here touches the page: no toast, no redirect, no DOM. The caller decides what to show.
   Usage: PeakTools.translateClip(jid, cid, "es").then(r => r.ok ? draw(r) : note(r.error)); */
(function () {
  const HEAD = {"Content-Type": "application/json"};
  const PLAIN = "Clipstorm could not do that. Try again.";
  const TIP = "We found no public clipping rule. Check their channel rules before you post.";
  const LABELS = {allowed: "Clipping allowed", ask: "Has clip tips", no: "No clipping", unknown: "Rules unknown"};
  const TONES = {allowed: "ok", ask: "warn", no: "bad", unknown: ""};
  const PLATFORMS = ["youtube", "twitch", "kick"];
  const RULES_TTL = 30000;                       // the rules table does not change while a page is open

  const said = v => typeof v === "string" ? v.trim() : "";
  const part = v => { const t = String(v == null ? "" : v).trim(); return t ? encodeURIComponent(t) : ""; };
  const esc = v => String(v == null ? "" : v).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[c]);

  // fetch + JSON the way the app page does it (a failed reply's "detail" is the message), but a failure is a value here.
  async function ask(path, opt) {
    try {
      const r = await fetch(path, opt);
      let body = null;
      try { body = await r.json(); } catch {}
      if (!r.ok) return {ok: false, error: because(r, body), status: r.status};
      return body && typeof body === "object" ? Object.assign({ok: true}, body) : {ok: true};
    } catch {
      return {ok: false, status: 0, error: navigator.onLine === false
        ? "You are offline. Check your connection." : "Clipstorm is not answering. Try again in a moment."};
    }
  }

  // "Not Found" and its friends are the server's own words for a route that is not there; a person should not read them.
  const STOCK = {"not found": 1, "method not allowed": 1, "internal server error": 1, "unprocessable entity": 1,
                 "bad request": 1, "unauthorized": 1, "forbidden": 1, "too many requests": 1};

  function because(r, body) {
    let detail = body && body.detail;
    if (Array.isArray(detail)) detail = detail[0] && detail[0].msg;      // FastAPI's own body validation wording
    if (said(detail) && !STOCK[said(detail).toLowerCase()]) return detail.trim();
    if (r.status === 401 || r.status === 403) return "Please sign in.";
    if (r.status === 404) return "That is not here any more.";
    if (r.status === 429) return "Too many at once. Wait a moment.";
    if (r.status >= 500) return "Clipstorm ran into a problem with that. Try again.";
    return PLAIN;
  }

  const post = (path, body) => ask(path, {method: "POST", headers: HEAD, body: JSON.stringify(body || {})});
  const clipPath = (jid, cid, tail) => `/api/jobs/${part(jid)}/clips/${part(cid)}/${tail}`;

  async function translateClip(jid, cid, lang) {
    if (!part(jid) || !part(cid)) return {ok: false, error: "Pick a clip first."};
    const code = said(lang).toLowerCase();
    if (!code) return {ok: false, error: "Pick the language to translate into."};
    return post(clipPath(jid, cid, "translate"), {lang: code});
  }

  async function editClip(jid, cid, words) {
    if (!part(jid) || !part(cid)) return {ok: false, error: "Pick a clip first."};
    if (!said(words)) return {ok: false, error: "Say what to change about the clip."};
    // "text" is the name the edit route reads: sending anything else makes every note look like an empty one.
    return post(clipPath(jid, cid, "edit"), {text: said(words)});
  }

  async function peekClip(jid) {
    if (!part(jid)) return {ok: false, error: "There is nothing to look at yet."};
    return post(`/api/jobs/${part(jid)}/peek`, {});
  }

  let cache = {at: 0, table: null}, pending = null;

  function rules() {                             // one GET shared by every creator row drawn on the page
    const now = Date.now();
    if (cache.table && now - cache.at < RULES_TTL) return Promise.resolve({ok: true, rules: cache.table});
    if (pending) return pending;
    pending = ask("/api/rules", {headers: {"Accept": "application/json"}}).then(got => {
      pending = null;
      if (!got.ok) return got;                   // not cached: the next row may reach a server this one could not
      cache = {at: Date.now(), table: got.rules && typeof got.rules === "object" ? got.rules : {}};
      return {ok: true, rules: cache.table};
    });
    return pending;
  }

  function platformOf(value) {
    const raw = String(value == null ? "" : value).trim().toLowerCase().replace(/^[a-z][a-z0-9+.\-]*:\/\//, "")
      .split(/[/?#]/)[0].replace(/^www\./, "").replace(/\.$/, "");
    if (PLATFORMS.indexOf(raw) >= 0) return raw;
    const named = raw.split(/[.:]/).filter(p => PLATFORMS.indexOf(p) >= 0)[0];
    if (named) return named;
    return {"yt": "youtube", "youtubecom": "youtube", "twitchtv": "twitch", "kickcom": "kick"}[raw.replace(/[^a-z]/g, "")] || "";
  }

  function handleOf(value) {
    let h = String(value == null ? "" : value).trim().toLowerCase();
    if (!h) return "";
    if (h.indexOf("://") >= 0 || h.indexOf("/") >= 0 || h.indexOf(" ") >= 0) {
      const bits = h.split(/[\s/?#]+/).filter(Boolean);      // a whole link is accepted; its last piece is the handle
      h = bits.length ? bits[bits.length - 1] : "";
    }
    return h.replace(/^[:\/]+/, "").replace(/[.,]+$/, "");
  }

  function keysOf(platform, handle) {            // same order the server tries: exact first, YouTube with its '@'
    const h = handleOf(handle);
    if (!h) return [];
    const plain = h.replace(/^@/, ""), found = platformOf(platform), out = [];
    const add = k => { if (out.indexOf(k) < 0) out.push(k); };
    (found ? [found] : PLATFORMS).forEach(plat => {
      add(plat + ":" + h);
      if (plat === "youtube") { add("youtube:@" + plain); add("youtube:" + plain); }
    });
    return out;
  }

  const sourceOf = v => typeof v === "string" && /^https?:\/\/[^\s"'<>]+$/i.test(v.trim()) ? v.trim() : "";

  function badgeFor(table, platform, handle) {
    const rows = table || {}, keys = keysOf(platform, handle);
    let row = null;
    for (let i = 0; i < keys.length && !row; i++) {
      if (Object.prototype.hasOwnProperty.call(rows, keys[i])) row = rows[keys[i]];
    }
    const rule = row && LABELS[row.rule] ? row.rule : "unknown";
    const tone = TONES[rule], label = LABELS[rule];
    const note = said(row && row.note), source = sourceOf(row && row.source);
    const pill = `<span class="pill${tone ? " " + tone : ""}" title="${esc(note || TIP)}">${esc(label)}</span>`;
    return {rule, tone, label, note, source, blocked: rule === "no",
            html: source ? `<a href="${esc(source)}" target="_blank" rel="noopener">${pill}</a>` : pill};
  }

  async function ruleBadge(platform, handle) {
    if (!handleOf(handle)) return {ok: true, html: "", rule: "unknown", tone: "", label: "", blocked: false};
    const got = await rules();
    if (!got.ok) return got;
    return Object.assign({ok: true}, badgeFor(got.rules, platform, handle));
  }

  window.PeakTools = Object.assign(window.PeakTools || {}, {
    translateClip: translateClip, editClip: editClip, peekClip: peekClip, ruleBadge: ruleBadge
  });
})();
