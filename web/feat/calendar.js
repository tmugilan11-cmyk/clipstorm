/* A real calendar of posts: one month at a time, every post that is waiting to go out and every one that went out lately,
 * on the day it is due or went out. Click a day to see its posts, open the clip, cancel a waiting post or try a failed one again.
 *
 * Until now the menu row called "Calendar" opened the page about timers (Windows Task Scheduler text), which is a setting, not a
 * calendar. That page is still there, now called Timers. This one reads the same list the Home page reads (/api/overview) and
 * draws it by day. The list holds the posts that are waiting plus the fifteen most recent finished ones, so an old month can
 * look empty; the page says so rather than letting that read as "nothing was ever posted". */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.page !== "function") return;

  P.css("calendar", `
    .pcal{display:grid;gap:14px;max-width:1100px}
    .pcal-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--ink)}
    .pcal-bar{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    .pcal-bar h2{font-size:17px;font-weight:600;margin:0 8px 0 0;min-width:150px}
    .pcal-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));border:1px solid var(--line);border-radius:var(--r);overflow:hidden;background:var(--line);gap:1px}
    .pcal-dow{padding:8px 10px;background:var(--muted);font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--dim)}
    .pcal-day{display:flex;flex-direction:column;gap:3px;min-height:104px;padding:6px 6px 8px;background:var(--bg);border:0;text-align:left;color:var(--text);cursor:pointer;transition:background-color .15s ease}
    .pcal-day:hover,.pcal-day:focus-visible{background:var(--brand-soft)}
    .pcal-day.out{background:var(--muted);color:var(--faint)}
    .pcal-day.now .pcal-n{background:var(--brand);color:var(--brand-ink)}
    .pcal-day.pick{background:var(--brand-soft);outline:1px solid var(--brand-line);outline-offset:-1px}
    .pcal-n{align-self:flex-start;min-width:22px;height:22px;padding:0 6px;border-radius:999px;font-size:12px;font-weight:600;display:grid;place-items:center;font-variant-numeric:tabular-nums}
    .pcal-i{display:block;max-width:100%;padding:1px 6px;border-radius:5px;font-size:11px;line-height:1.5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;background:var(--brand-soft);color:var(--brand-deep)}
    .pcal-i.ok{background:var(--good-soft);color:var(--good)}
    .pcal-i.bad{background:var(--bad-soft);color:var(--bad)}
    .pcal-more{font-size:11px;color:var(--dim);padding-left:6px}
    .pcal-list{display:grid;gap:8px}
    .pcal-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;align-items:center;padding:10px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--muted)}
    .pcal-row b{display:block;font-size:14px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .pcal-row small{display:block;font-size:12px;color:var(--dim)}
    .pcal-acts{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
    .pcal-note{font-size:12px;color:var(--faint);margin:0}
    @media (max-width:700px){
      .pcal-dow{padding:6px 2px;text-align:center;font-size:10px}
      .pcal-day{min-height:64px;padding:4px 3px}
      .pcal-i{font-size:0;height:6px;padding:0;border-radius:3px}
      .pcal-more{display:none}
      .pcal-row{grid-template-columns:1fr}.pcal-acts{justify-content:flex-start}
    }
  `);

  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  let shown = new Date(); shown.setDate(1);              // the month on screen
  let picked = new Date();                               // the day whose posts are listed below
  let posts = [];
  let loaded = false, failed = "";

  const day0 = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const same = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  const when = (p) => new Date((Number(p.posted_at) || Number(p.due_at) || 0) * 1000);
  const hm = (d) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const cls = (p) => (p.status === "posted" ? "ok" : p.status === "failed" ? "bad" : "");
  const label = (p) => ({ scheduled: "Waiting to go out", posting: "Posting now", posted: "Posted", failed: "Did not post", cancelled: "Cancelled" }[p.status] || String(p.status || ""));

  function cells() {
    const first = new Date(shown.getFullYear(), shown.getMonth(), 1);
    const lead = (first.getDay() + 6) % 7;                // Monday first
    const start = new Date(first.getFullYear(), first.getMonth(), 1 - lead);
    return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  }

  function body() {
    if (failed) return `<p class="pcal-note">${esc(failed)}</p>`;
    if (!loaded) return `<p class="pcal-note">Reading your posts…</p>`;
    const today = new Date();
    const list = posts.filter((p) => p.status !== "cancelled");
    const grid = cells().map((d) => {
      const mine = list.filter((p) => same(when(p), d));
      const out = d.getMonth() !== shown.getMonth();
      const items = mine.slice(0, 3).map((p) => `<span class="pcal-i ${cls(p)}" title="${esc(hm(when(p)) + " " + (p.title || "Clip"))}">${esc(hm(when(p)))} ${esc(p.title || "Clip")}</span>`).join("");
      return `<button type="button" class="pcal-day${out ? " out" : ""}${same(d, today) ? " now" : ""}${same(d, picked) ? " pick" : ""}" data-act="pcalday" data-t="${d.getTime()}" aria-label="${esc(d.toDateString() + ", " + mine.length + (mine.length === 1 ? " post" : " posts"))}">
          <span class="pcal-n">${d.getDate()}</span>${items}${mine.length > 3 ? `<span class="pcal-more">+${mine.length - 3} more</span>` : ""}</button>`;
    }).join("");
    const dayPosts = list.filter((p) => same(when(p), picked)).sort((a, b) => when(a) - when(b));
    const rows = dayPosts.length ? dayPosts.map((p) => `<div class="pcal-row"><div style="min-width:0"><b>${esc(p.title || "Clip")}</b>
        <small>${esc(hm(when(p)))} · ${esc(p.account_name || "An account")} · ${esc(label(p))}${p.creator_name ? " · " + esc(p.creator_name) : ""}${p.error ? " · " + esc(p.error) : ""}</small></div>
        <div class="pcal-acts">
          ${p.job && p.clip ? `<button type="button" class="btn sm" data-act="pcalopen" data-j="${esc(p.job)}" data-c="${esc(p.clip)}">Open the clip</button>` : ""}
          ${p.url ? `<a class="btn sm" href="${esc(p.url)}" target="_blank" rel="noopener">See the post</a>` : ""}
          ${p.status === "scheduled" ? `<button type="button" class="btn sm" data-act="pcalpost" data-id="${esc(p.id)}" data-do="cancel">Cancel this post</button>` : ""}
          ${p.status === "failed" ? `<button type="button" class="btn sm" data-act="pcalpost" data-id="${esc(p.id)}" data-do="retry">Try again</button>` : ""}
        </div></div>`).join("") : `<p class="pcal-note">Nothing on ${esc(picked.toDateString())}.</p>`;
    const none = list.length ? "" : `<p class="pcal-note">No posts are waiting or recent yet. They show here once a clip is added to the post queue.</p>`;
    return `${none}<div class="pcal-grid" role="group" aria-label="${esc(MONTHS[shown.getMonth()] + " " + shown.getFullYear())}">${DOW.map((x) => `<div class="pcal-dow">${x}</div>`).join("")}${grid}</div>
      <h3 style="font-size:14px;margin-top:6px">${esc(picked.toDateString())}</h3><div class="pcal-list">${rows}</div>
      <p class="pcal-note">This shows the posts waiting to go out and the most recent ones that went out. Clipstorm spaces posts by itself. To post more, select clips on a project page and press Post.</p>`;
  }

  function paint() {
    const box = document.getElementById("pcal");
    if (!box) return;
    const h = document.getElementById("pcal_title"); if (h) h.textContent = `${MONTHS[shown.getMonth()]} ${shown.getFullYear()}`;
    box.innerHTML = body();
  }

  async function read() {
    try { const o = await P.api("/api/overview"); posts = Array.isArray(o && o.posts) ? o.posts : []; failed = ""; }
    catch (e) { failed = "Could not read your posts. " + String((e && e.message) || ""); }
    loaded = true; paint();
  }

  P.page("calendar", {
    nav: "Calendar",
    icon: "calendar",
    tip: "Your posts by day: what is waiting and what went out",
    path: "calendar",
    group: "Understand",
    order: 22,
    view() {
      loaded = false;
      return `<section class="set-sec pcal"><h1 class="pcal-h">Calendar</h1>
        <p class="help">Every post by the day it goes out or went out. Click a day to see its posts.</p>
        <div class="pcal-bar"><h2 id="pcal_title"></h2>
          <button type="button" class="btn sm" data-act="pcalmove" data-d="-1" aria-label="Last month">Last month</button>
          <button type="button" class="btn sm" data-act="pcalmove" data-d="0">Today</button>
          <button type="button" class="btn sm" data-act="pcalmove" data-d="1" aria-label="Next month">Next month</button></div>
        <div id="pcal"></div></section>`;
    },
    async load() { paint(); await read(); },
  });

  P.add("calendar", {
    label: "Calendar of posts",
    act: {
      pcalmove(el) {
        const d = Number(el.dataset.d);
        if (!d) { shown = new Date(); shown.setDate(1); picked = new Date(); }
        else shown = new Date(shown.getFullYear(), shown.getMonth() + d, 1);
        paint();
      },
      pcalday(el) { picked = day0(new Date(Number(el.dataset.t))); paint(); },
      pcalopen(el) { if (typeof openClip === "function") openClip(el.dataset.j, el.dataset.c); },
      async pcalpost(el) {
        const id = el.dataset.id, doIt = el.dataset.do;
        if (doIt === "cancel" && typeof ask === "function" && !(await ask("Cancel this post?", "It will not go out. The clip itself is kept.", "Cancel the post", true))) return;
        try { await P.send(`/api/posts/${encodeURIComponent(id)}/${doIt === "retry" ? "retry" : "cancel"}`, {}); P.toast(doIt === "retry" ? "It will be tried again now." : "The post was cancelled.", "ok"); await read(); }
        catch (e) { P.toast(String((e && e.message) || "That did not work."), "bad"); }
      },
    },
  });
})();
