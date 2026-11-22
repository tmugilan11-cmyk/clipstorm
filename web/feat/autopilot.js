/* PeakCut autopilot -- the Tools card that puts clipping on a schedule.
   Until now that was a command to paste. This card shows the same plan, then
   offers to install it for you.
   studio/api_auto.py refuses every write that does not carry confirm: true, so
   this file always sends it and prints whatever sentence comes back. A refusal
   is the answer: it is shown as it arrived, and nothing is retried. */
(() => {
  window.PeakCut.css("autopilot", `
  .pcauto-form { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap; }
  .pcauto-form .f { flex: 1 1 190px; max-width: 280px; }
  .pcauto-out { display: grid; gap: 8px; margin-top: 14px; }
  .pcauto-out:empty { display: none; }
  .pcauto-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 0;
    font-size: 13px; color: var(--dim); }
  .pcauto-meta .pill { flex: none; }
  .pcauto-pre { margin: 0; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--r-sm);
    background: var(--muted); color: var(--text); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px; line-height: 1.55; white-space: pre; overflow: auto; max-height: 260px; }
  .pcauto-pre:empty { display: none; }
  .pcauto-note { margin: 0; font-size: 12px; color: var(--faint); }
  /* The warn panel sits on --brand-soft, so its ink is the light --brand-deep:
     #FFB27A on #2A1B10 measures 9.4:1. The near-black --brand-ink measured
     1.15:1 on this background, which no one could read. */
  .pcauto-warn { margin: 0; padding: 9px 11px; border-left: 3px solid var(--brand);
    border-radius: 0 var(--r-sm) var(--r-sm) 0; background: var(--brand-soft);
    color: var(--brand-deep); font-size: 12px; line-height: 1.5; }
  .pcauto-acts { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
  .pcauto-msg { display: grid; gap: 8px; margin-top: 12px; }
  .pcauto-msg:empty { display: none; }
  .pcauto-msg p { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; margin: 0;
    font-size: 13px; line-height: 1.5; color: var(--text); }
  .pcauto-msg .pill { flex: none; }
  .pcauto .btn:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) { .pcauto * { transition: none; } }
  `);

  const DAYS = { MON: "Monday", TUE: "Tuesday", WED: "Wednesday", THU: "Thursday",
                 FRI: "Friday", SAT: "Saturday", SUN: "Sunday" };
  const OSES = { windows: "Windows", macos: "macOS", linux: "Linux" };
  const MOST = 12;

  /* Tools paints the tab again on every visit, so remember the last answer and
     the box you typed into, or the plan would vanish each time you come back. */
  const last = { typed: "", key: "", spec: null, prev: null };

  const box = id => document.getElementById(id);
  const dayName = d => DAYS[String(d || "").toUpperCase()] || String(d || "");
  const osName = p => OSES[String(p || "").toLowerCase()] || "";

  function listText(xs) {
    const got = (xs || []).filter(Boolean);
    if (got.length < 2) return got[0] || "";
    return got.slice(0, -1).join(", ") + " and " + got[got.length - 1];
  }

  /* ---------- the card ---------- */
  function card() {
    return `<section class="set-sec pcauto">
    <h2>Clip on a schedule</h2>
    <p class="help">Clipstorm can ask this computer to run a batch of clips for you at set times. Look at the plan first. Nothing is written until you confirm.</p>
    <div class="pcauto-form">
      <label class="f" for="pcauto_times">Times
        <input id="pcauto_times" value="09:00,18:30" placeholder="09:00,18:30" autocomplete="off" spellcheck="false">
      </label>
      <button class="btn" data-act="pcauto_plan">Show me the plan</button>
    </div>
    <p class="hint">Up to ${MOST} times on a 24 hour clock, separated by commas.</p>
    <div class="pcauto-out" id="pcauto_out"></div>
    <div class="pcauto-acts">
      <button class="btn primary" data-act="pcauto_install">Install the schedule</button>
      <button class="btn" data-act="pcauto_remove">Remove it</button>
    </div>
    <div class="pcauto-msg" id="pcauto_msg" role="status" aria-live="polite"></div>
  </section>`;
  }

  /* ---------- what the card says back ---------- */
  function showMsg(html) {
    const at = box("pcauto_msg");
    if (at) at.innerHTML = html;
  }

  function showError(sentence, head) {
    showMsg(`<p><span class="pill bad">${esc(head || "Not done")}</span> <span>${esc(sentence)}</span></p>`);
  }

  /* The route answers with the sentences the scheduler printed. They are shown
     as they arrived, in the order they ran. */
  function showDone(kind, data) {
    const at = box("pcauto_msg");
    if (!at) return;
    const sched = (data && data.schedule) || {};
    const ran = Array.isArray(sched.ran) ? sched.ran : [];
    const said = ran.map(r => String((r && r.out) || "").trim()).filter(Boolean).join("\n");
    const line = kind === "install"
      ? "The schedule is on this machine now."
      : "The schedule is off this machine now.";
    at.innerHTML = `<p><span class="pill ok">${esc(kind === "install" ? "Installed" : "Removed")}</span> <span>${esc(line)}</span></p>`
      + (said ? `<pre class="pcauto-pre">${esc(said)}</pre>` : "");
  }

  function renderPlan(spec, prev) {
    const at = box("pcauto_out");
    if (!at) return;
    if (!spec || spec.ok !== true) {
      at.innerHTML = "";
      showError((spec && spec.error) || "Clipstorm could not work out a schedule for this machine.");
      return;
    }
    const platform = osName(spec.platform) || "This machine";
    const days = (spec.days || []).map(dayName);
    const times = spec.times || [];
    const when = [days.length ? listText(days) : "", times.length ? "at " + listText(times) : ""]
      .filter(Boolean).join(" ");
    const count = (spec.cmds || []).length;
    /* Both routes hand back the same text. The preview one is the copy an
       operator would paste, so it is the one shown. Its own footer says
       Clipstorm never touches your scheduler, which would read as a flat
       contradiction above an install button, so the card says its own line. */
    const body = (prev && prev.preview) || spec.text || "";
    at.innerHTML = `<p class="pcauto-meta"><span class="pill">${esc(platform)}</span>`
      + `<span>Runs ${esc(when || "at the times above")}.`
      + ` That is ${count} command${count === 1 ? "" : "s"} for the scheduler.</span></p>`
      + `<pre class="pcauto-pre">${esc(body)}</pre>`
      + `<p class="pcauto-note">That is the text to paste if you would rather run it yourself. Install runs it here instead.</p>`
      + (spec.warn ? `<p class="pcauto-warn">${esc(spec.warn)}</p>` : "");
  }

  /* ---------- reading the times box ---------- */
  /* The server quietly drops a bad time and falls back to 09:00, so the card
     checks first: people should see the mistake they typed. A plan for the old
     times is cleared away too, so it cannot sit under a message about a new
     one and look like the answer. */
  function badTimes(why) {
    const at = box("pcauto_out");
    if (at) at.innerHTML = "";
    last.spec = null;
    last.prev = null;
    last.key = "";
    showError(why, "Check the times");
    return null;
  }

  function readTimes() {
    const at = box("pcauto_times");
    const raw = at ? at.value : "";
    last.typed = raw;
    const list = [];
    String(raw || "").split(/[,;\s]+/).forEach(part => {
      const t = part.trim();
      if (t && list.indexOf(t) === -1) list.push(t);
    });
    if (!list.length) return badTimes("Type at least one time, like 09:00.");
    if (list.length > MOST) return badTimes(`That is ${list.length} times. Clipstorm takes up to ${MOST}.`);
    const bad = list.find(t => !/^\d{2}:\d{2}$/.test(t)
      || Number(t.slice(0, 2)) > 23 || Number(t.slice(3)) > 59);
    if (bad) return badTimes(`"${bad}" is not a time. Write it like 09:00.`);
    return list;
  }

  /* ---------- the two reads ---------- */
  async function planTimes(times) {
    const qs = "?times=" + encodeURIComponent(times.join(","));
    const got = await Promise.all([
      PeakCut.api("/api/autopilot/spec" + qs),
      PeakCut.api("/api/autopilot/preview" + qs),
    ]);
    last.spec = got[0];
    last.prev = got[1];
    last.key = times.join(",");
    renderPlan(last.spec, last.prev);
    return last.spec;
  }

  /* ---------- the confirm step ---------- */
  /* The page has its own dialog helper, ask(). It is reachable from here, so it
     is what people see. If it ever is not, the button takes a second click
     instead: the first click only changes the label.
     Each button keeps its own countdown on the element, so arming one button
     can never cancel the other button's countdown. */
  function stopArmClock(b) {
    const at = b && b.dataset.pcArmTimer ? Number(b.dataset.pcArmTimer) : 0;
    if (at) { clearTimeout(at); b.dataset.pcArmTimer = ""; }
  }

  function disarm(b) {
    stopArmClock(b);
    if (!b || b.dataset.pcArm !== "1") return;
    b.dataset.pcArm = "";
    b.className = b.dataset.pcCls || "btn";
    b.textContent = b.dataset.pcLabel || "Install the schedule";
  }

  function armAgain(b, backLabel, armedLabel) {
    if (b.dataset.pcArm === "1") { disarm(b); return true; }
    b.dataset.pcCls = b.className;
    b.dataset.pcLabel = backLabel;
    b.dataset.pcArm = "1";
    b.className = "btn danger";
    b.textContent = armedLabel;
    b.dataset.pcArmTimer = String(setTimeout(() => disarm(b), 8000));
    showMsg(`<p><span class="pill warn">One more click</span> <span>Nothing has happened yet. Press the same button again to go ahead.</span></p>`);
    return false;
  }

  /* Returns true to go ahead, false for a plain no, and "armed" when the button
     is now waiting for its second click. The callers must keep that button
     armed, so they do not put it back while it is waiting. */
  async function confirmStep(b, title, sentence, okLabel, backLabel, armedLabel, danger) {
    if (typeof window.ask === "function") {
      try { return await window.ask(title, sentence, okLabel, danger); }
      catch (err) { /* the dialog did not open, so fall through to the second click */ }
    }
    return armAgain(b, backLabel, armedLabel) === true ? true : "armed";
  }

  /* ---------- actions ---------- */
  async function doPlan(b) {
    const times = readTimes();
    if (!times) return;
    const label = b.textContent;
    b.disabled = true;
    b.textContent = "Working it out...";
    try {
      await planTimes(times);
      showMsg("");
    } catch (err) {
      showError((err && err.message) || "The plan could not be worked out.");
    } finally {
      b.disabled = false;
      b.textContent = label;
    }
  }

  async function doInstall(b) {
    const times = readTimes();
    if (!times) return;
    const key = times.join(",");
    const base = "Install the schedule";
    let waiting = false;
    b.disabled = true;
    try {
      let spec = last.spec;
      if (!spec || last.key !== key) spec = await planTimes(times);
      b.disabled = false;
      const when = [spec && (spec.days || []).length ? "on " + listText((spec.days || []).map(dayName)) : "",
                    "at " + listText((spec && spec.times && spec.times.length) ? spec.times : times)]
                   .filter(Boolean).join(" ");
      const yes = await confirmStep(b, "Install the schedule?",
        `This asks this computer to run a batch of clips ${when}. Nothing else on the machine changes, and you can remove it again from this card.`,
        "Install it", base, "Really install it?", false);
      if (yes !== true) {
        waiting = yes === "armed";
        return;
      }
      b.disabled = true;
      b.textContent = "Installing...";
      const got = await PeakCut.send("/api/autopilot/install", { confirm: true, times: key });
      if (got && got.installed === true) {
        showDone("install", got);
        PeakCut.toast("The schedule is set.", "ok");
      } else {
        showError(((got && got.schedule) || {}).error || "The server did not confirm the change.");
      }
    } catch (err) {
      /* A refusal carries a full sentence. It is shown as it arrived. */
      const said = (err && err.message) || "The install could not be sent.";
      showError(said);
      PeakCut.toast(said, "bad");
    } finally {
      if (!waiting) {
        disarm(b);
        b.disabled = false;
        b.textContent = base;
      }
    }
  }

  async function doRemove(b) {
    const times = readTimes();
    if (!times) return;
    const key = times.join(",");
    const base = "Remove it";
    let waiting = false;
    b.disabled = true;
    try {
      b.disabled = false;
      const yes = await confirmStep(b, "Remove the schedule?",
        "This asks this computer to drop the Clipstorm schedule. Clips you already made stay where they are. Remove uses the times in the box, so keep the list you installed with.",
        "Remove it", base, "Really remove it?", true);
      if (yes !== true) {
        waiting = yes === "armed";
        return;
      }
      b.disabled = true;
      b.textContent = "Removing...";
      const got = await PeakCut.send("/api/autopilot/remove", { confirm: true, times: key });
      if (got && got.removed === true) {
        showDone("remove", got);
        PeakCut.toast("The schedule was removed.", "ok");
      } else {
        showError(((got && got.schedule) || {}).error || "The server did not confirm the change.");
      }
    } catch (err) {
      const said = (err && err.message) || "The remove could not be sent.";
      showError(said);
      PeakCut.toast(said, "bad");
    } finally {
      if (!waiting) {
        disarm(b);
        b.disabled = false;
        b.textContent = base;
      }
    }
  }

  /* ---------- the cold load ---------- */
  /* plugins.js loads this file about 1.4 seconds after the page boots, and the
     Tools tab is painted once, when it opens. A hard load of
     /app/settings/tools therefore builds the mount before this file has
     registered, and it stays empty.
     Two cases, and they are handled differently on purpose:
       - The mount is empty. Nothing has filled it, so the whole mount is built
         the way index.html would have built it, after every feature file has
         registered. That brings back every card, not only this one, so another
         feature file doing the same thing cannot be starved by this watch.
       - The mount already holds other cards but not this one, so only this
         card is added, and nothing already there is touched. */
  function fillMount() {
    const mount = document.getElementById("toolsec");
    if (!mount) return false;
    if (mount.querySelector(".pcauto")) return true;
    if (!mount.querySelector(".toolsbox")) {
      if (!window.PeakCut._booted) return false;
      try { mount.innerHTML = window.PeakCut.toolsHtml(); }
      catch (err) { return false; }
      Promise.resolve(window.PeakCut.loadTools()).catch(() => {});
      return true;
    }
    let inner = "";
    try { inner = card(); } catch (err) { inner = ""; }
    mount.insertAdjacentHTML("beforeend",
      `<div class="toolsbox" id="tool_autopilot" data-tool="autopilot">${inner}</div>`);
    const def = window.PeakCut.autopilot;
    if (def && typeof def.load === "function") {
      Promise.resolve().then(() => def.load()).catch(() => {});
    }
    return true;
  }

  function watchMount() {
    if (!document.getElementById("toolsec")) return;
    if (fillMount()) return;
    let ticks = 0;
    const timer = setInterval(() => {
      ticks += 1;
      const done = fillMount();
      /* If the page never finishes booting, still put this one card up rather
         than leaving the tab empty. */
      if (done || ticks > 40) {
        clearInterval(timer);
        if (!done) {
          const mount = document.getElementById("toolsec");
          if (mount && !mount.querySelector(".pcauto")) {
            try {
              mount.insertAdjacentHTML("beforeend",
                `<div class="toolsbox" id="tool_autopilot" data-tool="autopilot">${card()}</div>`);
            } catch (err) { /* nothing more this file can do */ }
          }
        }
      }
    }, 250);
  }

  window.PeakCut.add("autopilot", {
    tools: card,

    /* Runs right after the Tools tab puts the card on the page, so a plan you
       already asked for is still there when you come back to it. */
    load() {
      const at = box("pcauto_times");
      if (!at) return;
      if (last.typed) at.value = last.typed;
      if (at.dataset.pcLive !== "1") {
        at.dataset.pcLive = "1";
        at.addEventListener("input", () => { last.typed = at.value; });
      }
      if (last.spec) renderPlan(last.spec, last.prev);
    },

    act: {
      pcauto_plan: b => doPlan(b),
      pcauto_install: b => doInstall(b),
      pcauto_remove: b => doRemove(b),
    },
  });

  watchMount();
})();
