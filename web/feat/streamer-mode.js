/* Streamer clipping: turn a finished video into clips, with the Grand Theft Auto VI preset.
 *
 * Recording a stream that is on air (start, stop, clip the last seconds, watching what it does) now lives on
 * the Live page, so this page no longer has a copy of it: one card sends the person there. What stays here is
 * what the Live page does not do: clip a finished video from its link, and the GTA 6 preset.
 *
 * It talks to routes that already exist: /api/jobs, /api/preview, /api/brand and /api/status.
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});

  P.css("streamer-mode", `
    .pcstr{max-width:900px}
    .pcstr-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--text);margin:0 0 6px}
    .pcstr-lede{margin:0 0 18px;max-width:64ch;color:var(--dim);font-size:13px;line-height:1.55}
    .pcstr-modes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 8px}
    .pcstr-mode{display:grid;grid-template-columns:20px 1fr auto;gap:2px 12px;align-items:start;text-align:left;
      padding:14px 15px 15px;border:1px solid var(--line-2);border-radius:var(--r-lg);background:var(--bg);
      color:var(--text);font:inherit;cursor:pointer;transition:border-color .18s ease,background-color .18s ease}
    .pcstr-mode:hover{border-color:var(--brand-line);background:var(--brand-soft)}
    .pcstr-mode[aria-pressed="true"]{border-color:var(--brand);background:var(--brand-soft)}
    .pcstr-mode svg{width:20px;height:20px;fill:currentColor;color:var(--brand-deep);margin-top:1px}
    .pcstr-mode .pcstr-txt{display:grid;gap:4px;min-width:0}
    .pcstr-mode .pcstr-txt b{font-size:14px;line-height:1.35;color:var(--text)}
    .pcstr-mode .pcstr-txt .e{font-size:12.5px;line-height:1.5;color:var(--dim)}
    /* The GTA card spans the row so it reads as the special mode. It used to paint the pressed colours all the time,
       so it looked chosen even when Live was the mode in force - the visible half of "it does not toggle". Only the
       border says "special" while it is off; the pressed rule above is what makes it look chosen. */
    .pcstr-mode.gta{border-color:var(--brand-line)}
    .pcstr-mode.gta .pcstr-txt b{font-size:15px}
    .pcstr-chip{grid-column:3;align-self:start;font-size:11px;font-weight:600;letter-spacing:.02em;
      padding:2px 8px;border-radius:999px;border:1px solid var(--brand-line);background:var(--bg);color:var(--brand-deep);white-space:nowrap}
    .pcstr-foot{margin:0;font-size:12px;color:var(--faint)}
    .pcstr-form{margin:18px 0 0;padding-top:16px;border-top:1px solid var(--line)}
    .pcstr-blurb{margin:0 0 14px;max-width:62ch;font-size:13px;line-height:1.55;color:var(--dim)}
    .pcstr-blurb b{color:var(--text);font-weight:600}
    .pcstr-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 14px}
    .pcstr-f{display:grid;gap:5px;align-content:start;min-width:0}
    .pcstr-f.wide{grid-column:1/-1}
    .pcstr-f label{font-size:12px;font-weight:600;color:var(--dim)}
    .pcstr-f input,.pcstr-f select{height:38px;padding:0 10px;border:1px solid var(--line-2);border-radius:var(--r-sm);
      background:var(--bg);color:var(--text);font:inherit;font-size:14px;min-width:0;width:100%;box-sizing:border-box}
    .pcstr-f input:focus-visible,.pcstr-f select:focus-visible,
    .pcstr-mode:focus-visible,.pcstr-ck input:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
    .pcstr-f .hint{margin:0}
    .pcstr-ck{display:grid;grid-template-columns:16px 1fr;gap:10px;align-items:start;padding:11px 12px;
      border:1px solid var(--line);border-radius:var(--r-sm);background:var(--muted)}
    .pcstr-ck input{margin:3px 0 0}
    .pcstr-ck label{font-weight:600;font-size:13px;color:var(--text)}
    .pcstr-ck .hint{margin:4px 0 0;grid-column:2}
    .pcstr-sum{margin:14px 0 0;padding:10px 12px;border:1px solid var(--brand-line);border-radius:var(--r-sm);
      background:var(--brand-soft);color:var(--text);font-size:13px;font-weight:600;line-height:1.5}
    .pcstr-act{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:14px 0 0}
    @media (max-width:680px){
      .pcstr-h{font-size:20px}
      .pcstr-modes{grid-template-columns:1fr}
      .pcstr-grid{grid-template-columns:1fr}
      .pcstr-mode{grid-template-columns:20px 1fr}
      .pcstr-mode .pcstr-chip{grid-column:2;justify-self:start}
    }
  `);

  /* ---- small helpers, local to this file ------------------------------------------------------------ */
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const at = (id) => document.getElementById(id);
  const stateOf = () => { try { return (P.state && P.state()) || {}; } catch { return {}; } };
  const styleMap = () => { const s = stateOf(); return (s.status && s.status.styles) || {}; };
  const styleLabel = (k) => styleMap()[k] || (k === "beast" ? "Beast" : String(k || ""));
  const int = (v, fallback) => { const n = Math.round(Number(v)); return Number.isFinite(n) ? n : fallback; };
  const sentence = (err, fallback) => {
    const text = err && err.message ? String(err.message) : "";
    return text.trim() || fallback;
  };
  const say = (text) => { const box = at("str_err"); if (box) box.innerHTML = text ? `<p class="err">${esc(text)}</p>` : ""; };

  /* ---- the cards ------------------------------------------------------------------------------------ */
  // `line` is the one sentence on the card. `blurb` is the paragraph the form itself starts with, so the
  // mode explains what it is about to do before any field asks anything. The Live card is not a mode: it
  // is a way to the Live page, where recording a stream that is on air is done.
  const MODES = [
    {
      k: "video", icon: "film", nav: "Clip a finished video",
      line: "Paste the link of a video that has already ended and Clipstorm cuts the best moments out of it.",
      blurb: "<b>Clip a finished video.</b> Paste the link of a stream recording or any other video that is no longer on air. A link that is still live is sent to the Live page instead.",
    },
    {
      k: "gta", icon: "crown", nav: "GTA 6 mode", chip: "Special",
      line: "Grand Theft Auto VI: huge captions, short clips, the menu screen trimmed off.",
      blurb: "<b>GTA 6 mode.</b> Set up for Grand Theft Auto VI gameplay: a chase or a heist peaks in seconds, so the clips are short, the captions are huge, and the first 8 seconds are dropped.",
    },
  ];
  const modeInfo = (k) => MODES.find((m) => m.k === k) || MODES[0];

  // No Grand Theft Auto word list exists in the research folder (docs/research holds the OpusClip pages, and
  // the only GTA note there names moment types but no words), so these are the starting words, kept in an
  // editable box. The page never sends them: PeakCut reads hook words from the saved brand.
  const GTA_HOOKS = "wanted level, police chase, crash, heist, WASTED, BUSTED";

  // What each mode starts with. Switching modes refills these, so the numbers always match the reason
  // printed under them. The link box is the only field that survives a switch.
  const START = {
    video: { clips: 6, min: 15, max: 60, style: "", captions: true, skip: false, chase: false, chat: "normal", minutes: 30, hooks: GTA_HOOKS },
    gta: { clips: 6, min: 12, max: 45, style: "beast", captions: true, skip: true, chase: true, chat: "normal", minutes: 30, hooks: GTA_HOOKS },
  };

  let mode = "video";
  const draft = {
    url: "", clips: 6, min: 15, max: 60, style: "", captions: true,
    chat: "normal", minutes: 30, hooks: GTA_HOOKS, skip: false, chase: false,
  };

  /* ---- the form ------------------------------------------------------------------------------------ */

  // Reads whatever is on screen into `draft`, so a mode switch and a redraw never lose what was typed.
  function readDraft() {
    const u = at("str_url");
    if (u) draft.url = String(u.value || "");
    const c = at("str_clips");
    if (c) draft.clips = int(c.value, draft.clips);
    const lo = at("str_min");
    if (lo) draft.min = int(lo.value, draft.min);
    const hi = at("str_max");
    if (hi) draft.max = int(hi.value, draft.max);
    const st = at("str_style");
    if (st) draft.style = String(st.value || "");
    const cap = at("str_capt");
    if (cap) draft.captions = !!cap.checked;
    const chat = at("str_chat");
    if (chat) draft.chat = String(chat.value || "normal");
    const mins = at("str_minutes");
    if (mins) draft.minutes = int(mins.value, draft.minutes);
    const hooks = at("str_hooks");
    if (hooks) draft.hooks = String(hooks.value || "");
    const sk = at("str_skip");
    if (sk) draft.skip = !!sk.checked;
    const ch = at("str_chase");
    if (ch) draft.chase = !!ch.checked;
  }

  // The caption looks the page knows, with the chosen one really selected. Both halves matter: the picker
  // shows a name, and the job is sent the key behind it, so the two can never disagree.
  function styleOptions() {
    const map = styleMap();
    const keys = Object.keys(map);
    if (!keys.length) { draft.style = ""; return ""; }
    const wanted = keys.indexOf(draft.style) >= 0 ? draft.style
      : (keys.indexOf("bounce") >= 0 ? "bounce" : keys[0]);
    draft.style = wanted;
    return keys.map((k) => `<option value="${esc(k)}"${k === wanted ? " selected" : ""}>${esc(map[k])}</option>`).join("");
  }

  function summaryLine() {
    const clips = int(draft.clips, 6);
    const lo = int(draft.min, 12);
    const hi = int(draft.max, 45);
    const look = draft.captions ? styleLabel(draft.style || "beast") + " captions" : "captions off";
    const intro = draft.skip ? "intro skipped" : "intro kept";
    return `${clips} clips, ${lo} to ${hi} seconds, ${look}, ${intro}`;
  }

  function paintSummary() {
    const box = at("str_summary");
    if (!box) return;
    if (mode !== "gta") { box.textContent = ""; return; }
    box.textContent = summaryLine();
  }

  function formHtml() {
    const m = modeInfo(mode);
    const styles = styleOptions();
    const urlHint = mode === "gta"
      ? "Paste a video that has already ended. It is clipped straight away. A stream that is still on air is recorded on the Live page."
      : "Paste the full link of a video that has ended. A stream that is still on air is recorded on the Live page.";
    const clipsHint = mode === "gta"
      ? "Six clips is enough for a day of posting without showing the same joke twice."
      : "The most clips this link can make. Clipstorm still makes fewer if the video has fewer good moments.";
    const minHint = mode === "gta"
      ? "A chase or a heist peaks in a few seconds, so 12 seconds is enough to let the moment land."
      : "The shortest clip Clipstorm will keep.";
    const maxHint = mode === "gta"
      ? "Past about 45 seconds a moment stops being a moment and starts being a video, and people leave."
      : "The longest clip Clipstorm will keep. Longer moments are cut down to this.";
    const styleHint = mode === "gta"
      ? "Beast writes each caption in huge bold words. GTA 6 gameplay is fast and busy, so small captions get lost."
      : "The caption look used on every clip of this job.";

    // Spike and catch used to carry two boxes no route reads: how loud chat must get, and how many
    // minutes a recording keeps. A box that changes nothing looks broken to the person filling the
    // form, so both are gone until a route grows a field for them. The starting values they held
    // stay in START below so nothing else has to change.
    const shape = `
      <div class="pcstr-grid">
        <div class="pcstr-f wide">
          <label for="str_url">Video link</label>
          <input id="str_url" type="url" autocomplete="off" spellcheck="false" placeholder="https://www.twitch.tv/name" value="${esc(draft.url)}">
          <p class="hint">${esc(urlHint)}</p>
        </div>
        <div class="pcstr-f">
          <label for="str_clips">How many clips</label>
          <input id="str_clips" type="number" min="1" max="20" step="1" value="${int(draft.clips, 6)}">
          <p class="hint">${esc(clipsHint)}</p>
        </div>
        <div class="pcstr-f">
          <label for="str_min">Shortest clip, seconds</label>
          <input id="str_min" type="number" min="5" max="120" step="1" value="${int(draft.min, 12)}">
          <p class="hint">${esc(minHint)}</p>
        </div>
        <div class="pcstr-f">
          <label for="str_max">Longest clip, seconds</label>
          <input id="str_max" type="number" min="10" max="180" step="1" value="${int(draft.max, 45)}">
          <p class="hint">${esc(maxHint)}</p>
        </div>
        <div class="pcstr-f">
          <label for="str_style">Caption look</label>
          <select id="str_style">${styles || `<option value="">Caption looks have not loaded</option>`}</select>
          <p class="hint">${esc(styleHint)}</p>
        </div>
        <div class="pcstr-f">
          <label for="str_capt">Captions</label>
          <div class="pcstr-ck" style="border:0;background:transparent;padding:0">
            <input id="str_capt" type="checkbox"${draft.captions ? " checked" : ""}>
            <label for="str_capt">Write the words on the clip</label>
          </div>
          <p class="hint">${mode === "gta" ? "On, because most people watch on mute first." : "Off makes silent clips. On writes what was said across the picture."}</p>
        </div>
      </div>`;

    const gta = mode !== "gta" ? "" : `
      <div class="pcstr-grid" style="margin-top:14px">
        <div class="pcstr-f wide">
          <label for="str_hooks">Hook words to listen for</label>
          <input id="str_hooks" type="text" autocomplete="off" spellcheck="false" maxlength="120" value="${esc(draft.hooks)}">
          <p class="hint">Clipstorm reads hook words from your saved brand, not from one job. Press the button to save
            these words there: they are what the AI is told to look for when it writes a hook, and every job after
            that uses them. The box holds up to 120 characters.</p>
          <button class="btn sm" data-act="str_savehooks">Save these words to my brand</button>
        </div>
        <div class="pcstr-f wide">
          <div class="pcstr-ck">
            <input id="str_skip" type="checkbox"${draft.skip ? " checked" : ""}>
            <label for="str_skip">Skip the intro</label>
            <p class="hint">Trims the first 8 seconds, where most streamers are still on the menu screen. This one is
              real: it is sent as the start of the part Clipstorm looks at.</p>
          </div>
        </div>
        <div class="pcstr-f wide">
          <div class="pcstr-ck">
            <input id="str_chase" type="checkbox"${draft.chase ? " checked" : ""}>
            <label for="str_chase">Prefer moments with a police chase, a crash or a wanted level</label>
            <p class="hint">This is a preference note, not a hard filter. Clipstorm does not read this tick yet, so
              clips are picked by what it hears, the same way for every video.</p>
          </div>
        </div>
        <div class="pcstr-f wide">
          <p class="pcstr-sum" id="str_summary" role="status" aria-live="polite"></p>
        </div>
      </div>`;

    return `
      <p class="pcstr-blurb">${m.blurb}</p>
      ${shape}
      ${gta}
      <div class="pcstr-act">
        <button class="btn primary" id="str_makebtn" data-act="str_make">Make the clips</button>
        <span class="pcstr-foot">Starts the job. The clips show up in your library.</span>
      </div>
      <div id="str_err"></div>`;
  }

  function paintForm() {
    const box = at("str_form");
    if (!box) return;
    const map = styleMap();
    if (mode === "gta" && !map[draft.style]) draft.style = "beast";
    if (!draft.style || (!map[draft.style] && mode !== "gta")) {
      draft.style = map.bounce ? "bounce" : (Object.keys(map)[0] || "");
    }
    box.innerHTML = formHtml();
    paintSummary();
  }

  function paintModes() {
    const strip = at("str_modes");
    if (!strip) return;
    for (const b of strip.querySelectorAll("[data-act='str_mode']")) {
      const on = String(b.dataset.m || "") === mode;
      b.setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function switchMode(k) {
    if (!MODES.some((m) => m.k === k)) return;
    readDraft();
    const url = draft.url;
    // Pressing the mode that is already on turns it off again: the page goes back to the plain
    // Clip a finished video form. Everything a person has typed stays in the boxes, because turning a
    // mode off is not a request to throw numbers away. (Without this press the GTA 6 card was a
    // one-way door: it painted itself pressed and no press could put it back.)
    if (mode === k) {
      mode = "video";
      // No message: `say` paints the error box, and turning a mode off is not a failure. The card
      // unpresses, and the form that follows is the feedback that matches the action.
      say("");
      paintModes();
      paintForm();
      return;
    }
    mode = k;
    Object.assign(draft, START[k]);
    draft.url = url;
    say("");
    paintModes();
    paintForm();
  }

  /* ---- starting a job from the link ----------------------------------------------------------------- */

  function numbers() {
    const clips = int(draft.clips, 6);
    const lo = int(draft.min, 15);
    const hi = int(draft.max, 60);
    if (clips < 1 || clips > 20) return { error: "How many clips has to be between 1 and 20." };
    if (lo < 5 || lo > 120) return { error: "The shortest clip has to be between 5 and 120 seconds." };
    if (hi < 10 || hi > 180) return { error: "The longest clip has to be between 10 and 180 seconds." };
    if (lo >= hi) return { error: "The shortest clip has to be shorter than the longest one." };
    return { clips, lo, hi };
  }

  async function make() {
    say("");
    readDraft();
    const url = String(draft.url || "").trim();
    if (!url) { say("Paste the link of the video first."); return; }
    if (!/^https?:\/\/[^\s/]+\.[^\s/]+/i.test(url)) {
      say("Paste the full address, starting with https://, not just the name of the channel.");
      return;
    }
    const n = numbers();
    if (n.error) { say(n.error); return; }

    // The shape /api/jobs really reads: the link, an options object, and nothing else. A key clean_options
    // does not know is thrown away by the server, so only the ones with a home are sent.
    const options = {
      max_clips: n.clips,
      min_len: n.lo,
      max_len: n.hi,
      style: String(draft.style || "bounce"),
      captions: !!draft.captions,
    };
    // Skip the intro is a real option: the job starts at second 8 instead of second 0.
    if (mode === "gta" && draft.skip) options.range_start = 8;

    const btn = at("str_makebtn");
    if (btn) { btn.disabled = true; btn.textContent = "Checking the link"; }
    try {
      // Ask the link route what this link is before posting. The job route downloads a finished video and
      // refuses a live one, so posting straight away would only make a job that fails later. This check is
      // best effort: if it cannot answer, the job is posted and the route has the final word.
      let seen = null;
      try {
        seen = await P.api("/api/preview?url=" + encodeURIComponent(url));
      } catch (err) {
        seen = null;
      }
      if (seen && seen.is_live) {
        say("That link is a stream that is still on air. Open the Live page to record it and clip it while it runs.");
        return;
      }
      if (btn) btn.textContent = "Starting";
      const job = await P.send("/api/jobs", { url: url, options: options });
      P.toast("Queued. Clipstorm will make up to " + n.clips + " clips from that link.", "ok");
      if (job && job.id) say("");
    } catch (err) {
      // The route answers with a sentence a person can act on, so it is shown exactly as it arrived.
      say(sentence(err, "Clipstorm could not start that job. Try the link again, or paste a different one."));
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Make the clips"; }
    }
  }

  /* ---- the page ----------------------------------------------------------------------------------- */

  // The page's own icon helper, if it is there. A name the page does not know draws nothing rather than the
  // word undefined, so a card can never look broken.
  const icon = (name) => {
    try {
      if (typeof ic !== "function") return "";
      if (typeof I !== "object" || !I || !I[name]) return "";
      return ic(name);
    } catch { return ""; }
  };

  const card = (m) => {
    const on = m.k === mode;
    // A mode that is already on says it can be turned off, and the GTA card carries an On/Off word so its
    // state is readable without relying on colour alone.
    const chip = m.k === "gta"
      ? `<span class="pcstr-chip">${on ? "On" : "Special"}</span>`
      : (m.chip ? `<span class="pcstr-chip">${esc(m.chip)}</span>` : "");
    return `<button type="button" class="pcstr-mode${m.k === "gta" ? " gta" : ""}" data-act="str_mode" data-m="${esc(m.k)}" aria-pressed="${on ? "true" : "false"}">
      ${icon(m.icon)}
      <span class="pcstr-txt"><b>${esc(m.nav)}</b><span class="e">${esc(m.line)}</span></span>
      ${chip}
    </button>`;
  };

  // The card that sends a person to the Live page. It looks like the mode cards but never becomes "pressed".
  const liveCard = () => `<button type="button" class="pcstr-mode" data-act="str_golive">
      ${icon("rec")}
      <span class="pcstr-txt"><b>Record a stream that is on air</b><span class="e">Recording, the clip buttons and the live monitor are on the Live page. Press here to open it.</span></span>
      <span class="pcstr-chip">Live page</span>
    </button>`;

  window.PeakCut.page("streamer", {
    nav: "Streamer clipping",
    icon: "video",
    tip: "Clip a finished stream video, or use the Grand Theft Auto VI preset",
    path: "streamer",
    group: "Make",
    order: 12,
    view() {
      return `<div class="pcstr">
        <section class="set-sec">
          <h1 class="pcstr-h">Streamer clipping</h1>
          <p class="pcstr-lede">Turn a finished stream video into clips. To record a stream while it is on air, use the Live page.</p>
          <div class="pcstr-modes" id="str_modes">${liveCard()}${MODES.map(card).join("")}</div>
          <p class="pcstr-foot">Pick a card to fill the form with its starting numbers. Press the one that is on to turn it off again.</p>
        </section>
        <section class="set-sec">
          <div id="str_form"></div>
        </section>
      </div>`;
    },
    load() {
      // The caption looks come with the page state. If that has not arrived, ask the status route rather than
      // showing an empty picker.
      const boot = (async () => {
        if (!Object.keys(styleMap()).length) {
          try {
            const got = await P.api("/api/status");
            if (got && got.styles) {
              const s = stateOf();
              s.status = s.status || {};
              s.status.styles = got.styles;
            }
          } catch (err) {
            say(sentence(err, "The caption looks could not be read. The picks below still work."));
          }
        }
      })();
      // One listener for the whole form: the fields are redrawn on every mode switch, so the handler lives on
      // the box that does not move.
      const box = at("str_form");
      if (box && box.dataset.pcBound !== "1") {
        box.dataset.pcBound = "1";
        box.addEventListener("input", () => { if (mode === "gta") { readDraft(); paintSummary(); } });
        box.addEventListener("change", () => { if (mode === "gta") { readDraft(); paintSummary(); } });
        box.addEventListener("keydown", (e) => {
          if (e.key === "Enter" && e.target && e.target.id === "str_url") { e.preventDefault(); make(); }
        });
      }
      paintModes();
      return boot.then(() => { paintForm(); });
    },
  });

  // The handlers live on the plug-in. web/plugins.js routes every [data-act] click through the objects it
  // registered with add(), so an act map on a page object would never be consulted.
  window.PeakCut.add("streamer-mode", {
    about: "Streamer clipping: clip a finished video from its link, with the GTA 6 preset, and a way to the Live page.",
    act: {
      str_mode(el) {
        switchMode(String(el.dataset.m || ""));
      },
      str_make() {
        return make();
      },
      // The hook words box is the one field on this page a person expects to matter, and the honest way to make
      // it matter is the brand, which is what the AI actually reads. Saving it here is the same write the Brand
      // page does, through the same route, so there is one home for the words rather than two.
      str_savehooks(el) {
        const box = at("str_hooks");
        const words = String((box && box.value) || "").trim().slice(0, 120);
        if (!words) { say("Type a few words first, like wanted level or police chase."); return Promise.resolve(); }
        if (el) el.disabled = true;
        say("");
        return P.api("/api/brand")
          .then((got) => {
            const doc = Object.assign({}, (got && got.brand) || {}, { hook_words: words });
            return P.send("/api/brand", doc, "PUT");
          })
          .then(() => {
            if (typeof P.toast === "function") P.toast("Saved. Every new clip will be told to look for those words.", "ok");
          })
          .catch((e) => say(sentence(e, "Those words were not saved.")))
          .then(() => { if (el) el.disabled = false; });
      },
      str_golive() {
        if (!P.openPage("live")) say("The Live page is not available.");
      },
    },
  });
})();
