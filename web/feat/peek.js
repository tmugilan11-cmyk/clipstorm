/* Stills on a finished clip, so a card is not a black box until someone plays it.
 *
 * The server already writes a four-frame strip beside every clip it looks at (`peek`, `peek_at`,
 * `peek_version`), and serves it as one jpg. This puts that strip on the card, with the moments it was
 * taken from under it. A clip nobody has looked at gets one quiet button instead: "Take stills".
 *
 * Drawing is free. The only request the page makes on a person's behalf is the button, which asks the
 * server for the frames and then re-reads the job so the strip replaces the button.
 */
(() => {
  const P = window.PeakCut;

  P.css("peek", `
    .pcpeek{margin:9px 0 1px;flex:none;min-width:0;container-type:inline-size}
    .pcpeek .pstrip{position:relative;display:block;line-height:0;border-radius:9px;overflow:hidden;
      background:var(--frame);border:1px solid var(--frame-2)}
    .pcpeek .pstrip img{display:block;width:100%;height:auto;background:var(--frame);
      aspect-ratio:auto 544 / 240}   /* reserve the usual strip shape before it arrives, never overrule a real one */
    .pcpeek .pat{display:grid;margin-top:6px;font-size:11px;line-height:1.35;color:var(--dim);
      font-variant-numeric:tabular-nums}
    .pcpeek .pat span{padding:0 1px;text-align:center;white-space:nowrap;overflow:hidden}
    .pcpeek .pat span + span{border-left:1px solid var(--line)}
    /* A card can be squeezed very narrow. The times are a nicety, so drop them rather than clip them. */
    @container (max-width: 126px){ .pcpeek .pat{display:none} }
    .pcpeek .pcpeekbtn{display:flex;width:100%;height:30px;padding:0 10px;gap:6px;font-size:13px;font-weight:500;
      color:var(--dim);background:transparent;border:1px dashed var(--line-2)}
    .pcpeek .pcpeekbtn svg{width:16px;height:16px;flex:none;opacity:.75}
    .pcpeek .pcpeekbtn:hover{background:var(--muted);border-color:#D4CAC3;color:var(--text)}
    .pcpeek .pcpeekbtn:hover svg{opacity:1}
    .pcpeek .pcpeekbtn[aria-busy="true"] svg{opacity:.45}
    /* On a phone the button is a real tap target; the existing height stays the desktop size
       and min-height wins here. The container query above already drops the times row when the card is very narrow. */
    @media (max-width:640px){
      .pcpeek .pcpeekbtn{min-height:44px}
    }
  `);

  const OK_ID = /^[A-Za-z0-9_-]+$/;   // the only shape an id may have before it goes into a URL
  const TAKING = new Set();           // "jid:cid" that has a request in flight right now
  const DEAD = new Set();             // "jid:cid" whose strip the server could not serve after all

  const ICON = `<svg viewBox="0 0 20 16" aria-hidden="true" focusable="false"><rect x="1" y="2.5" width="18" height="11" rx="2.2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M6 2.5v11M10 2.5v11M14 2.5v11" stroke="currentColor" stroke-width="1.1" opacity=".5"/></svg>`;

  const key = (jid, cid) => jid + ":" + cid;

  // Anything that came from the server goes through this before it becomes markup. The ids are checked
  // against OK_ID as well, so a bad one never gets this far.
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function mmss(s) {
    s = Math.max(0, Math.round(Number(s) || 0));
    const m = Math.floor(s / 60), q = s % 60;
    return m + ":" + String(q).padStart(2, "0");
  }

  // An id or a number, or nothing at all. Anything else never reaches the page or a URL.
  function okId(v) { return typeof v === "string" && OK_ID.test(v); }
  function okVer(v) { const n = Number(v); return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0; }

  // The strip is one jpg of all the frames side by side, so it is shown at its own shape, never cropped.
  function srcFor(jid, cid, clip) {
    const v = okVer(clip.peek_version);
    return "/api/jobs/" + jid + "/peek/" + cid + (v ? "?v=" + v : "");
  }

  function node(html) {
    const t = document.createElement("template");
    t.innerHTML = html;
    return t.content.firstElementChild;
  }

  function stripNode(jid, cid, clip) {
    const at = Array.isArray(clip.peek_at) ? clip.peek_at.filter(t => Number.isFinite(Number(t))) : [];
    const n = Math.max(1, Math.min(8, at.length));
    const alt = at.length ? "Still frames from this clip" : "A still from this clip";
    const table = n > 1
      ? `<div class="pat" style="grid-template-columns:repeat(${n},minmax(0,1fr))">${at.slice(0, n).map(t => `<span>${esc(mmss(t))}</span>`).join("")}</div>`
      : "";
    return node(`<div class="pcpeek" data-state="strip" data-cid="${esc(cid)}" role="group" aria-label="Stills from this clip">
        <div class="pstrip"><img src="${esc(srcFor(jid, cid, clip))}" alt="${esc(alt)}" loading="lazy" decoding="async"></div>${table}
      </div>`);
  }

  function takeNode(jid, cid, busy) {
    return node(`<div class="pcpeek" data-state="${busy ? "busy" : "take"}" data-cid="${esc(cid)}">
        <button type="button" class="btn sm pcpeekbtn" data-act="peektake" data-j="${esc(jid)}" data-c="${esc(cid)}"
          title="Take four stills from this clip"${busy ? ' disabled aria-busy="true"' : ""}>${ICON}<span class="plbl">${busy ? "Taking stills…" : "Take stills"}</span></button>
      </div>`);
  }

  // A lazy image can stay asleep: if the card was laid out while it was off screen, or while the tab was
  // in the background, the browser may never decide to fetch it, and its height stays zero. Ask for it as
  // soon as the card is really in view. The fallback check covers the second case, where the browser does
  // not report what is on screen at all. If it still will not load, `whenDead` decides what to show.
  function nudge(box, img, whenDead) {
    let started = false;
    const src = img.getAttribute("src");
    const alive = () => !(img.complete && img.naturalWidth === 0);
    const start = () => {
      if (started) return;
      started = true;
      img.loading = "eager";
      setTimeout(() => {
        if (img.complete) return alive() ? undefined : whenDead();
        let asked = false;
        try { asked = performance.getEntriesByType("resource").some(e => String(e.name).indexOf(src) >= 0); } catch {}
        if (asked) return;                     // on its way; the error and load handlers decide
        img.src = src;                         // it never even asked: ask now
        setTimeout(() => { if (img.complete && img.naturalWidth === 0) whenDead(); }, 3000);
      }, 400);
    };
    let io = null;
    if (typeof IntersectionObserver === "function") {
      io = new IntersectionObserver(seen => {
        for (const e of seen) if (e.isIntersecting) { io.disconnect(); return start(); }
      });
      io.observe(box);
    } else {
      start();
    }
    // The observer does not fire while the tab is hidden or the browser will not report layout. Look for
    // ourselves once, not on a loop: a card that is off screen still waits for the observer.
    setTimeout(() => {
      if (started) return;
      const r = box.getBoundingClientRect();
      const h = window.innerHeight || 0;
      if (r.width > 0 && r.height >= 0 && r.top < h + 200 && r.bottom > -200) start();
    }, 1500);
  }

  // The strip can be claimed and still be gone from disk. Swap it for the button and stop asking for it.
  function watchImage(box, jid, cid) {
    const img = box.querySelector("img");
    if (!img) return;
    const gone = () => {
      const k = key(jid, cid);
      if (DEAD.has(k)) return;
      DEAD.add(k);
      if (box.parentNode) box.parentNode.replaceChild(takeNode(jid, cid, TAKING.has(k)), box);
      say("The stills for that clip are gone. Take them again.", "bad");
    };
    img.addEventListener("error", gone);
    img.addEventListener("load", () => { if (img.naturalWidth === 0) gone(); });
    nudge(box, img, gone);
  }

  // Put the right thing under each finished clip, and leave everything else alone.
  function place(card, job) {
    const clips = job.clips;
    if (!Array.isArray(clips) || !clips.length) return;
    const jid = String(job.id == null ? "" : job.id);
    if (!okId(jid)) return;                                     // nothing is built from an id we cannot trust
    for (const el of card.querySelectorAll(".clip")) {
      const hit = el.querySelector('[data-act="openclip"][data-c]');
      const body = el.querySelector(".clip-body");
      if (!hit || !body) continue;
      const cid = String(hit.dataset.c || "");
      if (!okId(cid)) continue;
      const clip = clips.find(c => c && String(c.id) === cid);
      if (!clip || String(clip.status) !== "done") {
        const stale = body.querySelector(":scope > .pcpeek");     // a clip that stopped being finished
        if (stale) stale.remove();
        continue;
      }
      const k = key(jid, cid);
      const has = typeof clip.peek === "string" && clip.peek !== "" && !DEAD.has(k);
      const want = has ? "strip" : TAKING.has(k) ? "busy" : "take";
      const old = body.querySelector(":scope > .pcpeek");
      if (old && old.dataset.cid === cid && old.dataset.state === want) continue;   // already right
      const box = want === "strip" ? stripNode(jid, cid, clip) : takeNode(jid, cid, want === "busy");
      if (old) old.replaceWith(box); else body.insertBefore(box, body.querySelector(".clip-foot"));
      if (want === "strip") watchImage(box, jid, cid);
    }
  }

  // Copy only the three keys that decide the strip, so nothing else on the card can be clobbered.
  function merge(jid, job, got) {
    const state = P.state();
    const mine = ((state && state.jobs) || []).find(j => j && String(j.id) === jid);
    if (!mine || !Array.isArray(mine.clips)) return;
    const fresh = {};
    if (job && Array.isArray(job.clips)) for (const c of job.clips) if (c && c.id) fresh[String(c.id)] = c;
    else if (got && Array.isArray(got.frames)) for (const f of got.frames) if (f && f.id) fresh[String(f.id)] = f;
    for (const c of mine.clips) {
      const f = c && fresh[String(c.id)];
      if (!f) continue;
      for (const k of ["peek", "peek_at", "peek_version"]) if (k in f) c[k] = f[k];
    }
  }

  // Put the right thing under each finished clip, and leave everything else alone. Never asks the server
  // for anything: it only reads what is already on the job object.
  function paint(root) {
    if (!root) return;
    const state = P.state();
    const jobs = (state && state.jobs) || [];
    if (!jobs.length) return;
    const byId = new Map();
    for (const j of jobs) if (j && j.id != null) byId.set(String(j.id), j);
    for (const card of root.querySelectorAll("section[data-job]")) {
      const job = byId.get(card.dataset.job);
      if (job) place(card, job);
    }
  }

  function redraw(btn) {
    if (btn) {                                  // the button may still be here; leave it as we found it
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
      const lbl = btn.querySelector(".plbl");
      if (lbl) lbl.textContent = "Take stills";
    }
    try { if (typeof drawJobs === "function") drawJobs(); } catch {}
    let root = null;
    try { root = document.getElementById("jobs"); } catch {}
    try { paint(root); } catch {}                // do not rely on the plugin watcher noticing our edit
    try { document.dispatchEvent(new Event("peakcut:render")); } catch {}
  }

  function say(msg, kind) {
    try { if (P.toast) P.toast(msg, kind); } catch {}
  }

  P.add("peek", {
    after: {
      /** Runs whenever the job list is redrawn. Never asks the server for anything. */
      drawJobs(root) { paint(root); },
    },

    act: {
      /** The one button. Asks for the frames, re-reads the job, redraws. */
      async peektake(el) {
        const jid = String(el.dataset.j || ""), cid = String(el.dataset.c || "");
        if (!okId(jid) || !okId(cid)) return say("That clip cannot be read.", "bad");
        const k = key(jid, cid);
        if (TAKING.has(k)) return;
        TAKING.add(k);
        DEAD.delete(k);                                  // a person asked again: give the strip another chance
        el.disabled = true;
        el.setAttribute("aria-busy", "true");
        const lbl = el.querySelector(".plbl");
        if (lbl) lbl.textContent = "Taking stills…";
        try {
          // `cid` goes on the query string: that is the parameter the route reads.
          const got = await P.send("/api/jobs/" + jid + "/peek?cid=" + cid, { cid });
          const frames = (got && Array.isArray(got.frames)) ? got.frames : [];
          let job = null;
          try { job = await P.api("/api/jobs/" + jid); } catch {}
          merge(jid, job, got);
          const mine = frames.find(f => f && String(f.id) === cid);
          if (mine && mine.error) say(String(mine.error), "bad");
          else if (!mine) say("No stills came back for that clip.", "bad");
          else say("Stills added to this clip.", "ok");
        } catch (err) {
          say(String((err && err.message) || err || "Could not take the stills."), "bad");
        } finally {
          TAKING.delete(k);
          redraw(el);
        }
      },
    },
  });
})();
