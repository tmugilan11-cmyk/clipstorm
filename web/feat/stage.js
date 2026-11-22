/* Four small dots on a running job card: Download, Listen, Pick moments, Make clips.
 *
 * The card already says a percentage and a sentence. A percentage cannot say where the job is, so this
 * adds the four steps it really walks, one lit, the ones behind it done, the ones ahead waiting. It reads
 * the strings peakcut/studio/jobs.py really sets, so it never has to guess what a stage means. */
(() => {
  window.PeakCut.css("stage", `
    .pcstage{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin:0 0 7px}
    .pcstage .st{display:inline-flex;align-items:center;gap:6px;padding:3px 9px 3px 7px;border-radius:999px;border:1px solid var(--line);background:var(--bg);color:var(--faint);font-size:12px;font-weight:500;line-height:1.5;white-space:nowrap;transition:color .2s ease,background-color .2s ease,border-color .2s ease}
    .pcstage .st i{width:6px;height:6px;border-radius:999px;background:var(--line-2);flex:none;transition:background-color .2s ease}
    .pcstage .st.done{color:var(--brand-deep);border-color:var(--brand-line);background:var(--brand-soft)}
    .pcstage .st.done i{background:var(--brand)}
    .pcstage .st.now{color:var(--text);border-color:var(--brand);background:var(--brand);font-weight:600}
    .pcstage .st.now i{background:var(--brand-ink);animation:pcstagedot 1.6s ease-in-out infinite}
    .pcstage .st.wait{opacity:.72}
    @keyframes pcstagedot{0%,100%{opacity:.35;transform:scale(.86)}50%{opacity:1;transform:scale(1)}}
    @media (prefers-reduced-motion: reduce){.pcstage .st.now i{animation:none;opacity:1;transform:none}}
    @media (max-width:560px){.pcstage .st{font-size:11px;padding:2px 8px 2px 6px}}
  `);

  const STEPS = ["Download", "Listen", "Pick moments", "Make clips"];

  // The stages jobs.py really sets, matched in the order a job meets them.
  // "Getting the audio" is the audio download, so it lights Download and not Listen.
  const RULES = [
    [/transcript|transcrib|listening|hearing/i, 1],                    // Reading / Writing the transcript
    [/best moment|finding|moments?\b|\bai\b|thinking/i, 2],             // Finding the best moments
    [/finishing|making the clips|render|caption|export/i, 3],           // Finishing the clips
    [/getting|download|fetch|speech model|waiting|ahead of yours|high demand|queue/i, 0],
  ];

  // These two say nothing about how far along the job is, so the progress figure decides instead.
  const VAGUE = /^(picking up where it stopped|waiting)\b/i;

  // The bands the server's own progress numbers walk: fetching runs to about .13, the transcript from .14
  // to .92, and the clips from .92 on. A part of the file is written, then read by the AI, over and over,
  // so the middle band is mostly listening. Picking is named outright when it happens.
  function band(pct) {
    const p = Math.max(0, Math.min(1, Number(pct) || 0));
    if (p >= 0.92) return 3;
    if (p >= 0.14) return 1;
    return 0;
  }

  function stepOf(job) {
    const stage = String(job.stage || "").trim();
    if (VAGUE.test(stage)) return band(job.progress);
    for (const [re, idx] of RULES) if (re.test(stage)) return idx;
    return 0;    // a stage this file has not met yet stays on the first dot, and says nothing about it
  }

  function block(job) {
    const now = stepOf(job);
    const chips = STEPS.map((label, i) => {
      const state = i < now ? "done" : i === now ? "now" : "wait";
      return `<span class="st ${state}"${i === now ? ' aria-current="step"' : ""}><i aria-hidden="true"></i>${label}</span>`;
    }).join("");
    return `<div class="pcstage" data-step="${now}" role="group" aria-label="Step ${now + 1} of ${STEPS.length}: ${STEPS[now]}">${chips}</div>`;
  }

  // A finished, failed or recorded job keeps the plain card: the dots only mean something while work runs.
  const LIVE = new Set(["queued", "running"]);

  window.PeakCut.add("stage", {
    after: {
      /** Runs whenever the job list is redrawn. Puts the four dots under the bar of each job still being worked on. */
      drawJobs(root) {
        const state = window.PeakCut.state();
        const jobs = (state && state.jobs) || [];
        for (const card of root.querySelectorAll("section[data-job]")) {
          const job = jobs.find(j => String(j.id) === card.dataset.job);
          if (!job || !LIVE.has(String(job.status || ""))) continue;
          const bar = card.querySelector(".bar");
          if (!bar) continue;                                    // no bar, nothing to sit under
          const old = card.querySelector(".pcstage");
          if (old && old.dataset.step === String(stepOf(job))) continue;   // already right for this job
          if (old) old.remove();
          bar.insertAdjacentHTML("afterend", block(job));
        }
      },
    },
  });
})();
