/* The button that reads the numbers and improves the settings, with a way back.
 *
 * One page, in the main menu, because this is something a person does on purpose rather than a setting they
 * set once. It shows what the numbers say, what PeakCut wants to change and why, and an undo for every round.
 *
 * Nothing here invents a number. Every sentence on the page came from /api/learn/state or /api/learn/run. */
(() => {
  window.PeakCut.css("learn", `
    .lrn{display:grid;gap:18px;max-width:900px}
    .lrn .say{margin:0;color:var(--dim);font-size:13px;line-height:1.6}
    .lrn .box{border:1px solid var(--line);border-radius:14px;padding:16px 18px;background:var(--panel)}
    .lrn .box h3{margin:0 0 4px;font-size:15px}
    .lrn .box .sub{color:var(--dim);font-size:13px;line-height:1.55;margin:0 0 12px}
    .lrn .facts{margin:0;padding:0;list-style:none;display:grid;gap:8px}
    .lrn .facts li{display:flex;gap:10px;font-size:13px;line-height:1.55}
    .lrn .facts li::before{content:"";flex:0 0 6px;height:6px;margin-top:7px;border-radius:99px;background:var(--brand)}
    .lrn .run{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:2px}
    .lrn .run .span{margin-left:auto;display:flex;gap:8px;align-items:center;font-size:13px;color:var(--dim)}
    .lrn select{background:var(--panel2);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:13px}
    .lrn .why{margin:12px 0 0;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);font-size:13px;line-height:1.55;color:var(--dim)}
    .lrn .why b{color:var(--ink)}
    .lrn .chg{display:grid;gap:10px;margin:0;padding:0;list-style:none}
    .lrn .chg li{border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;gap:6px}
    .lrn .chg .hd{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
    .lrn .chg .nm{font-weight:600;font-size:13px}
    .lrn .chg code{background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:1px 6px;font-size:12px}
    .lrn .chg .ln{font-size:13px;color:var(--dim);line-height:1.55}
    .lrn .chg .ln b{color:var(--ink);font-weight:600}
    .lrn .none{font-size:13px;color:var(--dim);margin:0}
    .lrn .round{border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;gap:8px}
    .lrn .round .top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
    .lrn .round .when{font-size:13px;color:var(--dim)}
    .lrn .round .did{font-size:13px;line-height:1.55}
    .lrn .round ul{margin:0;padding-left:18px;font-size:13px;color:var(--dim);line-height:1.6}
    .lrn .rounds{display:grid;gap:12px}
    .lrn .empty{font-size:13px;color:var(--dim);line-height:1.6;margin:0}
    .lrn .err{font-size:13px;color:var(--bad);line-height:1.6;margin:0}
    .lrn .cost{font-size:13px;color:var(--dim);margin:4px 0 0}
    .lrn .btnrow{display:flex;gap:8px;flex-wrap:wrap}
    .lrn label.sw{display:flex;gap:8px;align-items:center;font-size:13px;color:var(--dim)}
  `);

  const P = window.PeakCut;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  let STATE = null;         // the last /api/learn/state answer
  let BUSY = false;
  let REPORT = null;        // the last round's report, shown until the page is left
  let ERR = "";
  let COST = null;          // rounds left today, or null when the route has nothing to say

  const NAMES = {
    style: "Caption look",
    hook_words: "How the hook is written",
    clip_len: "How long a clip may be",
    sound: "Sound under a clip",
    captions_always: "Captions on every clip",
  };

  const esc1 = (v) => (v === true ? "on" : v === false ? "off" : (v === "" || v == null) ? "not set" : String(v));

  function when(ts) {
    const t = Number(ts) * 1000;
    if (!t) return "";
    const d = new Date(t);
    const diff = (Date.now() - t) / 1000;
    const say = diff < 90 ? "just now"
      : diff < 3600 ? Math.round(diff / 60) + " minutes ago"
      : diff < 86400 ? Math.round(diff / 3600) + " hours ago"
      : Math.round(diff / 86400) + " days ago";
    return d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
      + " (" + say + ")";
  }

  function factsBlock() {
    const lines = (STATE && STATE.rounds && STATE.rounds[0] && STATE.rounds[0].facts)
      || (STATE && STATE.content && STATE.content.lines) || [];
    const st = (REPORT && REPORT.facts) || lines;
    const src = (REPORT && REPORT.source) || (STATE && STATE.rounds && STATE.rounds[0] && STATE.rounds[0].source) || "";
    const head = src === "youtube" ? "What your channel did"
      : src === "peakcut" ? "What Clipstorm knows" : "What the numbers say";
    if (!st.length) {
      return `<div class="box"><h3>${head}</h3>
        <p class="sub">Clipstorm has not looked yet. Press the button below and it will read the last 28 days first.</p></div>`;
    }
    // The lines a round recorded, plus anything PeakCut has learned about the clips SINCE that round.
    // A clip made after the last round is still evidence, and hiding it would make the page go stale.
    const now = (STATE && STATE.content && STATE.content.lines) || [];
    const extra = now.filter((line) => st.indexOf(line) < 0);
    const clips = (STATE && STATE.content && STATE.content.clips) || 0;
    return `<div class="box"><h3>${head}</h3>
      <p class="sub">Each line is one measurement, with the figure that made it.</p>
      <ul class="facts">${st.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>
      ${extra.length ? `<h4 class="sub" style="margin:14px 0 6px">Your clips, read just now${clips ? ` (${clips})` : ""}</h4>
        <ul class="facts">${extra.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : ""}</div>`;
  }

  function changeLine(c) {
    const nm = NAMES[c.setting] || c.setting;
    // The change's own sentence about the number it expects to move. Left out when the AI did not give one:
    // a made-up promise would be worse than a missing line.
    return `<li><div class="hd"><span class="nm">${esc(nm)}</span>
        <code>${esc(esc1(c.value))}</code></div>
        <div class="ln"><b>Why:</b> ${esc(c.why || "no reason given")}</div>
        ${c.expect ? `<div class="ln"><b>What this should move:</b> ${esc(c.expect)}</div>` : ""}</li>`;
  }

  // A number the server actually sent, or null. This is how the page keeps its promise never to invent one:
  // anything that is not a finite number is treated as missing rather than as zero.
  function num(v) {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function costLine() {
    if (!COST) return "";
    // The server answers in one of two shapes and both are worth showing. `/api/learn/cost` sends a
    // ready-written sentence in `report` ("9 of 20 rounds left today, and 58,000 of 60,000 tokens"), because
    // only it knows both ceilings; an older shape sends the two numbers. Reading just the numbers meant the
    // sentence the server had already written was thrown away and the line never appeared at all.
    if (typeof COST.report === "string" && COST.report.trim()) {
      return `<p class="cost">${esc(COST.report.trim())}</p>`;
    }
    const left = num(COST.left !== undefined ? COST.left : COST.rounds_left);
    const max = num(COST.max !== undefined ? COST.max : (COST.rounds_max !== undefined ? COST.rounds_max : COST.total));
    if (left === null || max === null) return "";
    return `<p class="cost">${left} of ${max} rounds left today</p>`;
  }

  async function readCost() {
    // The cost route is optional. If it is not there, or it answers something this page cannot read,
    // the page says nothing at all: a dash or an apology would be noise under the buttons.
    try {
      const got = await P.api("/api/learn/cost");
      const box = got && typeof got === "object" ? (got.cost && typeof got.cost === "object" ? got.cost : got) : null;
      COST = box;
    } catch {
      COST = null;
    }
    return COST;
  }

  // The two facts that make an empty page honest rather than sad: no clips of this person's own, and no
  // YouTube channel to read instead. Both have to be positively known, because "we could not tell" would
  // print an empty state over a page that is merely still loading.
  function noClips() {
    const c = STATE && STATE.content;
    return !!c && Object.prototype.hasOwnProperty.call(c, "clips") && num(c.clips) === 0;
  }

  function noChannel() {
    const s = STATE || {};
    if (s.channel === false || s.channel_connected === false || s.has_channel === false) return true;
    // The server's own words when there is no channel: `learn.facts` writes this line before anything else.
    const lines = (s.content && s.content.lines) || [];
    return lines.some((l) => String(l || "").indexOf("No YouTube channel is connected") === 0);
  }

  function emptyBlock() {
    if (!noClips() || !noChannel()) return "";
    return `<div class="box"><h3>Nothing to read yet</h3>
      <p class="empty">Make a clip in Clipstorm, or connect a YouTube channel under Settings, and this page will
        have numbers to read.</p></div>`;
  }

  // True only when there is nothing at all to measure. In that one case the empty box takes the place of the
  // facts box, because the only fact the server has to send is "no clips", which the box already says once.
  function nothingAtAll() {
    return !!emptyBlock() && !((STATE && STATE.rounds) || []).length;
  }

  function reportBlock() {
    if (!REPORT) return "";
    const kept = REPORT.changes || [], dropped = REPORT.dropped || [];
    const did = (REPORT.applied || []).length;
    const parts = [];
    if (did) {
      parts.push(`<div class="box"><h3>What Clipstorm changed</h3>
        <p class="sub">${did === 1 ? "One setting was changed" : did + " settings were changed"}, and every one
          is recorded below so it can be put back.</p>
        <ul class="chg">${(REPORT.applied || []).map((a) => `<li><div class="hd">
            <span class="nm">${esc(NAMES[a.setting] || a.setting)}</span>
            <code>${esc(esc1(a.from))}</code> to <code>${esc(esc1(a.to))}</code>
            ${a.ok ? "" : `<span class="pill bad">did not save</span>`}</div>
            ${a.why ? `<div class="ln">${esc(a.why)}</div>` : ""}</li>`).join("")}</ul></div>`);
    }
    if (kept.length) {
      parts.push(`<div class="box"><h3>Why those changes</h3>
        <p class="sub">The AI read the lines above and argued for each of these.</p>
        <ul class="chg">${kept.map(changeLine).join("")}</ul></div>`);
    }
    if (dropped.length) {
      parts.push(`<div class="box"><h3>What was left alone</h3>
        <p class="sub">A suggestion Clipstorm would not act on, and the reason.</p>
        <ul class="chg">${dropped.map((d) => `<li><div class="hd">
            <span class="nm">${esc(NAMES[d.setting] || d.setting || "unknown setting")}</span>
            <code>${esc(esc1(d.value))}</code></div>
            <div class="ln">${esc(d.reason || "")}</div></li>`).join("")}</ul></div>`);
    }
    if (REPORT.saying) {
      parts.push(`<div class="why"><b>In its own words:</b> ${esc(REPORT.saying)}</div>`);
    }
    if ((REPORT.moved || []).length) {
      parts.push(`<div class="why"><b>What moved since the last round:</b><ul>${(REPORT.moved || [])
        .map((m) => `<li>${esc(m)}</li>`).join("")}</ul></div>`);
    }
    if (REPORT.effect) {
      parts.push(`<div class="why"><b>Whether it worked:</b> ${esc(REPORT.effect)}</div>`);
    }
    return parts.join("");
  }

  function roundsBlock() {
    const rounds = (STATE && STATE.rounds) || [];
    if (!rounds.length) {
      return `<div class="box"><h3>Every round</h3>
        <p class="empty">No round has run yet. The first one will appear here with the numbers it read and the
          changes it made, and an undo beside it.</p></div>`;
    }
    return `<div class="box"><h3>Every round</h3>
      <p class="sub">Newest first. Undo puts the settings back to how they were before that round.</p>
      <div class="rounds">${rounds.map((r) => {
        const did = (r.applied || []).filter((a) => a.ok);
        const names = did.map((a) => (NAMES[a.setting] || a.setting) + " to " + esc1(a.value));
        // The pill above already says "nothing changed" when nothing changed, so this line only
        // speaks when it has something to add. Saying it twice in one card reads like a bug.
        const said = did.length ? "Changed " + esc(names.join(", "))
          : (r.saying && (r.facts || []).indexOf(r.saying) < 0 ? esc(r.saying) : "");
        return `<div class="round">
          <div class="top"><span class="when">${esc(when(r.at))}</span>
            ${r.undone ? `<span class="pill">undone</span>` : did.length ? `<span class="pill ok">changed ${did.length}</span>` : `<span class="pill">nothing changed</span>`}
            ${(r.source === "youtube") ? `<span class="pill">YouTube numbers</span>` : `<span class="pill">Clipstorm numbers</span>`}</div>
          ${said ? `<div class="did">${said}</div>` : ""}
          ${(r.facts || []).length ? `<ul>${(r.facts || []).map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : ""}
          ${(r.moved || []).length ? `<div class="did"><b>Since the round before it:</b> ${esc((r.moved || []).join(" "))}</div>` : ""}
          ${did.length && !r.undone ? `<div class="btnrow"><button class="btn sm" data-act="lrnundone" data-at="${esc(r.at)}">Undo this round</button></div>` : ""}
        </div>`;
      }).join("")}</div></div>`;
  }

  function runBlock() {
    if (BUSY) {
      return `<div class="box"><h3>Working</h3>
        <p class="sub">Clipstorm is reading the numbers and asking the AI what to change. This takes a few seconds.</p>
        <div class="btnrow"><button class="btn" disabled>Analysing…</button></div></div>`;
    }
    const can = STATE && STATE.can_run;
    const why = (STATE && STATE.why_not) || "";
    const last = STATE && STATE.rounds && STATE.rounds[0];
    const days = (last && last.days) || 28;
    return `<div class="box"><h3>Improve from the numbers</h3>
      <p class="sub">Clipstorm reads what your channel actually did, then changes at most two settings: the caption
        look, how the hook is written, how long a clip may be, the sound under a clip, or whether captions burn in.
        It never touches anything else, and every round can be undone.</p>
      <div class="run">
        <button class="btn" data-act="lrnrun" ${can ? "" : "disabled"}>Analyse and improve</button>
        <button class="btn sm" data-act="lrndry">What would it change?</button>
        <span class="span"><label class="sw">Look at
          <select id="lrn_days">
            ${[7, 28, 90, 365].map((d) => `<option value="${d}"${d === days ? " selected" : ""}>${d} days</option>`).join("")}
          </select></label></span>
      </div>
      ${costLine()}
      ${why ? `<div class="why">${esc(why)}</div>` : ""}
      </div>`;
  }

  function body() {
    return `<div class="lrn">
      <p class="say">Press one button and Clipstorm reads how your clips did, then improves the settings that decide
        what the next clip looks like. Nothing is claimed as an improvement until the next round has the numbers
        to prove it, and everything it changes can be put back.</p>
      ${runBlock()}
      ${ERR ? `<div class="box"><h3>That did not work</h3><p class="err">${esc(ERR)}</p></div>` : ""}
      ${reportBlock()}
      ${nothingAtAll() ? "" : factsBlock()}
      ${emptyBlock()}
      ${roundsBlock()}
      </div>`;
  }

  function paint() {
    const host = document.querySelector(".lrn");
    if (!host) return;
    const view = document.getElementById("view");
    if (!view) return;
    view.innerHTML = body();
  }

  async function load() {
    const view = document.getElementById("view");
    if (view && !view.querySelector(".lrn")) view.innerHTML = body();
    // Both reads go out together: the cost line is one short sentence and must not hold up the page.
    const [, state] = await Promise.all([
      readCost(),
      P.api("/api/learn/state").then((got) => ({ ok: true, got }), (e) => ({ ok: false, e })),
    ]);
    if (state.ok) {
      STATE = state.got && state.got.state ? state.got.state : state.got;
      ERR = "";
    } else {
      ERR = String((state.e && state.e.message) || state.e || "Clipstorm could not read what it knows.");
      STATE = STATE || { rounds: [], can_run: false, why_not: "" };
    }
    paint();
  }

  async function run(dry) {
    if (BUSY) return;
    BUSY = true;
    REPORT = null;
    ERR = "";
    paint();
    try {
      const days = Number((document.getElementById("lrn_days") || {}).value) || 28;
      const got = await P.send("/api/learn/run", { days, dry }, "POST");
      REPORT = got && got.report ? got.report : got;
      if (!dry) {
        try {
          const after = await P.api("/api/learn/state");
          STATE = after && after.state ? after.state : after;
        } catch { /* the report is already on screen; the log catches up on the next visit */ }
      }
      if (dry) P.toast("That is what it would change. Nothing was changed.", "ok");
      else P.toast((REPORT.applied || []).length ? "Done. The changes are recorded and can be undone."
                                                 : "Nothing needed changing this time.", "ok");
    } catch (e) {
      ERR = String((e && e.message) || e || "Clipstorm could not finish the round.");
      P.toast(ERR, "bad");
    } finally {
      BUSY = false;
      // A real round spends one, so the line goes stale the moment it succeeds. A preview spends nothing,
      // which is why only the real one re-reads it.
      if (!dry && !ERR) await readCost();
      paint();
    }
  }

  async function undo(at) {
    try {
      await P.send("/api/learn/undo", { at: Number(at) }, "POST");
      P.toast("Put back the way it was.", "ok");
      REPORT = null;
      await load();
    } catch (e) {
      ERR = String((e && e.message) || e || "Clipstorm could not undo that round.");
      P.toast(ERR, "bad");
      paint();
    }
  }

  P.page("improve", {
    nav: "Improve",
    icon: "bolt",
    group: "Understand",
    order: 22,
    path: "improve",
    tip: "Read how your clips did and improve the settings that decide what they look like",
    view: body,
    load,
  });

  P.add("learn", {
    act: {
      lrnrun: () => run(false),
      lrndry: () => run(true),
      lrnundone: (btn) => undo(btn && btn.dataset ? btn.dataset.at : null),
    },
  });
})();
