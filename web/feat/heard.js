/* How much of a video has really been listened to, and how many parts are written.
 *
 * The server already sends `heard_to`, `watched_pct`, `blocks_done` and `blocks_total` on every job, but the
 * job card could only ever show one number. This draws the actual thing: a line that fills as PeakCut listens,
 * one mark per part of the file, so a long video looks like a long video instead of a spinner. */
(() => {
  window.PeakCut.css("heard", `
    .heard{margin-top:9px;display:grid;gap:5px}
    .heard .rail{position:relative;height:8px;border-radius:99px;background:var(--line);overflow:hidden}
    .heard .fill{position:absolute;inset:0 auto 0 0;background:var(--brand);border-radius:99px;transition:width .45s ease}
    .heard .fill::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);animation:heardglow 1.9s linear infinite}
    @keyframes heardglow{from{transform:translateX(-100%)}to{transform:translateX(100%)}}
    .heard .parts{display:flex;gap:3px}
    .heard .part{height:4px;flex:1;border-radius:99px;background:var(--line)}
    .heard .part.on{background:var(--brand)}
    .heard .line{display:flex;justify-content:space-between;gap:10px;font-size:12px;color:var(--dim)}
    .heard .line b{color:var(--ink);font-weight:600}
    @media (prefers-reduced-motion: reduce){.heard .fill::after{animation:none}}
  `);

  const mmss = (s) => {
    s = Math.max(0, Math.round(Number(s) || 0));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), q = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(q).padStart(2, "0")}`
             : `${m}:${String(q).padStart(2, "0")}`;
  };

  // Only a job that is actually being worked on gets the picture; anything else keeps the plain card.
  const LIVE = new Set(["running", "queued"]);

  function block(job) {
    const pct = Number(job.watched_pct) || 0;
    const heard = Number(job.heard_to) || 0;
    const dur = Number(job.duration) || 0;
    const done = Number(job.blocks_done) || 0, all = Number(job.blocks_total) || 0;
    if (!dur && !all) return "";
    const parts = all > 1
      ? `<div class="parts">${Array.from({length: all}, (_, i) => `<div class="part${i < done ? " on" : ""}"></div>`).join("")}</div>`
      : "";
    const heardLine = dur
      ? `<span>Listened to <b>${esc(mmss(heard))}</b> of ${esc(mmss(dur))}</span>`
      : `<span>Listening</span>`;
    const partsLine = all > 1
      ? `<span>${done} of ${all} parts written</span>`
      : `<span>${Math.round(pct)}% of the file</span>`;
    return `<div class="heard" role="group" aria-label="Progress through this video">
        <div class="rail" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"><div class="fill" style="width:${Math.max(2, pct).toFixed(1)}%"></div></div>
        ${parts}
        <div class="line">${heardLine}${partsLine}</div>
      </div>`;
  }

  window.PeakCut.add("heard", {
    after: {
      /** Runs whenever the job list is redrawn. Looks up each live job's own card and drops the picture in. */
      drawJobs(root) {
        const state = window.PeakCut.state();
        const jobs = (state && state.jobs) || [];
        for (const job of jobs) {
          if (!LIVE.has(String(job.status || ""))) continue;
          const card = root.querySelector(`section[data-job="${CSS.escape(String(job.id))}"]`);
          if (!card || card.querySelector(".heard")) continue;      // already drawn, or no card for it yet
          const html = block(job);
          if (!html) continue;
          // Under the existing bar and stage line, which is where the old spinner-only look ended.
          const bar = card.querySelector(".bar");
          if (bar) bar.insertAdjacentHTML("afterend", html);
          else card.insertAdjacentHTML("beforeend", html);
        }
      },
    },
  });
})();
