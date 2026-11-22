/* The Schedule page: the three blocks of text that put PeakCut on a timer, shown as text you copy.
 *
 * Nothing on this page writes to this computer unless an operator presses Install twice. Every card says so.
 * Card 1 reads /api/autopilot/spec (the structured plan behind the clips tick), card 2 reads
 * /api/schedule/round (one Improve round, which is a separate schedule with its own task name), card 3 reads
 * /api/autopilot/preview (the same tick as pasted text, which is the timetable a scheduler would run rather than
 * a list of clips that are due right now). */
(() => {
  const P = window.PeakCut;

  P.css("schedule", `
    .sch{max-width:820px}
    .sch-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--ink);margin-bottom:6px}
    .sch-lead{max-width:62ch}
    .sch-field{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin:16px 0 4px}
    .sch-field label{display:block;font-size:13px;font-weight:600;color:var(--ink);margin-bottom:5px}
    .sch-field input{width:210px;height:38px}
    .sch .hint.block{display:block;margin:6px 0 0;max-width:62ch}
    .sch-card{margin-top:16px}
    .sch-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}
    .sch-head h2{margin:0}
    .sch-what{margin:4px 0 0;max-width:58ch}
    .sch-body{margin-top:14px;display:grid;gap:10px}
    .sch-facts{display:flex;gap:18px;flex-wrap:wrap;margin:0}
    .sch-facts div{min-width:0}
    .sch-facts dt{font-size:11px;color:var(--faint);margin-bottom:2px}
    .sch-facts dd{margin:0;font-size:13px;color:var(--ink);overflow-wrap:anywhere}
    .sch-pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;line-height:1.55;
      background:var(--muted);border:1px solid var(--line);border-left:3px solid var(--brand);
      border-radius:8px;padding:12px 14px;margin:0;overflow:auto;max-height:280px;white-space:pre;color:var(--text)}
    .sch-note{font-size:12px;color:var(--dim);margin:0;max-width:62ch}
    .sch-note b{color:var(--ink)}
    .sch-acts{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
    .sch-arm{font-size:12px;color:var(--brand-deep);background:var(--brand-soft);border:1px solid var(--brand-line);
      border-radius:8px;padding:7px 10px;margin:0;max-width:60ch}
    .sch-wait{color:var(--faint);font-size:12px;margin:0}
    .sch-fold{border:1px solid var(--line);border-radius:8px;padding:0 12px}
    .sch-fold>summary{cursor:pointer;font-size:13px;font-weight:600;color:var(--brand-deep);padding:10px 0}
    .sch-fold>summary:hover{color:var(--text)}
    .sch-fold[open]>summary{border-bottom:1px solid var(--line);margin-bottom:10px}
    .sch-fold .sch-pre{border:0;border-left:3px solid var(--brand);margin-bottom:12px}
    .sch-fold>summary:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px;border-radius:6px}
    .sch .err{margin:0}
    @media (max-width:560px){.sch-h{font-size:20px}.sch-field input{width:100%}}
  `);

  // The text each card handed out last, keyed by card. Kept out of the DOM so a copy never re-parses markup.
  const HAVE = { clips: "", improve: "", due: "" };
  // One stored "which button is armed, and for what" per card, plus one timer, so arming one card cannot
  // silently arm or cancel another. A value is the action ("install" or "remove") that a second press would do.
  const ARM = { clips: "", improve: "", due: "", timer: 0 };

  const timesField = () => {
    const el = document.getElementById("sch_times");
    return el ? String(el.value || "").trim() : "";
  };

  // true = the operator, false = signed in as someone else, null = the page could not tell. A throw here means the
  // shell has not loaded a user yet, which is not the same fact as "you are not the operator", and the card says so.
  const isOwner = () => {
    try {
      const s = P.state();
      if (!s || !s.status) return null;
      const u = s.status.user;
      if (!u) return null;
      return !!u.is_admin;
    } catch (err) { return null; }
  };

  // One quiet sentence in the card. Never a silent catch, never an alert.
  function fail(where, why) {
    const box = document.getElementById("sch_" + where);
    if (!box) return;
    box.innerHTML = `<p class="err">${esc(String(why || "That request did not come back."))}</p>`;
  }

  function facts(rows) {
    const made = rows.filter(r => r && r[1]).map(r =>
      `<div><dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd></div>`).join("");
    return made ? `<dl class="sch-facts">${made}</dl>` : "";
  }

  // A card body: the facts we were told, the text to copy, and what copying does not do.
  // `folded` puts the text behind a disclosure, used where two routes return the same words as an earlier card.
  function sheet(where, text, rows, folded) {
    HAVE[where] = text;
    const factsHtml = facts(rows);
    const pre = text
      ? `<pre class="sch-pre" id="sch_pre_${where}" tabindex="0">${esc(text)}</pre>`
      : `<p class="sch-note">Clipstorm did not get any text back for this schedule, so there is nothing to copy.</p>`;
    if (text && folded) {
      return `${factsHtml}<details class="sch-fold"><summary>Show the text this card would copy</summary>${pre}</details>`;
    }
    return `${factsHtml}${pre}`;
  }

  function copyLine() {
    return `<p class="sch-note"><b>Copying this text installs nothing.</b> It puts the words on your clipboard.
      Nothing runs, and nothing on this computer changes, until you paste it somewhere and run it yourself.</p>`;
  }

  /* ---------------------------------------------------------------- card 1, clips on a timer */
  async function drawClips() {
    const box = document.getElementById("sch_clips");
    if (!box) return;
    box.innerHTML = `<p class="sch-wait">Working out the clips schedule...</p>`;
    let spec;
    try {
      spec = await P.api("/api/autopilot/spec?times=" + encodeURIComponent(timesField()));
    } catch (e) {
      fail("clips", e && e.message ? e.message : e);
      return;
    }
    if (!spec || spec.ok !== true) {
      const why = (spec && (spec.error || spec.warn)) || "The server could not build a clips schedule for those times.";
      box.innerHTML = `<p class="err">${esc(why)}</p>`;
      return;
    }
    const days = Array.isArray(spec.days) ? spec.days.join(", ") : "";
    const at = Array.isArray(spec.times) ? spec.times.join(", ") : "";
    box.innerHTML =
      sheet("clips", String(spec.text || ""), [
        ["Scheduler", spec.platform],
        ["Days", days],
        ["Times", at],
      ]) +
      copyLine() +
      `<div class="sch-acts">
        <button class="btn sm" type="button" data-act="schcopy" data-t="clips">${ic("copy")}Copy the clips text</button>
      </div>
      <div class="sch-acts" id="sch_acts_clips"></div>`;
    drawClipActs();
  }

  // Install and Remove live here and both need two presses. The first press only arms.
  function drawClipActs() {
    const box = document.getElementById("sch_acts_clips");
    if (!box) return;
    const owner = isOwner();
    if (owner === null) {
      // Not knowing is its own case: saying "only the operator can" here would be a claim about the person that the
      // page cannot support, and it would hide the buttons for the operator on a slow first paint.
      box.innerHTML = `<p class="sch-note">Clipstorm could not tell whether you are the operator, so Install is
        hidden for now. Reload the page to ask again. You can still copy the text and run it yourself.</p>`;
      return;
    }
    if (!owner) {
      box.innerHTML = `<p class="sch-note">Only the operator account can write a task into this computer's
        scheduler. You can still copy the text and run it yourself.</p>`;
      return;
    }
    const armed = ARM.clips;
    box.innerHTML = `<button class="btn sm" type="button" data-act="scharm" data-t="clips" data-do="install"
        aria-pressed="${armed === "install" ? "true" : "false"}">${ic("plus")}${armed === "install" ? "Press again to install" : "Install on this computer"}</button>
      <button class="btn sm" type="button" data-act="scharm" data-t="clips" data-do="remove"
        aria-pressed="${armed === "remove" ? "true" : "false"}">${ic("trash")}${armed === "remove" ? "Press again to remove" : "Remove"}</button>
      ${armed ? `<p class="sch-arm">Nothing has been ${armed === "install" ? "installed" : "removed"} yet.
        Press the same button again within eight seconds to let Clipstorm change one task in this computer's
        scheduler. Pressing another button, or waiting, cancels it.</p>` : ""}`;
  }

  /* ---------------------------------------------------------------- card 2, an Improve round on a timer */
  async function drawImprove() {
    const box = document.getElementById("sch_improve");
    if (!box) return;
    box.innerHTML = `<p class="sch-wait">Working out the Improve schedule...</p>`;
    let got;
    try {
      got = await P.api("/api/schedule/round?times=" + encodeURIComponent(timesField()));
    } catch (e) {
      fail("improve", e && e.message ? e.message : e);
      return;
    }
    const text = String((got && got.preview) || "");
    const at = got && Array.isArray(got.times) ? got.times.join(", ") : "";
    const sameAsClips = text && HAVE.clips && text === HAVE.clips;
    box.innerHTML =
      sheet("improve", text, [
        ["Scheduler", got && got.os],
        ["Times", at],
      ], true) +
      (got && got.note ? `<p class="sch-note">${esc(got.note)}</p>` : "") +
      (sameAsClips ? `<p class="sch-note"><b>This is the same text as the clips card.</b> Copy the text above only
        if you meant the clips tick, not the Improve round.</p>` : "") +
      copyLine() +
      `<div class="sch-acts">
        <button class="btn sm" type="button" data-act="schcopy" data-t="improve">${ic("copy")}Copy the Improve text</button>
      </div>`;
  }

  /* ---------------------------------------------------------------- card 3, what is due */
  async function drawDue() {
    const box = document.getElementById("sch_due");
    if (!box) return;
    box.innerHTML = `<p class="sch-wait">Reading the tick command...</p>`;
    let got;
    try {
      got = await P.api("/api/autopilot/preview?times=" + encodeURIComponent(timesField()));
    } catch (e) {
      fail("due", e && e.message ? e.message : e);
      return;
    }
    const text = String((got && got.preview) || "");
    const at = got && Array.isArray(got.times) ? got.times.join(", ") : "";
    box.innerHTML =
      sheet("due", text, [
        ["Scheduler", got && got.os],
        ["Times", at],
      ], true) +
      `<p class="sch-note">This is the timetable a scheduler would run, not a list of clips waiting now. Clipstorm
        has no route that lists what is due at a moment, so this card shows the command the tick would use at
        those times instead of making numbers up. The text is the same as the clips card, because both come from
        the same tick.</p>` +
      copyLine() +
      `<div class="sch-acts">
        <button class="btn sm" type="button" data-act="schcopy" data-t="due">${ic("copy")}Copy this text</button>
      </div>`;
  }

  async function drawAll() {
    await drawClips();
    await drawImprove();
    await drawDue();
  }

  /* ---------------------------------------------------------------- the two-press install */
  async function arm(btn) {
    const which = btn.dataset.t;
    const doing = btn.dataset.do || "install";
    // Which button, if any, is already armed: the stored value is the action it would do.
    const waiting = ARM[which];
    // Any other armed button is disarmed first, so two things can never be armed at once.
    let disarmed = false;
    for (const k of Object.keys(ARM)) {
      if (k === "timer") continue;
      if (ARM[k] && !(k === which && waiting === doing)) { ARM[k] = ""; disarmed = true; }
    }
    if (disarmed) { clearTimeout(ARM.timer); ARM.timer = 0; }
    if (waiting !== doing) {
      // FIRST press: remember the action, show the warning, change nothing on the machine.
      ARM[which] = doing;
      drawClipActs();
      ARM.timer = setTimeout(() => { ARM[which] = ""; ARM.timer = 0; drawClipActs(); }, 8000);
      return;
    }
    // SECOND press on the same button with the same action. This is the only path that changes the machine.
    ARM[which] = "";
    clearTimeout(ARM.timer);
    ARM.timer = 0;
    drawClipActs();
    const acts = document.getElementById("sch_acts_clips");
    if (acts) acts.innerHTML = `<p class="sch-wait">Writing the schedule...</p>`;
    try {
      const out = await P.send(doing === "install" ? "/api/autopilot/install" : "/api/autopilot/remove",
        { confirm: true, times: timesField() });
      const done = doing === "install" ? out && out.installed : out && out.removed;
      P.toast(done ? (doing === "install" ? "The schedule was installed." : "The schedule was removed.")
                   : "The server did not confirm the change.", done ? "ok" : "bad");
    } catch (e) {
      P.toast(String((e && e.message) || e || "That did not work."), "bad");
    }
    drawClipActs();
  }

  // Handlers live on the plug-in, not the page: web/plugins.js routes [data-act] clicks and key presses
  // by walking PeakCut._order, which only holds names registered through PeakCut.add.
  P.add("schedule", {
    about: "The paste-ready text that puts clips and Improve rounds on a timer. Nothing is installed by copying.",
    act: {
      schredraw() { return drawAll(); },
      async schcopy(btn) {
        const which = btn.dataset.t;
        const text = HAVE[which] || "";
        if (!text) { P.toast("There is no text to copy yet.", "bad"); return; }
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(text);
          else throw new Error("This browser will not let the page copy for you.");
          P.toast("Copied. Nothing was installed.", "ok");
        } catch (e) {
          P.toast("The browser refused to copy. Select the text in the box and copy it yourself.", "bad");
        }
      },
      async scharm(btn) { return arm(btn); },
    },
  });

  // Enter inside the times field rebuilds the cards, which is what a person expects after typing. This listens
  // by itself: web/plugins.js hands key presses to plug-ins only when the cursor is NOT in a field (so a typed
  // letter is never taken for a shortcut), which meant a `keys` handler for this field could never run.
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" || !e.target || e.target.id !== "sch_times") return;
    e.preventDefault();
    drawAll();
  });

  P.page("schedule", {
    nav: "Schedule",
    icon: "clock",
    tip: "Put clips and Improve rounds on a timer, as text you copy",
    path: "schedule",
    group: "Set up",
    order: 42,
    view() {
      return `<div class="sch set-sec">
        <h1 class="sch-h">Schedule</h1>
        <p class="help sch-lead">Clipstorm does not run in the background by itself. This page writes the text that
          tells this computer to wake Clipstorm at a time you choose. You copy the text and set it up.</p>

        <div class="sch-field">
          <div>
            <label for="sch_times">Clock times</label>
            <input id="sch_times" type="text" value="06:00,18:00" autocomplete="off" spellcheck="false"
              aria-describedby="sch_times_hint">
          </div>
          <button class="btn" type="button" data-act="schredraw">${ic("cog")}Use these times</button>
        </div>
        <p class="hint block" id="sch_times_hint">Hours and minutes on this computer's own clock, separated by
          commas. Write 06:00,18:00 for a run at six in the morning and again at six in the evening.</p>

        <article class="card sch-card">
          <div class="sch-head">
            <h2>Clips on a timer</h2>
            <span class="pill">Text only</span>
          </div>
          <p class="help sch-what">The task that makes new clips at the times above. Built from this computer's
            own scheduler, so it matches Windows, macOS or Linux without you choosing.</p>
          <div class="sch-body" id="sch_clips"></div>
        </article>

        <article class="card sch-card">
          <div class="sch-head">
            <h2>An Improve round on a timer</h2>
            <span class="pill">Text only</span>
          </div>
          <p class="help sch-what">The task that runs one Improve round at the times above, so the clip rules get a
            little better without you remembering to press anything.</p>
          <div class="sch-body" id="sch_improve"></div>
        </article>

        <article class="card sch-card">
          <div class="sch-head">
            <h2>What is due</h2>
            <span class="pill">Read only</span>
          </div>
          <p class="help sch-what">The command a scheduler would run at the times above. It is the timetable, not a
            list of clips in the queue.</p>
          <div class="sch-body" id="sch_due"></div>
        </article>
      </div>`;
    },
    async load() { await drawAll(); },
  });
})();
