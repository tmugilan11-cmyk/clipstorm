/* This week, at a glance: seven day columns with the clips made and the posts that went out,
 * then the posts still waiting, soonest out first.
 *
 * The home page already draws fourteen days of the same numbers as one bar chart, which answers
 * "how am I doing" but not "what happened on Tuesday". The card is a page of its own in the menu; it
 * the smaller question: a week of days as columns you can read across, plus the queue that has not gone
 * out yet, so a week with a quiet day in it looks quiet instead of smooth. */
(() => {
  window.PeakCut.css("grid", `
    .pcgrid{margin-top:14px;display:grid;gap:16px}
    .pcgrid-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--ink);margin-bottom:6px}
    .pcgrid .row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .pcgrid .wk{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}
    .pcgrid .d{display:grid;gap:7px;padding:10px 8px 10px;border:1px solid var(--line);border-radius:var(--r);background:var(--muted)}
    .pcgrid .d.now{border-color:var(--brand-line);background:var(--brand-soft)}
    .pcgrid .wd{display:flex;justify-content:space-between;gap:4px;align-items:baseline;font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--dim)}
    .pcgrid .wd b{font-size:11px;font-weight:500;letter-spacing:0;text-transform:none;color:var(--faint)}
    .pcgrid .d.now .wd,.pcgrid .d.now .wd b{color:var(--brand-deep)}
    .pcgrid .plot{height:104px;display:flex;align-items:flex-end;justify-content:center;padding-bottom:2px}
    .pcgrid .bar{width:100%;max-width:24px;min-height:2px;margin:0;border:0;border-radius:4px 4px 2px 2px;background:var(--brand);transition:height .3s ease}
    /* The zero-day floor: measured #6B6B6B = 3.54:1 on the #111111 day panel and 3.12:1 on the
     * #2A1B10 today panel, above the 3:1 non-text minimum, and clearly quieter than a filled bar
     * (#FF8B33 = 8.09:1). var(--line-2) #2A2A2A measured 1.32:1 there, invisible. */
    .pcgrid .bar.zero{background:#6B6B6B}
    .pcgrid .num{display:grid;gap:1px;text-align:center;line-height:1.3}
    .pcgrid .num b{font-size:16px;font-weight:600;font-variant-numeric:tabular-nums}
    .pcgrid .num span{font-size:11px;color:var(--dim);font-variant-numeric:tabular-nums;white-space:nowrap}
    .pcgrid .num .v{color:var(--brand-deep)}
    .pcgrid .foot{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:baseline;font-size:12px;color:var(--dim);padding:0 1px}
    .pcgrid .foot b{color:var(--text);font-weight:600;font-variant-numeric:tabular-nums}
    .pcgrid .qhead{display:flex;justify-content:space-between;gap:10px;align-items:baseline;border-top:1px solid var(--line);padding-top:12px;font-size:12px;font-weight:600;color:var(--dim)}
    .pcgrid .qi{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:baseline;padding:7px 0;border-top:1px solid var(--line);font-size:13px}
    .pcgrid .qi:first-child{border-top:0}
    .pcgrid .qi .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .pcgrid .qi .t small{display:block;color:var(--dim);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .pcgrid .qi .w{text-align:right;white-space:nowrap;font-size:12px;color:var(--dim);font-variant-numeric:tabular-nums}
    .pcgrid .qi .w b{display:block;color:var(--text);font-weight:600}
    .pcgrid .err,.pcgrid .muted{color:var(--dim);font-size:13px}
    @media (max-width:640px){
      .pcgrid .wk{grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
      .pcgrid .d{padding:8px 6px}
      .pcgrid .plot{height:76px}
      .pcgrid .num b{font-size:15px}
    }
    @media (prefers-reduced-motion:reduce){.pcgrid .bar{transition:none}}
  `);

  // Short numbers: 980 stays 980, 1200 is 1.2k, 3400000 is 3.4m.
  const short = (n) => {
    n = Number(n) || 0;
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "m";
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
    return String(Math.round(n));
  };

  const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  // A day arrives as "YYYY-MM-DD" already in local time. Building the Date from its parts keeps the
  // browser from reading it as UTC midnight and showing the day before for anyone west of London.
  function parted(day) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(day || ""));
    return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
  }
  const sameDay = (a, b) => a.getDate() === b.getDate() && a.getMonth() === b.getMonth() && a.getFullYear() === b.getFullYear();
  function dayName(day) { const d = parted(day); return d ? WD[d.getDay()] : ""; }
  function dayNum(day) { const d = parted(day); return d ? `${d.getDate()} ${MON[d.getMonth()]}` : ""; }
  function isToday(day) { const d = parted(day); return !!d && sameDay(d, new Date()); }

  // "Today 18:30", "Tomorrow 09:00", or the weekday and date when it is further out. Due times are unix seconds.
  function due(t) {
    const s = Number(t) || 0;
    if (!s) return "No time set";
    const d = new Date(s * 1000), n = new Date();
    const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    if (sameDay(d, n)) return `Today ${hm}`;
    if (sameDay(d, new Date(n.getTime() + 86400000))) return `Tomorrow ${hm}`;
    return `${WD[d.getDay()]} ${d.getDate()} ${MON[d.getMonth()]}, ${hm}`;
  }

  // What the server really sets a post to while it is still waiting (studio/posting.py: OPEN).
  const WAITING = new Set(["scheduled", "posting"]);
  const LABEL = { scheduled: "Scheduled", posting: "Posting now" };

  function body(o) {
    const all = (o && Array.isArray(o.daily)) ? o.daily.filter(d => d && d.day) : [];
    if (!all.length) return `<p class="muted">The server sent no days to draw. Press Refresh to ask again.</p>`;

    const week = all.slice(-7);                  // the last seven of the fourteen the server sends
    const posts = (o && Array.isArray(o.posts)) ? o.posts : [];
    const peak = Math.max(1, ...week.map(d => Number(d.clips) || 0));
    const H = 104;

    const cols = week.map(d => {
      const clips = Number(d.clips) || 0, posted = Number(d.posted) || 0, views = Number(d.views) || 0;
      // Never a zero-height bar: an empty day keeps a 2px floor so the column still reads as a day.
      const h = Math.max(2, Math.round(clips / peak * H));
      const say = `${dayName(d.day)} ${dayNum(d.day)}: ${clips} clip${clips === 1 ? "" : "s"} made, ${posted} posted, ${views} view${views === 1 ? "" : "s"}`;
      return `<div class="d${isToday(d.day) ? " now" : ""}" role="listitem" aria-label="${esc(say)}">
          <div class="wd">${esc(dayName(d.day))}<b>${esc(dayNum(d.day))}</b></div>
          <div class="plot"><div class="bar${clips ? "" : " zero"}" style="height:${h}px" title="${esc(say)}"></div></div>
          <div class="num"><b>${esc(String(clips))}</b><span>clips</span>
            <span>${esc(String(posted))} post${posted === 1 ? "" : "s"}</span>
            <span class="v">${esc(short(views))} views</span></div>
        </div>`;
    }).join("");

    const made = week.reduce((a, d) => a + (Number(d.clips) || 0), 0);
    const out = week.reduce((a, d) => a + (Number(d.posted) || 0), 0);
    const seen = week.reduce((a, d) => a + (Number(d.views) || 0), 0);

    // Soonest out first, which is the order the queue runs in (studio/posting.py sorts the open-post
    // queue ascending by due_at). Ten at most, and the count says how many were left off so ten never
    // looks like all of them.
    const waitingAll = posts.filter(p => p && WAITING.has(String(p.status || "")))
      .sort((a, b) => (Number(a.due_at) || 0) - (Number(b.due_at) || 0));
    const waiting = waitingAll.slice(0, 10);

    const queue = waiting.length
      ? waiting.map(p => `<div class="qi">
            <div class="t">${esc(p.title || "Clip")}<small>${esc(p.creator_name || "No creator")}</small></div>
            <div class="w"><b>${esc(due(p.due_at))}</b>${esc(LABEL[String(p.status)] || "Waiting")}</div>
          </div>`).join("")
      : `<p class="muted">Nothing queued.</p>`;

    const clipWord = made === 1 ? "clip" : "clips";
    return `<div class="wk" role="list" aria-label="The last seven days, one column per day">${cols}</div>
      <div class="foot"><span><b>${esc(String(made))}</b> ${clipWord} made</span><span><b>${esc(String(out))}</b> posted</span><span><b>${esc(short(seen))}</b> views</span></div>
      <div class="qhead"><span>Waiting to go out</span><span>${waitingAll.length ? `${waiting.length} of ${waitingAll.length}` : "Empty"}</span></div>
      <div class="q" role="list" aria-label="Posts waiting to go out">${queue}</div>`;
  }

  // Write into the card if it is on the page. A draw that finishes after the person has navigated away
  // finds no card to fill, so every write checks first and returns quietly when it is not there.
  function paint(html) {
    const box = document.getElementById("pcgrid");
    if (box) box.innerHTML = html;
  }

  async function draw() {
    paint(`<p class="muted">Reading this week…</p>`);
    let data;
    try { data = await window.PeakCut.api("/api/overview"); }
    catch (err) { paint(`<p class="err">Could not read this week. ${esc(String((err && err.message) || err || ""))}</p>`); return; }
    try { paint(body(data)); }
    catch { paint(`<p class="err">This week came back in a shape this card does not know. Press Refresh to ask again.</p>`); }
  }

  // The card is its own page now. The Tools page holds scheduling only and has no generic plugin mount
  // any more, so the card had no home there. A page of its own is how every other read-only summary
  // reaches the person (menu-pages.js, learn.js): PeakCut.page puts the row in the menu under
  // "Understand", gives it the address /app/week, and draws the same card the Tools tab used to.
  window.PeakCut.page("week", {
    nav: "This week",
    icon: "chart",
    tip: "The week's clips and posts, one column per day",
    path: "week",
    group: "Understand",
    order: 21,
    view() {
      return `<section class="set-sec"><h1 class="pcgrid-h">This week</h1>
          <p class="help">Seven days as columns: the clips made, the posts that went out, and the views they brought in. Below that, the posts still waiting, soonest out first.</p>
          <div class="pcgrid"><div class="row"><button class="btn sm" data-act="pcgridrefresh">Refresh</button></div><div id="pcgrid"></div></div>
        </section>`;
    },
    async load() { await draw(); },
  });

  window.PeakCut.add("grid", {
    /** Called when the week page opens. */
    async load() { await draw(); },

    act: {
      /** [data-act="pcgridrefresh"] asks the server again and redraws. */
      async pcgridrefresh(el) {
        const btn = (el && el.closest && el.closest("button")) || el;
        if (btn && btn.disabled) return;                 // a second press while the first is running
        if (btn) { btn.disabled = true; btn.textContent = "Refreshing…"; }
        try { await draw(); }
        finally { if (btn) { btn.disabled = false; btn.textContent = "Refresh"; } }
      },
    },
  });

})();
