/* Status pills with live counts and a search box for the list of videos.
 *
 * The All videos page is one long column with no way to narrow it. This puts a bar above the list: four pills
 * (All, Making, Ready, Failed) that carry their own counts, and a search box that reads the job title, the source
 * name and the title or hook of every clip on that video. All of it runs in the page; nothing is asked of the
 * server and no video is re-fetched.
 *
 * The bar is built once per holder. It is a child of the element that holds #jobs, never a child of #jobs itself,
 * because drawJobs() writes the empty-state markup straight into #jobs and would wipe anything living in there. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  P.css("filters", `
    .pcf-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 20px}
    .pcf-pills{display:flex;flex-wrap:wrap;gap:6px;min-width:0}
    /* The ring around a pill is the only thing that separates it from the page behind it: the pill's own
     * background is the page's --bg, and so is the dialog's ground, so the old --line ring (#1E1E1E)
     * measured 1.19:1 there and the pill read as plain text rather than a control. #6B6B6B measures
     * 3.72:1 on that ground and 3.54:1 on #111111 (the lightest ground it can touch), both above the 3:1
     * minimum for a control's visible boundary. */
    .pcf-pill{display:inline-flex;align-items:center;gap:7px;height:32px;padding:0 12px;border-radius:999px;
      border:1px solid #6B6B6B;background:var(--bg);color:var(--dim);font-size:13px;font-weight:500;
      cursor:pointer;white-space:nowrap;transition:background-color .15s ease,border-color .15s ease,color .15s ease}
    .pcf-pill:hover{background:var(--muted);color:var(--text)}
    .pcf-pill[aria-pressed="true"]{background:var(--brand-soft);border-color:var(--brand-line);color:var(--text)}
    .pcf-pill b{font-weight:600;color:var(--faint);font-variant-numeric:tabular-nums}
    .pcf-pill[aria-pressed="true"] b{color:var(--brand-deep)}
    .pcf-search{position:relative;flex:1 1 180px;min-width:0;max-width:300px;margin-left:auto}
    .pcf-search svg{position:absolute;left:11px;top:50%;transform:translateY(-50%);width:15px;height:15px;
      fill:none;stroke:var(--faint);stroke-width:1.8;stroke-linecap:round;pointer-events:none}
    .pcf-search input[type="search"]{height:34px;padding:0 12px 0 32px;font-size:13px;border-radius:999px;
      background:var(--muted);border-color:transparent}
    .pcf-search input[type="search"]:focus{background:var(--bg);border-color:var(--brand)}
    .pcf-none{margin:8px 0 0;padding:34px 20px;border:1px dashed var(--line-2);border-radius:var(--r);
      text-align:center;color:var(--dim);font-size:13px}
    .pcf-none b{display:block;color:var(--text);font-size:15px;font-weight:600;margin-bottom:2px}
    /* The filter hides two kinds of element: a job card (a section inside #jobs) and, while the filter hides
     * everything, the page's own empty-state block. The selectors are written long on purpose: the page draws
     * .empty{display:flex} at a lower weight, and a short [data-pcfilter="out"] rule could lose to it. */
    #jobs section[data-pcfilter="out"],#jobs > .empty[data-pcfilter="out"]{display:none}
    @media (max-width:560px){.pcf-search{flex-basis:100%;max-width:none;margin-left:0}}
    /* On a phone the pills grow to a 44px tap target; min-height wins over the 32px height above. */
    @media (max-width:640px){.pcf-pill{min-height:44px}}
  `);

  // Remembered across redraws, so a tick from the server never throws the choice away.
  let mode = "all";      // all | make | ready | failed
  let query = "";

  /* "Making" is anything still being worked on, "Ready" is done, "Failed" is error. A live recording is neither of
   * the three, so it is only counted in All. */
  const bucket = (status) => {
    const s = String(status || "");
    if (s === "queued" || s === "running") return "make";
    if (s === "done") return "ready";
    if (s === "error") return "failed";
    return "";
  };

  // The jobs drawJobs would put on this page: everything, or one creator's videos when their page is open. A live
  // recording is shown in its own box above the list, not as a card, so it is left out of the counts the same way.
  function listed() {
    let state = null;
    try { state = P.state(); } catch { state = null; }
    const all = state && Array.isArray(state.jobs) ? state.jobs : [];
    const view = String((state && state.view) || "");
    const cid = view.startsWith("c:") ? view.slice(2) : "";
    const mine = cid ? all.filter(j => j && j.creator === cid) : all;
    return document.querySelector("#live") ? mine.filter(j => j && j.status !== "live") : mine;
  }

  function matches(job, text) {
    if (!job) return false;
    if (mode !== "all" && bucket(job.status) !== mode) return false;
    if (!text) return true;
    const hay = [];
    if (job.title) hay.push(job.title);
    if (job.source && job.source.name) hay.push(job.source.name);
    const clips = Array.isArray(job.clips) ? job.clips : [];
    for (const c of clips) {
      if (!c) continue;
      if (c.title) hay.push(c.title);
      if (c.hook) hay.push(c.hook);
    }
    return hay.some(s => String(s).toLowerCase().includes(text));
  }

  const BAR_HTML = `<div class="pcf-pills" role="group" aria-label="Which videos to show">
      <button type="button" class="pcf-pill" data-pcf="all" aria-pressed="true">All <b>0</b></button>
      <button type="button" class="pcf-pill" data-pcf="make" aria-pressed="false">Making <b>0</b></button>
      <button type="button" class="pcf-pill" data-pcf="ready" aria-pressed="false">Ready <b>0</b></button>
      <button type="button" class="pcf-pill" data-pcf="failed" aria-pressed="false">Failed <b>0</b></button>
    </div>
    <div class="pcf-search" role="search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><line x1="16" y1="16" x2="20" y2="20"/></svg>
      <input type="search" class="pcf-q" placeholder="Search videos and clips" autocomplete="off" spellcheck="false"
        aria-label="Search videos by title, source name, or the title and hook of their clips">
    </div>`;

  const barOf = (holder) => holder ? holder.querySelector(":scope > .pcf-bar") : null;

  /* One bar per holder, built the first time the list is drawn and left alone after that. It goes directly above
   * #jobs, so it heads the list itself and not the paste-a-link box that sits above it on All videos. */
  function ensure(holder, root) {
    let bar = barOf(holder);
    if (bar) return bar;
    bar = document.createElement("div");
    bar.className = "pcf-bar";
    bar.innerHTML = BAR_HTML;                    // a fixed string, no server value goes in here
    holder.insertBefore(bar, root || holder.firstChild);
    const input = bar.querySelector("input");
    if (input) {
      input.value = query;
      input.addEventListener("input", () => { query = input.value; paint(); });
      input.addEventListener("search", () => { query = input.value; paint(); });
      input.addEventListener("keydown", (e) => {
        if (e.key !== "Escape") return;
        e.stopPropagation();
        input.value = ""; query = "";
        paint();
      });
    }
    bar.addEventListener("click", (e) => {
      const btn = e.target.closest ? e.target.closest(".pcf-pill") : null;
      if (!btn) return;
      e.preventDefault();
      mode = btn.dataset.pcf || "all";
      paint();
    });
    return bar;
  }

  /* Idempotent: a second pass with the same numbers writes nothing, so the page's repaint loop stays quiet. */
  function counts(bar) {
    const jobs = listed();
    const n = {all: jobs.length, make: 0, ready: 0, failed: 0};
    for (const j of jobs) {
      const b = bucket(j && j.status);
      if (b) n[b] += 1;
    }
    const pills = bar.querySelectorAll(".pcf-pill");
    for (const btn of pills) {
      const key = btn.dataset.pcf;
      const num = btn.querySelector("b");
      const want = String(n[key] == null ? 0 : n[key]);
      if (num && num.textContent !== want) num.textContent = want;
      const pressed = String(key === mode);
      if (btn.getAttribute("aria-pressed") !== pressed) btn.setAttribute("aria-pressed", pressed);
    }
  }

  function noneLine(holder, root) {
    let el = holder.querySelector(":scope > .pcf-none");
    if (el) return el;
    el = document.createElement("p");
    el.className = "pcf-none";
    const b = document.createElement("b");
    b.textContent = "Nothing matches that.";
    const small = document.createElement("span");
    small.textContent = "Clear the search, or pick All.";
    el.append(b, small);
    root.insertAdjacentElement("afterend", el);
    return el;
  }

  function apply(root) {
    if (!root || !root.parentElement) return;
    const holder = root.parentElement;
    const bar = ensure(holder, root);
    counts(bar);

    const text = query.trim().toLowerCase();
    const active = mode !== "all" || text !== "";
    const jobs = new Map();
    for (const j of listed()) if (j && j.id != null) jobs.set(String(j.id), j);

    let shown = 0;
    const sections = root.querySelectorAll("section[data-job]");
    for (const sec of sections) {
      const job = jobs.get(String(sec.dataset.job));
      const on = !active || matches(job, text);
      if (on) {
        shown += 1;
        if (sec.hasAttribute("data-pcfilter")) sec.removeAttribute("data-pcfilter");
      } else if (sec.getAttribute("data-pcfilter") !== "out") {
        sec.setAttribute("data-pcfilter", "out");
      }
    }

    // drawJobs writes its own "No videos yet" block into #jobs. While a filter is hiding everything, that text is
    // wrong, so it steps aside for one line of ours and comes back when the filter is cleared. If the page drew no
    // cards at all there are simply no videos yet, and its own words are already right.
    const own = root.querySelector(":scope > .empty");
    const hideOwn = active && !shown && sections.length > 0;
    if (own) {
      if (hideOwn) { if (own.getAttribute("data-pcfilter") !== "out") own.setAttribute("data-pcfilter", "out"); }
      else if (own.hasAttribute("data-pcfilter")) own.removeAttribute("data-pcfilter");
    }
    const line = holder.querySelector(":scope > .pcf-none");
    if (hideOwn) noneLine(holder, root);
    else if (line) line.remove();
  }

  function paint() {
    const roots = document.querySelectorAll("#jobs");
    for (const root of roots) apply(root);
  }

  /* The page repaints #jobs on its own loop and the plug-in hooks fire when that markup changes. The slow tick is
   * only a safety net: counts must stay right when a job changes status without changing the length of its card. */
  let timer = 0;

  P.add("filters", {
    after: {
      drawJobs(root) {
        apply(root);
        if (!timer) timer = setInterval(paint, 800);
      },
    },
  });
})();
