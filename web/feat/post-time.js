/* "When to post" - a card on the Improve page.
   Reads this account's own posting record; the honest answer for a quiet account is the route's own
   "Not enough posts yet", never a made-up clock. */
(() => {
  const P = window.PeakCut;
  if (!P) return;
  let CACHE = null;

  P.css("post-time", `
    .ptm .best{display:grid;gap:8px;margin-top:10px}
    .ptm .row{display:flex;gap:10px;align-items:baseline;font-size:13px;line-height:1.5}
    .ptm .hr{font-weight:600;min-width:52px}
    .ptm .say{color:var(--dim);font-size:12px}
  `);

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function card(got) {
    if (!got.enough) return `<section class="box ptm" data-ptm><h3>When to post</h3>
      <p class="sub">${esc(got.note || "Not enough posts yet.")}</p></section>`;
    const rows = (got.best || []).map((b) =>
      `<div class="row"><span class="hr">${esc(b.label)}</span>
       <span>${esc(b.posts)} post${b.posts === 1 ? "" : "s"}, ${b.mean_views} views on average</span></div>`).join("");
    return `<section class="box ptm" data-ptm><h3>When to post</h3>
      <p class="sub">${esc(got.note || "")}</p><div class="best">${rows}</div></section>`;
  }

  function fill(root) {
    const host = (root && root.querySelector ? root : document).querySelector("#view .lrn");
    if (!host || host.querySelector("[data-ptm]")) return;
    const t = document.createElement("template");
    t.innerHTML = card(CACHE || { enough: false, note: "Reading the posting record…" });
    const node = t.content.firstElementChild;
    host.appendChild(node);
    if (CACHE) return;
    P.api("/api/posttime").then((got) => {
      CACHE = got;
      const fresh = host.querySelector("[data-ptm]");
      if (fresh) fresh.outerHTML = card(got);
    }).catch((e) => {
      const fresh = host.querySelector("[data-ptm]");
      if (fresh) fresh.querySelector(".sub").textContent = (e && e.message) || "The posting record could not be read.";
    });
  }

  P.add("post-time", { after: { drawSettings(root) { try { fill(root); } catch (e) { /* never break the page */ } } } });
})();
