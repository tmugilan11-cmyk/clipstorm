/* The sound library everyone else borrows: search, trending meme sounds, My sounds, one shared player.
 *
 * This file used to add a "From the web" box under the Sounds page. It is now the one place that knows how to
 * browse the web catalogue, keep a sound on this machine, remove it, upload your own, and play it. Three screens
 * draw from it, so a card looks and behaves the same everywhere:
 *   * Sounds (web/feat/sounds.js)       the whole library, with the search box and the two lists
 *   * Audio (web/feat/audio-page.js)    the shelf, with favourites and downloads, and its own Listen buttons
 *   * Edit audio (web/feat/audio-edit.js)  the picker that opens over a clip's timeline
 *
 * It hands them `window.PeakCut.snd`: `mount(host, options)` draws the library into a box, `hear(button, address,
 * say)` is the ONE player (pressing a second Listen stops the first), and a few small helpers (`mmss`, `secs1`).
 *
 * Routes, all in `studio/api_memesound.py` and `studio/api_sound.py`:
 *   GET    /api/memesounds/library          what is kept on this machine (name, length, where it came from)
 *   GET    /api/memesounds/trending         what people are playing on the web right now
 *   GET    /api/memesounds/search?q=        by name, tag, mood or use
 *   GET    /api/memesounds/for?situation=   sounds for a moment or a kind of sound
 *   POST   /api/memesounds/keep             copy one to this machine (the only way a sound can be played or used)
 *   DELETE /api/memesounds/library/<slug>   remove one from this machine
 *   POST   /api/memesounds/upload           keep a file of the person's own
 *   GET    /api/memesounds/play/<slug>      the bytes of a kept sound
 *   GET    /api/moods                       the kinds of sound PeakCut knows (the filter buttons come from here)
 *
 * Why Listen saves a copy first: the page's security rules only let the browser play files that come from PeakCut
 * itself, never straight from the web catalogue. So pressing Listen on a web sound keeps a copy on this machine and
 * then plays that copy. The page says so, and Remove undoes it.
 *
 * A length is drawn only when the server sent one (the catalogue lists names, not lengths): a missing length shows
 * nothing, never "0.0 s". */
