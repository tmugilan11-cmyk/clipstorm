/* Choose a caption look or a layout by looking at it, not by reading a name in a menu. This is the ONE caption picker.
 *
 * Every caption-look <select> in the page (the clip editor Look tab, the creator Setup tab and Settings > Brand) is
 * kept exactly where it is, because the page saves from it, and a picker is drawn after it:
 *   - Looks: a small search box and cards grouped under plain headings (Bold and loud, Karaoke and highlight, Boxes
 *     and pills, Neon and colour, Fun and meme, Clean and quiet). Each card is a real frame of that look from
 *     /looks/<name>.jpg (made by the real renderer, loaded lazily), its name, and a few plain words for how it moves.
 *     If a picture is missing the card shows the look's own font and colours instead, so it is never blank.
 *   - Layouts: small 9:16 sketches of where the video and the webcam sit.
 * Clicking a card writes the value into the select and fires the same `input` and `change` events the page already
 * listens to, so saving and the live preview work as before. The cards are a radio group: arrow keys move, Enter or
 * Space choose. The select stays in the page, hidden the screen-reader way, and is still the one value.
 *
 * Which selects are touched: select[data-caption-style], select#br_style, and select[data-k=layout] / [data-f=layout].
 * Each is also checked by its options: every option must be a look (or layout) this file knows, or it is left alone.
 * style-tiles.js used to draw a second grid for #br_style; it no longer draws one, so the page shows a single picker.
 *
 * The server does not send a look's colours or font, so the small table below copies the caption table in
 * studio/captions.py (font file, text, highlight, outline, box). The fonts are the ones the server already serves
 * for ffmpeg at /assets/font/<file>.ttf, loaded only when a card has to fall back to its font sample. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function" || typeof P.css !== "function") return;

  /* name: [font file, text colour, highlighted word, outline, box behind the words or ""] */
  const LOOKS = {
    bounce: ["Poppins-ExtraBold", "FFFFFF", "FFF000", "000000", ""],
    hype: ["Anton-Regular", "FFFFFF", "FF3C3C", "000000", ""],
    clean: ["Poppins-ExtraBold", "FFFFFF", "FFD76B", "000000", ""],
    classic: ["Montserrat-ExtraBold", "FFFFFF", "FFE500", "000000", ""],
    beast: ["Anton-Regular", "FFFFFF", "FFD400", "000000", ""],
    hormozi: ["Anton-Regular", "FFFFFF", "F7C204", "000000", ""],
    mozi: ["Anton-Regular", "FFFFFF", "FFFFFF", "000000", "16A34A"],
    karaoke: ["Poppins-Bold", "A3A3A3", "F7C204", "000000", ""],
    pill: ["Anton-Regular", "FFFFFF", "FFFFFF", "000000", "7C3AED"],
    lemon: ["Anton-Regular", "FFFFFF", "111111", "000000", "FACC15"],
    neon: ["Poppins-Bold", "FFFFFF", "22D3EE", "164E63", ""],
    ember: ["Anton-Regular", "FFF7ED", "FB923C", "431407", ""],
    bubble: ["Poppins-Bold", "FFFFFF", "FFFFFF", "000000", "2563EB"],
    retro: ["Anton-Regular", "FDE68A", "F472B6", "3B0764", ""],
    crimson: ["Poppins-Bold", "FFFFFF", "EF4444", "000000", ""],
    minimal: ["Poppins-Medium", "FFFFFF", "FFFFFF", "000000", ""],
    word: ["Anton-Regular", "FFFFFF", "FFE500", "000000", ""],
    pop: ["LilitaOne-Regular", "FFFFFF", "FFD60A", "000000", ""],
    typewriter: ["CourierPrime-Bold", "F8F8F2", "4ADE80", "000000", ""],
    slide: ["ArchivoBlack-Regular", "FFFFFF", "FF4D6D", "000000", ""],
    shake: ["Anton-Regular", "FFFFFF", "FF3B30", "000000", ""],
    sweep: ["BowlbyOne-Regular", "FFFFFF", "FFFFFF", "000000", "FF2E93"],
    twotone: ["ArchivoBlack-Regular", "FFF200", "FF3D00", "000000", ""],
    emoji: ["LilitaOne-Regular", "FFFFFF", "FFD60A", "000000", ""],
    lower: ["Poppins-Medium", "FFFFFF", "FFE500", "000000", ""],
    duo: ["Poppins-Bold", "9CA3AF", "FFFFFF", "000000", ""],
    meme: ["Anton-Regular", "FFFFFF", "FFFFFF", "000000", ""],
    glow: ["Righteous-Regular", "FFFFFF", "FF4FD8", "FF00C8", ""],
    comic: ["Bangers-Regular", "FFE600", "FFFFFF", "000000", ""],
    whisper: ["Poppins-Medium", "FFFFFF", "FFFFFF", "000000", ""],
    punch: ["BowlbyOne-Regular", "FFFFFF", "FFE500", "000000", ""],
    tiktok: ["Poppins-Bold", "FFFFFF", "FFFFFF", "000000", ""],
    drop: ["Montserrat-ExtraBold", "FFFFFF", "A78BFA", "000000", ""],
    hollow: ["BebasNeue-Regular", "FFFFFF", "FFE500", "000000", ""],
    stamp: ["ArchivoBlack-Regular", "FFFFFF", "FFFFFF", "000000", "E11D48"],
    "hormozi-pro": ["Montserrat-ExtraBold", "FFFFFF", "F7C204", "000000", ""],
    "red-alert": ["Anton-Regular", "FFFFFF", "FF3B30", "000000", ""],
    "butter-cozy": ["Poppins-Bold", "F5D76E", "FFFFFF", "000000", ""],
    "pill-dark": ["Poppins-Bold", "FFFFFF", "1A1A1A", "000000", "FFFFFF"],
    "cream-ink": ["Poppins-Medium", "FFF3E6", "111827", "1F1A17", "FFF3E6"],
    "neon-pop": ["Righteous-Regular", "FF2E88", "00D2FF", "101018", ""],
    brainrot: ["Anton-Regular", "FFFFFF", "02FB23", "000000", ""],
    "lowercase-hook": ["Poppins-Medium", "FFFFFF", "FFE066", "000000", ""],
    "duo-speaker": ["Poppins-Bold", "FFFFFF", "F5D76E", "000000", ""],
    "title-slide": ["ArchivoBlack-Regular", "FFFFFF", "FFFFFF", "000000", ""],
  };
  const SMALL_LETTERS = new Set(["clean", "lowercase-hook", "whisper", "minimal"]);

  /* Plain headings. A look appears under exactly one; a look this table does not know goes under "More looks". */
  const GROUPS = [
    ["Bold and loud", ["classic", "beast", "hormozi", "hormozi-pro", "red-alert", "ember", "crimson", "shake", "punch", "word", "brainrot", "bounce", "hype"]],
    ["Karaoke and highlight", ["karaoke", "mozi", "twotone", "sweep", "duo", "duo-speaker", "hollow"]],
    ["Boxes and pills", ["pill", "lemon", "bubble", "pill-dark", "cream-ink", "stamp", "lower", "butter-cozy", "lowercase-hook"]],
    ["Neon and colour", ["neon", "neon-pop", "glow", "retro"]],
    ["Fun and meme", ["meme", "comic", "pop", "emoji", "drop", "typewriter", "slide", "title-slide"]],
    ["Clean and quiet", ["minimal", "whisper", "tiktok", "clean"]],
  ];
  /* A few plain words for how each look moves. */
  const TAGS = {
    classic: "highlights each word", beast: "highlights each word", hormozi: "highlights each word", mozi: "green box on the word",
    karaoke: "lights up as said", pill: "pill on the word", lemon: "yellow box on the word", neon: "highlights each word",
    ember: "highlights each word", bubble: "blue bubble on the word", retro: "highlights each word", crimson: "highlights each word",
    minimal: "highlights each word", word: "one word at a time", pop: "pops in", typewriter: "types out", slide: "slides up",
    shake: "shakes", sweep: "colour bar sweeps", twotone: "two colours", emoji: "adds emoji", lower: "subtitle box",
    duo: "fills in, two lines", meme: "top and bottom", glow: "glows", comic: "pops, tilted", whisper: "soft and faint",
    punch: "one word, punches in", tiktok: "whole line", drop: "drops in", hollow: "outline fills in", stamp: "stamps in",
    "hormozi-pro": "punches in", "red-alert": "punches in", "butter-cozy": "subtitle box", "pill-dark": "chip on the word",
    "cream-ink": "chip on the word", "neon-pop": "glows", brainrot: "one word, shakes", "lowercase-hook": "subtitle box",
    "duo-speaker": "fills in, two lines", "title-slide": "slides up", bounce: "pops in", hype: "highlights each word", clean: "highlights each word",
  };
  const groupOf = (n) => { for (const g of GROUPS) if (g[1].includes(n)) return g[0]; return "More looks"; };

  const LAYOUTS = {
    blur: "Blurred fill",
    zoom: "Zoomed in",
    crop: "Fill screen",
    gameplay: "Gameplay + facecam",
    stack: "Streamer top, game below",
  };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const hex = (h, fallback) => (/^[0-9A-Fa-f]{6}$/.test(String(h || "")) ? "#" + h : fallback);
  const CONT = ".lp-grid, .lp-looks";

  P.css("look-picker", `
    html body select.lp-hide{position:absolute!important;width:1px!important;height:1px!important;min-height:0!important;margin:-1px!important;
      padding:0!important;border:0!important;overflow:hidden!important;clip:rect(0 0 0 0)!important;white-space:nowrap!important;opacity:0!important}
    .lp-host{position:relative;grid-column:1/-1}
    .lp-grid{grid-column:1/-1;display:grid;gap:10px;margin:0}
    .lp-grid.layouts{grid-template-columns:repeat(auto-fill,minmax(104px,1fr))}
    .lp-looks{grid-column:1/-1;display:block;margin:0}
    .lp-search{display:block;width:100%;max-width:320px;margin:0 0 12px;box-sizing:border-box}
    .lp-sec{margin:0 0 14px}
    .lp-sec[hidden],.lp-card[hidden],.lp-none[hidden]{display:none}
    .lp-h{margin:0 0 8px;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--faint,#A0948C)}
    .lp-row{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(168px,1fr))}
    .lp-none{margin:0;font-size:13px;color:var(--dim)}
    .lp-card{position:relative;display:flex;flex-direction:column;gap:8px;padding:10px;min-width:0;cursor:pointer;text-align:left;
      color:var(--dim);background:var(--field,#141414);border:2px solid var(--sk-edge,#666666);border-radius:var(--r,12px);
      transition:border-color .14s ease,background-color .14s ease,color .14s ease}
    .lp-card:hover{border-color:var(--sk-edge-hi,#8A8A8A);background:var(--muted)}
    .lp-card[aria-checked="true"]{border-color:var(--brand);background:var(--brand-soft);color:var(--text)}
    .lp-card:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
    .lp-grid[aria-disabled="true"],.lp-looks[aria-disabled="true"]{opacity:.5}
    .lp-grid[aria-disabled="true"] .lp-card,.lp-looks[aria-disabled="true"] .lp-card{cursor:not-allowed;pointer-events:none}
    .lp-name{display:block;font-size:13px;font-weight:600;line-height:1.25;overflow-wrap:anywhere}
    .lp-card.look{padding:0;overflow:hidden;gap:0}
    .lp-pic{position:relative;display:block;aspect-ratio:9/5;overflow:hidden;background:linear-gradient(150deg,#2B3350,#161A2B 60%,#3A2438)}
    .lp-pic .lp-stage{position:absolute;inset:0;height:auto;border-radius:0}
    .lp-pic img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;background:#161A2B}
    .lp-meta{display:block;padding:7px 9px 9px;min-width:0}
    .lp-tag{display:block;margin-top:2px;font-size:11.5px;line-height:1.25;color:var(--dim)}
    /* The check is dark ink on the orange disc: --brand-ink on --brand measures 8.22:1; white on it is 2.34:1. */
    .lp-check{position:absolute;top:6px;right:6px;display:none;place-items:center;width:20px;height:20px;border-radius:50%;
      background:var(--brand);color:var(--brand-ink);z-index:2}
    .lp-card[aria-checked="true"] .lp-check{display:grid}
    .lp-check svg{width:12px;height:12px;fill:none;stroke:currentColor;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}
    /* A caption sample: a dark, game-like frame so white letters and their outlines read as they will on a clip. */
    .lp-stage{display:grid;place-items:center;height:72px;overflow:hidden;border-radius:var(--r-sm);background:linear-gradient(150deg,#2B3350,#161A2B 60%,#3A2438)}
    .lp-words{display:block;text-align:center;font-size:17px;line-height:1.15;padding:0 6px;-webkit-text-stroke:3px var(--lp-o);paint-order:stroke fill}
    .lp-words i{font-style:normal;display:block}
    .lp-words.boxed i{display:inline-block;padding:2px 6px;border-radius:5px;margin:1px 0}
    /* A layout sample: a 9:16 phone frame drawn with plain boxes. */
    .lp-phone{position:relative;width:48px;height:86px;margin:0 auto;overflow:hidden;border-radius:7px;background:#161A2B;border:1px solid var(--sk-edge,#666666)}
    .lp-phone .bg{position:absolute;inset:-6px;background:linear-gradient(160deg,#6B7FB8,#2B3350 70%,#7A3E5E);filter:blur(3px);opacity:.85}
    .lp-phone .game{position:absolute;left:0;right:0;background:linear-gradient(135deg,#4F86C6,#27437A 60%,#3E8E7E)}
    .lp-phone .cam{position:absolute;display:grid;place-items:center;background:var(--brand-soft);border:1px solid var(--brand)}
    .lp-phone .cam::after{content:"";width:35%;aspect-ratio:1;border-radius:50%;background:var(--brand-deep)}
    .lp-phone.blur .game{top:34%;height:32%}
    .lp-phone.zoom .game{top:26%;height:48%;left:-8px;right:-8px}
    .lp-phone.crop .game{top:0;bottom:0}
    .lp-phone.gameplay .game{top:0;bottom:0}
    .lp-phone.gameplay .cam{right:4px;bottom:6px;width:17px;height:17px;border-radius:5px}
    .lp-phone.stack .cam{top:0;left:0;right:0;height:40%;border-width:0 0 1px 0}
    .lp-phone.stack .cam::after{width:26%}
    .lp-phone.stack .game{top:40%;bottom:0}
    .lp-live{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
    @media (max-width:700px){
      .lp-grid.layouts{grid-template-columns:repeat(3,minmax(0,1fr))}
      .lp-row{grid-template-columns:repeat(2,minmax(0,1fr))}
      .lp-card{min-height:44px}
    }
    @media (prefers-reduced-motion:reduce){.lp-card{transition:none}}
  `);

  /* ---- fonts: each file is fetched once, only when a card has to draw its own sample ------------------------- */
  const faces = new Set();
  function loadFace(stem) {
    if (faces.has(stem) || !/^[\w-]{1,60}$/.test(stem) || !document.fonts || typeof FontFace !== "function") return;
    faces.add(stem);
    try {
      const face = new FontFace("pk " + stem, `url("/assets/font/${stem}.ttf")`);
      face.load().then((f) => document.fonts.add(f)).catch(() => faces.delete(stem));
    } catch { faces.delete(stem); }
  }

  /* ---- what a card looks like --------------------------------------------------------------------------------- */
  const CHECK = `<span class="lp-check" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12.5 10 17.5 19 7"/></svg></span>`;

  function lookCard(name, label, on, tab) {
    const row = LOOKS[name];
    let style = "--lp-o:#000000;color:#FFFFFF", boxed = "", second = "color:#AF9BFF", t = ["YOUR", "CAPTION"];
    if (row) {
      const base = hex(row[1], "#FFFFFF"), hl = hex(row[2], "#AF9BFF"), out = hex(row[3], "#000000"), box = row[4] ? hex(row[4], "") : "";
      style = `font-family:'pk ${row[0]}',system-ui,sans-serif;--lp-o:${out};color:${base}`;
      second = box ? `background:${box};color:${base}` : `color:${hl}`;
      boxed = box ? " boxed" : "";
      if (SMALL_LETTERS.has(name)) t = ["your", "caption"];
    }
    const safe = /^[\w-]{1,40}$/.test(name) ? name : "";
    const pic = safe ? `<img src="/looks/${esc(safe)}.jpg" alt="" width="360" height="200" loading="lazy" decoding="async" data-face="${esc(row ? row[0] : "")}">` : "";
    const tag = TAGS[name] || "";
    return `<div class="lp-card look" role="radio" tabindex="${tab}" aria-checked="${on}" data-v="${esc(name)}" data-s="${esc((label + " " + tag + " " + groupOf(name)).toLowerCase())}" title="${esc(label)}">
      ${CHECK}<span class="lp-pic"><span class="lp-stage" aria-hidden="true"><span class="lp-words${boxed}" style="${style}"><i>${t[0]}</i><i style="${second}">${t[1]}</i></span></span>${pic}</span>
      <span class="lp-meta"><span class="lp-name">${esc(label)}</span>${tag ? `<span class="lp-tag">${esc(tag)}</span>` : ""}</span></div>`;
  }

  function layoutCard(name, label, full, on, tab) {
    return `<div class="lp-card" role="radio" tabindex="${tab}" aria-checked="${on}" data-v="${esc(name)}" title="${esc(full)}">
      ${CHECK}<span class="lp-phone ${esc(name)}" aria-hidden="true"><span class="bg"></span><span class="game"></span><span class="cam"></span></span>
      <span class="lp-name">${esc(label)}</span></div>`;
  }

  /* ---- recognising a select with certainty -------------------------------------------------------------------- */
  function kindOf(sel) {
    if (!sel || sel.tagName !== "SELECT" || sel.multiple) return "";
    const vals = Array.from(sel.options).map((o) => o.value).filter(Boolean);
    if (!vals.length) return "";
    if (sel.hasAttribute("data-caption-style") || sel.id === "br_style") {
      // Every option must be a look this build knows by name, or the list is something else wearing the attribute.
      const known = (window.PeakCut.state && window.PeakCut.state() && window.PeakCut.state().status && window.PeakCut.state().status.styles) || {};
      return vals.every((v) => Object.prototype.hasOwnProperty.call(LOOKS, v) || Object.prototype.hasOwnProperty.call(known, v)) ? "look" : "";
    }
    if (sel.dataset.k === "layout" || sel.dataset.f === "layout") {
      return vals.every((v) => Object.prototype.hasOwnProperty.call(LAYOUTS, v)) ? "layout" : "";
    }
    return "";
  }

  /* ---- building and keeping the grid in step ------------------------------------------------------------------ */
  function groupName(host) {
    const t = Array.from(host.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join(" ").trim();
    return t || "Choose one";
  }

  function build(sel, kind, host) {
    const opts = Array.from(sel.options).filter((o) => o.value);
    const key = kind + ":" + opts.map((o) => o.value).join(",");
    const cur = sel.value;
    const first = opts.find((o) => o.value === cur) || opts[0];
    const card = (o) => {
      const on = o.value === cur;
      const tab = first && o.value === first.value ? 0 : -1;
      const label = (o.textContent || "").trim() || o.value;
      return kind === "look" ? lookCard(o.value, label, on, tab) : layoutCard(o.value, LAYOUTS[o.value] || label, label, on, tab);
    };
    const box = document.createElement("div");
    box.dataset.key = key;
    const label = groupName(host);
    if (kind !== "look") {
      box.className = "lp-grid layouts";
      box.setAttribute("role", "radiogroup");
      box.setAttribute("aria-label", label);
      box.innerHTML = opts.map(card).join("") + `<p class="lp-live" role="status"></p>`;
      return box;
    }
    box.className = "lp-looks";
    const heads = GROUPS.map((g) => g[0]).concat(["More looks"]);
    const secs = heads.map((h) => {
      const mine = opts.filter((o) => groupOf(o.value) === h);
      return mine.length ? `<div class="lp-sec" role="radiogroup" aria-label="${esc(label + ", " + h)}"><h4 class="lp-h">${esc(h)}</h4><div class="lp-row">${mine.map(card).join("")}</div></div>` : "";
    }).join("");
    box.innerHTML = `<input type="search" class="lp-search" placeholder="Search looks" aria-label="Search ${esc(label)}" autocomplete="off">` + secs +
      `<p class="lp-none" hidden>No look matches that.</p><p class="lp-live" role="status"></p>`;
    return box;
  }

  /* The search box hides cards (and headings with nothing left) without removing them, so the choice never changes. */
  function filter(box, q) {
    const words = String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const sec of Array.from(box.querySelectorAll(".lp-sec"))) {
      let any = 0;
      for (const c of Array.from(sec.querySelectorAll(".lp-card"))) {
        const hit = words.every((w) => (c.dataset.s || "").includes(w));
        c.hidden = !hit;
        if (hit) any++;
      }
      sec.hidden = !any;
      shown += any;
    }
    const none = box.querySelector(".lp-none");
    if (none) none.hidden = shown > 0;
    const live = box.querySelector(".lp-live");
    if (live) live.textContent = words.length ? shown + (shown === 1 ? " look" : " looks") + " shown." : "";
    const sel = selectFor(box);
    if (sel) sync(sel, box);
  }

  function sync(sel, grid) {
    const cur = sel.value;
    const off = !!sel.disabled;
    if (grid.getAttribute("aria-disabled") !== String(off)) grid.setAttribute("aria-disabled", String(off));
    let rover = null;
    const cards = Array.from(grid.querySelectorAll(".lp-card"));
    for (const c of cards) {
      const on = c.dataset.v === cur;
      if (c.getAttribute("aria-checked") !== String(on)) c.setAttribute("aria-checked", String(on));
      if (on && !c.hidden) rover = c;
    }
    if (!rover) rover = cards.find((c) => !c.hidden) || cards[0];
    for (const c of cards) {
      const t = c === rover ? "0" : "-1";
      if (c.getAttribute("tabindex") !== t) c.setAttribute("tabindex", t);
    }
  }

  function enhance(sel) {
    const kind = kindOf(sel);
    if (!kind) return;
    const host = sel.closest("label");
    if (!host || !host.parentElement) return;                   // the picker goes after the label, never inside it
    const next = host.nextElementSibling;
    if (sel.dataset.lp === "1" && next && next.matches(CONT)) {
      const opts = Array.from(sel.options).filter((o) => o.value);
      if (next.dataset.key === kind + ":" + opts.map((o) => o.value).join(",")) { sync(sel, next); return; }
      next.remove();                                            // the options changed: draw again
    }
    const grid = build(sel, kind, host);
    host.classList.add("lp-host");
    sel.classList.add("lp-hide");
    sel.dataset.lp = "1";
    host.after(grid);
    sync(sel, grid);
    if (!sel.dataset.lpOn) {
      sel.dataset.lpOn = "1";
      sel.addEventListener("change", () => {
        const g = sel.closest("label") && sel.closest("label").nextElementSibling;
        if (g && g.matches(CONT)) sync(sel, g);
      });
    }
  }

  function selectFor(grid) {
    const host = grid.previousElementSibling;
    return host && host.querySelector ? host.querySelector("select.lp-hide") : null;
  }

  function choose(card) {
    const grid = card.closest(CONT);
    const sel = grid && selectFor(grid);
    if (!sel || sel.disabled) return;
    const v = card.dataset.v;
    if (!v || !Array.from(sel.options).some((o) => o.value === v)) return;
    if (sel.value !== v) {
      sel.value = v;
      sel.dispatchEvent(new Event("input", { bubbles: true }));
      sel.dispatchEvent(new Event("change", { bubbles: true }));
    }
    sync(sel, grid);
    const live = grid.querySelector(".lp-live");
    const name = card.querySelector(".lp-name");
    if (live) live.textContent = (name ? name.textContent : v) + " chosen.";
  }

  /* One click handler and one key handler for every picker on the page. */
  document.addEventListener("click", (e) => {
    const card = e.target && e.target.closest && e.target.closest(".lp-card");
    if (card) choose(card);
  });
  document.addEventListener("keydown", (e) => {
    const card = e.target && e.target.closest && e.target.closest(".lp-card");
    if (!card) return;
    const grid = card.closest(CONT);
    if (!grid) return;
    const cards = Array.from(grid.querySelectorAll(".lp-card:not([hidden])"));
    const at = cards.indexOf(card);
    let to = -1;
    if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") { e.preventDefault(); choose(card); return; }
    if (e.key === "ArrowRight" || e.key === "ArrowDown") to = (at + 1) % cards.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") to = (at - 1 + cards.length) % cards.length;
    else if (e.key === "Home") to = 0;
    else if (e.key === "End") to = cards.length - 1;
    if (to < 0) return;
    e.preventDefault();
    for (const c of cards) c.setAttribute("tabindex", c === cards[to] ? "0" : "-1");
    cards[to].focus();
  });

  /* A picture that is not there (or a server that does not serve /looks) leaves the card's own font sample showing,
   * and only then is that look's font fetched. `error` does not bubble, so it is caught on the way down. */
  document.addEventListener("error", (e) => {
    const img = e.target;
    if (!img || img.tagName !== "IMG" || !img.closest || !img.closest(".lp-pic")) return;
    loadFace(img.dataset.face || "");
    img.remove();
  }, true);
  document.addEventListener("input", (e) => {
    const t = e.target;
    if (!t || !t.classList || !t.classList.contains("lp-search")) return;
    const box = t.closest(".lp-looks");
    if (box) filter(box, t.value);
  });

  function scan(root) {
    try {
      const top = root && root.querySelectorAll ? root : document;
      for (const sel of Array.from(top.querySelectorAll("select[data-caption-style], select#br_style, select[data-k=layout]"))) enhance(sel);
    } catch { /* a picker that cannot draw leaves the plain select, which still works */ }
  }

  // The page redraws the editor and the creator form whenever a job changes, which replaces the selects, so the
  // pickers are put back after each redraw. A mutation watcher plus the plug-in hooks below cover every path.
  let queued = false;
  function later() {
    if (queued) return;
    queued = true;
    setTimeout(() => { queued = false; scan(document); }, 40);   // a timer, not a frame: a background tab runs no frames
  }
  try {
    new MutationObserver((rows) => {
      for (const r of rows) {
        if (r.target && r.target.closest && r.target.closest(CONT)) continue;   // our own drawing
        later();
        return;
      }
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["disabled"] });
  } catch { /* the hooks below still run */ }

  P.add("look-picker", {
    after: {
      drawClipDlg(el) { scan(el); },
      drawCreator(el) { scan(el); },
      drawOverview(el) { scan(el); },
      drawSettings(el) { scan(el); },
    },
  });
  scan(document);
})();
