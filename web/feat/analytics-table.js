/* Every video, one row, with its numbers for the last N days. Fills #an_table, the Content tab.
 * The panel asks for a number of days, because that is the only window /api/analytics/videos reads;
 * the days it prints are the two the server answered with, not a range this page invented.
 * Headers sort on click and a second click flips them. Search narrows by title as you type.
 * A number the server did not send is a hyphen, never a zero. */
(() => {
  const P = window.PeakCut;
  if (!P) return;
  P.css("analytics-table", `
    .ant{display:flex;flex-direction:column;gap:14px}
    .ant-bar{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap}
    .ant-count{font-size:15px;font-weight:600;color:var(--text)}
    .ant-pick{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--dim)}
    .ant-pick select,.ant-tools input{height:34px;border:1px solid var(--line-2);border-radius:8px;background:var(--bg);font-size:13px;color:var(--text)}
    .ant-pick select{padding:0 10px;font-weight:500}
    .ant-tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    .ant-tools input{width:240px;max-width:100%;padding:0 11px}
    .ant-t{width:100%;border-collapse:collapse;font-size:13px;min-width:960px}
    .ant-t th{padding:0 10px 9px;border:0;border-bottom:1px solid var(--line-2);vertical-align:bottom;white-space:nowrap}
    .ant-t th button{display:inline-flex;align-items:center;gap:4px;padding:0;border:0;background:none;font:inherit;font-size:12px;font-weight:500;color:var(--faint);cursor:pointer}
    .ant-t th button:hover{color:var(--text)}
    .ant-t th[aria-sort] button{color:var(--text);font-weight:600}
    .ant-s,.ant-s svg{width:12px;height:12px}.ant-s{opacity:0;display:inline-flex}
    .ant-t th[aria-sort] .ant-s{opacity:1;color:var(--brand)}
    .ant-t th[aria-sort=ascending] .ant-s{transform:rotate(180deg)}
    .ant-t td{padding:10px;border:0;border-bottom:1px solid var(--line);vertical-align:middle}
    .ant-t tbody tr:hover td{background:var(--muted)}
    .ant-v{display:flex;align-items:center;gap:10px;min-width:260px}
    .ant-th,.ant-ph{flex:none;width:68px;height:38px;border:1px solid var(--line);border-radius:6px;background:var(--muted)}
    .ant-th{object-fit:cover}.ant-ph{display:grid;place-items:center;color:var(--faint)}.ant-ph svg{width:16px;height:16px}
    .ant-name{font-weight:500;color:var(--text);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;max-width:340px}
    .ant-short:not(:empty){display:inline-block;margin-top:3px;font-size:11px;font-weight:600;color:var(--brand-deep)}
    .ant-u{color:var(--faint);font-weight:400}.ant-na{color:var(--faint);cursor:help}
    .ant-empty{padding:36px 18px;text-align:center;color:var(--dim);border:1px dashed var(--line-2);border-radius:var(--r)}
    .ant-empty b{display:block;color:var(--text);font-size:15px;margin-bottom:4px}
    .ant-err{margin:0;padding:12px 14px;border-radius:var(--r);background:var(--bad-soft);color:var(--bad);font-size:13px}
    .ant-err button{margin-left:8px;border:0;background:none;color:var(--bad);font-weight:600;text-decoration:underline;cursor:pointer}
    @media (max-width:700px){.ant-pick,.ant-tools input{width:100%}}
  `);

  const DAYS = [7, 28, 90, 365], CACHE = new Map(), DEAD = "-";   // a hyphen: that number was not sent
  let days = 28, q = "", sort = { key: "views", dir: -1 };

  const COLS = [
    { k: "title", h: "Video", tip: "The video. Sorting puts titles in alphabetical order." },
    { k: "views", h: "Views", tip: "How many times the video was played.", num: 1 },
    { k: "watch", h: "Watch time", u: "hours", tip: "Total time people spent watching, in hours.", num: 1 },
    { k: "avd", h: "Avg view duration", u: "min:sec", tip: "How long an average view lasted.", num: 1 },
    { k: "avp", h: "Avg viewed", u: "%", tip: "The share of the video an average view watched.", num: 1 },
    { k: "imp", h: "Impressions", tip: "How often the thumbnail was shown. Shorts often do not report this.", num: 1 },
    { k: "ctr", h: "Click-through", u: "%", tip: "The share of impressions that became views. Shorts often do not report this.", num: 1 },
    { k: "likes", h: "Likes", tip: "How many people liked it.", num: 1 },
    { k: "comments", h: "Comments", tip: "How many comments it got.", num: 1 },
    { k: "shares", h: "Shares", tip: "How many times it was shared.", num: 1 },
    { k: "subs", h: "Subscribers", u: "gained", tip: "Subscribers gained while watching this video.", num: 1 },
  ];
  const INT = new Set(["views", "imp", "likes", "comments", "shares", "subs"]);
  const nf = new Intl.NumberFormat();
  const nf1 = new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? null : Number(v));
  const dayTxt = (s) => {
    const d = new Date(String(s || "").slice(0, 10) + "T00:00:00");
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
  };
  const first = (o, keys) => keys.reduce((hit, k) => (hit !== null ? hit : o[k] ?? null), null);
  const caret = () => `<span class="ant-s">${ic("caret")}</span>`;
  const LOADING = `<div class="ant-empty"><b>Loading the video list.</b>The numbers land here as soon as the server answers.</div>`;

  const MOST = 3650;   // the route's own limit: /api/analytics/videos refuses anything wider

  // /api/analytics/videos reads one number, `days`, and counts back from today. It has no start or end
  // argument, so a range shown elsewhere on the page becomes that count here instead of being sent and
  // silently dropped. A whole number of days is the only thing this panel can honestly ask for.
  let pick = false;
  function asked() {
    const P2 = window.PeakCutAnalytics, r = (pick || !P2 ? {} : P2) || {}, g = r.range || r;
    const s = String(g.start || g.from || "").slice(0, 10), e = String(g.end || g.to || "").slice(0, 10);
    const from = new Date(s + "T00:00:00"), to = new Date(e + "T00:00:00");
    const span = from.getTime() && to.getTime() ? Math.round((to - from) / 864e5) + 1 : 0;
    if (span > 0) return Math.min(MOST, Math.max(1, span));
    const n = Number(g.days);
    return Number.isFinite(n) && n >= 0 ? Math.min(MOST, n) : days;
  }

  function mmss(s) {
    const t = Math.max(0, Math.round(Number(s) || 0)), m = Math.floor(t / 60), r = t % 60;
    return m < 60 ? m + ":" + String(r).padStart(2, "0")
      : Math.floor(m / 60) + ":" + String(m % 60).padStart(2, "0") + ":" + String(r).padStart(2, "0");
  }

  function hours(v, units) {                    // hours, because the header says hours
    const h = num(first(v, ["watch_time_hours", "watch_hours"]));
    if (h !== null) return h;
    const m = num(first(v, ["watch_time_minutes", "watch_time"])), u = (units && units.watch_time) || "minutes";
    return m === null ? null : u === "hours" ? m : u === "seconds" ? m / 3600 : m / 60;
  }

  const pct = (v, keys, units) => {
    const n = num(first(v, keys));
    return n === null ? null : (units && units.percent === "fraction") ? n * 100 : n;
  };

  function normalize(v, units) {
    return {
      title: String(first(v, ["title", "video_title", "name"]) || "Untitled video"),
      thumb: first(v, ["thumbnail", "thumb", "thumbnail_url"]),
      short: !!(v.is_short || v.short || String(v.format || "").toLowerCase() === "short"),
      views: num(first(v, ["views", "view_count"])), watch: hours(v, units),
      avd: num(first(v, ["average_view_duration", "avg_view_duration", "avg_duration"])),
      avp: pct(v, ["average_view_percentage", "avg_view_percentage", "avg_viewed"], units),
      imp: num(first(v, ["impressions", "impression_count"])),
      ctr: pct(v, ["click_through_rate", "ctr", "click_through"], units),
      likes: num(first(v, ["likes", "like_count"])), comments: num(first(v, ["comments", "comment_count"])),
      shares: num(first(v, ["shares", "share_count"])),
      subs: num(first(v, ["subscribers_gained", "subs_gained", "subscribers"])),
    };
  }

  function rowsOf(data) {
    const list = Array.isArray(data) ? data : data && (data.videos || data.rows || data.items);
    const units = Object.assign({}, (data && !Array.isArray(data) && data.units) || {});
    // /api/analytics/videos already divides minutes by 60 before it answers: its watch_time is hours
    // (studio/api_analytics.py, the `watch_time` key). It sends no units block, so the fallback
    // "minutes" would divide those hours again and report a sixtieth of the real figure.
    if (!Array.isArray(data) && data && data.rows && !units.watch_time) units.watch_time = "hours";
    return (Array.isArray(list) ? list : []).map((v) => normalize(v || {}, units));
  }

  async function get(path) {
    if (typeof P.api === "function") return P.api(path);
    const r = await fetch(path);
    if (!r.ok) throw new Error(r.status === 404 ? "This server has no analytics route yet." : (r.statusText || "The request failed."));
    return r.json();
  }

  const head = () => COLS.map((c) => `<th scope="col" class="${c.num ? "num" : ""}" data-k="${c.k}" title="${esc(c.tip)}">`
    + `<button type="button" data-sort="${c.k}">${esc(c.h)}${c.u ? ` <span class="ant-u">${esc(c.u)}</span>` : ""}${caret()}</button></th>`).join("");

  function cell(key, r) {
    const v = r[key];
    if (v !== null) return `<td class="num">${key === "avd" ? mmss(v) : INT.has(key) ? nf.format(Math.round(v)) : nf1.format(v)}</td>`;
    const why = r.short && (key === "imp" || key === "ctr")
      ? "Shorts do not report impressions or click-through, so this stays empty."
      : "This video did not report this number.";
    return `<td class="num"><span class="ant-na" title="${esc(why)}" aria-label="not reported">${DEAD}</span></td>`;
  }

  function row(r) {
    const pic = r.thumb
      ? `<img class="ant-th" src="${esc(r.thumb)}" alt="" loading="lazy" width="68" height="38">`
      : `<span class="ant-ph">${ic("film")}</span>`;
    const name = `<div class="ant-name">${esc(r.title)}</div><div class="ant-short">${r.short ? "Short" : ""}</div>`;
    return `<tr><td><div class="ant-v">${pic}<div>${name}</div></div></td>${COLS.slice(1).map((c) => cell(c.k, r)).join("")}</tr>`;
  }

  const table = (rows) => `<div class="scroll"><table class="ant-t"><thead><tr>${head()}</tr></thead>`
    + `<tbody>${rows.map(row).join("")}</tbody></table></div>`;

  function sorted(rows) {
    const k = sort.key, d = sort.dir;
    return rows.slice().sort((a, b) => (k === "title" ? a.title.localeCompare(b.title) * d
      : a[k] === null || b[k] === null ? (a[k] === null ? (b[k] === null ? 0 : 1) : -1) : (a[k] - b[k]) * d));
  }

  /* days=0 is the route's own word for "as far back as the channel goes", so it gets its own label
     rather than reading "Last 0 days". */
  const label = (n) => (n === 0 ? "Lifetime" : "Last " + n + " days");

  function frame() {
    const now = asked();
    // A window inherited from the rest of the page need not be one of the four offered here. Show it as
    // its own option rather than leaving the picker blank and implying 28 days.
    const list = DAYS.includes(now) || now === 0 ? DAYS : DAYS.concat([now]).sort((a, b) => a - b);
    const opts = list.map((d) => `<option value="${d}"${d === now ? " selected" : ""}>${esc(label(d))}</option>`).join("");
    return `<div class="ant"><div class="ant-bar"><div><div class="ant-count" data-ant="count">Counting videos</div>
        <p class="help" data-ant="span" style="margin:2px 0 0"></p></div>
        <div><label class="ant-pick"><span>Date range</span><select data-ant="range">${opts}</select></label>
        <p class="hint">The video list counts back from today, so pick how many days back to look.</p></div></div>
      <div class="ant-tools"><input type="search" data-ant="q" placeholder="Filter by title" aria-label="Filter videos by title" value="${esc(q)}">
        <span class="help" data-ant="shown" role="status" aria-live="polite"></span></div>
      <p class="hint">Type part of a title to narrow the list. The count above follows what you type.</p>
      <div data-ant="body">${LOADING}</div>
      <p class="hint">Click a column heading to sort by it, and click it again to turn the order around.</p></div>`;
  }

  /* The window the server actually used. Until it has answered, say what was asked for and no dates:
     printing dates this page guessed would be the same lie in a different place. */
  function when(st) {
    const a = dayTxt(st.start), b = dayTxt(st.end);
    if (a && b) return "Every number covers " + a + " to " + b + ".";
    if (!st.days) return "Every number covers the widest window the server allows.";
    return "Every number covers the last " + st.days + " days, ending today.";
  }

  function paint(box) {
    const st = box.__ant || {};
    const body = box.querySelector('[data-ant="body"]'), count = box.querySelector('[data-ant="count"]');
    const shown = box.querySelector('[data-ant="shown"]');
    box.querySelector('[data-ant="span"]').textContent = when(st);
    syncPick(box);
    const say = (title, html) => { count.textContent = title; shown.textContent = ""; body.innerHTML = html; };
    if (st.loading) return say("Counting videos", LOADING);
    if (st.err) return say("No numbers to show", `<p class="ant-err">Could not load the video numbers. ${esc(st.err)}`
      + ` <button type="button" data-ant="retry">Try again</button></p>`);
    const all = st.rows || [], needle = q.trim().toLowerCase();
    const list = needle ? all.filter((x) => x.title.toLowerCase().includes(needle)) : all;
    const one = !needle && all.length === 1;
    count.innerHTML = `<b>${(needle ? list.length + " of " + all.length : String(list.length)) + (one ? " video" : " videos")}</b>`;
    if (!all.length) return say(count.textContent, `<div class="ant-empty"><b>No videos in these ${esc(String(st.days || days))} days.</b>`
      + `Nothing was published, or nothing was tracked, in that window. Publish a clip, or pick a wider date range.</div>`);
    if (!list.length) return say(count.textContent, `<div class="ant-empty"><b>No titles match "${esc(q.trim())}".</b>`
      + `Clear the search to see all ${all.length} ${all.length === 1 ? "video" : "videos"}.</div>`);
    body.innerHTML = table(sorted(list));
    box.querySelectorAll("th[data-k]").forEach((th) => {
      if (th.dataset.k === sort.key) th.setAttribute("aria-sort", sort.dir === 1 ? "ascending" : "descending");
      else th.removeAttribute("aria-sort");
    });
    const col = COLS.find((c) => c.k === sort.key);
    shown.textContent = "Sorted by " + col.h + ", " + (sort.key === "title"
      ? (sort.dir === 1 ? "A to Z" : "Z to A") : (sort.dir === 1 ? "low to high" : "high to low")) + ".";
  }

  /* rowsOf also returns the window the server says it used, because that is the only honest source
     for the dates under the picker. The route sends start and end back with every answer. */
  function windowOf(data) {
    const s = String((data && !Array.isArray(data) && (data.start || data.from)) || "").slice(0, 10);
    const e = String((data && !Array.isArray(data) && (data.end || data.to)) || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || !/^\d{4}-\d{2}-\d{2}$/.test(e)) return {};
    return { start: s, end: e };
  }

  async function ask(box) {
    const n = asked(), key = String(n), hit = CACHE.get(key);
    box.__ant = Object.assign({ rows: hit ? hit.rows : [], loading: !hit, days: n }, hit ? hit.win : {});
    paint(box);
    if (hit) return;
    try {
      const data = await get("/api/analytics/videos?days=" + n);
      const got = { rows: rowsOf(data), win: windowOf(data) };
      if (!box.isConnected) return;                      // the page moved on while this was out
      CACHE.set(key, got);
      box.__ant = Object.assign({ rows: got.rows, days: n }, got.win);
    } catch (err) {
      if (!box.isConnected) return;
      box.__ant = { rows: [], days: n, err: String((err && err.message) || err || "The server did not answer.") };
    }
    paint(box);
  }

  function bind(box) {
    box.addEventListener("click", (e) => {
      const s = e.target.closest("[data-sort]");
      if (s) {
        const k = s.dataset.sort;
        sort = sort.key === k ? { key: k, dir: -sort.dir } : { key: k, dir: k === "title" ? 1 : -1 };
        return paint(box);
      }
      if (!e.target.closest("[data-ant=retry]")) return;
      CACHE.delete(String(asked()));
      ask(box);
    });
    box.addEventListener("change", (e) => {
      if (!e.target.matches("[data-ant=range]")) return;
      days = Number(e.target.value) || 28;
      pick = true;
      ask(box);
    });
    box.addEventListener("input", (e) => {
      if (!e.target.matches("[data-ant=q]")) return;
      q = e.target.value;
      paint(box);
    });
  }

  function mount() {
    const box = document.getElementById("an_table");
    if (!box || box.querySelector(".ant")) return;       // nothing to fill, or already ours
    box.innerHTML = frame();
    if (!box.dataset.antBound) { bind(box); box.dataset.antBound = "1"; }
    ask(box);
  }

  /* The window can come from the rest of the page, so the select has to show the one this panel is
     really asking for. Rewriting only the select keeps a typed search and the sorted table in place. */
  function syncPick(box) {
    const sel = box.querySelector("[data-ant=range]");
    if (!sel) return;
    const now = asked();
    if (!Array.from(sel.options).some((o) => Number(o.value) === now)) {
      const o = document.createElement("option");
      o.value = String(now); o.textContent = label(now);
      sel.appendChild(o);
    }
    sel.value = String(now);
  }

  let queued = false;
  // Draw on the next frame, but never wait for a frame that may not come: a page opened in a
  // background tab gets no animation frames at all, so the table would stay empty until somebody
  // looked at it. A zero-delay timer runs either way, and the frame is only an optimisation on top.
  let look = () => {
    if (queued) return;
    queued = true;
    const draw = () => {
      if (!queued) return;
      queued = false;
      try { mount(); } catch (err) { console.warn("[PeakCut] analytics table:", err); }
    };
    setTimeout(draw, 0);
    try { requestAnimationFrame(draw); } catch (err) { /* the timer above still draws it */ }
  };

  P.add("analytics-table", { label: "Analytics table", mount });
  try {
    new MutationObserver(look).observe(document.getElementById("view") || document.body, { childList: true, subtree: true });
  } catch (err) { /* without an observer only the look below draws it */ }
  document.addEventListener("peakcut:render", look);
  look();
})();
