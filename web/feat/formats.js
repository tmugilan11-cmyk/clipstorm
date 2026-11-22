/* Real caption animations and saved defaults. Editing ideas are reference notes, not automatic assembly. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.page !== "function") return;

  P.css("formats", `
    .fmtp{max-width:1120px}
    .fmtp-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--ink);margin:0 0 6px}
    .fmtp .help{max-width:64ch;margin:0}
    .fmtp-meta{margin:9px 0 0;font-size:13px;line-height:1.5;color:var(--dim);max-width:64ch}
    .fmtp-sec{margin-top:24px;border-top:1px solid var(--line);padding-top:18px}
    .fmtp-top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
    .fmtp-sub{margin:0;font-size:15px;font-weight:600;color:var(--ink);letter-spacing:-.005em}
    .fmtp-hint{display:block;margin:5px 0 0;font-size:13px;line-height:1.45;color:var(--dim);max-width:62ch}
    .fmtp-sec > .fmtp-hint{margin-top:6px}

    .fmt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin-top:13px}
    .fmt-card{display:flex;flex-direction:column;gap:7px;padding:13px 14px 12px;border:1px solid var(--line);
      border-radius:var(--r-sm);background:var(--bg);transition:border-color .14s ease}
    .fmt-card:hover{border-color:var(--line-2)}
    .fmt-name{margin:0;font-size:15px;font-weight:600;line-height:1.25;color:var(--ink)}
    .fmt-line{margin:0;font-size:13px;line-height:1.5;color:var(--dim)}
    .fmt-card{flex-direction:row;align-items:flex-start;gap:12px}
    .fmt-card[data-state="unavailable"]{background:var(--muted)}
    .fmt-card[data-state="unavailable"] .fmt-name,.fmt-card[data-state="unavailable"] .fmt-line{color:var(--dim)}
    .fmt-body{display:flex;flex-direction:column;gap:6px;min-width:0;flex:1}
    .fmt-best{margin:0;font-size:12.5px;line-height:1.45;color:var(--dim)}
    .fmt-best b{font-weight:600;color:var(--ink)}
    .fmt-state{margin:2px 0 0;font-size:12px;line-height:1.4;font-weight:600;color:var(--dim)}
    .fmt-state[data-s="ready"]{color:var(--brand-deep)}
    .fmt-state[data-s="needs_webcam"]{color:var(--ink)}
    .fmt-state span{font-weight:400}
    /* The little 9:16 picture: a phone-shaped frame with the parts of the clip drawn as plain blocks. */
    .fmt-dg{position:relative;flex:none;width:45px;height:80px;border:1px solid var(--line-2);border-radius:5px;
      background:var(--muted);overflow:hidden}
    .fmt-dg i{position:absolute;display:block;border-radius:2px;background:var(--line-2)}
    .fmt-dg i.b{background:var(--brand)}
    .fmt-dg i.h{background:var(--ink)}
    .fmt-dg i.d{background:var(--faint);opacity:.55}
    .fmt-dg i.f{background:var(--brand-soft);border:1px solid var(--brand)}
    .fmt-looks{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;margin-top:13px}
    .ftile{margin:0;display:flex;flex-direction:column;gap:6px}
    /* The server draws the whole 9:16 frame, where the words are a thin strip three quarters of the way down. Shown
       whole in a small tile that strip was a few pixels tall and every tile looked empty, so the tile is a window
       onto the part of the frame the words are in. */
    .ftile-fr{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;border:1px solid var(--line);
      border-radius:var(--r-sm);background:var(--muted)}
    /* the moving clip is drawn with its words two fifths of the way down, not three quarters like the still */
    .ftile-fr video{position:absolute;inset:0;object-position:50% 34% !important}
    .ftile-fr img,.ftile-fr video{display:block;width:100%;height:100%;object-fit:cover;object-position:50% 76%;opacity:0;
      border-radius:0;background:var(--muted);transition:opacity .18s ease}
    .ftile[data-st="ok"] .ftile-fr img,.ftile[data-st="ok"] .ftile-fr video{opacity:1}
    .ftile[data-st="off"] .ftile-fr img,.ftile[data-st="off"] .ftile-fr video{display:none}
    .ftile[data-st="off"] .ftile-fr::after{content:"Frame not drawn";position:absolute;inset:0;display:grid;
      place-items:center;padding:0 8px;text-align:center;font-size:11px;line-height:1.3;color:var(--dim)}
    /* While the moving preview is being drawn, the still frame shows and this says so, so a person is never left
       wondering whether the look has no motion at all. */
    .ftile .moving{position:absolute;left:5px;bottom:5px;font-size:9.5px;line-height:1.2;padding:2px 5px;
      border-radius:999px;background:rgba(0,0,0,.62);color:#F5F5F5;pointer-events:none}
    .ftile[data-mv="on"] .moving{display:none}
    .ftile .ftile-actions{display:grid;gap:6px}
    .ftile .btn{width:100%;justify-content:center;font-size:12px}
    .ftile [aria-pressed="true"]{border-color:var(--brand);color:var(--brand-deep)}
    .fmt-ideas{margin-top:28px;border-top:1px solid var(--line);padding-top:18px}
    .fmt-ideas summary{cursor:pointer;font-weight:600}
    .fmtp-status{min-height:22px;margin-top:8px;font-size:13px;color:var(--dim)}
    .ftile:not([data-st="ok"]):not([data-st="off"]) .ftile-fr::after{content:"";position:absolute;inset:0;
      transform:translateX(-100%);background:linear-gradient(100deg,transparent 25%,rgba(255,255,255,.14) 50%,transparent 75%);
      animation:fmtSheen 1.6s ease-in-out infinite}
    @keyframes fmtSheen{to{transform:translateX(100%)}}
    .ftile-lb{font-size:12px;line-height:1.3;color:var(--dim);overflow-wrap:anywhere}
    .ftile-do{font-size:11px;color:var(--faint)}
    .ftile[data-st="off"] .ftile-lb{color:var(--dim)}

    .fmt-empty{margin-top:13px;padding:16px 16px 15px;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--muted)}
    .fmt-empty p{margin:0;font-size:13px;line-height:1.5;color:var(--dim);max-width:60ch}
    .fmt-empty p + p{margin-top:6px}
    .fmtp .err{font-size:13px;line-height:1.5;max-width:62ch}

    @media (max-width:560px){
      .fmtp-h{font-size:20px}
      .fmt-grid{grid-template-columns:1fr}
      .fmt-looks{grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:10px}
    }
    @media (prefers-reduced-motion:reduce){
      .ftile-fr img{transition:none}
      .ftile:not([data-st="ok"]):not([data-st="off"]) .ftile-fr::after{animation:none;transform:none;background:transparent}
    }
  `);

  /* ---- small readers ---------------------------------------------------- */
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // A number the server sent, or null. Nothing is guessed: null means "this page has no number", which is a
  // different thing from the server saying zero, and the two are printed differently.
  const num = (v) => {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const icon = (n) => { try { return typeof ic === "function" ? ic(n) : ""; } catch { return ""; } };

  /** A server hint is written as a fragment ("one strong clip, the default"). Only the first letter is touched. */
  const sentence = (s) => {
    const t = String(s ?? "").trim();
    return t ? t.charAt(0).toUpperCase() + t.slice(1) : "";
  };

  /** One sentence for a failed read. The page never says nothing and never says "error" on its own. */
  const why = (err, what) => {
    const m = err && err.message ? String(err.message) : "";
    return m ? `${what}: ${m}` : `${what}. The app did not say why.`;
  };

  /* ---- the two lists ---------------------------------------------------- */
  // null means "not asked yet", [] means "asked and the answer was empty". They are different states and the page
  // shows them differently, so the distinction is kept rather than collapsed.
  let shapes = null;
  let shapeWhy = "";
  let looks = null;
  let lookWhy = "";
  let askedShapes = false;
  let askedLooks = false;
  let savingDefault = false;

  function readShapes(j) {
    const raw = j && Array.isArray(j.formats) ? j.formats : [];
    const out = [];
    for (const f of raw) {
      if (!f || typeof f !== "object") continue;
      const id = String(f.id ?? "").trim();
      const label = String(f.label ?? "").trim() || id;
      if (!id || out.some((x) => x.id === id)) continue;
      // `state` is the server's own word for whether the type really works: ready, needs_webcam or unavailable.
      // An older server that sends no state is treated as unavailable, never as ready, so nothing is promised.
      const state = ["ready", "needs_webcam", "unavailable"].includes(f.state) ? f.state : "unavailable";
      out.push({ id, label, hint: String(f.hint ?? "").trim(), line: String(f.line ?? "").trim(),
        best: String(f.best_for ?? "").trim(), state, reason: String(f.reason ?? "").trim(),
        needs: num(f.needs_parts) === null ? null : Math.max(0, Math.round(num(f.needs_parts))) });
    }
    const stated = j && Number.isFinite(Number(j.count)) ? num(j.count) : out.length;
    return { rows: out, count: out.length === 0 ? 0 : Math.max(out.length, stated), pick: j && String(j.default ?? "") };
  }

  /** The server answers {styles:[{name,label,house}]}; an older build answers {styles:{name:label}}. Both work. */
  function readLooks(j) {
    const out = [];
    // `anim` is kept, not dropped: the tile shows how the words move, and a look whose motion name were thrown away
    // here would render a card with nothing under its name. "house" means render.py gives it its own motion.
    const add = (name, label, anim) => {
      const n = String(name ?? "").trim();
      if (!n || out.some((x) => x.name === n)) return;
      out.push({ name: n, label: String(label ?? "").trim() || n, anim: String(anim ?? "").trim() });
    };
    if (j && Array.isArray(j.styles)) {
      for (const s of j.styles) {
        if (!s) continue;
        if (typeof s === "object") add(s.name, s.label, s.anim || (s.house ? "house" : ""));
        else add(s, s, "");
      }
    } else if (j && j.styles && typeof j.styles === "object") {
      for (const [k, v] of Object.entries(j.styles)) add(k, v, "");
    }
    const stated = j && Number.isFinite(Number(j.count)) ? num(j.count) : out.length;
    return { rows: out, count: out.length === 0 ? 0 : Math.max(out.length, stated), pick: j && String(j.default ?? "") };
  }

  let shapeCount = 0, shapePick = "", lookCount = 0, lookPick = "";

  // Every visit to the page draws fresh markup, so the paint runs every time: the fetch does not. Coming back to
  // the page costs no request, and a "Check again" press costs two.
  function askShapes(force) {
    if (askedShapes && !force) { paintShapes(); paintMeta(); return Promise.resolve(); }
    askedShapes = true;
    return Promise.resolve()
      .then(() => P.api("/api/formats"))
      .then((j) => {
        const got = readShapes(j);
        shapes = got.rows; shapeCount = got.count; shapePick = got.pick; shapeWhy = "";
      })
      .catch((err) => {
        shapes = []; shapeCount = 0; shapePick = "";
        shapeWhy = why(err, "The clip formats could not be read");
      })
      .then(() => { paintShapes(); paintMeta(); });
  }

  function askLooks(force) {
    if (askedLooks && !force) { paintLooks(); paintMeta(); return Promise.resolve(); }
    askedLooks = true;
    return Promise.resolve()
      .then(() => P.api("/api/captions/styles"))
      .then((j) => {
        const got = readLooks(j);
        looks = got.rows; lookCount = got.count; lookPick = got.pick; lookWhy = "";
      })
      .catch((err) => {
        looks = []; lookCount = 0; lookPick = "";
        lookWhy = why(err, "The caption looks could not be read");
      })
      .then(() => { paintLooks(); paintMeta(); });
  }

  /* ---- what the page says it holds ------------------------------------- */
  function labelOf(list, key, value) {
    const hit = (list || []).find((x) => x[key] === value);
    return hit ? (hit.label || hit.id || hit.name) : "";
  }

  function paintMeta() {
    const box = document.getElementById("fmt_meta");
    if (!box) return;
    box.textContent = looks && looks.length ? `${looks.length} video caption styles. Use a default for future clips, or change one clip in its editor.` : "Loading caption styles…";
  }

  /* ---- the clip type cards --------------------------------------------- */
  // Each card says what the viewer sees, shows the clip's structure as a tiny 9:16 picture, says when to use it, and
  // says honestly whether it works today. [left %, top %, width %, height %, kind] blocks; kinds: h = hook title,
  // b = brand colour (tag, bar, bubble), d = dark picture, f = frame, "" = plain picture.
  const DIAGRAMS = {
    moment: [[10, 8, 80, 8, "h"], [0, 28, 100, 44, ""], [14, 80, 72, 7, "b"]],
    callback: [[10, 6, 60, 8, "h"], [8, 18, 84, 26, ""], [30, 47, 40, 6, "b"], [8, 56, 84, 26, ""]],
    compilation: [[8, 8, 84, 24, ""], [8, 36, 84, 24, ""], [8, 64, 84, 24, "f"], [12, 12, 20, 8, "b"]],
    escalation: [[8, 8, 84, 24, ""], [8, 36, 84, 24, ""], [8, 64, 84, 24, ""], [8, 8, 84, 4, "d"], [8, 36, 84, 4, "b"], [8, 64, 84, 4, "b"]],
    thenvsnow: [[8, 8, 84, 36, ""], [14, 12, 26, 8, "b"], [8, 54, 84, 36, "f"], [14, 58, 26, 8, "b"]],
    reveal: [[0, 0, 100, 48, "d"], [10, 10, 60, 9, "b"], [0, 49, 100, 51, ""]],
    chat: [[0, 20, 100, 52, ""], [8, 58, 44, 7, "b"], [8, 68, 30, 7, "b"], [8, 78, 52, 7, "b"]],
    waitforit: [[0, 4, 62, 3, "b"], [8, 10, 46, 8, "b"], [0, 28, 100, 44, ""], [0, 80, 100, 8, "d"]],
  };

  function diagram(id) {
    const blocks = DIAGRAMS[id] || DIAGRAMS.moment;
    return `<span class="fmt-dg" aria-hidden="true">${blocks.map(([x, y, w, h, k]) =>
      `<i${k ? ` class="${k}"` : ""} style="left:${x}%;top:${y}%;width:${w}%;height:${h}%"></i>`).join("")}</span>`;
  }

  function stateLine(f) {
    if (f.state === "ready") return `<p class="fmt-state" data-s="ready">Ready</p>`;
    if (f.state === "needs_webcam") {
      return `<p class="fmt-state" data-s="needs_webcam">Needs a webcam in the stream <span>- it hides the webcam picture, so a clip without one is made as a plain moment.</span></p>`;
    }
    return `<p class="fmt-state" data-s="unavailable">Not available yet: <span>${esc(f.reason || "Clipstorm cannot make this type yet.")}</span></p>`;
  }

  function shapeCard(f) {
    return `<article class="fmt-card" data-state="${esc(f.state)}" data-type="${esc(f.id)}">${diagram(f.id)}
      <div class="fmt-body"><h3 class="fmt-name">${esc(f.label)}</h3>
      <p class="fmt-line">${esc(f.line || sentence(f.hint))}</p>
      ${f.best ? `<p class="fmt-best"><b>Best for:</b> ${esc(f.best)}</p>` : ""}
      ${stateLine(f)}</div></article>`;
  }

  function paintShapes() {
    const box = document.getElementById("fmt_formats");
    if (!box) return;
    if (shapes === null) {
      box.innerHTML = `<p class="hint fmtp-hint">Loading clip types…</p>`;
      return;
    }
    if (!shapes.length) {
      const note = shapeWhy || "This Clipstorm answered with an empty list of clip types.";
      box.innerHTML = `<div class="fmt-empty">
        <p>The clip types could not be loaded.</p>
        <p>${esc(note)}</p>
        <p>You can still trim and style individual clips.</p>
      </div>`;
      return;
    }
    box.innerHTML = `<div class="fmt-grid">${shapes.map(shapeCard).join("")}</div>`;
  }

  /* ---- the look tiles --------------------------------------------------- */
  // Each frame is a real ffmpeg render on the server, so the grid spends them carefully: one perception check per
  // tile, four in flight, and one net under the observer for a tile that never announced itself.
  const SLOTS = 4;
  const waiting = [];
  let live = 0;
  let seen = null;
  let motionSeen = null;      // the observer for the moving previews, separate so each can be dropped alone

  function pump() {
    while (live < SLOTS && waiting.length) {
      const [img, src] = waiting.shift();
      if (!img.isConnected) continue;
      live++;
      let freed = false;
      const free = () => { if (freed) return; freed = true; live--; pump(); };
      img.addEventListener("load", free, { once: true });
      img.addEventListener("error", free, { once: true });
      setTimeout(free, 20000);            // a frame that never answers must not hold a slot for ever
      img.src = src;
    }
  }

  function want(img) {
    const src = img.getAttribute("data-src");
    if (!src) return;
    img.removeAttribute("data-src");      // asked once, whatever the observer says next
    waiting.push([img, src]);
    pump();
  }

  function onScreen(grid) {
    const imgs = Array.from(grid.querySelectorAll("img[data-src]"));
    if (!imgs.length) return;
    if (document.hidden || !("IntersectionObserver" in window)) { imgs.forEach(want); return; }
    if (!seen) {
      seen = new IntersectionObserver((rows) => {
        for (const row of rows) {
          if (!row.isIntersecting) continue;
          seen.unobserve(row.target);
          want(row.target);
        }
      }, { rootMargin: "350px 0px" });
    }
    imgs.forEach((i) => seen.observe(i));
    setTimeout(() => {
      for (const img of Array.from(grid.querySelectorAll("img[data-src]"))) {
        const b = img.getBoundingClientRect();
        if (b.bottom > -400 && b.top < (window.innerHeight || 800) + 400) want(img);
      }
    }, 900);      // was 8 seconds: where the observer is slow to speak, every tile sat empty for that long
  }

  /** One listener per grid: a frame that loads shows itself, a frame that fails keeps its label and says so. */
  function onFrame(e) {
    const img = e.target;
    if (!img || img.tagName !== "IMG") return;
    const tile = img.closest(".ftile");
    if (!tile) return;
    // The first picture asked for is the look drawn over a real game frame (web/looks, made by the real renderer).
    // A look with no such picture falls back, once, to the frame the server draws on a plain background.
    const alt = img.getAttribute("data-alt");
    if (e.type === "error" && alt) { img.removeAttribute("data-alt"); img.src = alt; return; }
    tile.dataset.st = e.type === "load" ? "ok" : "off";
  }

  function tileHtml(x) {
    const label = esc(x.label || x.name);
    // The caption under the frame says what the look DOES, because the name alone does not tell anyone that
    // "Typewriter" types or that "Neon pop" glows. `anim` comes from the catalogue; "house" means render.py
    // gives it its own motion.
    const kind = String(x.anim || "").trim();
    const what = kind === "house" ? "Fades and pops" : (kind ? kind.charAt(0).toUpperCase() + kind.slice(1) : "");
    // width and height are the real frame the server draws (1080x1920, shown at a ninth), so the grid never jumps.
    return `<figure class="ftile" data-st="wait" data-mv="wait" data-look="${esc(x.name)}">
      <span class="ftile-fr"><img alt="" width="270" height="480" decoding="async"
        data-src="/looks/${encodeURIComponent(x.name)}.jpg" data-alt="/api/style/preview?style=${encodeURIComponent(x.name)}"
        ><span class="moving">Still frame</span></span>
      <figcaption class="ftile-lb">${label}${what ? `<br><span class="ftile-do">${esc(what)}</span>` : ""}</figcaption>
      <div class="ftile-actions"><button class="btn sm" type="button" data-act="fmtplay">Play preview</button>
      <button class="btn sm" type="button" data-act="fmtuse" data-style="${esc(x.name)}" aria-pressed="false">Use as default</button></div>
    </figure>`;
  }

  /* ---- the moving previews -------------------------------------------------
   * A still cannot show a bounce bouncing. Each look also has a three-second clip (`/api/style/motion`), and this
   * loads it into the tile so the motion loops in place.
   *
   * Three rules, because each clip is one ffmpeg run on the server:
   *   1. Only a handful are in flight at once.
   *   2. Only tiles the person can actually see are asked for, so opening the page never draws every clip.
   *   3. A tile whose clip does not arrive keeps its still frame and says "Still frame" rather than pretending.
   */
  const motionWaiting = [];
  let motionLive = 0;
  const MOTION_SLOTS = 3;

  function pumpMotion() {
    while (motionLive < MOTION_SLOTS && motionWaiting.length) {
      const [tile, src] = motionWaiting.shift();
      if (!tile.isConnected) continue;
      motionLive++;
      let freed = false;
      const free = () => { if (freed) return; freed = true; motionLive--; pumpMotion(); };
      const vid = document.createElement("video");
      vid.muted = true;
      vid.loop = true;
      vid.autoplay = true;
      vid.playsInline = true;
      vid.setAttribute("muted", "");
      vid.setAttribute("playsinline", "");
      vid.setAttribute("aria-hidden", "true");
      vid.addEventListener("loadeddata", () => {
        const fr = tile.querySelector(".ftile-fr");
        if (fr) fr.appendChild(vid);
        tile.dataset.mv = "ready";
        // A tile whose still never loaded is still shown as working, because the moving frame is the better proof.
        if (tile.dataset.st !== "ok") tile.dataset.st = "ok";
        vid.play().then(() => { tile.dataset.mv = "on"; }).catch(() => {
          tile.dataset.mv = "ready";
          const badge = tile.querySelector(".moving");
          if (badge) badge.textContent = "Press Play preview";
        });
        free();
      }, { once: true });
      vid.addEventListener("error", () => { tile.dataset.mv = "off"; free(); }, { once: true });
      setTimeout(() => { if (!["on", "ready"].includes(tile.dataset.mv)) tile.dataset.mv = "off"; free(); }, 45000);
      vid.src = src;
      vid.load();
    }
  }

  function wantMotion(tile) {
    if (!tile || tile.dataset.mv !== "wait") return;
    const name = tile.getAttribute("data-look");
    if (!name) return;
    tile.dataset.mv = "asked";
    motionWaiting.push([tile, "/api/style/motion?style=" + encodeURIComponent(name)]);
    pumpMotion();
  }

  function motionOnScreen(grid) {
    const tiles = Array.from(grid.querySelectorAll('.ftile[data-mv="wait"]'));
    if (!tiles.length) return;
    // Somebody who asked the system to reduce motion should not get dozens of looping videos. They keep the still frames.
    let calm = false;
    try { calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { calm = false; }
    if (calm) return;
    if (document.hidden || !("IntersectionObserver" in window)) {
      // A hidden tab draws no animation anyway, and an observer never fires in one, so the visible ones are asked
      // for directly. The loop starts when the page is looked at.
      tiles.forEach(wantMotion);
      return;
    }
    if (!motionSeen) {
      motionSeen = new IntersectionObserver((rows) => {
        for (const row of rows) {
          if (!row.isIntersecting) continue;
          motionSeen.unobserve(row.target);
          wantMotion(row.target);
        }
      }, { rootMargin: "120px 0px" });
    }
    tiles.forEach((t) => motionSeen.observe(t));
  }

  function paintLooks() {
    const box = document.getElementById("fmt_looks");
    if (!box) return;
    if (looks === null) {
      box.innerHTML = `<p class="hint fmtp-hint">Reading the looks from this Clipstorm.</p>`;
      return;
    }
    if (!looks.length) {
      const note = lookWhy || "This Clipstorm answered with an empty list of looks.";
      box.innerHTML = `<div class="fmt-empty">
        <p>No looks were drawn, because the server sent none.</p>
        <p>${esc(note)}</p>
        <p>A clip still gets its captions. It uses the look saved on the Brand page.</p>
      </div>`;
      return;
    }
    box.innerHTML = `<div class="fmt-looks">${looks.map(tileHtml).join("")}</div>`;
    const grid = box.querySelector(".fmt-looks");
    if (!grid) return;
    grid.addEventListener("load", onFrame, true);
    grid.addEventListener("error", onFrame, true);
    // The markup was replaced, so every tile the old observer watched is gone. Drop it before watching the new grid.
    if (seen) { try { seen.disconnect(); } catch {} seen = null; }
    if (motionSeen) { try { motionSeen.disconnect(); } catch {} motionSeen = null; }
    onScreen(grid);                       // the observer needs the grid in the page first
    // The still frame is deliberately asked for FIRST: it is what the tile shows, and the moving preview replaces
    // it a moment later when it is ready. Asking for both at once would queue every ffmpeg preview for one glance.
    setTimeout(() => motionOnScreen(grid), 1200);
  }

  /* ---- the page --------------------------------------------------------- */
  P.add("formats", {
    about: "Preview caption animations and save a default for future clips.",
    act: {
      async fmtuse(button) {
        if (savingDefault) return;
        const style = button.dataset.style;
        if (!style || (looks && !looks.some(x => x.name === style))) return;
        savingDefault = true;
        button.disabled = true;
        const status = document.getElementById("fmt_status");
        try {
          const got = await P.api("/api/brand");
          if (!got || !got.brand) throw new Error("The current brand could not be read. Nothing was changed.");
          const saved = await P.send("/api/brand", {brand:{...got.brand, style}}, "PUT");
          if (P.state) { const st=P.state(); if (st) st.brand=saved.brand; }
          document.querySelectorAll('[data-act="fmtuse"]').forEach(b => {
            const chosen=b.dataset.style===style;
            b.setAttribute("aria-pressed",String(chosen)); b.textContent=chosen?"Default for new clips":"Use as default";
          });
          if (status) status.textContent="Saved. Future clips use this style; existing videos are unchanged.";
          P.toast("Default caption style saved.", "ok");
        } catch (err) {
          if (status) status.textContent=why(err,"The default was not saved");
          P.toast(why(err,"The default was not saved"),"bad");
        } finally { savingDefault=false; button.disabled=false; }
      },
      async fmtplay(button) {
        const tile=button.closest(".ftile");
        if (!tile) return;
        const video=tile.querySelector("video");
        if (video) {
          try { video.muted=true; await video.play(); tile.dataset.mv="on"; }
          catch { P.toast("The browser paused this preview. Keep the page visible and try again.","bad"); }
        } else { tile.dataset.mv="wait"; wantMotion(tile); }
      },
      /** Read both lists again. The frames already on screen keep their pixels; only the lists are fetched. */
      fmtreload() {
        return Promise.all([askShapes(true), askLooks(true)]).then(() => {
          const bad = !!shapeWhy || !!lookWhy;
          P.toast(bad ? (shapeWhy || lookWhy) : "Caption styles refreshed.", bad ? "bad" : "ok");
        });
      },
    },
  });

  P.page("formats", {
    nav: "Clip formats",
    icon: "film",
    tip: "Preview caption animations and choose a default for your clips",
    path: "formats",
    group: "Make",
    order: 19,
    view() {
      return `<div class="fmtp">
        <section class="fmtp-top"><div><h1 class="fmtp-h">Caption styles</h1>
          <p class="help">See how each style moves before choosing it.</p></div>
          <div class="row"><button class="btn" type="button" data-act="pcpage" data-v="brand">Customize text and colors</button>
            <button class="btn" type="button" data-act="fmtreload">Refresh styles</button></div></section>
        <p class="fmtp-meta" id="fmt_meta"></p><p class="fmtp-status" id="fmt_status" role="status"></p>
        <div id="fmt_looks"></div>
        <section class="fmtp-sec"><h2 class="fmtp-sub">Clip types</h2>
          <p class="fmtp-hint">A clip type is the shape of one Short. Each card shows how it is built, what viewers see
            and when to use it. A type marked "Not available yet" is not offered, because Clipstorm cannot make it
            properly today. New clips are plain Moments unless another type is chosen for them. To choose one,
            open a clip, go to <b>Look</b>, pick it under <b>Clip type</b>, then press Save and re-make clip.</p>
          <div id="fmt_formats"></div></section>
      </div>`;
    },
    load() {
      return Promise.all([askShapes(false), askLooks(false)]);
    },
  });
})();
