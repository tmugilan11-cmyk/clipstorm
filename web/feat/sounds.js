/* Sounds: the one screen for finding, hearing, keeping and understanding every sound a clip can carry.
 *
 * Top to bottom, the way a beginner works:
 *   1. one line on how a sound reaches a clip (this page only lists sounds; placing happens in Edit audio on a clip)
 *   2. the library (search, kinds of sound, trending meme sounds, My sounds, upload): drawn by
 *      `web/feat/meme-timeline.js`, which also owns the one shared player
 *   3. the sounds Clipstorm makes itself: the nine mood sounds and four music beds, and whether each is built
 *
 * Words used on every audio screen: a SOUND is a short effect, MUSIC is a bed under the voice, a MOOD is the one
 * word that picks one of them for you.
 *
 * Section 3 is `studio/meme.py` and `studio/music.py`, which synthesise their files with numpy, so on a fresh install
 * most rows are honestly "not built" until `POST /api/moods/prime` has run once. `ready` comes from the server, which
 * looks at the data folder instead of building anything. A word can name both a sound and a bed (`hype` is both), so a
 * row is keyed by kind and name together.
 *
 * Routes:
 *   GET  /api/moods                  the moods and whether their file is on disk
 *   GET  /api/sounds/<music|meme>/<mood>   the bytes of a built sound (a 404 means "not built yet")
 *   POST /api/moods/prime            build what is missing
 * and, through meme-timeline.js, everything under /api/memesounds. */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});

  P.css("sounds", `
    .snd{display:grid;gap:6px;max-width:980px}
    .snd-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--ink);margin-bottom:6px}
    .snd-lede{max-width:64ch;margin:0}
    .snd-how{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:14px 16px;margin:0 0 24px;
      border:1px solid var(--brand-line);border-radius:var(--r);background:var(--brand-soft)}
    .snd-how p{margin:0;flex:1 1 300px;font-size:14px;line-height:1.5;color:var(--text)}
    .snd-how p b{color:var(--brand-deep)}
    .snd-sec-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
    .snd-sec-head h2{font-size:15px;font-weight:700;color:var(--ink);margin:0}
    .snd-rows{margin-top:12px;border-top:1px solid var(--line)}
    .snd-row{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}
    .snd-name{font-weight:600;color:var(--ink);flex:0 0 128px;overflow-wrap:anywhere}
    .snd-note{flex:1 1 200px;min-width:0;font-size:13px;color:var(--dim);line-height:1.45}
    .snd-say{flex:1 1 100%;font-size:12px;color:var(--faint);min-height:15px;order:9}
    .snd-off{font-size:12px;color:var(--faint)}
    .snd-none{margin:12px 0 0;color:var(--dim);max-width:64ch}
    @media (max-width:560px){
      .snd-h{font-size:20px}
      .snd-name{flex:1 1 100%}
      .snd-note{flex:1 1 100%}
    }
  `);

  const MEME = "meme", MUSIC = "music";
  const TITLE = { [MEME]: "Sounds Clipstorm makes", [MUSIC]: "Music Clipstorm makes" };
  const UNDER = {
    [MEME]: "A short effect at the funny or shocking moment of a clip, like a horn, a rimshot or a record scratch. You get one by picking its mood on a clip.",
    [MUSIC]: "A music bed that plays under the voice for the whole clip. You get one by picking chill or tense as the mood on a clip.",
  };

  const hint = (line) => `<p class="hint">${esc(line)}</p>`;
  const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : ""; };
  const snd = () => P.snd || null;

  let rows = null;       // the moods as read, or null before the first answer
  let reading = null;    // one request at a time, shared by every redraw that happens meanwhile
  let trouble = "";      // one sentence when the read failed, "" when it did not

  const css1 = (s) => {
    const v = String(s == null ? "" : s);
    if (typeof CSS !== "undefined" && CSS && typeof CSS.escape === "function") return CSS.escape(v);
    return v.replace(/["\\]/g, "\\$&");
  };

  /** The small line under one built-in row. Silent when the row is no longer on the page. */
  function say(id, text) {
    const box = document.querySelector(`#snd_body [data-say="${css1(id)}"]`);
    if (box) box.textContent = text;
  }

  /** The address of one built-in sound. Asked by kind and mood, never by file: the server knows which file answers. */
  function urlFor(row) {
    const key = String(row.key || "");
    if (!/^[A-Za-z0-9_-]{1,60}$/.test(key)) return "";
    return `/api/sounds/${row.kind === MUSIC ? "music" : "meme"}/${key}`;
  }

  /**
   * Press Listen on a built-in sound. The address is asked first with a HEAD, so a 404 can say "not made yet, press
   * Build" instead of blaming the browser for a file that was never there. The shared player does the playing, so
   * pressing any other Listen on any audio screen stops this one.
   */
  function play(row, btn) {
    const id = row.id;
    const P2 = snd();
    if (!P2) { say(id, "The sound player did not load. Reload the page."); return; }
    if (btn.classList.contains("on")) { P2.hear(btn, "", null); return; }   // a second press is Stop
    const src = urlFor(row);
    if (!src) { say(id, "That sound is kept under a folder name, so this page cannot play it directly."); return; }
    say(id, "");
    fetch(src, { method: "HEAD" }).then((r) => {
      if (r.ok) { P2.hear(btn, src, (t) => say(id, t)); return; }
      say(id, r.status === 404
        ? `The ${row.label} sound has not been made yet. Press "Build the missing sounds" at the bottom of this page.`
        : `The server could not hand over the ${row.label} sound (answered ${r.status}).`);
    }, () => say(id, "The page could not reach the server for that sound."));
  }

  /* ---------------------------------------------------------------- reading the moods */
  function read() {
    if (reading) return reading;
    reading = (async () => {
      try {
        const got = await P.api("/api/moods");
        const list = got && Array.isArray(got.moods) ? got.moods : [];
        rows = list
          .filter((r) => r && typeof r.name === "string" && r.name)
          .map((r) => {
            const kind = r.kind === MUSIC ? MUSIC : MEME;
            const name = String(r.name);
            return { id: `${kind}:${name}`, kind, key: name, label: name.charAt(0).toUpperCase() + name.slice(1), ready: r.ready === true };
          });
        trouble = "";
      } catch (err) {
        rows = [];
        const why = err && err.message ? String(err.message) : "";
        trouble = why ? `The list of built-in sounds could not be read: ${why}` : "The list of built-in sounds could not be read. The server did not say why.";
      } finally {
        reading = null;
      }
      return rows;
    })();
    return reading;
  }

  /* ---------------------------------------------------------------- drawing */
  const ORDER = ["funny", "fail", "shock", "hype", "win", "embarrassing", "awkward", "cringe", "suspense"];

  function inKind(all, kind) {
    const mine = all.filter((r) => r.kind === kind);
    if (kind !== MEME) return mine.sort((a, b) => a.key.localeCompare(b.key));
    const rank = (r) => { const i = ORDER.indexOf(r.key); return i < 0 ? ORDER.length : i; };
    return mine.sort((a, b) => rank(a) - rank(b) || a.key.localeCompare(b.key));
  }

  function about(row) {
    const info = snd() ? snd().moodInfo(row.key, row.kind) : null;
    return info ? info[0] : (row.kind === MUSIC ? "Music mixed under the voice." : "A sound laid over the clip.");
  }

  function rowHtml(row) {
    const state = row.ready ? `<span class="pill ok">Ready</span>` : `<span class="pill">Not built yet</span>`;
    const P2 = snd();
    const control = row.ready && P2
      ? P2.playBtn(row.id, `${row.label} ${row.kind === MUSIC ? "music" : "sound"}`, urlFor(row) || "")
      : `<span class="snd-off">Build it to listen</span>`;
    return `<div class="snd-row" data-row="${esc(row.id)}">
        <span class="snd-name">${esc(row.label)}</span>
        <span class="snd-note">${esc(about(row))}</span>
        ${state}${control}
        <span class="snd-say" data-say="${esc(row.id)}" aria-live="polite"></span>
      </div>`;
  }

  function sectionHtml(all, kind) {
    const mine = inKind(all, kind);
    const built = mine.filter((r) => r.ready).length;
    const count = mine.length ? `<span class="pill">${num(built)} of ${num(mine.length)} built</span>` : `<span class="pill">none listed</span>`;
    const body = mine.length
      ? `<div class="snd-rows">${mine.map(rowHtml).join("")}</div>`
      : `<p class="snd-none">The server listed none of these. If this stays empty, the server log says why.</p>`;
    return `<div class="snd-block">
        <div class="snd-sec-head"><h3 style="margin:0;font-size:14px;font-weight:700;color:var(--ink)">${esc(TITLE[kind])}</h3>${count}</div>
        ${hint(UNDER[kind])}
        ${body}
      </div>`;
  }

  function draw() {
    const box = document.getElementById("snd_body");
    if (!box) return;
    if (trouble) {
      box.innerHTML = `<p class="err">${esc(trouble)}</p><p class="hint">Reload the page. If it stays empty, the server log says why.</p>`;
      return;
    }
    const all = rows || [];
    if (!all.length) {
      box.innerHTML = `<p class="snd-none">The server answered, but there are no built-in sounds listed yet.</p>`;
      return;
    }
    box.innerHTML = sectionHtml(all, MEME) + `<div style="height:18px"></div>` + sectionHtml(all, MUSIC);
  }

  /* ---------------------------------------------------------------- building what is missing */
  async function build() {
    const btn = document.getElementById("snd_build");
    const note = document.getElementById("snd_build_note");
    if (!btn || btn.disabled) return;
    const was = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Building...";
    if (note) note.textContent = "Making the missing files. This takes a few seconds for each sound.";
    try {
      const got = await P.send("/api/moods/prime", {}, "POST");
      const made = (got && got.built) || {};
      const errors = Array.isArray(made.errors) ? made.errors.filter(Boolean) : [];
      const bits = [];
      if (Number.isFinite(Number(made.sounds))) bits.push(`${num(made.sounds)} sounds`);
      if (Number.isFinite(Number(made.beds))) bits.push(`${num(made.beds)} music beds`);
      await read();
      draw();
      if (errors.length) {
        if (note) note.textContent = `Some files could not be made: ${errors.join(" ")}`;
        P.toast("Some sounds could not be built.", "bad");
      } else {
        if (note) note.textContent = bits.length
          ? `Made ${bits.join(" and ")}. The lists above show what is ready now.`
          : "Done. The lists above show what is ready now.";
        P.toast("Sounds built.", "ok");
      }
    } catch (err) {
      const why = err && err.message ? String(err.message) : "";
      if (note) note.textContent = why ? `The sounds were not built: ${why}` : "The sounds were not built. The server did not say why.";
      P.toast("The sounds were not built.", "bad");
    } finally {
      btn.disabled = false;
      btn.textContent = was || "Build the missing sounds";
    }
  }

  /* ---------------------------------------------------------------- the page */
  window.PeakCut.page("sounds", {
    nav: "Audio",
    icon: "radio",
    tip: "Find, hear and keep sounds and music",
    path: "sounds",
    group: "Make",
    order: 18,
    view() {
      return `<div class="snd">
        <section class="set-sec">
          <h1 class="snd-h">Audio</h1>
          <p class="help snd-lede">Search for a sound, listen to it, and keep the ones you like. Keep means Clipstorm saves a copy on this computer, so it works without the internet. You can also like, bookmark, download or remove a kept sound.</p>
        </section>
        <div class="snd-how">
          <p><b>How a sound gets onto a clip:</b> this page only lists sounds. To put one on a clip, open the clip in My videos and press Edit audio, or pick a mood under Sound.</p>
        </div>
        <div class="row" role="group" aria-label="Jump to"><button class="btn sm" type="button" data-act="snd-jump" data-to="snd_lib">Sounds</button><button class="btn sm" type="button" data-act="snd-jump" data-to="snd_music">Music</button></div>
        <div id="snd_lib" data-sx-lib><div class="set-load">Reading your sounds...</div></div>
        <section class="set-sec" id="snd_music" style="margin-top:26px">
          <h2>Music and sounds Clipstorm makes itself</h2>
          <p class="help snd-lede">These are made on your computer, so they cost nothing and nobody else owns them. A mood is one word on a clip that picks one of these for you.</p>
          <div id="snd_body"><div class="set-load">Reading the list...</div></div>
        </section>
        <section class="set-sec" id="snd_loud">
          <h2>How loud the music is</h2>
          <ul class="help">
            <li>The music starts 14 dB below the voice, so speech stays clear.</li>
            <li>It drops further while someone is talking, then rises again in the gaps.</li>
            <li>The finished clip is levelled to about -14 LUFS, the same as the rest of Clipstorm.</li>
          </ul>
          ${hint("These are fixed in Clipstorm today, so there is nothing to change here. A saved brand can carry a default mood for every clip.")}
        </section>
        <section class="set-sec">
          <div class="row"><button class="btn" type="button" id="snd_build">Build the missing sounds</button></div>
          ${hint("Makes every file above that says Not built yet. Files that are already there are left alone, so pressing it twice costs nothing.")}
          <p class="hint" id="snd_build_note"></p>
        </section>
      </div>`;
    },
    load() {
      const lib = document.getElementById("snd_lib");
      if (lib) {
        if (snd()) snd().mount(lib, {});
        else lib.innerHTML = `<p class="err">The sound library did not load. Reload the page.</p>`;
      }
      const buildBtn = document.getElementById("snd_build");
      if (buildBtn) buildBtn.addEventListener("click", build);
      return read().then(() => {
        draw();
        const body = document.getElementById("snd_body");
        if (body) {
          body.addEventListener("click", (ev) => {
            const btn = ev.target.closest("[data-key]");
            if (!btn) return;
            const row = (rows || []).find((r) => r.id === btn.getAttribute("data-key"));
            if (row) play(row, btn);
          });
        }
      });
    },
  });

  P.add("sounds", { act: { "snd-jump"(btn) { const t = document.getElementById(btn.dataset.to); if (t && t.scrollIntoView) t.scrollIntoView({ behavior: "smooth", block: "start" }); } }, about: "The Sounds screen: find, listen to and keep sounds, and the sounds and music Clipstorm makes itself." });
})();
