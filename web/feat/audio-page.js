/* Audio: the music Clipstorm puts under a clip, and how loud it is, plus your marked sounds.
 *
 * MUSIC comes first: the four music beds (`studio/music.py`), whether each is built, a Listen button, and the facts about
 * how loud a bed is (read from music.py; they are fixed in code, so this page shows them and does not pretend to change
 * them). Beds are read from GET /api/moods, played from GET /api/sounds/music/<name>, built with POST /api/moods/prime.
 *
 * The sound LIBRARY is not here. Finding new sounds (searching the web catalogue, trending, kinds of sound, listening before you keep) used to be
 * done here AND on the Sounds page, which left a beginner with two libraries that looked alike. That is now done in
 * ONE place, Sounds, and this page says so at the top and has a button to it. What stays here is what Sounds does
 * not do:
 *   * Like and Bookmark: marks you make for yourself, remembered in this browser only (no account holds them)
 *   * Download: save a kept sound's file to your own folders
 *   * a picture of each sound's loudness, drawn from the real file
 *   * the shelves Saved, Liked, Bookmarked and Uploaded by me, with a name filter and a length filter
 *
 * This page is a LIBRARY, not an editor. Placing a sound on a clip happens in the clip's sound editor
 * (`web/feat/audio-edit.js`). Every Listen button here is the shared player from `web/feat/meme-timeline.js`, so
 * pressing one stops a sound playing anywhere else.
 *
 * Routes (all in `studio/api_memesound.py`):
 *   GET    /api/memesounds/library          what is kept on this machine
 *   DELETE /api/memesounds/library/<slug>   remove one
 *   GET    /api/memesounds/play/<slug>      the bytes, for Listen, the loudness picture and Download
 * Searching the catalogue (/api/memesounds/search and /api/memesounds/for), trending and keeping a new sound
 * (/api/memesounds/keep) now live on the Sounds page. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.page !== "function" || typeof P.add !== "function") return;

  const NAME = "audio-page";

  P.css(NAME, `
    #main>.content:has(.alb-page){max-width:none;padding-left:22px;padding-right:22px}
    .alb-page{display:grid;gap:14px}

    .alb-head{display:flex;align-items:flex-end;gap:14px;flex-wrap:wrap}
    .alb-head .ttl{display:grid;gap:3px}
    .alb-h{margin:0;font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--text)}
    .alb-sub{margin:0;font-size:13px;color:var(--dim);line-height:1.5;max-width:70ch}
    .alb-head .sp{margin-left:auto}
    .alb-count{font-size:12px;color:var(--faint);font-variant-numeric:tabular-nums}

    .alb-beds{display:grid;gap:10px}
    .alb-bed{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:11px 14px;border:1px solid var(--line);border-radius:var(--r);background:var(--card)}
    .alb-bed b{flex:0 0 90px;color:var(--text);font-size:14px}
    .alb-bed span.line{flex:1 1 220px;min-width:0;font-size:13px;line-height:1.45;color:var(--dim)}
    .alb-sec{display:grid;gap:8px}
    .alb-sec h2{margin:0 0 4px;font-size:17px;color:var(--text)}
    .alb-facts{margin:0;padding-left:20px;font-size:13px;line-height:1.6;color:var(--dim)}
    details.alb-more{border:1px solid var(--line);border-radius:var(--r);padding:0 14px}
    details.alb-more>summary{cursor:pointer;padding:12px 0;font-weight:600;color:var(--text);font-size:14px}
    details.alb-more>summary:hover{color:var(--brand-deep)}
    details.alb-more[open]>summary{border-bottom:1px solid var(--line);margin-bottom:14px}
    details.alb-more>.alb-inner{display:grid;gap:14px;padding-bottom:14px}
    /* the card that points to Sounds */
    .alb-goto{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:14px 16px;border:1px solid var(--brand-line);
      border-radius:var(--r);background:var(--brand-soft)}
    .alb-goto div{flex:1 1 320px;min-width:0}
    .alb-goto b{display:block;font-size:14px;color:var(--text);margin-bottom:2px}
    .alb-goto p{margin:0;font-size:13px;line-height:1.5;color:var(--dim)}

    /* the shelf bar: one coloured pill per shelf. White text was measured on each base colour:
       5.02:1 at the dimmest (Saved), well over the 4.5 the small size needs. */
    .alb-bar{display:flex;gap:6px;flex-wrap:wrap;padding:7px;border:1px solid var(--line);
      border-radius:14px;background:var(--card)}
    .alb-cat{border:1px solid transparent;border-radius:999px;padding:7px 14px;font:inherit;font-size:12px;
      font-weight:700;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;color:#fff;
      background:var(--c,#5B4C40);transition:border-color .16s ease}
    .alb-cat:disabled{cursor:default}
    .alb-cat:hover{border-color:rgba(255,255,255,.6)}
    .alb-cat[aria-pressed="true"]{border-color:#fff}
    .alb-cat:focus-visible{outline:2px solid #fff;outline-offset:2px}

    .alb-body{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:24px;align-items:start}
    .alb-results{min-width:0;display:grid;gap:16px}
    .alb-sidebar{position:sticky;top:80px;padding:18px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
    .alb-sidebar h2{font-size:14px;margin:0 0 14px}
    .alb-tools{display:grid;gap:16px;align-items:stretch}
    .alb-sidebar .alb-tools input[type=search],.alb-sidebar .alb-tools select{width:100%;min-width:0}
    .alb-sidebar .alb-tools .sp{display:none}
    @media(max-width:900px){.alb-body{grid-template-columns:minmax(0,1fr) 220px;gap:14px}}
    @media(max-width:640px){.alb-body{display:flex;flex-direction:column}.alb-sidebar{position:static;order:-1;width:100%;box-sizing:border-box}.alb-tools{grid-template-columns:1fr 1fr}.alb-tab{grid-column:1/-1}
      .alb-mini{min-height:44px}.alb-tab button{min-height:44px}}
    .alb-tools label{display:grid;gap:3px;font-size:12px;color:var(--dim)}
    .alb-tools small{font-size:11px;color:var(--faint);line-height:1.4}
    .alb-tools input[type=search]{height:34px;padding:0 10px;border:1px solid var(--line-2);
      border-radius:var(--r-sm);background:var(--field);color:var(--text);font:inherit;font-size:13px}
    .alb-tools select{height:34px;padding:0 9px;border:1px solid var(--line-2);border-radius:var(--r-sm);
      background:var(--field);color:var(--text);font:inherit;font-size:13px}
    .alb-tab{display:inline-flex;gap:2px;padding:3px;border:1px solid var(--line);border-radius:10px;background:var(--muted)}
    .alb-tab button{border:0;background:none;color:var(--dim);font:inherit;font-size:12px;font-weight:600;
      padding:5px 11px;border-radius:7px;cursor:pointer;transition:color .15s ease,background-color .15s ease}
    .alb-tab button:hover{color:var(--text)}
    .alb-tab button[aria-pressed="true"]{background:var(--bg);color:var(--text)}

    .alb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));gap:10px}
    .alb-card{display:grid;gap:8px;padding:11px 12px 10px;border:1px solid var(--line);
      border-radius:var(--r);background:var(--card);min-width:0}
    .alb-card:hover{border-color:var(--line-2)}
    .alb-card.playing{border-color:var(--brand)}
    .alb-card .top{display:flex;align-items:center;gap:10px;min-width:0}
    .alb-card .nm{min-width:0;display:grid;gap:2px}
    .alb-card .nm b{font-size:13px;font-weight:600;line-height:1.3;color:var(--text);overflow:hidden;
      display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow-wrap:anywhere}
    .alb-card .nm small{font-size:12px;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .alb-wave{display:block;width:100%;height:30px;border-radius:6px;background:#0C0C0C;
      border:1px solid var(--line);overflow:hidden}
    .alb-row{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
    .alb-row .sp{margin-left:auto}
    .alb-mini{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line-2);
      background:var(--bg);color:var(--dim);border-radius:7px;padding:4px 9px;font:inherit;font-size:12px;
      cursor:pointer;transition:border-color .15s ease,color .15s ease;text-decoration:none}
    .alb-mini:hover{border-color:var(--brand);color:var(--brand-deep)}
    .alb-mini[aria-pressed="true"]{border-color:var(--brand);color:var(--brand-deep);background:var(--brand-soft)}
    .alb-mini svg{width:13px;height:13px}
    .alb-note{margin:0;font-size:12px;line-height:1.5;color:var(--dim)}
    .alb-empty{padding:26px 18px;border:1px dashed var(--line-2);border-radius:var(--r);text-align:center;
      color:var(--dim);font-size:13px;line-height:1.6}
    .alb-empty .btn{margin-top:10px}
    .alb-hit{display:flex;align-items:center;gap:10px;padding:7px 10px;border:1px solid var(--line);
      border-radius:8px;background:var(--card);min-width:0}
    .alb-hit .nm{min-width:0;flex:1;font-size:13px;color:var(--text);overflow:hidden;text-overflow:ellipsis;
      white-space:nowrap}
    .alb-hit .nm small{color:var(--dim);margin-left:6px}
  `);

  /* ---- helpers ------------------------------------------------------------------------------------- */
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
  const $ = (id) => document.getElementById(id);
  /* A number only when the server gave one. "0.0s" is a claim that a sound is empty, so a sound with no known
     length shows no length at all. */
  const known = (n) => n !== null && n !== undefined && n !== "" && isFinite(Number(n)) && Number(n) > 0;
  const secs1 = (n) => (known(n) ? (Math.round(Number(n) * 10) / 10).toFixed(1) + "s" : "");
  const sentence = (e, fallback) => ((e && e.message) ? String(e.message) : "") || fallback;
  const snd = () => P.snd || null;

  function read(path, opt) {
    if (typeof P.api === "function") return P.api(path, opt);
    return Promise.reject(new Error("Clipstorm is still starting. Try again in a moment."));
  }
  function say(text, kind) {
    if (!text) return;
    if (typeof P.toast === "function") { P.toast(text, kind === "bad" ? "bad" : "ok"); return; }
    const box = $("alb_note");
    if (box) { box.textContent = text; box.className = "alb-note" + (kind ? " " + kind : ""); }
  }

  /* ---- what the page remembers --------------------------------------------------------------------- */
  const B = {
    board: "kept", rows: [], note: "", err: "", busy: false,
    likes: {}, marks: {},          // kept in this browser: this build has no account for a like
    q: "", max: 0, view: "grid",
  };

  // One coloured pill per shelf. Every shelf is a view of what is kept on this machine.
  const BOARDS = [
    { k: "kept", label: "Saved", c: "#B45309" },
    { k: "liked", label: "Liked", c: "#9D174D" },
    { k: "bookmarked", label: "Bookmarked", c: "#1D4ED8" },
    { k: "mine", label: "Uploaded by me", c: "#8A5A2B" },
  ];

  const likeKey = "peakcut.audio.taste";
  function taste() {
    try {
      const raw = window.localStorage.getItem(likeKey);
      const got = raw ? JSON.parse(raw) : null;
      if (got && typeof got === "object") {
        B.likes = got.likes && typeof got.likes === "object" ? got.likes : {};
        B.marks = got.marks && typeof got.marks === "object" ? got.marks : {};
      }
    } catch (e) { /* a browser with storage turned off simply forgets */ }
  }
  function savetaste() {
    try {
      window.localStorage.setItem(likeKey, JSON.stringify({ likes: B.likes, marks: B.marks }));
    } catch (e) { /* nothing here is worth failing a page over */ }
  }

  /* ---- the bars ------------------------------------------------------------------------------------ */
  function barHtml() {
    return '<div class="alb-bar" role="group" aria-label="Shelves">'
      + BOARDS.map((b) => '<button class="alb-cat" type="button" data-act="alb-cat" data-b="' + esc(b.k)
        + '" style="--c:' + esc(b.c) + '" aria-pressed="' + (b.k === B.board ? "true" : "false") + '"'
        + (B.busy ? " disabled" : "") + ">" + esc(b.label) + "</button>").join("")
      + "</div>";
  }

  function toolsHtml() {
    // "Find" is pinned by tests/test_text_ink.py (the label was once "Shortest" and disagreed with the box), so the
    // word stays and the hint says what it really does: it narrows the sounds shown, it does not search the web.
    return '<div class="alb-tools">'
      + '<label>Find<input type="search" id="alb_q" placeholder="Type part of a name" '
      + 'autocomplete="off" value="' + esc(B.q) + '"><small>narrows the sounds shown here</small></label>'
      + '<label>How long<select id="alb_max" aria-label="How long">'
      + [["0", "Any length"], ["2", "Under 2s"], ["5", "Under 5s"], ["10", "Under 10s"]]
        .map(([v, t]) => '<option value="' + v + '"' + (String(B.max) === v ? " selected" : "") + ">" + t + "</option>").join("")
      + '</select><small>sounds with no known length still show</small></label>'
      + '<span class="sp"></span>'
      + '<div class="alb-tab" role="group" aria-label="How to show them">'
      + '<button type="button" data-act="alb-view" data-v="grid" aria-pressed="' + (B.view === "grid" ? "true" : "false") + '">Cards</button>'
      + '<button type="button" data-act="alb-view" data-v="list" aria-pressed="' + (B.view === "list" ? "true" : "false") + '">List</button>'
      + "</div>"
      + "</div>";
  }

  function pageHtml() {
    return '<div class="alb-page">'
      + '<div class="alb-head">'
      + '<div class="ttl"><h1 class="alb-h">Audio</h1>'
      + '<p class="alb-sub">The music Clipstorm can put under a clip, and how loud it plays. '
      + 'To find, listen to and keep sounds, use Sounds.</p></div>'
      + '<span class="sp"></span>'
      + '<span class="alb-count" id="alb_count"></span>'
      + "</div>"
      + '<section class="alb-sec" aria-label="Music"><h2>Music under the voice</h2>'
      + '<p class="alb-sub">A music bed plays under the voice for the whole clip. A clip gets one when its mood is chill or tense. '
      + 'Funny and Hype beds exist too, but a clip with those moods gets the meme sound instead, so you will not hear them by choosing a mood.</p>'
      + '<div class="alb-beds" id="alb_beds"><p class="alb-note">Reading the music list...</p></div>'
      + '<div class="alb-row" style="margin-top:6px"><button class="btn sm" type="button" data-act="alb-build">Build the missing music</button>'
      + '<span class="alb-note" id="alb_buildsay"></span></div></section>'
      + '<section class="alb-sec" aria-label="Loudness"><h2>How loud the music is</h2>'
      + '<ul class="alb-facts"><li>The bed starts 14 dB below the voice, so speech stays clear.</li>'
      + '<li>It drops further while someone is talking, then rises again in the gaps.</li>'
      + '<li>The finished clip is levelled to about -14 LUFS, the same as the rest of Clipstorm.</li></ul>'
      + '<p class="alb-note">These are fixed in Clipstorm today, so there is nothing to change here. A saved brand can carry a default mood for every clip.</p></section>'
      + '<details class="alb-more"><summary>Sounds you have marked: likes, bookmarks and downloads</summary><div class="alb-inner">'
      + '<div class="alb-goto"><div><b>Looking for new sounds?</b>'
      + '<p>Searching, trending sounds and keeping a sound happen in Sounds. Kept sounds can be liked, bookmarked and downloaded there too.</p></div>'
      + '<button class="btn primary" type="button" data-act="alb-sounds">Open Sounds</button></div>'
      + '<div id="alb_bars">' + barHtml() + "</div>"
      + '<div class="alb-body"><section class="alb-results" aria-label="Your kept sounds">'
      + '<p class="alb-note" id="alb_top"></p>'
      + '<div class="alb-grid" id="alb_grid"></div>'
      + '<p class="alb-note" id="alb_note"></p>'
      + '</section><aside class="alb-sidebar" aria-label="Audio filters"><h2>Show</h2><div id="alb_tools">' + toolsHtml() + '</div></aside></div>'
      + '<p class="alb-note">Sounds from the web catalogue are clips from shows, games and songs, and the catalogue marks most of '
      + 'them "rights unverified". They are fine for personal memes and commentary, but not a promise for advertising.</p>'
      + "</div></details></div>";
  }

  /* ---- loading ------------------------------------------------------------------------------------- */
  async function loadBoard() {
    B.err = "";
    B.note = "";
    const got = await read("/api/memesounds/library");
    const lib = Array.isArray(got.sounds) ? got.sounds : [];
    if (B.board === "liked" || B.board === "bookmarked") {
      const marks = B.board === "liked" ? B.likes : B.marks;
      B.rows = lib.filter((r) => marks[r.slug]);
      B.note = B.rows.length
        ? "Marked in this browser. Liking does not change anything on the internet."
        : "Nothing marked yet. Press " + (B.board === "liked" ? "Like" : "Bookmark") + " on one of your sounds.";
      return;
    }
    if (B.board === "mine") {
      B.rows = lib.filter((r) => r.source === "uploaded" || String(r.slug || "").startsWith("mine-"));
      B.note = B.rows.length ? "Files you uploaded yourself." : "You have not uploaded a file yet. You can do that on the Sounds page.";
      return;
    }
    B.rows = lib;
    B.note = lib.length
      ? "Kept on this machine. A like or a bookmark is remembered in this browser."
      : "You have not kept any sounds yet.";
  }

  async function go(board) {
    if (B.busy) return;
    B.board = board;
    B.busy = true;
    const bars = $("alb_bars");
    if (bars) bars.innerHTML = barHtml();
    const grid = $("alb_grid");
    if (grid) grid.innerHTML = '<p class="alb-note">Reading your sounds...</p>';
    try {
      await loadBoard();
    } catch (e) {
      B.rows = [];
      B.err = "Your sounds could not be read: " + sentence(e, "the server did not say why.");
    } finally {
      B.busy = false;
    }
    if (bars) bars.innerHTML = barHtml();
    draw();
  }

  function shown() {
    const q = B.q.trim().toLowerCase();
    const cap = Number(B.max) || 0;
    return B.rows.filter((r) => {
      if (cap && known(r.seconds) && Number(r.seconds) > cap) return false;
      if (!q) return true;
      return String(r.title || r.slug || "").toLowerCase().includes(q);
    });
  }

  function waveHtml(slug) {
    // Drawn from the real bytes, decoded once. A sound that cannot be decoded shows a flat line, not an invented shape.
    return '<canvas class="alb-wave" data-wave="' + esc(slug) + '" width="240" height="30" aria-hidden="true"></canvas>';
  }

  function listen(slug, title) {
    const s = snd();
    if (!s) return "";
    return s.playBtn(slug, title, s.playUrl(slug)).replace('data-sx="hear"', 'data-act="alb-play"');
  }

  function card(r) {
    const slug = String(r.slug || "");
    const title = String(r.title || slug);
    const liked = !!B.likes[slug];
    const marked = !!B.marks[slug];
    const sub = [secs1(r.seconds), r.source === "uploaded" || slug.startsWith("mine-") ? "your file" : ""].filter(Boolean).join(" · ");
    return '<div class="alb-card">'
      + '<div class="top">' + listen(slug, title)
      + '<div class="nm"><b title="' + esc(title) + '">' + esc(title) + "</b>"
      + (sub ? "<small>" + esc(sub) + "</small>" : "") + "</div></div>"
      + waveHtml(slug)
      + '<div class="alb-row">'
      + '<button class="alb-mini" type="button" data-act="alb-like" data-slug="' + esc(slug) + '" aria-pressed="'
      + (liked ? "true" : "false") + '" title="Like: a mark for you, kept in this browser">Like</button>'
      + '<button class="alb-mini" type="button" data-act="alb-mark" data-slug="' + esc(slug) + '" aria-pressed="'
      + (marked ? "true" : "false") + '" title="Bookmark: a mark for you, kept in this browser">Bookmark</button>'
      + '<span class="sp"></span>'
      + '<a class="alb-mini" download href="/api/memesounds/play/' + encodeURIComponent(slug) + '" title="Save a copy of this file">Download</a>'
      + '<button class="alb-mini" type="button" data-act="alb-forget" data-slug="' + esc(slug) + '" data-title="' + esc(title) + '" title="Remove from this machine">Remove</button>'
      + "</div></div>";
  }

  function draw() {
    const count = $("alb_count");
    const rows = shown();
    if (count) count.textContent = rows.length ? rows.length + (rows.length === 1 ? " sound" : " sounds") : "";
    const top = $("alb_top");
    if (top) top.textContent = B.err || B.note || "";
    const grid = $("alb_grid");
    if (!grid) return;
    if (B.err) {
      grid.innerHTML = '<p class="alb-empty">' + esc(B.err) + '<br>Reload the page to try again.</p>';
    } else if (!rows.length) {
      const empty = B.rows.length
        ? "Nothing matches that filter. Clear the Find box or choose Any length."
        : (B.board === "kept"
          ? "You have not kept any sounds yet. Open Sounds, press Listen on one you like, then press Keep."
          : "Nothing on this shelf yet.");
      grid.innerHTML = '<div class="alb-empty">' + esc(empty)
        + (!B.rows.length ? '<br><button class="btn primary sm" type="button" data-act="alb-sounds">Open Sounds</button>' : "") + "</div>";
    } else if (B.view === "list") {
      grid.style.gridTemplateColumns = "1fr";
      grid.innerHTML = rows.map((r) => '<div class="alb-hit">'
        + listen(String(r.slug), String(r.title || r.slug))
        + '<span class="nm"><b style="font-weight:600">' + esc(r.title || r.slug) + "</b>"
        + (secs1(r.seconds) ? "<small>" + esc(secs1(r.seconds)) + "</small>" : "") + "</span>"
        + '<button class="alb-mini" type="button" data-act="alb-like" data-slug="' + esc(r.slug) + '" aria-pressed="'
        + (B.likes[r.slug] ? "true" : "false") + '">Like</button>'
        + '<button class="alb-mini" type="button" data-act="alb-mark" data-slug="' + esc(r.slug) + '" aria-pressed="'
        + (B.marks[r.slug] ? "true" : "false") + '">Bookmark</button>'
        + '<a class="alb-mini" download href="/api/memesounds/play/' + encodeURIComponent(r.slug) + '">Download</a>'
        + '<button class="alb-mini" type="button" data-act="alb-forget" data-slug="' + esc(r.slug) + '" data-title="' + esc(r.title || r.slug) + '">Remove</button>'
        + "</div>").join("");
    } else {
      grid.style.gridTemplateColumns = "";
      grid.innerHTML = rows.map(card).join("");
    }
    grid.querySelectorAll("canvas[data-wave]").forEach((cv) => {
      const slug = cv.getAttribute("data-wave");
      bars(slug).then((got) => {
        if (!got) { cv.setAttribute("data-none", "1"); return; }
        paint(cv, got);
      });
    });
  }

  /* ---- loudness pictures --------------------------------------------------------------------------- */
  // One decode per sound, cached, from the same bytes Listen streams. A failure caches `null`, so a sound that
  // cannot be decoded is drawn flat instead of being asked again on every repaint.
  const waves = new Map();
  let ctx = null;
  const BARS = 46;

  function bars(slug) {
    if (waves.has(slug)) return Promise.resolve(waves.get(slug));
    return new Promise((resolve) => {
      const done = (v) => { waves.set(slug, v); resolve(v); };
      try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return done(null);
        ctx = ctx || new AC();
        fetch("/api/memesounds/play/" + encodeURIComponent(slug), { credentials: "same-origin" })
          .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error("no bytes"))))
          .then((buf) => {
            const p = ctx.decodeAudioData(buf, (decoded) => {
              try {
                const data = decoded.getChannelData(0);
                const step = Math.max(1, Math.floor(data.length / BARS));
                const out = [];
                for (let i = 0; i < BARS; i++) {
                  let peak = 0;
                  const from = i * step;
                  for (let j = 0; j < step; j += 8) {
                    const v = Math.abs(data[from + j] || 0);
                    if (v > peak) peak = v;
                  }
                  out.push(peak);
                }
                done(out);
              } catch (e) { done(null); }
            }, () => done(null));
            if (p && typeof p.then === "function") p.catch(() => done(null));
          })
          .catch(() => done(null));
      } catch (e) { done(null); }
      setTimeout(() => { if (!waves.has(slug)) done(null); }, 8000);
    });
  }

  function paint(cv, heights) {
    const g = cv.getContext("2d");
    if (!g) return;
    const w = cv.width, h = cv.height;
    g.clearRect(0, 0, w, h);
    const top = Math.max(0.02, Math.max.apply(null, heights));
    const bw = w / heights.length;
    g.fillStyle = "#FF8B33";
    for (let i = 0; i < heights.length; i++) {
      const v = heights[i] / top;
      const bh = Math.max(1.5, v * (h - 6));
      g.fillRect(i * bw + 0.5, (h - bh) / 2, Math.max(1, bw - 1), bh);
    }
  }

  /* ---- removing ------------------------------------------------------------------------------------ */
  async function forget(slug, title) {
    const text = String(slug).startsWith("mine-")
      ? '"' + title + '" is a file you uploaded. Removing it deletes it from this machine, and you cannot get it back from the web.'
      : '"' + title + '" is deleted from this machine. You can keep it again from Sounds any time.';
    const yes = typeof window.ask === "function" ? await window.ask("Remove this sound?", text, "Remove", true) : true;
    if (!yes) return;
    try {
      const got = await read("/api/memesounds/library/" + encodeURIComponent(slug), { method: "DELETE" });
      if (snd()) snd().hush();
      if (got && got.ok === false) say("That sound was already gone from this machine.", "bad");
      else say("Removed from this machine.");
      await loadBoard();
      draw();
    } catch (e) {
      say(sentence(e, "That sound could not be removed."), "bad");
    }
  }

  /* ---- music beds ---------------------------------------------------------------------------------- */
  const M = { rows: null, err: "" };
  async function loadBeds() {
    try {
      const got = await read("/api/moods");
      M.rows = (got && Array.isArray(got.moods) ? got.moods : []).filter((r) => r && r.kind === "music" && r.name);
      M.err = "";
    } catch (e) {
      M.rows = [];
      M.err = "The music list could not be read: " + sentence(e, "the server did not say why.");
    }
    drawBeds();
  }
  function drawBeds() {
    const box = $("alb_beds");
    if (!box) return;
    if (M.err) { box.innerHTML = '<p class="alb-empty">' + esc(M.err) + "</p>"; return; }
    if (!M.rows || !M.rows.length) { box.innerHTML = '<p class="alb-empty">The server listed no music beds.</p>'; return; }
    const s = snd();
    box.innerHTML = M.rows.map((r) => {
      const name = String(r.name);
      const label = name.charAt(0).toUpperCase() + name.slice(1);
      const ctl = r.ready === true && s
        ? s.playBtn("bed:" + name, label + " music", "/api/sounds/music/" + encodeURIComponent(name)).replace('data-sx="hear"', 'data-act="alb-bed"')
        : '<span class="alb-note">Press Build the missing music to listen.</span>';
      return '<div class="alb-bed"><b>' + esc(label) + '</b><span class="line">' + esc(r.note || "Music mixed under the voice.")
        + "</span>" + (r.ready === true ? '<span class="pill ok">Ready</span>' : '<span class="pill">Not built yet</span>') + ctl + "</div>";
    }).join("");
  }
  async function buildBeds() {
    const out = $("alb_buildsay");
    if (out) out.textContent = "Making the missing files. This takes a few seconds for each one.";
    try {
      await P.send("/api/moods/prime", {}, "POST");
      await loadBeds();
      if (out) out.textContent = "Done. The list shows what is ready now.";
    } catch (e) {
      if (out) out.textContent = "The music was not built: " + sentence(e, "the server did not say why.");
    }
  }

  /* ---- the page ------------------------------------------------------------------------------------ */
  P.page("audio", {
    nav: "Audio moved",
    icon: "music",
    tip: "Music beds, how loud they play, and your marked sounds",
    path: "audio",
    hidden: true,
    group: "Make",
    order: 16,
    // Old links land here. The music beds and loudness facts now live on the one Audio page (path "sounds").
    view() {
      return '<div class="alb-page"><div class="alb-head"><div class="ttl"><h1 class="alb-h">Audio moved</h1>'
        + '<p class="alb-sub">Sounds and music are now together on one Audio page. To put audio on a clip, open the clip in My videos and press Edit audio.</p></div></div>'
        + '<button class="btn primary" type="button" data-act="alb-sounds">Open Audio</button></div>';
    },
    load() { if (P.openPage) P.openPage("sounds"); },
  });

  // The handlers live on their own add() call: web/plugins.js only walks the objects registered with add()
  // when a [data-act] button is pressed, so a handler written inside page() would never run.
  P.add("audio-page", {
    about: "Audio: the music beds, how loud they play, and the sounds you have marked.",
    act: {
      "alb-build"() { buildBeds(); },
      "alb-bed"(btn) {
        const s = snd();
        if (!s) { say("The sound player did not load. Reload the page.", "bad"); return; }
        s.hear(btn, btn.getAttribute("data-src"), (t) => say(t, "bad"));
      },
      "alb-sounds"() {
        if (!(P.openPage && P.openPage("sounds"))) say("The Sounds page did not load. Reload the page and try again.", "bad");
      },
      "alb-cat"(btn) {
        const b = btn.dataset.b || "kept";
        B.q = "";
        const q = $("alb_q");
        if (q) q.value = "";
        go(b);
      },
      "alb-view"(btn) { B.view = btn.dataset.v === "list" ? "list" : "grid"; draw(); },
      "alb-play"(btn) {
        const s = snd();
        if (!s) { say("The sound player did not load. Reload the page.", "bad"); return; }
        s.hear(btn, btn.getAttribute("data-src"), (t) => say(t, "bad"));
      },
      "alb-like"(btn) {
        const slug = btn.dataset.slug;
        B.likes[slug] = !B.likes[slug];
        if (!B.likes[slug]) delete B.likes[slug];
        savetaste();
        say(B.likes[slug] ? "Liked. It is on the Liked shelf." : "Like taken off.");
        if (B.board === "liked") { go("liked"); return; }
        draw();
      },
      "alb-mark"(btn) {
        const slug = btn.dataset.slug;
        B.marks[slug] = !B.marks[slug];
        if (!B.marks[slug]) delete B.marks[slug];
        savetaste();
        say(B.marks[slug] ? "Bookmarked. It is on the Bookmarked shelf." : "Bookmark taken off.");
        if (B.board === "bookmarked") { go("bookmarked"); return; }
        draw();
      },
      "alb-forget"(btn) { forget(btn.dataset.slug, btn.dataset.title || btn.dataset.slug); },
    },
  });

  // The filter boxes are plain fields, not actions, so they are wired once when the page draws.
  document.addEventListener("input", (e) => {
    const t = e.target;
    if (!t || !t.id || !document.querySelector(".alb-page")) return;
    if (t.id === "alb_q") { B.q = t.value; draw(); }
  });
  document.addEventListener("change", (e) => {
    const t = e.target;
    if (!t || !t.id || !document.querySelector(".alb-page")) return;
    if (t.id === "alb_max") { B.max = Number(t.value) || 0; draw(); }
  });
})();
