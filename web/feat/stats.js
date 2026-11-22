/* The numbers behind a moment: what the source video itself has done on YouTube.
 *
 * The clip dialog can say a moment scored 84, but not whether the video it came from was ever watched by
 * anyone. `GET /api/stats/video` already answers that, and Settings > Tools can ask it by hand; this puts the
 * same answer next to the clip, folded away, so it costs one quiet row until someone wants it.
 *
 * The dialog keeps its job and clip ids in a module-private `D` that the page never exposes, so they are read
 * back out of the dialog's own markup instead: the copy button in the footer carries `data-j` and `data-c`, and
 * the stage video's path carries the job id. `PeakCut.state()` then turns that id into the job, and the job's
 * `source.url` into the link to ask about.
 *
 * The read is a button, not a fetch on open. Every read spends the operator's YouTube quota, and the route
 * refuses without a Data API key, so nothing is asked until someone presses it. An answer is kept per link for
 * the life of the tab. A key that gets pasted lives in a plain variable in this closure: never localStorage,
 * never an attribute, never sent anywhere except to PeakCut's own route.
 */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  if (typeof P.css === "function") P.css("stats", `
    .statsbox{margin:0;border:1px solid var(--line);border-radius:var(--r);background:var(--muted);
      transition:border-color .18s ease,background-color .18s ease}
    .statsbox[open]{background:var(--bg);border-color:var(--line-2)}
    .statsbox>summary{display:flex;align-items:center;gap:8px;padding:9px 12px;cursor:pointer;list-style:none;
      font-size:13px;font-weight:600;color:var(--dim);border-radius:var(--r);user-select:none;
      transition:color .18s ease}
    .statsbox>summary::-webkit-details-marker{display:none}
    .statsbox>summary:hover{color:var(--brand-deep)}
    .statsbox>summary:focus-visible{outline:2px solid var(--brand-line);outline-offset:-2px}
    .statsbox>summary::before{content:"";flex:none;width:6px;height:6px;border-right:1.6px solid currentColor;
      border-bottom:1.6px solid currentColor;transform:rotate(-45deg);transform-origin:60% 60%;
      transition:transform .18s ease}
    .statsbox[open]>summary::before{transform:rotate(45deg)}
    .statsbox .pcs-badge{margin-left:auto;padding:1px 8px;border:1px solid var(--brand-line);border-radius:999px;
      background:var(--brand-soft);color:var(--brand-deep);font-size:12px;font-weight:600;
      font-variant-numeric:tabular-nums;white-space:nowrap}
    .statsbox .pcs-body{display:grid;gap:9px;padding:0 12px 12px}
    .statsbox .pcs-note{margin:0;font-size:13px;line-height:1.55;color:var(--dim)}
    .statsbox .pcs-go{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .statsbox .pcs-hint{font-size:12px;line-height:1.45;color:var(--faint)}
    .statsbox .pcs-title{margin:0;font-size:13px;font-weight:600;line-height:1.45;color:var(--text);
      overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
    .statsbox .pcs-tiles{display:grid;gap:8px;margin:0;grid-template-columns:repeat(auto-fit,minmax(92px,1fr))}
    .statsbox .pcs-t{display:grid;gap:3px;padding:9px 11px;border:1px solid var(--line);border-radius:var(--r-sm);
      background:var(--bg);transition:border-color .18s ease}
    .statsbox .pcs-t:hover{border-color:var(--brand-line)}
    .statsbox .pcs-t dt{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
      color:var(--faint)}
    .statsbox .pcs-t dd{margin:0;font-size:17px;font-weight:650;line-height:1.1;letter-spacing:-.01em;
      color:var(--text);font-variant-numeric:tabular-nums}
    .statsbox .pcs-t.pcs-when dd{font-size:13px;letter-spacing:0;line-height:1.35}
    .statsbox .pcs-link{width:max-content;max-width:100%;font-size:12px;color:var(--dim);text-decoration:none;
      border-bottom:1px solid var(--line-2);padding-bottom:1px;
      transition:color .18s ease,border-color .18s ease}
    .statsbox .pcs-link:hover{color:var(--brand-deep);border-color:var(--brand-line)}
    .statsbox .pcs-keyrow{display:grid;gap:6px}
    .statsbox .pcs-kf{display:grid;gap:5px;font-size:12px;font-weight:600;color:var(--dim)}
    .statsbox .pcs-key{height:34px;font-size:13px}
    @media (prefers-reduced-motion: reduce){
      .statsbox,.statsbox *,.statsbox>summary::before{transition:none}
    }
    @media (max-width:560px){
      .statsbox .pcs-tiles{grid-template-columns:repeat(auto-fit,minmax(78px,1fr))}
      .statsbox .pcs-t dd{font-size:16px}
    }
  `);

  /* ---------------------------------------------------------------- the shape of an answer */
  // The route sends {vid, video, wanted}. `video` is one flattened row from studio/ytstats.py, and a field the
  // creator hid is null rather than 0 ("0 and hidden are different things"), so a null is left out, not printed.
  const LABELS = {views: "Views", likes: "Likes", comments: "Comments", seconds: "Length", published: "Published"};
  const KNOWN = ["views", "likes", "comments", "seconds", "published"];
  const SKIP = new Set(["id", "title"]);

  const words = s => String(s || "").replace(/[_-]+/g, " ").replace(/^\w/, c => c.toUpperCase()).trim();
  const group = Intl.NumberFormat("en-US");
  const short = Intl.NumberFormat("en-US", {notation: "compact", maximumFractionDigits: 1});
  const big = n => n >= 100000 ? short.format(n) : group.format(n);

  const mmss = s => {
    s = Math.max(0, Math.round(Number(s) || 0));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), q = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(q).padStart(2, "0")}`
             : `${m}:${String(q).padStart(2, "0")}`;
  };
  const day = iso => {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, {year: "numeric", month: "short", day: "numeric"});
  };

  /** Can this field be shown as it stands? A missing, hidden or nonsense value cannot. */
  function usable(k, val) {
    if (k === "published") return typeof val === "string" && !!day(val);
    if (typeof val !== "number" || !Number.isFinite(val)) return false;
    return k === "seconds" ? val > 0 : val >= 0;      // a zero view count is a real zero
  }

  /** The fields to draw, in reading order. `wanted` is normally the settings knobs, so a list is honoured only
   *  when one actually arrives; anything present in the row but not named in the list still gets a tile. */
  function plan(video, wanted) {
    const used = new Set(), out = [];
    const add = (k, label) => {
      if (used.has(k) || !usable(k, video[k])) return;
      used.add(k);
      out.push({k, label: label || LABELS[k] || words(k)});
    };
    if (Array.isArray(wanted)) {
      for (const w of wanted) {
        if (typeof w !== "string") continue;
        const want = w.toLowerCase().replace(/[^a-z]/g, "");
        const hit = Object.keys(video).find(x => {
          const k = x.toLowerCase().replace(/[^a-z]/g, "");
          return k === want || k === want + "s" || k + "s" === want;
        });
        if (hit && !SKIP.has(hit)) add(hit, LABELS[hit] || words(hit));
      }
    }
    for (const k of KNOWN) add(k);
    for (const k of Object.keys(video)) if (!SKIP.has(k)) add(k);
    return out;
  }

  const shown = (k, val) => k === "seconds" ? mmss(val) : k === "published" ? day(val) : big(val);
  const exact = (k, val) => k === "seconds" ? `${Math.round(val)} seconds`
    : k === "published" ? String(val) : group.format(val);

  function doneHtml(data) {
    const got = data && typeof data === "object" ? data : {};
    const video = got.video && typeof got.video === "object" ? got.video : null;
    if (!video) return `<p class="pcs-note">YouTube sent no numbers for this video.</p>`;
    const tiles = plan(video, got.wanted).map(({k, label}) =>
      `<div class="pcs-t${k === "published" ? " pcs-when" : ""}"><dt>${esc(label)}</dt><dd title="${esc(exact(k, video[k]))}">${esc(shown(k, video[k]))}</dd></div>`
    ).join("");
    const title = typeof video.title === "string" && video.title.trim()
      ? `<p class="pcs-title">${esc(video.title.trim())}</p>` : "";
    const vid = typeof got.vid === "string" && /^[\w-]{11}$/.test(got.vid) ? got.vid : "";
    const link = vid
      ? `<a class="pcs-link" href="https://www.youtube.com/watch?v=${esc(vid)}" target="_blank" rel="noopener noreferrer">Watch it on YouTube</a>`
      : "";
    if (!tiles && !title) return `<p class="pcs-note">This video has no numbers to show yet.</p>`;
    return `${title}${tiles ? `<dl class="pcs-tiles" aria-label="How this video did on YouTube">${tiles}</dl>` : ""}${link}`;
  }

  /* ---------------------------------------------------------------- what the section says */
  const reads = new Map();     // link -> {phase, data, msg, keyNeeded}; an answer is reused for the whole tab
  let key = "";                // the Data API key, in this closure only

  function bodyHtml(url) {
    if (!url) return `<p class="pcs-note">This one is a file, so there are no numbers.</p>`;
    const st = reads.get(url);
    if (st && st.phase === "loading") return `<p class="pcs-note" aria-busy="true">Reading the numbers…</p>`;
    if (st && st.phase === "done") return doneHtml(st.data);
    const said = st && st.msg ? `<p class="pcs-note">${esc(st.msg)}</p>` : "";
    const ask = st && st.keyNeeded
      ? `<div class="pcs-keyrow">
          <label class="pcs-kf">YouTube API key
            <input class="pcs-key" type="password" maxlength="200" autocomplete="off" spellcheck="false" placeholder="Paste the key" aria-label="YouTube API key">
          </label>
          <span class="pcs-hint">Kept in this tab only. Never saved.</span>
        </div>`
      : "";
    const hint = st ? "" : `<span class="pcs-hint">How this video has done on YouTube.</span>`;
    return `${said}${ask}<div class="pcs-go"><button class="btn sm" data-act="pcstatsread">Read the numbers</button>${hint}</div>`;
  }

  /* ---------------------------------------------------------------- which clip is on screen */
  /** The job and clip ids the dialog is showing, read from its own markup. `D` is private to the page. */
  function ids(root) {
    const tries = ['[data-act="copy"][data-j]', "#dlgvers [data-j][data-c]", "[data-j][data-c]"];
    for (const sel of tries) {
      const el = root.querySelector(sel);
      if (el && el.dataset && el.dataset.j) return {job: el.dataset.j, clip: el.dataset.c || ""};
    }
    const stage = root.querySelector("#stage") || root;
    const hit = String(stage.innerHTML || "").match(/\/media\/([^\/"'?#]+)\//);
    return {job: hit ? hit[1] : "", clip: ""};
  }

  function now(root) {
    const st = P.state ? P.state() : null;
    const jobs = (st && Array.isArray(st.jobs) && st.jobs) || [];
    const id = ids(root);
    const job = id.job ? jobs.find(j => j && String(j.id) === String(id.job)) || null : null;
    return {job, jobId: job ? String(job.id) : "", clip: id.clip, url: job ? sourceUrl(job) : ""};
  }

  /** The link the job was made from. A file job has no link, which is the one case worth saying out loud. */
  function sourceUrl(job) {
    const s = (job && job.source) || {};
    for (const v of [s.url, s.link, s.href, s.name]) {
      if (typeof v === "string" && /^https?:\/\//i.test(v.trim())) return v.trim();
    }
    return "";
  }

  /* ---------------------------------------------------------------- drawing */
  function paint(root) {
    const box = root.querySelector(".statsbox");
    if (!box) return;
    const who = now(root);
    put(box.querySelector(".pcs-body"), bodyHtml(who.url));

    // The headline count rides on the summary, so the section says something even while it is folded shut.
    const got = who.url ? (reads.get(who.url) || {}).data : null;
    const views = got && got.video && typeof got.video.views === "number" ? got.video.views : null;
    const summary = box.querySelector("summary");
    const had = summary.querySelector(".pcs-badge");
    if (views === null) { if (had) had.remove(); }
    else {
      if (!had) summary.insertAdjacentHTML("beforeend", `<span class="pcs-badge"></span>`);
      put(summary.querySelector(".pcs-badge"), `${esc(big(views))} views`);
    }

    // A key that is already held is put back after every redraw, so a failed read is not paid for twice.
    const field = box.querySelector(".pcs-key");
    if (field && key) field.value = key;
  }

  // One keydown listener per section, added the first time that section is drawn (a new dialog draw makes a new
  // one). Enter in the key field should press the button, not do nothing.
  const armed = new WeakSet();
  function arm(box) {
    if (!box || armed.has(box)) return;
    armed.add(box);
    box.addEventListener("keydown", e => {
      try {
        if (e.key !== "Enter" || !e.target || !e.target.classList.contains("pcs-key")) return;
        e.preventDefault();
        const b = box.querySelector('[data-act="pcstatsread"]');
        if (b) b.click();
      } catch { /* a stray key is not worth an error on the page */ }
    });
  }

  /* The page only calls the hook when the dialog's markup changes length, so a clip whose dialog looks exactly
   * like the last one can pass it by. A listener on the dialog opening closes that gap: one listener per dialog,
   * added on the first draw, doing the same small job the hook does. */
  const seen = new WeakSet();
  function ensure(root) {
    try {
      if (!root) return;
      // Watch the opening first, because the page fills the dialog before it opens: the hook can run once on a
      // closed dialog and then never again for that same markup. This listener is what catches the open.
      if (!seen.has(root)) {
        seen.add(root);
        root.addEventListener("toggle", () => { if (root.open) ensure(root); });
      }
      if (!root.open) return;                             // closed: nothing to draw into
      const panel = root.querySelector(".panel");
      if (!panel) return;                                 // opened but not filled yet
      const who = now(root);
      if (!who.job) return;                               // no job in state yet: leave the dialog alone

      let box = panel.querySelector(".statsbox");
      if (!box) {
        const html = `<details class="statsbox">
            <summary>YouTube numbers</summary>
            <div class="pcs-body" aria-live="polite"></div>
          </details>`;
        // The section sits between the tab rail and the panes, so it shows on every tab. The Look pane's own
        // h3 is the first h3 in the panel, so anchoring to it would tuck the section inside that one pane,
        // above its heading, and hide it on the other tabs.
        const rail = panel.querySelector(".ed-railnav");
        if (rail) rail.insertAdjacentHTML("afterend", html);
        else panel.insertAdjacentHTML("afterbegin", html);
        box = panel.querySelector(".statsbox");
      }
      if (!box) return;
      arm(box);
      const sig = who.jobId + "|" + who.clip + "|" + who.url;
      if (box.dataset.sig === sig) return;                // already showing this clip: nothing to rewrite
      box.dataset.sig = sig;
      paint(root);
    } catch { /* a redraw is never worth an error on the page */ }
  }

  P.add("stats", {
    act: {
      /** Reads the source video's own numbers. One call per link, then the same answer is drawn again. */
      async pcstatsread(btn) {
        const root = btn.closest("dialog");
        if (!root || !root.open) return;
        const who = now(root);
        if (!who.url) return paint(root);
        const had = reads.get(who.url);
        if (had && had.phase === "loading") return;         // already asking: a second press would spend a second call

        const field = root.querySelector(".pcs-key");
        if (field && String(field.value || "").trim()) key = String(field.value).trim();

        reads.set(who.url, {phase: "loading"});
        paint(root);
        try {
          const call = (window.PeakCut && window.PeakCut.api) || (typeof api === "function" ? api : null);
          if (!call) throw new Error("The page is still starting. Try again in a moment.");
          const path = "/api/stats/video?url=" + encodeURIComponent(who.url)
            + (key ? "&key=" + encodeURIComponent(key) : "");
          reads.set(who.url, {phase: "done", data: await call(path)});
        } catch (err) {
          const msg = String((err && err.message) || err || "The numbers could not be read just now.");
          reads.set(who.url, {phase: "fail", msg, keyNeeded: /key/i.test(msg)});
        }
        paint(root);
      },
    },

    after: {
      /** Runs whenever the clip dialog is drawn. Adds the folded section once, then keeps it on the right clip. */
      drawClipDlg(root) { ensure(root); },
    },
  });
})();
