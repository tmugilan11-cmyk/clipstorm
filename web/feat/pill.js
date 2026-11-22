/* One small button in the top bar that says work is happening, from anywhere in the app.
 *
 * A running job used to be visible only on the video list. Open Settings while a video was being made and the app
 * went quiet: no sign of the work, and no way back to it. This counts what is running and takes you to it. */
(() => {
  window.PeakCut.css("pill", `
/* The pill sits on the dark topbar, so the resting states are dark tints with pale
 * ink and the hover states flip to light grounds with dark ink. Every pair below is
 * measured: #FFB27A on --brand-soft 9.43, #7A3406 on #FFEEDF 7.99, var(--bad) on
 * --bad-soft 6.25, #9E121B on #FFE9EA 7.08, --dim on --line 7.49, and #3A2C25 on
 * #F1ECE7 11.42. The flash stops are dark for the same reason (7.0:1 at brightest);
 * a light flash under pale ink measured 1.47:1. */
.pcrun.btn{flex:none;gap:7px;border-color:var(--brand-line);background:var(--brand-soft);color:var(--brand-deep);font-weight:600}
.pcrun.btn:hover{background:#FFEEDF;border-color:#FFC79E;color:#7A3406}
.pcrun.btn:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
.pcrun.btn.is-rec{border-color:#FFD3D5;background:var(--bad-soft);color:var(--bad)}
.pcrun.btn.is-rec:hover{border-color:#FFB9BD;background:#FFE9EA;color:#9E121B}
.pcrun.btn.is-wait{border-color:#606060;background:var(--line);color:var(--dim)}
.pcrun.btn.is-wait:hover{background:#F1ECE7;border-color:#D4CAC3;color:#3A2C25}
.pcrun .pcrun-dot{position:relative;width:8px;height:8px;flex:none;border-radius:50%;background:var(--brand)}
.pcrun .pcrun-dot::after{content:"";position:absolute;inset:-3px;border-radius:50%;border:1px solid var(--brand);opacity:0;animation:pcrunglow 2.2s ease-out infinite}
.pcrun.is-rec .pcrun-dot{background:var(--live)}
.pcrun.is-rec .pcrun-dot::after{border-color:var(--live)}
.pcrun.is-wait .pcrun-dot{background:var(--faint)}
.pcrun.is-wait .pcrun-dot::after{display:none}
.pcrun-2{display:none;font-weight:500;color:var(--dim)}
.pcrun.has2 .pcrun-2{display:inline}
.pcrun.has2 .pcrun-2::before{content:"·";margin:0 5px;color:var(--faint)}
@keyframes pcrunglow{0%{opacity:.75;transform:scale(.65)}70%{opacity:0;transform:scale(1.7)}100%{opacity:0;transform:scale(1.7)}}
/* The flash marks the pill when a job starts. Its stops are dark warm tints, not the light creams they
 * used to be: the ink on the pill is pale (--brand-deep), so a light ground left the label at 1.47:1
 * for the whole animation. These stops keep the pale ink readable (7.0:1 at the brightest). */
.pcrun-flash{animation:pcrunflash 1.8s ease-out 1}
@keyframes pcrunflash{0%{background-color:#3A2415;border-color:#7A4A22}55%{background-color:#2E1D12;border-color:#5A3618}100%{background-color:transparent;border-color:var(--line)}}
@media (max-width:760px){.pcrun.has2 .pcrun-2{display:none}}
@media (max-width:560px){.pcrun.btn{height:30px;padding:0 9px;font-size:12px;gap:6px}.pcrun .pcrun-dot{width:7px;height:7px}}
@media (prefers-reduced-motion:reduce){.pcrun .pcrun-dot::after{display:none}.pcrun-flash{animation:none;background-color:#2E1D12;border-color:#5A3618}}
  `);

  /* ---- what is happening ------------------------------------------------ */
  const state = () => { try { return window.PeakCut.state() || null; } catch { return null; } };

  // One pass over the state the page already polls. A recording is a job with `status: "live"`, but the creator
  // row carries `live_job` a moment before that job reaches the list, so both are counted and never twice.
  function tally() {
    const s = state(), jobs = (s && s.jobs) || [], creators = (s && s.creators) || [];
    let running = 0, waiting = 0, live = 0;
    let firstRun = "", firstWait = "", firstLive = "";
    const seen = new Set();
    for (const j of jobs) {
      if (!j || j.id == null) continue;
      const id = String(j.id), st = String(j.status || "");
      seen.add(id);
      if (st === "running") { running++; if (!firstRun) firstRun = id; }
      else if (st === "queued") { waiting++; if (!firstWait) firstWait = id; }
      else if (st === "live") { live++; if (!firstLive) firstLive = id; }
    }
    for (const c of creators) {
      if (!c || !c.live_job) continue;
      const id = String(c.live_job);
      if (seen.has(id)) continue;
      live++; if (!firstLive) firstLive = id;
    }
    return { running, waiting, live, firstRun, firstWait, firstLive };
  }

  // What the button says. A recording is named as a recording so the two are never added together in one word.
  function words(t) {
    if (t.live) return {
      main: t.live === 1 ? "1 recording" : t.live + " recordings",
      more: t.running ? (t.running === 1 ? "1 video running" : t.running + " videos running") : "",
      kind: "rec", id: t.firstLive,
      hint: t.live === 1 ? "Go to the recording that is running" : "Go to the recordings that are running",
    };
    if (t.running) return {
      main: t.running === 1 ? "1 video running" : t.running + " videos running",
      more: "", kind: "run", id: t.firstRun,
      hint: t.running === 1 ? "Go to the video that is running" : "Go to the videos that are running",
    };
    if (t.waiting) return {
      main: t.waiting === 1 ? "1 video waiting" : t.waiting + " videos waiting",
      more: "", kind: "wait", id: t.firstWait,
      hint: t.waiting === 1 ? "Go to the video that is waiting" : "Go to the videos that are waiting",
    };
    return null;
  }

  /* ---- moving the page -------------------------------------------------- */
  const calm = () => { try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; } };

  function cardFor(id) {
    if (!id) return null;
    try { return document.querySelector('section[data-job="' + CSS.escape(String(id)) + '"]'); } catch { return null; }
  }
  // A live recording is drawn into its own box on the library page, not as a normal job card.
  const liveBox = () => document.querySelector("#live .livecard") || document.querySelector("#live");

  const timers = new WeakMap();
  function flash(node) {
    if (!node) return;
    node.classList.remove("pcrun-flash");
    void node.offsetWidth;                                  // a second click restarts the flash
    node.classList.add("pcrun-flash");
    const old = timers.get(node);
    if (old) clearTimeout(old);
    timers.set(node, setTimeout(() => { node.classList.remove("pcrun-flash"); timers.delete(node); }, 1900));
  }

  function reveal(id, kind) {
    const hit = kind === "rec" ? (cardFor(id) || liveBox()) : cardFor(id);
    if (!hit) return false;
    try { hit.scrollIntoView({ block: "center", behavior: calm() ? "auto" : "smooth" }); }
    catch { try { hit.scrollIntoView(); } catch {} }
    flash(hit);
    return true;
  }

  // The page's own router, reached the same way the sidebar is: the click opens the library and draws the cards
  // before it returns, so the flash can happen right away.
  function toLibrary() {
    const nav = document.querySelector('#nav [data-act="go"][data-v="library"]');
    if (!nav) return false;
    try { nav.click(); return true; } catch { return false; }
  }

  /* ---- the button ------------------------------------------------------- */
  function paint() {
    const bar = document.querySelector(".topbar");
    if (!bar) return;                                       // some pages have no top bar, and that is fine
    let el = bar.querySelector(".pcrun");
    const w = words(tally());
    if (!w) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement("button");
      el.type = "button";
      el.className = "btn sm pcrun";
      el.dataset.act = "pcrungo";
      el.innerHTML = '<span class="pcrun-dot" aria-hidden="true"></span><span class="pcrun-tx"></span><span class="pcrun-2"></span>';
    }
    if (!bar.contains(el)) {                                // the slot the shell already has, just after the actions
      const acts = bar.querySelector("#actions");
      if (acts && acts.parentNode === bar) bar.insertBefore(el, acts.nextSibling); else bar.append(el);
    }
    const tx = el.querySelector(".pcrun-tx"), more = el.querySelector(".pcrun-2");
    if (tx.textContent !== w.main) tx.textContent = w.main;
    if (more.textContent !== w.more) more.textContent = w.more;
    el.classList.toggle("has2", !!w.more);
    el.classList.toggle("is-rec", w.kind === "rec");
    el.classList.toggle("is-wait", w.kind === "wait");
    const said = w.main + (w.more ? ", " + w.more : "");
    if (el.getAttribute("aria-label") !== said) el.setAttribute("aria-label", said);   // the two clauses touch, so name them
    if (el.title !== w.hint) el.title = w.hint;
    if (el.dataset.kind !== w.kind) el.dataset.kind = w.kind;
    el.dataset.job = w.id || "";
  }

  window.PeakCut.add("pill", {
    after: {
      drawShell() { paint(); },                             // the bar was just redrawn
      drawJobs() { paint(); },                              // a job changed, so the words may have too
    },
    act: {
      pcrungo() {
        const w = words(tally());
        if (!w) { paint(); return; }
        const v = String((state() || {}).view || "");
        if (v !== "library" && !toLibrary()) { location.href = "/app/videos"; return; }
        if (!reveal(w.id, w.kind)) {                        // the list can land one frame after the view change
          // A background tab runs no animation frames, so a timer tries as well; whichever comes
          // first scrolls the row into view, and the other then finds it and does nothing.
          setTimeout(() => { reveal(w.id, w.kind); }, 240);
          try { requestAnimationFrame(() => { reveal(w.id, w.kind); }); } catch (err) { /* the timer above did it */ }
        }
        paint();
      },
    },
  });

  // State changes do not always change the top bar, so the button refreshes itself. It only writes when the
  // words actually differ, so this costs a loop over the job list every so often and nothing else.
  try { setInterval(() => { try { paint(); } catch {} }, 1200); } catch {}
})();
