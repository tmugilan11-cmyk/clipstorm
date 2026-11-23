/* Edit audio: put sounds on one clip, on a wide track you can read at a glance.
 *
 * This is where a sound is PLACED. It opens from the "Edit audio" button in the clip editor, or from the button on
 * the Sounds page, and nowhere else, so Sounds and Audio stay libraries. Three zones, left to right: the picture,
 * the track, and a column holding the clip picker and every sound already on the clip.
 *
 * How it reads, for someone who has never used it:
 *   * the video is the playhead: pause it where a sound should land, press "Add a sound here"
 *   * a picker opens with My sounds and Trending, the same Listen / Stop cards as the Sounds page
 *   * each placed sound is a flag on the track showing its name and its time (m:ss), with Listen and Remove; drag
 *     the flag sideways to move it
 *   * "Save and add to clip" saves the list and mixes it into the clip file
 *
 * A cue is `{slug, at, volume, end}`. `at` is a second of the CLIP file, which is what the track draws. `volume` is
 * dB (the server keeps -30 to +12) and `end` is where a long sound is cut; both have plain-word controls.
 *
 * "Save and add to clip" is not a full re-make: the route copies the picture and only mixes the sound, which takes a
 * few seconds and spends nothing. The clip dialog's own "Save and re-make clip" is the one that renders again.
 *
 * Ink on this sheet is measured, not picked: the words drawn on the track and the ruler use var(--dim) #A3A3A3.
 * That is 7.17:1 on the ruler's #161616 and 7.49:1 on the lane's #111111, both over the 4.5 the small text needs.
 *
 * Routes, all in `studio/api_memesound.py`:
 *   GET  /api/jobs/<j>/clips/<c>/sounds             the cues on a clip
 *   PUT  /api/jobs/<j>/clips/<c>/sounds             replace them
 *   POST /api/jobs/<j>/clips/<c>/sounds/suggest     let the AI place them
 *   POST /api/jobs/<j>/clips/<c>/sounds/hear        mix them into the file now
 *   GET  /api/memesounds/library                    what is kept (names for the flags)
 *   POST /api/memesounds/keep                       copy a web sound to this machine
 *   GET  /api/memesounds/play/<slug>                the bytes, for Listen
 * and, through the shared library in meme-timeline.js, trending, search and upload. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.page !== "function" || typeof P.add !== "function") return;

  const NAME = "audio-edit";

  P.css(NAME, `
    #main>.content:has(.aed-page){max-width:none;padding-left:16px;padding-right:16px}
    .aed-page{display:grid;gap:12px;--track:#0C0C0C;--track2:#161616;--trackline:#2A2A2A}

    .aed-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    .aed-head .ttl{display:grid;gap:2px;min-width:0}
    .aed-h{margin:0;font-size:20px;line-height:1.25;letter-spacing:-.01em;color:var(--text)}
    .aed-sub{margin:0;font-size:13px;color:var(--dim);line-height:1.45;max-width:78ch}
    .aed-head .sp{margin-left:auto}
    .aed-pick{display:grid;gap:8px;padding:12px;font-size:13px;color:var(--dim)}
    .aed-pick select{height:34px;min-width:0;width:100%;max-width:100%;padding:0 9px;border:1px solid var(--line-2);
      border-radius:var(--r-sm);background:var(--field);color:var(--text);font:inherit;font-size:13px}

    /* three zones: picture | track | column */
    .aed-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(340px,440px);
      gap:14px;align-items:start}
    .aed-left{display:grid;gap:12px;min-width:0}

    .aed-vid{border:1px solid var(--line);border-radius:var(--r);background:#000;padding:6px;display:grid;gap:6px;align-self:start}
    .aed-vid video{width:100%;max-height:min(40vh,340px);border-radius:6px;background:#000;display:block}
    .aed-vid .cap{font-size:12px;color:var(--dim);line-height:1.4;margin:0;padding:0 2px 2px}

    /* the track. The lane keeps a fixed, readable height: stretching it to the whole column turned flags into blocks. */
    .aed-mid{display:grid;gap:10px;min-width:0;align-content:start}
    .aed-mid{grid-template-rows:auto auto auto}
    .aed-tl{border:1px solid var(--line);border-radius:var(--r);background:var(--track);padding:10px;
      display:grid;gap:7px;min-width:0;grid-template-rows:auto auto auto}
    .aed-tl-top{display:flex;align-items:center;gap:9px;flex-wrap:wrap;font-size:12.5px;color:var(--dim)}
    .aed-tl-top b{color:var(--text);font-weight:600}
    .aed-tl-top .sp{margin-left:auto}
    .aed-ruler{position:relative;height:18px;border-radius:5px 5px 0 0;background:var(--track2);
      border:1px solid var(--trackline);border-bottom:0;overflow:hidden}
    .aed-ruler i{position:absolute;top:5px;bottom:0;width:1px;background:#333}
    .aed-ruler i.b{top:1px;background:#4A4A4A}
    .aed-ruler b{position:absolute;top:2px;transform:translateX(3px);font:11px/13px var(--mono,monospace);
      font-weight:500;color:var(--dim);font-variant-numeric:tabular-nums}
    .aed-lane{position:relative;height:240px;border:1px solid var(--trackline);
      border-radius:0 0 5px 5px;background:#111;overflow:hidden;touch-action:none;cursor:pointer}
    .aed-lane.empty{cursor:pointer}
    /* a placed sound: a thin line at its exact moment, and a label beside it */
    .aed-chip{position:absolute;top:0;bottom:0;width:0;border-left:2px solid var(--brand);cursor:grab;user-select:none}
    .aed-chip .aed-tag{position:absolute;left:0;width:172px;max-width:46vw;display:grid;gap:3px;padding:6px 8px;
      border:1px solid var(--brand);border-left:0;border-radius:0 7px 7px 0;background:#1F1939;color:#F5F5F5;font-size:12px;line-height:1.25}
    .aed-chip.flip .aed-tag{left:auto;right:0;border-left:1px solid var(--brand);border-right:0;border-radius:7px 0 0 7px}
    .aed-chip .t{font-weight:700;font-variant-numeric:tabular-nums;color:var(--brand-deep);font-size:12px}
    .aed-chip .n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
    .aed-chip .acts{display:flex;gap:5px;flex-wrap:wrap;align-items:center}
    .aed-chip.on{border-left-color:var(--brand-deep);border-left-width:3px}
    .aed-chip.on .aed-tag{border-color:var(--brand-deep)}
    .aed-chip.ai{border-left-color:#22D3EE}
    .aed-chip.ai .t{color:#22D3EE}
    .aed-chip.miss .aed-tag{border-style:dashed}
    .aed-chip .sx-play{height:24px;padding:0 9px 0 7px;font-size:11.5px}
    .aed-chip .sx-play svg{width:11px;height:11px}
    .aed-play{position:absolute;top:0;bottom:0;width:2px;background:#fff;pointer-events:none;opacity:.85;z-index:2}
    .aed-play::before{content:"";position:absolute;top:0;left:-4px;border:5px solid transparent;border-top-color:#fff}
    .aed-caret{position:absolute;top:0;bottom:0;width:2px;background:var(--brand-deep);pointer-events:none;display:none}
    .aed-empty{position:absolute;inset:0;display:grid;place-items:center;padding:0 22px;pointer-events:none;
      color:var(--dim);font-size:13px;line-height:1.55}
    .aed-empty b{color:var(--text);display:block;margin-bottom:6px;font-size:14px}
    .aed-empty ol{margin:0;padding-left:20px;text-align:left}
    .aed-empty li{margin:3px 0}

    /* the three things you can do, each with a sentence on what it does */
    .aed-acts{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
    .aed-act{display:grid;gap:6px;align-content:start;padding:11px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--card)}
    .aed-act.main{border-color:var(--brand-line);background:var(--brand-soft)}
    .aed-act .btn{width:100%;justify-content:center}
    .aed-act p{margin:0;font-size:12px;line-height:1.45;color:var(--dim)}
    .aed-more{display:flex;gap:7px;flex-wrap:wrap;align-items:center}
    .aed-more .sp{margin-left:auto}
    .aed-note{margin:0;font-size:13px;line-height:1.5;color:var(--dim);min-height:18px}
    .aed-note.bad{color:var(--bad)}
    .aed-note.ok{color:var(--good)}

    /* the picker that opens under the track */
    .aed-picker{border:1px solid var(--brand-line);border-radius:var(--r);background:var(--card);padding:12px;display:grid;gap:10px;min-width:0;
      position:sticky;top:8px;max-height:calc(100vh - 24px);overflow:auto;align-content:start}
    .aed-picker-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .aed-picker-head h2{margin:0;font-size:15px;color:var(--text)}
    .aed-picker-head .sp{margin-left:auto}
    .aed-picker .sx-grid{grid-template-columns:minmax(0,1fr)}
    .aed-picker .sx-card{cursor:grab}

    /* the right column: the clip, then what is on it */
    .aed-col{display:grid;gap:10px;min-width:0;align-content:start}
    .aed-box{border:1px solid var(--line);border-radius:var(--r);background:var(--card);display:grid;
      overflow:hidden;min-width:0}
    .aed-box>h3{margin:0;padding:10px 12px 6px;font-size:13.5px;font-weight:600;color:var(--text);
      display:flex;align-items:center;gap:7px}
    .aed-box>h3 .n{margin-left:auto;font-size:12px;font-weight:500;color:var(--dim);
      font-variant-numeric:tabular-nums}
    .aed-box>p{margin:0;padding:0 12px 8px;font-size:12px;color:var(--dim);line-height:1.45}

    .aed-cues{max-height:min(60vh,560px);overflow:auto;border-top:1px solid var(--line)}
    .aed-cue{display:grid;gap:6px;padding:10px 12px;border-bottom:1px solid var(--line)}
    .aed-cue:last-child{border-bottom:0}
    .aed-cue.on{background:var(--brand-soft)}
    .aed-cue .top{display:flex;align-items:center;gap:6px;min-width:0}
    .aed-cue .top b{font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .aed-cue .meta{font-size:12px;color:var(--dim);font-variant-numeric:tabular-nums}
    .aed-cue .row{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
    .aed-cue .row .sp{margin-left:auto}
    .aed-cue label{display:grid;gap:2px;font-size:11px;color:var(--dim)}
    .aed-mini{border:1px solid var(--line-2);background:var(--bg);color:var(--dim);border-radius:6px;
      padding:3px 9px;font:inherit;font-size:12px;cursor:pointer;transition:border-color .15s ease,color .15s ease}
    .aed-mini:hover{border-color:var(--brand);color:var(--brand-deep)}
    .aed-cue select{height:28px;padding:0 6px;border:1px solid var(--line-2);border-radius:6px;
      background:var(--field);color:var(--text);font:inherit;font-size:12px}
    .aed-ghost{position:fixed;z-index:99;pointer-events:none;background:#1F1939;border:1px solid var(--brand);
      border-radius:6px;color:#F5F5F5;font:12px/1.2 inherit;padding:3px 8px;opacity:.92}
    .aed-hint{font-size:12px;line-height:1.4;color:var(--dim);margin:0}
    @media (max-width:980px){.aed-body{grid-template-columns:minmax(0,1fr)}.aed-picker{position:static;max-height:none}}
    @media (max-width:760px){.aed-mini{min-height:44px}}
  `);

  /* ---- helpers ------------------------------------------------------------------------------------- */
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
  const enc = encodeURIComponent;
  const $ = (id) => document.getElementById(id);
  const known = (n) => n !== null && n !== undefined && n !== "" && isFinite(Number(n)) && Number(n) > 0;
  const secs1 = (n) => (Math.round((Number(n) || 0) * 10) / 10).toFixed(1) + "s";
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const sentence = (e, fallback) => ((e && e.message) ? String(e.message) : "") || fallback;
  const snd = () => P.snd || null;

  function read(path, opt) {
    if (typeof P.api === "function") return P.api(path, opt);
    return Promise.reject(new Error("Clipstorm is still starting. Try again in a moment."));
  }
  function write(path, body, method) {
    if (typeof P.send === "function") return P.send(path, body, method || "POST");
    return Promise.reject(new Error("Clipstorm is still starting. Try again in a moment."));
  }
  function say(text, kind) {
    if (!text) return;
    const box = $("aed_note");
    if (box) { box.textContent = text; box.className = "aed-note" + (kind ? " " + kind : ""); }
    if (kind === "bad" && typeof window.toast === "function") window.toast(text, "bad");
  }
  /* A moment on the track as m:ss. Tenths are kept in the cue; the page shows the second a person would say. */
  const MMSS = (t) => {
    const s = Math.max(0, Math.round(Number(t) || 0));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  };

  /* ---- state --------------------------------------------------------------------------------------- */
  const E = {
    clips: [], at: -1, jid: "", cid: "", secs: 0, version: 0, status: "",
    cues: [], sel: -1, dirty: false, busy: false,
    lib: [], libReady: false,
    armed: null, picker: null,
  };
  const MAX_CUES = 12;
  // How loud, in plain words. The number is dB, which is what the server keeps.
  const LOUD = [[-12, "Much quieter"], [-6, "Quieter"], [0, "Normal"], [6, "Louder"], [12, "Much louder"]];

  function stateOf() {
    try {
      if (typeof P.state === "function") return P.state() || {};
    } catch (e) { /* the shell may not have loaded yet */ }
    return {};
  }

  function allClips() {
    const jobs = Array.isArray(stateOf().jobs) ? stateOf().jobs : [];
    const out = [];
    for (const job of jobs) {
      for (const clip of job.clips || []) {
        if (!clip || clip.status !== "done") continue;
        const len = Math.max(0, (Number(clip.end) || 0) - (Number(clip.start) || 0));
        const file = String((job.source && job.source.name) || job.title || "a video");
        const t = Number(job.created) || 0;
        const day = t ? new Date(t * 1000).toLocaleString([], { day: "numeric", month: "short" }) : "";
        out.push({
          jid: String(job.id || ""), cid: String(clip.id || ""), clip, job, len,
          label: [file, String(clip.id || ""), secs1(len), day].filter(Boolean).join(" · "),
        });
      }
    }
    const same = new Map();
    for (const row of out) same.set(row.label, (same.get(row.label) || 0) + 1);
    for (const row of out) if (same.get(row.label) > 1) row.label += " · #" + row.jid.slice(-4);
    return out;
  }

  /** What a sound is called: the shelf's title, then the cue's own, then its slug in words. */
  function titleOf(cue) {
    const slug = cue && cue.slug;
    const row = E.lib.find((r) => r.slug === slug);
    if (row && row.title) return row.title;
    if (cue && cue.title) return String(cue.title);
    return String(slug || "").replace(/^mine-/, "").replace(/-/g, " ");
  }
  const onShelf = (slug) => !E.libReady || E.lib.some((r) => r.slug === slug);
  const playhead = () => {
    const v = $("aed_video");
    const t = v ? Number(v.currentTime) : 0;
    return Number.isFinite(t) ? clamp(t, 0, Math.max(0, E.secs)) : 0;
  };

  /* ---- markup -------------------------------------------------------------------------------------- */
  function pageHtml() {
    return '<div class="aed-page">'
      + '<div class="aed-head">'
      + '<button class="btn" type="button" data-act="aed-back" id="aed_back">Back to the clip</button>'
      + '<div class="ttl"><h1 class="aed-h">Edit audio</h1>'
      + '<p class="aed-sub" id="aed_sub">Choose a clip. Pause the video where a sound should land, then add one.</p></div>'
      + '<span class="sp"></span>'
      + "</div>"
      + '<div class="aed-body">'
      // LEFT: the clip and its timeline, what to do, and what is on the clip
      + '<div class="aed-left">'
      + '<div class="aed-box"><label class="aed-pick">Clip<select id="aed_pick" aria-label="Which clip"></select></label></div>'
      + '<div class="aed-vid"><video id="aed_video" controls preload="metadata" playsinline></video>'
      + '<p class="cap" id="aed_cap">No clip chosen.</p></div>'
      + '<div class="aed-mid">'
      + '<div class="aed-tl">'
      + '<div class="aed-tl-top"><b id="aed_cliplabel">The track</b><span class="sp"></span>'
      + '<span id="aed_where">No clip chosen</span></div>'
      + '<div class="aed-ruler" id="aed_ruler"></div>'
      + '<div class="aed-lane empty" id="aed_lane" role="group" aria-label="The clip\'s track. Press it to move the playhead."></div>'
      + "</div>"
      + '<div class="aed-acts">'
      + '<div class="aed-act"><button class="btn" type="button" data-act="aed-addhere">Add a sound here</button>'
      + '<p id="aed_addsay">Choose a sound on the right and press Add. It lands at the playhead, the white line on the track. You can also drag a sound onto the track.</p></div>'
      + '<div class="aed-act"><button class="btn" type="button" data-act="aed-ask">Let the AI place sounds</button>'
      + '<p>The AI reads what is said in this clip and suggests where sounds fit. You see its picks first; nothing changes until you save.</p></div>'
      + '<div class="aed-act main"><button class="btn primary" type="button" data-act="aed-savemix">Save and add to clip</button>'
      + '<p>Saves your sounds, then mixes them into the clip. The picture is copied, not made again, so it takes a few seconds.</p></div>'
      + "</div>"
      + '<div class="aed-more">'
      + '<button class="btn sm" type="button" data-act="aed-save" title="Keep the list without changing the clip file yet">Save only</button>'
      + '<button class="btn ghost sm" type="button" data-act="aed-preview" title="Play the clip from one second before the first sound">Play from the first sound</button>'
      + "</div>"
      + '<p class="aed-note" id="aed_note">Reading this clip...</p>'
      + "</div>"
      + '<div class="aed-box"><h3>Sounds on this clip<span class="n" id="aed_count"></span></h3>'
      + '<p id="aed_sum">Nothing on this clip yet.</p>'
      + '<div class="aed-cues" id="aed_cues"></div></div>'
      + "</div>"
      // RIGHT: the sound panel. Search first, popular sounds listed first, then My sounds.
      + '<aside class="aed-picker" id="aed_picker" aria-label="Sounds to add">'
      + '<div class="aed-picker-head"><h2 id="aed_pickh">Sounds</h2></div>'
      + '<p class="aed-hint" id="aed_pickhint">Search, press Listen to hear one, then Add. The sound goes on the track at the playhead, or drag a card onto the track.</p>'
      + '<div id="aed_lib"></div></aside>'
      + "</div></div>";
  }

  /* ---- the picker ---------------------------------------------------------------------------------- */
  function readPicker() {
    const sel = $("aed_pick");
    if (!sel) return;
    sel.innerHTML = E.clips.length
      ? E.clips.map((c, i) => '<option value="' + i + '"' + (i === E.at ? " selected" : "") + ">"
        + esc(c.label) + "</option>").join("")
      : '<option value="-1">No finished clip yet</option>';
  }

  async function open(index) {
    const row = E.clips[index];
    if (!row) {
      say("You have no finished clip yet. Make one in My videos, then come back.", "bad");
      return;
    }
    E.at = index;
    E.jid = row.jid;
    E.cid = row.cid;
    E.secs = row.len;
    E.sel = -1;
    E.cues = [];
    E.dirty = false;
    readPicker();
    const sub = $("aed_sub");
    if (sub) sub.textContent = row.label;
    const label = $("aed_cliplabel");
    if (label) label.textContent = "The track";
    setVideo(row);
    drawWhere();
    drawRuler();
    drawTrack();
    drawCues();
    await readCues();
    await readLib();
  }

  function setVideo(row) {
    const v = $("aed_video");
    if (!v) return;
    const clip = row.clip || {};
    const file = clip.file || (row.clip && row.clip.file);
    if (!file) {
      v.removeAttribute("src");
      v.load();
      const cap = $("aed_cap");
      if (cap) cap.textContent = "This clip has no finished file yet.";
      return;
    }
    v.src = "/media/" + enc(row.jid) + "/" + enc(String(file)) + "?v=" + (Number(clip.version) || 0);
    try { v.load(); } catch (e) { /* the browser will try again on play */ }
    const cap = $("aed_cap");
    if (cap) cap.textContent = String(file) + " · " + secs1(E.secs);
  }

  async function readCues() {
    if (!E.jid || !E.cid) return;
    try {
      const got = await read("/api/jobs/" + enc(E.jid) + "/clips/" + enc(E.cid) + "/sounds");
      const clip = (got && got.clip) || {};
      E.cues = Array.isArray(clip.cues) ? clip.cues : [];
      E.version = Number(clip.version) || 0;
      E.status = String(clip.status || "");
      if (Number(clip.seconds)) E.secs = Number(clip.seconds);
      E.dirty = false;
      const sum = $("aed_sum");
      if (sum) {
        sum.textContent = clip.sounds_line
          || (E.cues.length ? E.cues.length + (E.cues.length === 1 ? " sound." : " sounds.") : "Nothing on this clip yet.");
      }
      say(E.cues.length
        ? "Drag a flag sideways to move it. Press Save and add to clip when you are happy."
        : "This clip has no sounds yet. Follow the three steps on the track.");
    } catch (e) {
      say("The sounds on this clip could not be read: " + sentence(e, "the server did not say why."), "bad");
    }
    drawRuler();
    drawTrack();
    drawCues();
  }

  async function readLib() {
    // The sounds kept on this machine. libReady says the list was read, which is how an empty list is told apart
    // from one that was never seen.
    try {
      const got = await read("/api/memesounds/library");
      E.lib = Array.isArray(got.sounds) ? got.sounds : [];
      E.libReady = true;
    } catch (e) {
      E.lib = [];
      E.libReady = false;
      say("Your kept sounds could not be read: " + sentence(e, "the server did not say why."), "bad");
    }
    drawTrack();
    drawCues();
  }

  /* ---- drawing the track --------------------------------------------------------------------------- */
  function drawWhere() {
    const where = $("aed_where");
    if (where) where.textContent = E.jid ? "Playhead " + MMSS(playhead()) + " of " + MMSS(E.secs) : "No clip chosen";
    const add = $("aed_addsay");
    if (add && E.jid) add.textContent = "Choose a sound on the right and press Add. It lands at the playhead (" + MMSS(playhead()) + "), the white line on the track. You can also drag a sound onto the track.";
    const head = $("aed_pickh");
    if (head) head.textContent = "Sounds · adds at " + MMSS(playhead());
    const pl = $("aed_play");
    if (pl) pl.style.left = pctOf(playhead()) + "%";
  }

  function drawRuler() {
    const box = $("aed_ruler");
    if (!box) return;
    const total = Math.max(0.1, E.secs);
    const step = total <= 15 ? 1 : total <= 45 ? 5 : 10;
    const out = [];
    for (let t = 0; t <= total + 0.001; t += step) {
      const pct = clamp((t / total) * 100, 0, 100);
      const big = Math.abs(t % (step * 2)) < 0.001;
      out.push('<i class="' + (big ? "b" : "") + '" style="left:' + pct + '%"></i>');
      if (big) out.push('<b style="left:' + pct + '%">' + MMSS(t) + "</b>");
    }
    box.innerHTML = out.join("");
  }

  const pctOf = (t) => (E.secs > 0 ? clamp((Number(t) / E.secs) * 100, 0, 100) : 0);

  function emptySteps() {
    if (!E.jid) return '<p class="aed-empty"><span>No clip chosen yet. Pick one on the right.</span></p>';
    return '<div class="aed-empty"><div><b>No sounds on this clip yet. Three steps:</b><ol>'
      + "<li>Play the video and pause it where a sound should land.</li>"
      + "<li>Press Add a sound here and pick one.</li>"
      + "<li>Press Save and add to clip.</li></ol></div></div>";
  }

  function chipHtml(c, i) {
    const start = pctOf(c.at);
    const name = titleOf(c);
    const miss = !onShelf(c.slug);
    const flip = start > 62;
    const row = (i % 3) * 76 + 8;
    const s = snd();
    const listen = miss ? '<button type="button" class="aed-mini" data-chipact="keep" data-slug="' + esc(c.slug) + '">Keep it</button>'
      : (s ? s.playBtn("cue" + i + ":" + c.slug, name, s.playUrl(c.slug)).replace('data-sx="hear"', 'data-chipact="hear" data-i="' + i + '"') : "");
    return '<div class="aed-chip' + (i === E.sel ? " on" : "") + (c.ai ? " ai" : "") + (miss ? " miss" : "") + (flip ? " flip" : "")
      + '" data-chip="' + i + '" style="left:' + start + '%" title="' + esc(name) + " at " + MMSS(c.at) + '">'
      + '<div class="aed-tag" style="top:' + row + 'px">'
      + '<span class="t">' + MMSS(c.at) + (c.ai ? " · AI" : "") + "</span>"
      + '<span class="n">' + esc(name) + "</span>"
      + '<span class="acts">' + listen
      + '<button type="button" class="aed-mini" data-chipact="remove" data-i="' + i + '">Remove</button></span>'
      + "</div></div>";
  }

  function drawTrack() {
    const lane = $("aed_lane");
    if (!lane) return;
    lane.classList.toggle("empty", !E.cues.length);
    lane.innerHTML = (E.cues.length ? "" : emptySteps())
      + E.cues.map(chipHtml).join("")
      + '<span class="aed-caret" id="aed_caret"></span>'
      + '<span class="aed-play" id="aed_play" style="left:' + pctOf(playhead()) + '%"></span>';
    const s = snd();
    if (s && lane.querySelector(".sx-play")) s.hush();
  }

  function loudSelect(i, vol) {
    const opts = LOUD.slice();
    if (!opts.some(([v]) => v === vol)) { opts.push([vol, (vol > 0 ? "+" : "") + vol + " dB"]); opts.sort((a, b) => a[0] - b[0]); }
    return '<label>How loud<select data-vol="' + i + '" aria-label="How loud">'
      + opts.map(([v, t]) => '<option value="' + v + '"' + (v === vol ? " selected" : "") + ">" + esc(t) + "</option>").join("")
      + "</select></label>";
  }

  function drawCues() {
    const box = $("aed_cues");
    if (!box) return;
    const count = $("aed_count");
    if (count) count.textContent = E.cues.length ? E.cues.length + " of " + MAX_CUES : "";
    if (!E.cues.length) {
      box.innerHTML = '<p class="aed-hint" style="padding:14px 12px">Nothing yet. Each sound you add shows here with its time, how loud it is, and Listen and Remove.</p>';
      return;
    }
    const s = snd();
    box.innerHTML = E.cues.map((c, i) => {
      const vol = Math.round(Number(c.volume) || 0);
      const end = Number(c.end) || 0;
      const name = titleOf(c);
      const miss = !onShelf(c.slug);
      const hearBtn = miss ? "" : (s ? s.playBtn("row" + i + ":" + c.slug, name, s.playUrl(c.slug)).replace('data-sx="hear"', 'data-act="aed-hear" data-i="' + i + '"') : "");
      return '<div class="aed-cue' + (i === E.sel ? " on" : "") + '">'
        + '<div class="top"><b title="' + esc(name) + '">' + esc(name) + "</b>"
        + (c.ai ? '<span class="aed-hint" style="margin-left:auto">from the AI</span>' : "")
        + "</div>"
        + '<span class="meta">At ' + MMSS(c.at) + " of " + MMSS(E.secs)
        + (end ? " · stops after " + secs1(end) : "") + "</span>"
        + (miss ? '<span class="aed-hint">This sound is not on this machine yet, so it cannot play or be mixed.</span>' : "")
        + '<div class="row">' + loudSelect(i, vol)
        + '<label>Plays for<select data-end="' + i + '" aria-label="How long it plays">'
        + [["", "The whole sound"], ["0.5", "0.5 seconds"], ["1", "1 second"], ["2", "2 seconds"], ["3", "3 seconds"]]
          .map(([v, t]) => '<option value="' + v + '"' + (String(end) === v || (!end && !v) ? " selected" : "") + ">" + t + "</option>").join("")
        + "</select></label></div>"
        + '<div class="row">' + hearBtn
        + (miss ? '<button class="aed-mini" type="button" data-act="aed-keep" data-slug="' + esc(c.slug) + '">Keep it on this machine</button>' : "")
        + '<span class="sp"></span>'
        + '<button class="aed-mini" type="button" data-act="aed-take" data-i="' + i + '">Remove</button>'
        + "</div></div>";
    }).join("");
  }

  /* ---- placing ------------------------------------------------------------------------------------- */
  function addAt(slug, at) {
    if (!E.jid) { say("Choose a clip first.", "bad"); return; }
    if (E.cues.length >= MAX_CUES) {
      say("That is the most one clip can hold (" + MAX_CUES + " sounds). Remove one first.", "bad");
      return;
    }
    const when = clamp(Math.round(Number(at) * 20) / 20, 0, Math.max(0, E.secs - 0.1));
    const tooClose = E.cues.some((c) => Math.abs(Number(c.at) - when) < 0.35);
    if (tooClose) {
      say("Two sounds that close would land on top of each other. Move the playhead a little and try again.", "bad");
      return;
    }
    E.cues.push({ slug, at: when, volume: 0 });
    E.cues.sort((a, b) => Number(a.at) - Number(b.at));
    E.sel = E.cues.findIndex((c) => Number(c.at) === when && c.slug === slug);
    E.dirty = true;
    const row = E.lib.find((r) => r.slug === slug);
    say((row && row.title ? row.title : slug) + " added at " + MMSS(when) + ". Press Save and add to clip when you are done.", "ok");
    drawTrack();
    drawCues();
  }

  async function save() {
    if (!E.jid || E.busy) return;
    E.busy = true;
    try {
      const got = await write("/api/jobs/" + enc(E.jid) + "/clips/" + enc(E.cid) + "/sounds",
        { cues: E.cues.map((c) => ({ slug: c.slug, at: c.at, volume: c.volume, end: c.end || 0 })) }, "PUT");
      const clip = (got && got.clip) || {};
      // The server tidies the list (order, volume limits, the shortest gap), so the page takes ITS answer
      // rather than assuming the list it sent survived unchanged.
      if (Array.isArray(clip.cues)) E.cues = clip.cues;
      // The list was replaced wholesale, so a highlight aimed at the old order would point at a
      // different sound; nothing is selected after a save.
      E.sel = -1;
      E.version = Number(clip.version) || E.version;
      E.dirty = false;
      const sum = $("aed_sum");
      if (sum && clip.sounds_line) sum.textContent = clip.sounds_line;
      say((clip.sounds_line || "Saved.") + " The clip file has not changed yet. Press Save and add to clip to mix them in.", "ok");
    } catch (e) {
      say(sentence(e, "Those sounds could not be saved."), "bad");
    } finally {
      E.busy = false;
    }
    drawTrack();
    drawCues();
  }

  async function mix() {
    if (!E.jid || E.busy) return;
    if (E.dirty) {
      // Mixing reads the saved list on the server, so unsaved work would be silently left out.
      await save();
      if (E.dirty) return;
    }
    E.busy = true;
    say("Mixing the sounds into the clip. This takes a few seconds.");
    try {
      const got = await write("/api/jobs/" + enc(E.jid) + "/clips/" + enc(E.cid) + "/sounds/hear", {});
      const clip = (got && got.clip) || {};
      E.version = Number(clip.version) || (E.version + 1);
      say("Done. The sounds are mixed into the clip. The picture was copied, so nothing else changed.", "ok");
      // The file is the same path, so the player must be told to fetch it again.
      const v = $("aed_video");
      if (v && v.src) {
        const base = v.src.split("?")[0];
        v.src = base + "?v=" + E.version + "&mx=" + Date.now();
        try { v.load(); } catch (e) { /* the browser will retry on play */ }
      }
    } catch (e) {
      say(sentence(e, "The sounds could not be mixed into the clip."), "bad");
    } finally {
      E.busy = false;
    }
  }

  async function saveAndMix() {
    if (!E.jid || E.busy) return;
    await save();           // saves what is on the track, then
    if (E.dirty) return;    // a failed save stops here, with its own sentence
    await mix();
  }

  async function ask() {
    if (!E.jid || E.busy) return;
    // The AI's picks replace what is on the track (a cue missing from the saved list is removed from
    // the clip), so a track that carries sounds placed by hand is confirmed away before the slow call
    // is made. window.ask is the shell's own dialog; the local ask() shadows that name in here.
    const hand = E.cues.filter((c) => !c.ai).length;
    if (hand && typeof window.ask === "function") {
      const ok = await window.ask("Let the AI place sounds",
        "Replace the " + hand + " sound" + (hand === 1 ? "" : "s") + " on the track with the AI's picks?"
        + " Sounds you placed by hand come off the track.", "Use the AI's picks");
      if (!ok) return;
    }
    E.busy = true;
    say("Asking the AI where sounds fit. A slow answer can take a minute.");
    try {
      const got = await write("/api/jobs/" + enc(E.jid) + "/clips/" + enc(E.cid) + "/sounds/suggest", {});
      const cues = Array.isArray(got.cues) ? got.cues : [];
      if (!cues.length) {
        say(got.why || "The AI did not find a moment that earns a sound.", "");
      } else {
        // The answer arrives as cues with a slug already on the shelf, or as sounds that still need a download.
        E.cues = cues.map((c) => ({
          slug: c.slug, at: Number(c.at) || 0, volume: Number(c.volume) || 0,
          end: Number(c.end) || 0, ai: true, title: c.title || "",
        }));
        // The list was replaced wholesale, so a highlight aimed at the old order would point at a
        // different sound; nothing is selected after an ask.
        E.sel = -1;
        E.dirty = true;
        const need = Array.isArray(got.need) ? got.need : [];
        say((got.why || cues.length + " sounds chosen.") + (need.length
          ? " " + need.length + " of them are not on this machine yet: press Keep it next to them before you save."
          : " Look them over, then press Save and add to clip."), "");
      }
    } catch (e) {
      say(sentence(e, "The AI could not answer just now. Your sounds were not changed."), "bad");
    } finally {
      E.busy = false;
    }
    drawTrack();
    drawCues();
  }

  /* Listen to one placed sound, at the loudness chosen, and move the video to its moment. */
  function hearHere(btn, index) {
    const cue = E.cues[index];
    if (!cue) return;
    const v = $("aed_video");
    if (v && Number.isFinite(Number(cue.at))) {
      try { v.currentTime = Math.max(0, Number(cue.at)); } catch (e) { /* seeking before metadata lands */ }
    }
    const s = snd();
    if (!s) { say("The sound player did not load. Reload the page.", "bad"); return; }
    // A sound that is not kept has no file here: say so instead of blaming the browser.
    if (!onShelf(cue.slug)) { say("That sound is not on this machine yet. Press Keep it next to it first.", "bad"); return; }
    const vol = clamp(Math.pow(10, (Number(cue.volume) || 0) / 20), 0, 1);
    s.hear(btn, s.playUrl(cue.slug), (t) => say(t, "bad"), vol);
  }

  async function keep(slug) {
    try {
      await write("/api/memesounds/keep", { slug });
      await readLib();
      say("Kept on this machine. It can play and be mixed now.", "ok");
    } catch (e) {
      say(sentence(e, "That sound could not be kept."), "bad");
    }
  }

  function removeAt(i) {
    if (!Number.isInteger(i) || i < 0 || i >= E.cues.length) return;
    E.cues.splice(i, 1);
    E.sel = -1;
    E.dirty = true;
    say("Removed. Press Save and add to clip to keep that.", "");
    drawTrack();
    drawCues();
  }

  /* ---- the sound panel on the right ---------------------------------------------------------------- */
  function mountPanel() {
    const host = $("aed_lib");
    if (!host) return;
    const s = snd();
    if (!s) { host.innerHTML = '<p class="err">The sound library did not load. Reload the page.</p>'; return; }
    // Trending is listed first (the web catalogue's most played), then My sounds. Add keeps a web sound first.
    E.picker = s.mount(host, {
      pick: true, mineFirst: false, upload: false, addWord: "Add",
      onPick: async (slug) => { await readLib(); addAt(slug, playhead()); },
    });
  }

  /** "Add a sound here" points the person at the panel: it scrolls there and focuses the search box. */
  function openPicker() {
    if (!E.jid) { say("Choose a clip first.", "bad"); return; }
    const box = $("aed_picker");
    if (!box) return;
    try { box.scrollIntoView({ block: "nearest", behavior: "smooth" }); } catch (e) { /* older browsers */ }
    const q = box.querySelector('[data-box="q"]');
    if (q) q.focus();
    say("Search or pick a sound on the right, then press Add.");
  }

  function closePicker() {
    const s = snd();
    if (s) s.hush();
  }

  /* ---- dragging ------------------------------------------------------------------------------------ */
  function wireTrack() {
    const lane = $("aed_lane");
    if (!lane || lane.dataset.wired === "1") return;
    lane.dataset.wired = "1";
    let hold = null;            // the flag being dragged, or null

    const timeAt = (x) => {
      const b = lane.getBoundingClientRect();
      return clamp(((x - b.left) / Math.max(1, b.width)) * E.secs, 0, E.secs);
    };

    lane.addEventListener("pointerdown", (ev) => {
      // A button inside a flag is a click, not the start of a drag.
      if (ev.target.closest("button")) return;
      const chip = ev.target.closest("[data-chip]");
      if (chip) {
        ev.preventDefault();
        const i = Number(chip.getAttribute("data-chip"));
        E.sel = i;
        hold = { i, moved: false };
        chip.classList.add("on");
        try { chip.setPointerCapture(ev.pointerId); } catch (e) { /* synthetic pointers cannot be captured */ }
        return;
      }
      // The empty track is a scrubber: pressing it moves the playhead there.
      const v = $("aed_video");
      if (v && E.secs > 0) {
        try { v.currentTime = timeAt(ev.clientX); } catch (e) { /* metadata not loaded yet */ }
        drawWhere();
      }
    });

    lane.addEventListener("pointermove", (ev) => {
      if (!hold || E.sel < 0) return;
      hold.moved = true;
      const at = Math.round(timeAt(ev.clientX) * 20) / 20;
      E.cues[E.sel].at = clamp(at, 0, Math.max(0, E.secs - 0.1));
      E.dirty = true;
      // No full redraw while the finger is down: rebuilding the lane would detach the flag mid-gesture.
      const chip = lane.querySelector('[data-chip="' + E.sel + '"]');
      if (chip) {
        chip.style.left = pctOf(E.cues[E.sel].at) + "%";
        const t = chip.querySelector(".t");
        if (t) t.textContent = MMSS(E.cues[E.sel].at);
      }
      const where = $("aed_where");
      if (where) where.textContent = "Moving to " + MMSS(E.cues[E.sel].at) + " of " + MMSS(E.secs);
    });

    const up = () => {
      if (!hold) return;
      const moved = hold.moved;
      hold = null;
      if (moved) {
        E.cues.sort((a, b) => Number(a.at) - Number(b.at));
        E.sel = -1;
        say("Moved. Press Save and add to clip to keep that.", "");
      }
      drawTrack();
      drawCues();
      drawWhere();
    };
    lane.addEventListener("pointerup", up);
    lane.addEventListener("pointercancel", up);

    // Buttons inside the flags: Listen, Keep it, Remove.
    lane.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-chipact]");
      if (!b) return;
      const act = b.getAttribute("data-chipact");
      const i = Number(b.getAttribute("data-i"));
      if (act === "hear") hearHere(b, i);
      else if (act === "remove") removeAt(i);
      else if (act === "keep") keep(b.getAttribute("data-slug"));
    });

    // The video moves the playhead line as it plays or is scrubbed.
    const v = $("aed_video");
    if (v) ["timeupdate", "seeked", "loadedmetadata"].forEach((n) => v.addEventListener(n, drawWhere));
  }

  /* Dragging a card from the picker onto the track places it where it is dropped. */
  function wireDrop() {
    const host = $("aed_picker");
    if (!host || host.dataset.wired === "1") return;
    host.dataset.wired = "1";
    let ghost = null, slugHeld = "", nameHeld = "", startAt = null;

    host.addEventListener("pointerdown", (ev) => {
      const card = ev.target.closest(".sx-card[data-slug]");
      if (!card || ev.target.closest("button, a, input, select")) return;
      slugHeld = card.getAttribute("data-slug");
      const nm = card.querySelector(".sx-nm b");
      nameHeld = nm ? nm.textContent : slugHeld;
      startAt = { x: ev.clientX, y: ev.clientY };
      ghost = null;
    });

    document.addEventListener("pointermove", (ev) => {
      if (!slugHeld || !startAt) return;
      if (!ghost) {
        if (Math.abs(ev.clientX - startAt.x) + Math.abs(ev.clientY - startAt.y) < 8) return;   // a click, not a drag
        ghost = document.createElement("div");
        ghost.className = "aed-ghost";
        ghost.textContent = nameHeld;
        document.body.appendChild(ghost);
        const lane = $("aed_lane");
        if (lane) lane.classList.add("armed");
      }
      ghost.style.left = ev.clientX + 12 + "px";
      ghost.style.top = ev.clientY + 12 + "px";
    });

    document.addEventListener("pointerup", async (ev) => {
      if (!slugHeld) return;
      const slug = slugHeld;
      const dragged = !!ghost;
      if (ghost) { ghost.remove(); ghost = null; }
      slugHeld = ""; startAt = null;
      const lane = $("aed_lane");
      if (lane) lane.classList.remove("armed");
      if (!dragged || !lane) return;
      const b = lane.getBoundingClientRect();
      const inside = ev.clientX >= b.left && ev.clientX <= b.right && ev.clientY >= b.top - 8 && ev.clientY <= b.bottom + 8;
      if (!inside) return;
      const at = clamp(((ev.clientX - b.left) / Math.max(1, b.width)) * E.secs, 0, E.secs);
      // A web sound must be on this machine before a clip can carry it.
      if (E.picker && !E.picker.kept().has(slug)) {
        const ok = await E.picker.keep(slug, nameHeld);
        if (!ok) return;
      }
      await readLib();
      addAt(slug, at);
    });
  }

  /* ---- page ---------------------------------------------------------------------------------------- */
  P.page("audio-edit", {
    // The label is only ever read by the test that insists every page owns a distinct one: this page is `hidden`,
    // so no menu row is drawn for it and the only way in is the "Edit audio" button in the clip editor.
    nav: "Edit audio",
    icon: "music",
    tip: "Put sounds on one clip, on a wide track",
    path: "audio-edit",
    group: "Make",
    order: 37,
    hidden: true,
    view() { return pageHtml(); },
    async load() {
      E.picker = null;          // the page was redrawn, so the old panel is gone
      E.clips = allClips();
      let first = E.clips.length ? 0 : -1;
      // The clip editor hands over the clip it was showing, so "Edit audio" opens THAT clip.
      const from = stateOf().audioFrom;
      if (!(from && from.jid && from.cid)) {
        // An old link: no clip came with it, so say where to start instead of showing an empty editor.
        const pg = document.querySelector(".aed-page");
        if (pg) pg.innerHTML = '<div class="aed-head"><div class="ttl"><h1 class="aed-h">Edit audio</h1>'
          + '<p class="aed-sub">Open a clip in My videos and press Edit audio.</p></div></div>'
          + '<p class="aed-sub">Sounds are placed on one clip, so this editor opens from the clip itself (the Sound tab in the clip editor).</p>'
          + '<button class="btn primary" type="button" data-act="aed-tovideos">Go to My videos</button>';
        return;
      }
      {
        // audioFrom names the clip the editor was showing: that row is the one opened
        const want = E.clips.findIndex((c) => c.jid === String(from.jid) && c.cid === String(from.cid));
        if (want >= 0) first = want;
      }
      readPicker();
      mountPanel();
      wireTrack();
      wireDrop();
      if (first < 0) {
        drawRuler();
        drawTrack();
        drawCues();
        say("You have no finished clip yet. Make one in My videos, then come back.", "bad");
        return;
      }
      await open(first);
    },
  });

  P.add("audio-edit", {
    about: "Edit audio: a wide track for putting sounds on one clip.",
    act: {
      "aed-back"() {
        const f = stateOf().audioFrom;
        stateOf().audioFrom = null;
        if (typeof go === "function") go("library");
        if (f && f.jid && f.cid && typeof openClip === "function") openClip(f.jid, f.cid);
      },
      "aed-tovideos"() { if (typeof go === "function") go("library"); },
      "aed-ask"() { ask(); },
      "aed-save"() { save(); },
      "aed-mix"() { mix(); },
      "aed-savemix"() { saveAndMix(); },
      "aed-addhere"() { openPicker(); },
      "aed-closepick"() { closePicker(); },
      "aed-take"(btn) { removeAt(Number(btn.dataset.i)); },
      "aed-hear"(btn) { hearHere(btn, Number(btn.dataset.i)); },
      "aed-keep"(btn) { keep(btn.dataset.slug); },
      "aed-preview"() {
        // Play the clip from where the first cue sits, so the person hears it in place.
        const v = $("aed_video");
        if (!v) return;
        if (!E.cues.length) { say("Nothing on this clip yet. Add a sound first."); return; }
        try {
          v.currentTime = Math.max(0, Number(E.cues[0].at) - 1);
          v.play().catch(() => say("The browser would not play here.", "bad"));
        } catch (e) { say("The browser would not play here.", "bad"); }
      },
    },
    keys(e) {
      if (!document.querySelector(".aed-page")) return false;
      const typing = document.activeElement
        && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName || "");
      if (typing) return false;
      if ((e.key === "Delete" || e.key === "Backspace") && E.sel >= 0 && E.cues[E.sel]) {
        removeAt(E.sel);
        return true;
      }
      return false;
    },
  });

  // The clip picker and the loudness / length controls are plain fields, so they are wired by delegation.
  document.addEventListener("change", (e) => {
    const t = e.target;
    if (!t || !document.querySelector(".aed-page")) return;
    if (t.id === "aed_pick") {
      const i = Number(t.value);
      if (Number.isInteger(i) && i >= 0) { closePicker(); open(i); }
      return;
    }
    if (t.dataset && t.dataset.vol != null) {
      const i = Number(t.dataset.vol);
      if (E.cues[i]) {
        E.cues[i].volume = Number(t.value) || 0;
        E.dirty = true;
        say("Loudness changed. Press Save and add to clip to keep that.", "");
      }
    }
    if (t.dataset && t.dataset.end != null) {
      const i = Number(t.dataset.end);
      if (E.cues[i]) {
        E.cues[i].end = Number(t.value) || 0;
        E.dirty = true;
        say("Length changed. Press Save and add to clip to keep that.", "");
        drawCues();
      }
    }
  });
})();
