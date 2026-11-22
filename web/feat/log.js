/* What actually happened when a video failed.
 *
 * A failed video's card shows one red line and stops there, which leaves a person with no way to see the reason.
 * The server keeps that reason in the job's own folder and now sends the end of it back as `log_tail` on
 * `GET /api/jobs/{jid}`. This puts a "Show log" control on the error line and opens the text underneath it,
 * only when someone asks for it. Nothing is fetched until then. */
(() => {
  window.PeakCut.css("log", `
    .joblog{margin:2px 0 12px}
    .joblog:empty{display:none}
    .joblog-pre{margin:0;padding:11px 12px;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--muted);
      color:var(--text);font:12px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
      max-height:260px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;tab-size:2;animation:joblogin .14s ease both}
    .joblog-pre:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
    .joblog-none{margin:0;padding:11px 12px;border:1px dashed var(--line-2);border-radius:var(--r-sm);color:var(--dim);font-size:13px}
    .joblog-btn:focus-visible{outline:2px solid var(--bad);outline-offset:2px;border-radius:3px}
    @keyframes joblogin{from{opacity:0}to{opacity:1}}
    @media (prefers-reduced-motion:reduce){.joblog-pre{animation:none}}
  `);

  const LIMIT = 80;                 // the server caps it too; this is a second cap on this side
  const open = new Map();           // job id -> is the text showing right now
  const cache = new Map();          // job id -> {lines} or {errorText}, so a redraw never asks the server again
  const asking = new Set();         // job ids with a request in flight

  const cardFor = (id) => document.querySelector(`section[data-job="${CSS.escape(String(id))}"]`);
  const boxId = (id) => "logbox-" + String(id).replace(/[^\w-]/g, "");
  const short = (e) => String((e && e.message) || e || "").slice(0, 160);

  // The text itself. Every line goes through esc(): a traceback is full of angles and quotes.
  function boxHtml(got) {
    const attrs = `class="joblog-pre" tabindex="0" aria-label="Log for this video"`;
    if (!got) return `<pre ${attrs}>Reading the log...</pre>`;
    if (got.errorText) return `<pre ${attrs}>${esc(got.errorText)}</pre>`;
    const lines = (got.lines || []).slice(-LIMIT);
    if (!lines.length) return `<p class="joblog-none">This video has no log written for it.</p>`;
    return `<pre ${attrs}>${lines.map(esc).join("\n")}</pre>`;
  }

  async function ask(id) {
    asking.add(id);
    const path = "/api/jobs/" + encodeURIComponent(id);
    try {
      const d = await (window.PeakCut.api ? window.PeakCut.api(path) : api(path));
      cache.set(id, {lines: d && Array.isArray(d.log_tail) ? d.log_tail.map(String) : []});
    } catch (e) {
      // One quiet line in the box. Nothing is thrown at the page.
      cache.set(id, {lines: [], errorText: "The log could not be read just now. " + short(e)});
    } finally {
      asking.delete(id);
    }
    const card = cardFor(id);
    if (card) paint(id, card.querySelector(".joblog"), card.querySelector(".joblog-btn"));
  }

  // Draw one card's control and box from the state above. Safe to call as often as the list repaints.
  function paint(id, box, btn) {
    const isOpen = open.get(id) === true;
    const got = cache.get(id);
    if (btn) {
      btn.textContent = isOpen ? "Hide log" : "Show log";
      btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }
    if (!box) return;
    const stamp = !isOpen ? "closed" : !got ? "loading" : got.errorText ? "failed"
                : ((got.lines || []).length ? "lines" : "empty");
    if (box.dataset.log === stamp) return;          // already showing this: leave the scroll position alone
    box.dataset.log = stamp;
    box.innerHTML = isOpen ? boxHtml(got) : "";
    if (isOpen && !got && !asking.has(id)) ask(id);
  }

  window.PeakCut.add("log", {
    after: {
      /** Runs whenever the job list is redrawn: one control per card that says something failed. */
      drawJobs(root) {
        const state = window.PeakCut.state && window.PeakCut.state();
        const jobs = (state && state.jobs) || [];
        for (const job of jobs) {
          if (!job || !job.id || !job.error) continue;        // only a card that reports a failure
          const card = root.querySelector(`section[data-job="${CSS.escape(String(job.id))}"]`);
          if (!card) continue;
          const line = card.querySelector(".err");
          if (!line) continue;
          if (!line.querySelector(".joblog-btn")) {
            line.insertAdjacentHTML("beforeend",
              `<button class="rep joblog-btn" type="button" data-act="joblog" data-j="${esc(job.id)}" ` +
              `aria-controls="${esc(boxId(job.id))}">Show log</button>`);
          }
          let box = card.querySelector(".joblog");
          if (!box) {
            box = document.createElement("div");
            box.className = "joblog";
            box.id = boxId(job.id);
            line.insertAdjacentElement("afterend", box);
          }
          paint(job.id, box, line.querySelector(".joblog-btn"));
        }
      },
    },

    act: {
      /** The button itself: open or close this card's log. */
      joblog(b) {
        const id = String(b.dataset.j || "").trim();
        if (!id) return;
        const nowOpen = !open.get(id);
        open.set(id, nowOpen);
        const got = cache.get(id);
        if (nowOpen && got && got.errorText) cache.delete(id);   // it failed last time: give it another go
        const card = b.closest("section[data-job]");
        paint(id, card && card.querySelector(".joblog"), b);
      },
    },
  });
})();