(function () {
  "use strict";
  const P = window.PeakCut;
  if (!P) return;

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
  const enc = encodeURIComponent;
  const known = (n) => n !== null && n !== undefined && n !== "" && isFinite(Number(n)) && Number(n) > 0;
  const secs1 = (n) => (known(n) ? (Math.round(Number(n) * 10) / 10).toFixed(1) + " s" : "");
  const mmss = (t) => {
    const s = Math.max(0, Math.round(Number(t) || 0));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  };
  const sentence = (e, fallback) => ((e && e.message) ? String(e.message) : "") || fallback;

  P.css("meme-timeline", `
.sx{display:grid;gap:6px;min-width:0}
.sx-sec{display:grid;gap:10px;padding:0 0 22px;margin:0 0 22px;border-bottom:1px solid var(--line);min-width:0}
.sx-sec:last-child{border-bottom:0;margin-bottom:0;padding-bottom:0}
.sx-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.sx-head h2{margin:0;font-size:17px;color:var(--text)}
.sx-head .sx-sp{margin-left:auto}
.sx-count{font-size:12px;color:var(--dim);font-variant-numeric:tabular-nums}
.sx-sub{margin:0;font-size:13px;line-height:1.5;color:var(--dim);max-width:70ch}
.sx-say{margin:0;font-size:13px;line-height:1.5;color:var(--dim);min-height:18px}
.sx-say.bad{color:var(--bad)}
.sx-search{display:flex;gap:8px;max-width:620px}
.sx-search input[type=search]{flex:1;min-width:0;height:38px;padding:0 12px;border:1px solid var(--line-2);
  border-radius:var(--r-sm);background:var(--field);color:var(--text);font:inherit;font-size:14px}
.sx-search input[type=search]:hover{border-color:var(--brand-line)}
.sx-chips{display:flex;gap:6px;flex-wrap:wrap}
.sx-chip{border:1px solid var(--line-2);background:var(--bg);color:var(--dim);border-radius:999px;padding:6px 13px;
  font:inherit;font-size:13px;font-weight:600;cursor:pointer;transition:border-color .15s ease,color .15s ease}
.sx-chip:hover{border-color:var(--brand);color:var(--brand-deep)}
.sx-chip[aria-pressed="true"]{border-color:var(--brand);background:var(--brand-soft);color:var(--brand-deep)}
.sx-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
.sx-card{display:grid;gap:8px;align-content:start;padding:12px;border:1px solid var(--line);border-radius:var(--r);
  background:var(--card);min-width:0;transition:border-color .15s ease}
.sx-card:hover{border-color:var(--line-2)}
.sx-card.playing{border-color:var(--brand)}
.sx-top{display:flex;align-items:center;gap:10px;min-width:0}
.sx-nm{min-width:0;display:grid;gap:2px}
.sx-nm b{font-size:14px;font-weight:600;line-height:1.3;color:var(--text);overflow:hidden;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow-wrap:anywhere}
.sx-nm small{font-size:12px;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sx-about{margin:0;font-size:12px;line-height:1.45;color:var(--dim);overflow:hidden;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical}
.sx-acts{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.sx-acts .sx-sp{margin-left:auto}
.sx-play{display:inline-flex;align-items:center;justify-content:center;gap:6px;flex:none;height:34px;padding:0 14px 0 11px;
  border-radius:999px;border:1px solid var(--brand);background:var(--brand);color:var(--brand-ink);font:inherit;
  font-size:13px;font-weight:700;cursor:pointer;transition:background-color .15s ease,color .15s ease}
.sx-play:hover{background:var(--brand-press);border-color:var(--brand-press)}
.sx-play.on{background:var(--brand-soft);color:var(--brand-deep)}
.sx-play.on:hover{background:var(--brand-line)}
.sx-play:focus-visible,.sx-chip:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
.sx-play[disabled]{opacity:.5;cursor:default}
.sx-btn{height:32px;padding:0 12px;font-size:13px}
.sx-done{color:var(--good);border-color:var(--good-soft);background:var(--good-soft);cursor:default}
.sx-empty{padding:22px 16px;border:1px dashed var(--line-2);border-radius:var(--r);color:var(--dim);font-size:13px;
  line-height:1.6;text-align:center}
.sx-empty .btn{margin-top:8px}
.sx-file{cursor:pointer}
.sx-mark[aria-pressed="true"]{border-color:var(--brand);color:var(--brand-deep);background:var(--brand-soft)}
.sx-sw{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--dim);cursor:pointer}
.sx-sw input{accent-color:var(--brand)}
@media (max-width:560px){.sx-grid{grid-template-columns:minmax(0,1fr)}.sx-btn,.sx-play{min-height:40px}}
  `);


  /* ------------------------------------------------------------------ what each mood does, in plain words
   * Taken from MOODS in studio/meme.py (a sound plus a small picture trick at the payoff) and studio/music.py (a bed
   * under the voice). A mood word that is both a meme sound and a bed (funny, hype) is the meme sound: `_add_sound`
   * in studio/jobs.py asks the meme table first. So chill and tense are the two moods that give music. */
  const MOOD_LINE = {
    funny: ["A rimshot, then a ding, at the punchline.", "Adds a meme sound at the punchline"],
    fail: ["A sad violin or trombone and a quick push-in on the mistake.", "Adds a sad sound when something goes wrong"],
    shock: ["A vine boom and a punch-in when something surprising lands.", "Adds a loud boom when something shocking lands"],
    hype: ["An airhorn and a bass drop, with a shake and a flash. The loudest one.", "Adds an airhorn and a bass drop at the big moment"],
    win: ["A bass drop and a push-in at the win.", "Adds a bass drop when someone wins"],
    embarrassing: ["A sad trombone and a freeze on the awkward moment.", "Freezes the picture on the embarrassing moment"],
    awkward: ["Curb music, or crickets, and a short freeze.", "Adds crickets and a short freeze after an awkward line"],
    cringe: ["A record scratch and a short freeze.", "Adds a record scratch and a short freeze"],
    suspense: ["A slow heartbeat and a darker edge to the picture.", "Adds a slow heartbeat and darkens the edges"],
    chill: ["Slow, warm music under the voice. Good for a talk or a story.", "Adds slow, warm music under the voice"],
    tense: ["Low, held music under the voice. Good for a chase or a near miss.", "Adds low, uneasy music under the voice"],
  };
  const BED_ONLY = { chill: 1, tense: 1 };
  /** [long line, short line] for a mood word, or a general line when the word is new. */
  function moodInfo(name, kind) {
    const k = String(name || "").toLowerCase();
    if (MOOD_LINE[k] && (kind !== "music" || BED_ONLY[k])) return MOOD_LINE[k];
    return kind === "music"
      ? ["A loop of music mixed under the voice.", "Adds music under the voice"]
      : ["A short sound laid over the clip.", "Adds a short sound over the clip"];
  }

  /* ------------------------------------------------------------------ the one player */
  const ICON_PLAY = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M7 4.5v15l12-7.5z" fill="currentColor"/></svg>';
  const ICON_STOP = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor"/></svg>';
  const HEAR = { audio: null, btn: null, key: "" };

  /** A round Listen button. `key` says which sound it is, so a redraw can find its own button again. */
  function playBtn(key, name, src, label) {
    const word = label || "Listen";
    return `<button type="button" class="sx-play" data-sx="hear" data-key="${esc(key)}" data-src="${esc(src)}" data-name="${esc(name)}" data-word="${esc(word)}" aria-pressed="false" aria-label="${esc(word + " to " + name)}">${ICON_PLAY}<span>${esc(word)}</span></button>`;
  }

  function paint(btn, on) {
    if (!btn) return;
    const word = btn.getAttribute("data-word") || "Listen";
    const name = btn.getAttribute("data-name") || "this sound";
    btn.classList.toggle("on", !!on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.setAttribute("aria-label", (on ? "Stop " : word + " to ") + name);
    btn.innerHTML = (on ? ICON_STOP : ICON_PLAY) + "<span>" + esc(on ? "Stop" : word) + "</span>";
    const card = btn.closest(".sx-card");
    if (card) card.classList.toggle("playing", !!on);
  }

  /** Stops whatever is playing and puts every Listen button on the page back to rest. */
  function hush() {
    if (HEAR.audio) { try { HEAR.audio.pause(); } catch (e) { /* nothing was playing */ } }
    document.querySelectorAll(".sx-play.on").forEach((b) => paint(b, false));
    HEAR.btn = null;
    HEAR.key = "";
  }

  /** Press: play this address, stopping any other sound first. Pressing the same button again is Stop. */
  function hear(btn, src, say, volume) {
    const was = HEAR.btn === btn && HEAR.audio && !HEAR.audio.paused;
    hush();
    if (was || !btn || !src) return;
    const a = HEAR.audio || (HEAR.audio = new Audio());
    a.onended = () => hush();
    a.onerror = () => {
      if (HEAR.btn !== btn) return;
      hush();
      if (say) say("That sound could not be played here. Press Keep again, or reload the page.");
    };
    HEAR.btn = btn;
    HEAR.key = btn.getAttribute("data-key") || "";
    paint(btn, true);
    a.volume = Number.isFinite(volume) ? Math.max(0, Math.min(1, volume)) : 1;
    a.src = src;
    const started = a.play();
    if (started && typeof started.catch === "function") {
      started.catch(() => {
        if (HEAR.btn !== btn) return;          // a later press already took over
        hush();
        if (say) say("Your browser would not play that sound here.");
      });
    }
  }

  /** After a list is redrawn the pressed button is a new element: find it again so it still says Stop. */
  function rebind(root) {
    if (!HEAR.key || !HEAR.audio || HEAR.audio.paused || !root) return;
    const btns = root.querySelectorAll(".sx-play[data-key]");
    for (const b of btns) {
      if (b.getAttribute("data-key") === HEAR.key) { HEAR.btn = b; paint(b, true); return; }
    }
  }

  // Leaving a screen with a sound still playing would leave it playing under the next one.
  setInterval(() => {
    if (HEAR.btn && !HEAR.btn.isConnected) {
      const key = HEAR.key;
      const again = key ? Array.from(document.querySelectorAll(".sx-play[data-key]")).find((b) => b.getAttribute("data-key") === key) : null;
      if (again) { HEAR.btn = again; paint(again, true); } else hush();
    }
  }, 700);

  /* ------------------------------------------------------------------ keeping, removing, uploading */
  const playUrl = (slug) => "/api/memesounds/play/" + enc(slug);

  async function readKept() {
    const got = await P.api("/api/memesounds/library");
    const rows = got && Array.isArray(got.sounds) ? got.sounds : [];
    const map = new Map();
    for (const r of rows) if (r && r.slug) map.set(String(r.slug), r);
    return { rows, map };
  }

  function removeText(slug, name) {
    return String(slug).indexOf("mine-") === 0
      ? `"${name}" is a file you uploaded. Removing it deletes it from this machine, and you cannot get it back from the web.`
      : `"${name}" is deleted from this machine. You can keep it again from the web list any time.`;
  }

  function asked(title, text, ok) {
    return typeof window.ask === "function" ? window.ask(title, text, ok, true) : Promise.resolve(true);
  }

  /* ------------------------------------------------------------------ one library on a page */
  /**
   * Draws the library into `host`.
   *   options.pick     true inside the clip editor: the cards offer "Add" instead of Keep and Remove
   *   options.onPick   (slug, title) called when Add is pressed; the sound is on this machine by then
   *   options.addWord  the Add button's words (the editor says "Add at 0:12")
   *   options.mineFirst  draw My sounds above the web list
   *   options.upload   false hides the Upload button
   */
  function mount(host, options) {
    if (!host) return null;
    if (host.__sx) { host.__sx.refresh(); return host.__sx; }
    const o = options || {};
    const L = {
      kept: new Map(), rows: [], ready: false, keptErr: "",
      trend: null, trendErr: "", busy: false,
      results: null, resultsFor: "", resultsErr: "", looking: false,
      chip: "", moods: [], saving: {}, hidden: 0,
      adult: false, likes: {}, marks: {},
    };
    // 18+ sounds are OFF unless the person turned the switch on; the choice is remembered in this browser only.
    try { L.adult = window.localStorage.getItem("peakcut.sounds.adult") === "1"; } catch (e) { /* storage is off: stays hidden */ }
    try {
      const raw = window.localStorage.getItem("peakcut.audio.taste");
      const got = raw ? JSON.parse(raw) : null;
      if (got && typeof got === "object") { L.likes = got.likes || {}; L.marks = got.marks || {}; }
    } catch (e) { /* a browser with storage turned off simply forgets */ }
    const saveTaste = () => { try { window.localStorage.setItem("peakcut.audio.taste", JSON.stringify({ likes: L.likes, marks: L.marks })); } catch (e) { /* nothing to save to */ } };
    const box = (n) => host.querySelector(`[data-box="${n}"]`);
    const say = (text, bad) => {
      const el = box("say");
      if (!el) return;
      el.textContent = text || "";
      el.classList.toggle("bad", !!bad);
    };

    const webSection = `<section class="sx-sec" aria-label="Sounds from the web">
        <div class="sx-head"><h2 data-box="webh">Trending meme sounds</h2><span class="sx-count" data-box="webn"></span>
          <span class="sx-sp"></span><button type="button" class="btn sm" data-sx="clear" data-box="clear" hidden>Back to trending</button></div>
        <p class="sx-sub" data-box="websub"></p>
        <div class="sx-grid" data-box="web"></div>
      </section>`;
    const mineSection = `<section class="sx-sec" aria-label="Sounds kept on this machine">
        <div class="sx-head"><h2>My sounds</h2><span class="sx-count" data-box="minen"></span><span class="sx-sp"></span>
          ${o.upload === false ? "" : `<label class="btn sm sx-file">Upload your own<input type="file" accept="audio/*" data-box="file" hidden></label>`}</div>
        <p class="sx-sub">${o.pick
          ? "These are on this machine, so they can go on the clip right now."
          : "Kept on this machine, so a clip never needs the internet to use them. Listen, remove, or upload a short sound of your own."}</p>
        <p class="sx-say" data-box="upsay" aria-live="polite"></p>
        <div class="sx-grid" data-box="mine"></div>
      </section>`;
    host.classList.add("sx");
    host.innerHTML = `<section class="sx-sec" aria-label="Find a sound">
        <h2 class="sx-h" style="margin:0;font-size:17px;color:var(--text)">Find a sound</h2>
        <form class="sx-search" data-sx="find" role="search">
          <input type="search" data-box="q" placeholder="Name a sound, or describe the moment" aria-label="Search for a sound" autocomplete="off">
          <button class="btn primary sm" type="submit">Search</button>
        </form>
        <div class="sx-chips" data-box="chips" role="group" aria-label="Kinds of sound"></div>
        <label class="sx-sw"><input type="checkbox" data-box="adult"> Show 18+ sounds</label>
        <p class="sx-say" data-box="say" aria-live="polite"></p>
      </section>${o.mineFirst ? mineSection + webSection : webSection + mineSection}`;

    /* ---- 18+ filter. The catalogue (dankmachine) sends no age flag today, so this only acts on a row that carries
       one: an explicit/nsfw/adult/age field set to true, or such a word among its category, moods or use cases. */
    const ADULT = /^(nsfw|explicit|18\+?|adult|mature|porn|sexual|age[-_ ]?restricted)$/i;
    const isAdult = (r) => !!r && (r.explicit === true || r.nsfw === true || r.adult === true || r.age_restricted === true
      || ADULT.test(String(r.category || "")) || [].concat(r.moods || [], r.use_cases || [], r.tags || []).some((t) => ADULT.test(String(t))));
    const visible = (list) => {
      const ok = L.adult ? list : list.filter((r) => !isAdult(r));
      L.hidden = list.length - ok.length;
      return ok;
    };

    /* ---- cards */
    function cardHtml(r, mine) {
      const slug = String(r.slug || "");
      if (!slug) return "";
      const have = L.kept.get(slug);
      const name = String(r.title || (have && have.title) || slug.replace(/^mine-/, "").replace(/-/g, " "));
      const len = secs1(have && have.seconds) || secs1(r.seconds);
      const tags = Array.isArray(r.moods) ? r.moods.slice(0, 2) : [];
      const bits = [len, mine ? ((have && have.source === "uploaded") || slug.indexOf("mine-") === 0 ? "your file" : "") : "", ...tags].filter(Boolean);
      const saving = !!L.saving[slug];
      let acts;
      if (o.pick) {
        acts = `<button type="button" class="btn primary sm sx-btn" data-sx="pick" data-slug="${esc(slug)}" data-name="${esc(name)}"${saving ? " disabled" : ""}>${esc(saving ? "Adding" : (o.addWord || "Add"))}</button>`;
      } else if (have) {
        acts = `<span class="btn sm sx-btn sx-done" aria-label="${esc(name)} is kept on this machine">Kept</span>`
          + `<button type="button" class="btn sm sx-btn sx-mark" data-sx="like" data-slug="${esc(slug)}" aria-pressed="${L.likes[slug] ? "true" : "false"}" title="A mark for you, remembered in this browser">Like</button>`
          + `<button type="button" class="btn sm sx-btn sx-mark" data-sx="mark" data-slug="${esc(slug)}" aria-pressed="${L.marks[slug] ? "true" : "false"}" title="A mark for you, remembered in this browser">Bookmark</button>`
          + `<a class="btn sm sx-btn" download href="${esc(playUrl(slug))}" title="Save a copy of this file to your computer">Download</a>`
          + `<button type="button" class="btn ghost sm sx-btn" data-sx="remove" data-slug="${esc(slug)}" data-name="${esc(name)}">Remove</button>`;
      } else {
        acts = `<button type="button" class="btn sm sx-btn" data-sx="keep" data-slug="${esc(slug)}" data-name="${esc(name)}"${saving ? " disabled" : ""}>${esc(saving ? "Keeping" : "Keep")}</button>`;
      }
      const about = !mine && r.about ? `<p class="sx-about" title="${esc(r.about)}">${esc(r.about)}</p>` : "";
      return `<div class="sx-card" data-slug="${esc(slug)}">
        <div class="sx-top">${playBtn(slug, name, playUrl(slug))}
          <div class="sx-nm"><b title="${esc(name)}">${esc(name)}</b>${bits.length ? `<small>${esc(bits.join(" · "))}</small>` : ""}</div></div>
        ${about}
        <div class="sx-acts">${acts}</div>
      </div>`;
    }

    /* ---- drawing */
    function drawChips() {
      const el = box("chips");
      if (!el) return;
      if (!L.moods.length) { el.innerHTML = ""; return; }
      el.innerHTML = `<button type="button" class="sx-chip" data-sx="chip" data-mood="" aria-pressed="${L.chip ? "false" : "true"}">Trending</button>`
        + L.moods.map((m) => `<button type="button" class="sx-chip" data-sx="chip" data-mood="${esc(m)}" aria-pressed="${L.chip === m ? "true" : "false"}">${esc(m.charAt(0).toUpperCase() + m.slice(1))}</button>`).join("");
    }

    function drawWeb() {
      const grid = box("web"), head = box("webh"), sub = box("websub"), cnt = box("webn"), back = box("clear");
      if (!grid) return;
      const searching = !!L.resultsFor;
      if (head) head.textContent = searching ? `Results for “${L.resultsFor}”` : "Trending meme sounds";
      if (back) back.hidden = !searching;
      if (sub) {
        sub.textContent = searching
          ? "Press Listen to hear one. Press Keep to put a copy on this machine."
          : "What people are playing on the web right now. Press Listen to hear one. Press Keep to put a copy in My sounds.";
      }
      if (L.looking || (!searching && L.trend === null && !L.trendErr)) {
        grid.innerHTML = `<p class="sx-sub">${searching ? "Looking for sounds..." : "Reading the web catalogue..."}</p>`;
        if (cnt) cnt.textContent = "";
        return;
      }
      const err = searching ? L.resultsErr : L.trendErr;
      if (err) {
        grid.innerHTML = `<div class="sx-empty">The web catalogue could not be reached: ${esc(err)}<br>Check the internet connection. Your own sounds below still work.<br>
          <button type="button" class="btn sm" data-sx="retry">Try again</button></div>`;
        if (cnt) cnt.textContent = "";
        return;
      }
      const list = visible((searching ? L.results : L.trend) || []);
      if (cnt) cnt.textContent = (list.length ? list.length + (list.length === 1 ? " sound" : " sounds") : "")
        + (L.hidden ? (list.length ? " · " : "") + L.hidden + " hidden (18+)" : "");
      grid.innerHTML = list.length
        ? list.map((r) => cardHtml(r, false)).join("")
        : `<div class="sx-empty">${searching ? "Nothing matched that. Try another word, or press a kind of sound above." : "Nothing is trending right now. Try a kind of sound above."}</div>`;
      rebind(grid);
    }

    function drawMine() {
      const grid = box("mine"), cnt = box("minen");
      if (!grid) return;
      if (L.keptErr) {
        grid.innerHTML = `<div class="sx-empty">${esc(L.keptErr)}<br><button type="button" class="btn sm" data-sx="reload">Try again</button></div>`;
        return;
      }
      if (!L.ready) { grid.innerHTML = `<p class="sx-sub">Reading your sounds...</p>`; return; }
      if (cnt) cnt.textContent = L.rows.length ? L.rows.length + (L.rows.length === 1 ? " sound" : " sounds") : "";
      grid.innerHTML = L.rows.length
        ? L.rows.map((r) => cardHtml(r, true)).join("")
        : `<div class="sx-empty">${o.pick
          ? "You have not kept any sounds yet. Keep one from the web list, or upload your own, and it shows here."
          : "Nothing kept yet. Press Keep on a trending sound above, or upload a short sound of your own."}</div>`;
      rebind(grid);
    }

    function drawAll() { drawChips(); drawWeb(); drawMine(); }

    /* ---- reading */
    async function loadKept() {
      try {
        const got = await readKept();
        L.rows = got.rows;
        L.kept = got.map;
        L.ready = true;
        L.keptErr = "";
      } catch (e) {
        L.ready = true;
        L.keptErr = "Your sounds could not be read: " + sentence(e, "the server did not say why.");
      }
    }
    async function loadTrend() {
      L.trendErr = "";
      try {
        const got = await P.api("/api/memesounds/trending?window=24h");
        L.trend = got && Array.isArray(got.sounds) ? got.sounds : [];
      } catch (e) {
        L.trend = [];
        L.trendErr = sentence(e, "the server did not say why.");
      }
    }
    async function loadMoods() {
      try {
        const got = await P.api("/api/moods");
        const names = got && Array.isArray(got.meme) ? got.meme : [];
        L.moods = names.map(String).filter(Boolean);
      } catch (e) { L.moods = []; }
    }
    async function look(q, mood) {
      const word = String(q || "").trim();
      if (!word) { L.results = null; L.resultsFor = ""; L.chip = ""; drawAll(); return; }
      L.chip = mood ? word : "";
      L.resultsFor = word;
      L.results = null;
      L.resultsErr = "";
      L.looking = true;
      drawAll();
      const words = word.split(/\s+/).filter(Boolean);
      // A kind of sound or a described moment goes to /for; one or two plain words go to /search.
      const path = (mood || words.length >= 3)
        ? "/api/memesounds/for?situation=" + enc(word) + "&limit=24"
        : "/api/memesounds/search?q=" + enc(word) + "&limit=24";
      try {
        const got = await P.api(path);
        if (L.resultsFor !== word) return;     // a later search took over
        L.results = got && Array.isArray(got.sounds) ? got.sounds : [];
      } catch (e) {
        if (L.resultsFor !== word) return;
        L.results = [];
        L.resultsErr = sentence(e, "the server did not say why.");
      }
      L.looking = false;
      drawAll();
    }

    async function refresh() {
      await Promise.all([loadKept(), L.moods.length ? Promise.resolve() : loadMoods()]);
      drawAll();
      if (L.trend === null) { await loadTrend(); drawAll(); }
    }

    /* ---- doing things */
    async function keep(slug, name, thenListen) {
      if (L.saving[slug]) return false;
      L.saving[slug] = true;
      drawAll();
      let ok = false;
      try {
        await P.api("/api/memesounds/keep", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slug, title: name || "" }) });
        await loadKept();
        ok = true;
        say(thenListen ? "" : `Kept "${name || slug}". It is in My sounds now.`);
      } catch (e) {
        say(sentence(e, "That sound could not be kept."), true);
      }
      delete L.saving[slug];
      drawAll();
      return ok;
    }

    async function remove(slug, name) {
      const yes = await asked("Remove this sound?", removeText(slug, name), "Remove");
      if (!yes) return;
      try {
        const got = await P.api("/api/memesounds/library/" + enc(slug), { method: "DELETE" });
        if (HEAR.key === slug) hush();
        if (got && got.ok === false) say("That sound was already gone from this machine.");
        else say(`Removed "${name || slug}".`);
      } catch (e) {
        say(sentence(e, "That sound could not be removed."), true);
      }
      await loadKept();
      drawAll();
    }

    async function listen(btn) {
      const slug = btn.getAttribute("data-key") || "";
      const name = btn.getAttribute("data-name") || slug;
      if (!L.kept.has(slug)) {
        // The browser cannot play straight from the web, so a copy comes here first.
        say(`Saving a copy of "${name}" so you can hear it. It will be in My sounds.`);
        const ok = await keep(slug, name, true);
        if (!ok) return;
        say("");
        const again = host.querySelector(`.sx-play[data-key="${(window.CSS && CSS.escape) ? CSS.escape(slug) : slug}"]`);
        if (again) hear(again, playUrl(slug), (t) => say(t, true));
        return;
      }
      hear(btn, btn.getAttribute("data-src"), (t) => say(t, true));
    }

    async function pick(btn) {
      const slug = btn.getAttribute("data-slug") || "";
      const name = btn.getAttribute("data-name") || slug;
      if (!L.kept.has(slug)) {
        const ok = await keep(slug, name, true);
        if (!ok) return;
      }
      if (typeof o.onPick === "function") o.onPick(slug, name);
    }

    async function upload(file) {
      const note = box("upsay");
      if (!file) return;
      if (note) note.textContent = `Keeping ${file.name}...`;
      const fd = new FormData();
      fd.append("file", file, file.name);
      try {
        const r = await fetch("/api/memesounds/upload", { method: "POST", body: fd });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j.detail || "The upload did not happen.");
        if (note) note.textContent = `Kept ${file.name}. It is in My sounds now.`;
        await loadKept();
        drawAll();
      } catch (e) {
        if (note) note.textContent = sentence(e, "The upload did not happen.");
      }
    }

    host.addEventListener("click", (ev) => {
      const t = ev.target.closest("[data-sx]");
      if (!t || !host.contains(t)) return;
      const what = t.getAttribute("data-sx");
      if (what === "hear") { listen(t); return; }
      if (what === "keep") { keep(t.getAttribute("data-slug"), t.getAttribute("data-name")); return; }
      if (what === "remove") { remove(t.getAttribute("data-slug"), t.getAttribute("data-name")); return; }
      if (what === "pick") { pick(t); return; }
      if (what === "like" || what === "mark") {
        const slug = t.getAttribute("data-slug");
        const bag = what === "like" ? L.likes : L.marks;
        if (bag[slug]) delete bag[slug]; else bag[slug] = true;
        saveTaste();
        say(bag[slug] ? (what === "like" ? "Liked." : "Bookmarked.") : "Mark taken off.");
        drawMine();
        return;
      }
      if (what === "chip") {
        const m = t.getAttribute("data-mood") || "";
        const q = box("q");
        if (q) q.value = "";
        if (!m) { look(""); return; }
        look(m, true);
        return;
      }
      if (what === "clear") { const q = box("q"); if (q) q.value = ""; look(""); return; }
      if (what === "retry") {
        if (L.resultsFor) look(L.resultsFor, !!L.chip);
        else { L.trend = null; refresh(); }
        return;
      }
      if (what === "reload") { L.ready = false; refresh(); }
    });
    host.addEventListener("submit", (ev) => {
      if (!ev.target.closest('[data-sx="find"]')) return;
      ev.preventDefault();
      const q = box("q");
      look(q ? q.value : "", false);
    });
    host.addEventListener("input", (ev) => {
      // Emptying the box puts the trending list back, so a person is never stuck on old results.
      if (ev.target && ev.target.matches && ev.target.matches('[data-box="q"]') && !ev.target.value.trim() && L.resultsFor) look("");
    });
    host.addEventListener("change", (ev) => {
      const f = ev.target;
      if (f && f.matches && f.matches('[data-box="adult"]')) {
        L.adult = !!f.checked;
        try { window.localStorage.setItem("peakcut.sounds.adult", L.adult ? "1" : "0"); } catch (e) { /* not remembered */ }
        say(L.adult ? "18+ sounds are shown." : "18+ sounds are hidden.");
        drawWeb();
        return;
      }
      if (f && f.matches && f.matches('[data-box="file"]')) {
        const one = f.files && f.files[0];
        upload(one).then(() => { try { f.value = ""; } catch (e) { /* nothing to clear */ } });
      }
    });

    const api = { refresh, kept: () => L.kept, rows: () => L.rows, say, keep: (slug, name) => keep(slug, name, true) };
    host.__sx = api;
    const sw = box("adult");
    if (sw) sw.checked = L.adult;
    drawAll();
    refresh();
    return api;
  }

  P.snd = { moodInfo, mount, hear, hush, playBtn, paint, mmss, secs1, known, esc, playUrl, readKept };

  /* The Sounds page and any other screen that carries an empty box marked `data-sx-lib` get the library from the
   * paint hook below, so a screen that forgot to call mount() still shows something rather than a blank. */
  function drawWeb(root) {
    const host = root && root.querySelector ? root.querySelector("[data-sx-lib]") : null;
    if (host && !host.__sx) mount(host, {});
  }

  P.add("meme-timeline", {
    about: "The shared sound library: search, trending meme sounds, My sounds and one player for every audio screen.",
    after: {
      // Pages report through this hook; it only fills a box that is empty and marked for the library.
      drawSettings(root) {
        try { drawWeb(root || document.getElementById("view") || document); } catch (e) { /* never break a page */ }
      },
    },
  });
})();
