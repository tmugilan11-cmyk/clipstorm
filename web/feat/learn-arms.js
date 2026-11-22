/* A two arm trial on the Improve page: one setting at a time, so the numbers can name the change.
 *
 * `studio/learn.py` changes up to two settings in one round, which is the confound this card exists to
 * remove: when views move nobody can say which of the two did it. A trial here runs the first setting,
 * measures it, then runs the second, and `studio/ai_arms.py` keeps the record and writes the sentence
 * that compares the two windows. The card never writes that sentence itself, it prints the one the
 * server sent, including when that sentence says the difference is inside the noise.
 *
 * It draws into the Improve page rather than owning one, so the page keeps its button, its history and
 * its facts, and this card sits under the main card. When the Improve page is not on screen nothing
 * here runs at all. */
(() => {
  window.PeakCut.css("learn-arms", `
    .lar .laform{display:grid;gap:10px;margin-top:12px}
    .lar .laform .two{display:grid;gap:10px;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
    .lar .laform label{display:grid;gap:5px;font-size:13px;color:var(--dim);line-height:1.4}
    .lar .laform select,.lar .laform input[type=text]{background:var(--panel2);color:var(--ink);
      border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:13px;min-width:0}
    .lar .laform input[type=text]:focus,.lar .laform select:focus{outline:none;border-color:var(--brand)}
    .lar .armline{margin:0;font-size:13px;line-height:1.55;color:var(--ink)}
    .lar .armline code{background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:1px 6px;font-size:12px}
    .lar .said{margin:12px 0 0;padding:10px 12px;border-radius:10px;border:1px solid var(--line);
      background:var(--panel2);font-size:13px;line-height:1.55;color:var(--ink)}
    @media (max-width:620px){.lar .laform .two{grid-template-columns:minmax(0,1fr)}}
  `);

  const P = window.PeakCut;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // The five settings the Improve page names. The trial refuses anything else, and `ai_arms.start()`
  // refuses it too, so the two lists are the same words on purpose.
  const FIVE = [
    ["style", "Caption look"],
    ["hook_words", "How the hook is written"],
    ["clip_len", "How long a clip may be"],
    ["sound", "Sound under a clip"],
    ["captions_always", "Captions on every clip"],
  ];
  // Names the route may use for the sentence `ai_arms.read()` returns. Tried in order, because the
  // wire agent owns the route and this card must print whatever wording it chose rather than one of
  // its own. A record that carries none of them falls through to the scan in `sentenceOf`.
  const SAYS = ["result", "read", "saying", "summary", "effect", "said"];

  let DATA = null;        // the last answer from /api/learn/arms
  let ERR = "";           // one sentence, shown in the card
  let OPEN = false;       // the start form is showing
  let BUSY = false;       // a request is in flight
  let LOADED = false;     // the page has been read once, so a tick does not re-ask
  let SIG = "";           // what is on screen, so a tick with no news draws nothing
  // What the person has chosen in the form so far. The card redraws itself while a request is in
  // flight, which throws the fields away, so their answer is kept here and put back afterwards:
  // a failure should cost one sentence, not the four things they just typed.
  const FILL = { target: "hook_words", value: "", other: "clip_len", other_value: "" };

  const nameOf = (key) => {
    const hit = FIVE.find((pair) => pair[0] === String(key || "").trim());
    return hit ? hit[1] : (String(key || "").trim() || "an unnamed setting");
  };
  /** One sentence for the card, built from what the request threw.
   *
   * The server's own words are worth showing, but a route that answers with a bare status phrase
   * ("Not Found") leaves the person without the thing that failed. So a short phrase is folded into
   * the fallback sentence in brackets, and a longer one is used as it stands, which keeps the card
   * to exactly one sentence either way. */
  const one = (e, fallback) => {
    const said = String((e && e.message) || e || "").replace(/\s+/g, " ").trim();
    if (!said) return fallback;
    if (said.split(" ").length <= 5) {
      const stem = fallback.replace(/[.!?]+$/, "");
      return `${stem} (${said.replace(/[.!?]+$/, "")}).`;
    }
    return /[.!?]$/.test(said) ? said : `${said}.`;
  };

  /** The trial record from the answer, or null when the answer says there is no trial.
   *
   * The route may hand the record on its own or under a name, so the three shapes the rest of the
   * improvement work uses are all read here. A record is only believed when it names a setting, which
   * is what stops an empty answer from being drawn as a trial. */
  function trialOf() {
    const p = DATA && typeof DATA === "object" ? DATA : null;
    if (!p) return null;
    for (const box of [p.trial, p.arms, p.record, p]) {
      if (box && typeof box === "object" && !Array.isArray(box) && (box.target || box.other)) return box;
    }
    return null;
  }

  /** The arms that have run, read from the record `ai_arms.turn()` writes. */
  const ranOf = (t) => (t && Array.isArray(t.runs) ? t.runs : []);

  /** Whether both arms have run, so the comparison sentence is the thing worth showing. */
  function doneOf(t) {
    const ran = ranOf(t);
    return ran.indexOf("a") >= 0 && ran.indexOf("b") >= 0;
  }

  /** The comparison sentence exactly as the server sent it, or an empty string.
   *
   * `esc()` runs at print time, not here, so the words that reach the screen are the server's own. */
  function sentenceOf() {
    const t = trialOf();
    for (const box of [t, DATA]) {
      if (!box || typeof box !== "object") continue;
      for (const key of SAYS) {
        const got = box[key];
        if (typeof got === "string" && got.trim()) return got.trim();
      }
    }
    // A route that named its sentence something else still gets printed, but only when both arms
    // have run and the string really is a sentence, so a note or a key cannot be shown as a result.
    const skip = ["why_not", "note", "error", "detail", "status", "arm", "target", "other"];
    for (const key of Object.keys(DATA || {})) {
      if (skip.indexOf(key) >= 0) continue;
      const got = DATA[key];
      if (typeof got !== "string") continue;
      if (got.trim().split(/\s+/).length >= 6 && /[.!]$/.test(got.trim())) return got.trim();
    }
    return "";
  }

  function options(selected) {
    return FIVE.map(([key, label]) =>
      `<option value="${esc(key)}"${key === selected ? " selected" : ""}>${esc(label)}</option>`).join("");
  }

  function formBlock() {
    return `<div class="laform">
        <div class="two">
          <label>First setting to try
            <select id="la_target">${options(FILL.target)}</select></label>
          <label>Value for the first setting
            <input id="la_value" type="text" value="${esc(FILL.value)}"
              placeholder="wait for it, or 45" autocomplete="off"></label>
        </div>
        <div class="two">
          <label>Second setting to try
            <select id="la_other">${options(FILL.other)}</select></label>
          <label>Value for the second setting
            <input id="la_other_value" type="text" value="${esc(FILL.other_value)}"
              placeholder="45, or a style name" autocomplete="off"></label>
        </div>
        <p class="sub" style="margin:0">Clipstorm runs the first setting, measures it, then runs the second, so
          the next numbers can say which one did the work. Both values are written down as you type them.</p>
        <div class="btnrow">
          <button class="btn sm" data-act="lastart"${BUSY ? " disabled" : ""}>Start the trial</button>
          <button class="btn sm" data-act="lacancel">Cancel</button>
        </div>
      </div>`;
  }

  function trialBlock(t) {
    const arm = String(t.arm || "a").toLowerCase() === "b" ? "b" : "a";
    const running = arm === "b"
      ? { setting: t.other, value: t.other_value }
      : { setting: t.target, value: t.value };
    const other = arm === "b"
      ? { setting: t.target, value: t.value }
      : { setting: t.other, value: t.other_value };
    const done = doneOf(t);
    const said = sentenceOf();
    const parts = [
      `<p class="armline">On trial: <b>${esc(nameOf(t.target))}</b> at <code>${esc(t.value == null ? "" : t.value)}</code>,
        against <b>${esc(nameOf(t.other))}</b> at <code>${esc(t.other_value == null ? "" : t.other_value)}</code>.</p>`,
    ];
    if (done) {
      parts.push(`<p class="armline">Both settings have been tried.</p>`);
    } else {
      parts.push(`<p class="armline">Running now: ${esc(nameOf(running.setting))} at
        <code>${esc(running.value == null ? "" : running.value)}</code>. ${esc(nameOf(other.setting))}
        runs after this one.</p>`);
    }
    if (said) parts.push(`<div class="said">${esc(said)}</div>`);
    else if (done) {
      // Saying nothing here would look like the trial finished without an answer, so the card says
      // which piece is missing instead of filling the gap with a sentence of its own.
      parts.push(`<p class="sub" style="margin:11px 0 0">Both settings have been measured. The sentence
        comparing them is not written yet. It appears here once Clipstorm has finished.</p>`);
    }
    parts.push(`<div class="btnrow" style="margin-top:12px">
        <button class="btn sm" data-act="lastop"${BUSY ? " disabled" : ""}>${done ? "Clear this trial" : "Stop the trial"}</button>
      </div>`);
    return parts.join("");
  }

  function body() {
    const t = trialOf();
    let inner = `<p class="err" id="la_err"${ERR ? "" : " hidden"}>${esc(ERR)}</p>`;
    if (t) {
      inner += trialBlock(t);
    } else {
      inner += `<p class="sub">A trial runs one setting on your clips, then a second one, so the next numbers
        can say which change did the work instead of guessing between two at once.</p>`;
      inner += OPEN ? formBlock() : `<div class="btnrow">
          <button class="btn sm" data-act="laopen"${BUSY ? " disabled" : ""}>Start a trial</button>
          <button class="btn sm" data-act="lareload">Read it again</button>
        </div>`;
    }
    return `<div class="box lar" id="la_arms"><h3>Two-setting trial</h3>${inner}</div>`;
  }

  /** Puts one sentence of failure in the card, without a redraw that would wipe a half typed form. */
  function fail(text) {
    ERR = text;
    const el = document.getElementById("la_err");
    if (el) { el.textContent = text; el.hidden = !text; }
  }

  /** Draws the card into the Improve page. Does nothing when that page is not on screen. */
  function paint() {
    const host = document.querySelector("#view .lrn") || document.querySelector(".lrn");
    if (!host) { LOADED = false; return; }        // left the page, so the next visit reads again
    const html = body();
    const box = host.querySelector("#la_arms");
    if (!box) {
      // Under the page's own button card, which is the work this trial belongs to.
      const first = host.querySelector(".box");
      if (first) first.insertAdjacentHTML("afterend", html);
      else host.insertAdjacentHTML("beforeend", html);
      SIG = html;
      return;
    }
    if (SIG === html) return;                      // nothing new to say, so nothing is touched
    box.outerHTML = html;
    SIG = html;
  }

  async function load(force) {
    if (BUSY) return;
    if (LOADED && !force) return;
    BUSY = true;
    try {
      const got = await P.api("/api/learn/arms");
      DATA = got && typeof got === "object" ? got : {};
      ERR = "";
      LOADED = true;
    } catch (e) {
      ERR = one(e, "Clipstorm could not read the trial.");
      DATA = DATA || {};
      LOADED = true;                               // one sentence, then a button to ask again
    } finally {
      BUSY = false;
      paint();
    }
  }

  /** Reads the four fields into FILL, so a redraw cannot lose what the person typed.
   *
   * A field that is not on screen is left as FILL has it: the page has just been redrawn and the
   * answer from before that redraw is still the best one there is. Blanking it here would turn a
   * redraw into an empty form. */
  function keep() {
    const read = (id) => {
      const el = document.getElementById(id);
      if (!el) return null;
      return String(el.value == null ? "" : el.value).trim();
    };
    const target = read("la_target"), other = read("la_other");
    const value = read("la_value"), otherValue = read("la_other_value");
    if (target) FILL.target = target;
    if (other) FILL.other = other;
    if (value !== null) FILL.value = value;
    if (otherValue !== null) FILL.other_value = otherValue;
    return { target: FILL.target, value: FILL.value, other: FILL.other, other_value: FILL.other_value };
  }

  async function start() {
    if (BUSY) return;
    const want = keep();
    if (!want.target || !want.other || want.target === want.other) {
      fail("Pick two different settings for the trial.");
      return;
    }
    if (!want.value || !want.other_value) {
      fail("Give both settings a value to try.");
      return;
    }
    BUSY = true;
    ERR = "";
    paint();
    let wrote = false;
    try {
      await P.send("/api/learn/arms", want, "POST");
      wrote = true;
      OPEN = false;
    } catch (e) {
      ERR = one(e, "Clipstorm could not start the trial.");
      OPEN = true;                                 // the form stays, with what they typed in it
    } finally {
      BUSY = false;
      if (!wrote) paint();
    }
    if (!wrote) return;
    P.toast("The trial is written down. The first setting runs first.", "ok");
    // The write answers with whatever the route chose to say, so the card asks for the record
    // `ai_arms` keeps rather than drawing the reply as if it were the trial.
    LOADED = false;
    load(true);
  }

  async function stop() {
    if (BUSY) return;
    BUSY = true;
    ERR = "";
    paint();
    try {
      await P.api("/api/learn/arms", { method: "DELETE" });
      DATA = {};
      OPEN = false;
      SIG = "";
      P.toast("The trial is stopped. The settings are as they were.", "ok");
    } catch (e) {
      ERR = one(e, "Clipstorm could not stop the trial.");
    } finally {
      BUSY = false;
      paint();
    }
  }

  /** One quiet check while the Improve page is open. The page redraws itself after every action and
   * would drop this card, so the card puts itself back instead of asking the page to remember it.
   *
   * A form that is on screen is left alone, because rebuilding it would throw away the keystrokes
   * since it opened. A form the page has already removed is put back from what `FILL` last saw. */
  function tick() {
    if (!document.querySelector(".lrn")) { LOADED = false; return; }
    if (BUSY) return;
    if (OPEN && document.getElementById("la_arms") && document.getElementById("la_target")) return;
    if (OPEN) keep();
    if (!LOADED) { load(); return; }
    paint();
  }

  P.add("learn-arms", {
    after: {
      /** Runs when a page is drawn. The Settings form is also drawn through this hook, so the card
       * only appears in the node that carries the Improve page. */
      drawSettings(root) {
        if (!root || typeof root.querySelector !== "function") return;
        if (!root.querySelector(".lrn")) return;
        paint();
        if (!LOADED) load();
      },
    },
    act: {
      laopen: () => { OPEN = true; ERR = ""; paint(); },
      lacancel: () => { OPEN = false; ERR = ""; paint(); },
      lastart: () => start(),
      lastop: () => stop(),
      lareload: () => load(true),
    },
  });

  try { setInterval(tick, 700); } catch { /* no timer: the hook above still draws the card once */ }
})();
