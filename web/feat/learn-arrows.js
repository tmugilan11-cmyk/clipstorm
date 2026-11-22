/* "Every round, before and after" - a card on the Improve page.
   Reads /api/learn/report and draws each round's settings as they were and as they became, from the
   stored rounds only. No invented numbers: a round that changed nothing shows that it changed nothing. */
(() => {
  const P = window.PeakCut;
  if (!P) return;
  let CACHE = null;

  P.css("learn-arrows", `
    .lra .rnd{border:1px solid var(--line);border-radius:12px;padding:10px 14px;display:grid;gap:6px}
    .lra .rnd .top{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;font-size:13px}
    .lra .rnd .top .w{color:var(--dim)}
    .lra .chg{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:13px;line-height:1.5}
    .lra code{background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:1px 6px;font-size:12px}
    .lra .arrow{color:var(--brand);font-weight:600}
    .lra .none{color:var(--dim);font-size:13px}
  `);

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const NAMES = { style: "Caption look", hook_words: "How the hook is written", clip_len: "How long a clip may be",
                  sound: "Sound under a clip", captions_always: "Captions on every clip" };

  function card(got) {
    const rounds = (got.rounds || []).slice(0, 8);
    const body = rounds.length ? rounds.map((r) => {
      const chg = (r.changes || []).map((c) =>
        `<div class="chg"><span>${esc(NAMES[c.setting] || c.setting)}</span><code>${esc(c.from)}</code>
         <span class="arrow">&#8594;</span><code>${esc(c.to)}</code></div>`).join("");
      return `<div class="rnd"><div class="top"><b>${esc(r.when || "")}</b><span class="w">${esc(r.days ? "looked at " + r.days + " days" : "")}</span></div>
        ${chg || `<div class="none">${esc(r.saying || r.effect || "Nothing was changed.")}</div>`}</div>`;
    }).join("") : `<div class="none">No rounds have run yet. Press "Analyse and improve" above.</div>`;
    return `<section class="box lra" data-lra><h3>Every round, before and after</h3>${body}</section>`;
  }

  function fill(root) {
    const host = (root && root.querySelector ? root : document).querySelector("#view .lrn");
    if (!host || host.querySelector("[data-lra]")) return;
    const t = document.createElement("template");
    t.innerHTML = card(CACHE || { rounds: [] });
    const node = t.content.firstElementChild;
    host.appendChild(node);
    if (CACHE) return;
    P.api("/api/learn/report?limit=8").then((got) => {
      CACHE = got;
      const fresh = host.querySelector("[data-lra]");
      if (fresh) fresh.outerHTML = card(got);
    }).catch((e) => {
      const fresh = host.querySelector("[data-lra]");
      if (fresh) fresh.insertAdjacentHTML("beforeend", `<p class="none">${esc((e && e.message) || "The report could not be read.")}</p>`);
    });
  }

  P.add("learn-arrows", { after: { drawSettings(root) { try { fill(root); } catch (e) { /* never break the page */ } } } });
})();
