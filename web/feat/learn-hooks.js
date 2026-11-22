/* "How the hooks read" - a card on the Improve page.
   Scores the hooks of real finished clips with the same checker the engine uses, so the page and the
   engine cannot disagree. Every number comes from /api/learn/hooks; when there are no clips it says so. */
(() => {
  const P = window.PeakCut;
  if (!P) return;
  let CACHE = null;

  P.css("learn-hooks", `
    .lhk .row{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:13px;line-height:1.5}
    .lhk .pill{border-radius:99px;padding:1px 9px;font-size:12px;border:1px solid var(--line)}
    .lhk .pill.s{color:var(--good);border-color:var(--good)}
    .lhk .pill.w{color:#B98900;border-color:#B98900}
    .lhk .pill.k{color:var(--bad);border-color:var(--bad)}
    .lhk .rows{display:grid;gap:8px;margin-top:10px}
  `);

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function card(got) {
    const pill = (v) => `<span class="pill ${v === "strong" ? "s" : v === "workable" ? "w" : "k"}">${esc(v)}</span>`;
    const top = got.count
      ? `<p class="sub">${got.count} hook${got.count === 1 ? "" : "s"} scored: ${got.strong} strong, ${got.workable} workable, ${got.weak} weak.</p>`
      : `<p class="sub">${esc(got.note || "No finished clips with hooks yet.")}</p>`;
    const rows = (got.hooks || []).slice(0, 6).map((h) =>
      `<div class="row"><span class="pill ${h.verdict === "strong" ? "s" : h.verdict === "workable" ? "w" : "k"}">${h.score}</span>
       <span>${esc(h.hook)}</span><span style="color:var(--dim);font-size:12px">${esc((h.reasons || [])[0] || "")}</span></div>`).join("");
    return `<section class="box lhk" data-lhk><h3>How the hooks read</h3>${top}
      ${rows ? `<div class="rows">${rows}</div>` : ""}</section>`;
  }

  function fill(root) {
    const host = (root && root.querySelector ? root : document).querySelector("#view .lrn");
    if (!host || host.querySelector("[data-lhk]")) return;
    const sec = document.createElement("template");
    sec.innerHTML = card(CACHE || { count: 0, hooks: [], note: "Reading the hooks…" });
    const node = sec.content.firstElementChild;
    host.appendChild(node);
    if (CACHE) return;
    P.api("/api/learn/hooks?limit=40").then((got) => {
      CACHE = got;
      const fresh = host.querySelector("[data-lhk]");
      if (fresh) fresh.outerHTML = card(got);
    }).catch((e) => {
      const fresh = host.querySelector("[data-lhk]");
      if (fresh) fresh.querySelector(".sub").textContent = (e && e.message) || "The hooks could not be read.";
    });
  }

  P.add("learn-hooks", { after: { drawSettings(root) { try { fill(root); } catch (e) { /* never break the page */ } } } });
})();
