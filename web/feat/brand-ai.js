/* "Ask for a brand" - a card on the Improve page.
   Asks the AI for brand settings that could travel better, shows them next to the current ones, and
   applies ONLY on an explicit press of Apply. The route itself never writes, and neither does this card
   until the person says so. */
(() => {
  const P = window.PeakCut;
  if (!P) return;
  let LINES = null;   // the last suggestion, kept so a repaint does not clear it

  P.css("brand-ai", `
    .bai .ask{display:flex;gap:8px;flex-wrap:wrap}
    .bai .ask input{flex:1;min-width:220px;background:var(--panel2);color:var(--ink);border:1px solid var(--line);
      border-radius:10px;padding:8px 10px;font-size:13px}
    .bai .chg{margin:0;padding:0;list-style:none;display:grid;gap:8px}
    .bai .chg li{font-size:13px;line-height:1.55}
    .bai .chg li b{font-weight:600}
    .bai code{background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:1px 6px;font-size:12px}
  `);

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const NAMES = { style: "Caption look", hook_words: "How the hook is written", clip_len: "How long a clip may be",
                  sound: "Sound under a clip", captions: "Captions on every clip" };

  function card() {
    if (!LINES) return `<section class="box bai" data-bai><h3>Ask for a brand</h3>
      <p class="sub">Describe what you post and the AI suggests caption settings that could travel better.
      Nothing is applied until you press Apply.</p>
      <div class="ask"><input data-bai-q maxlength="200" placeholder="what do you post? for example: game highlights with big reactions">
        <button class="btn sm" type="button" data-bai-go>Ask</button></div>
      <p class="why" data-bai-note></p></section>`;
    const chg = (LINES.changes || []).map((c) =>
      `<li><b>${esc(NAMES[c.key] || c.key)}:</b> <code>${esc(c.from)}</code> to <code>${esc(c.to)}</code>
       ${c.why ? `<span style="color:var(--dim)"> - ${esc(c.why)}</span>` : ""}</li>`).join("");
    return `<section class="box bai" data-bai><h3>Ask for a brand</h3>
      <div class="ask"><input data-bai-q maxlength="200" value="${esc(LINES.q || "")}" placeholder="what do you post?">
        <button class="btn sm" type="button" data-bai-go>Ask again</button></div>
      ${chg ? `<ul class="chg">${chg}</ul>
        <div class="btnrow" style="margin-top:10px"><button class="btn sm" type="button" data-bai-apply>Apply these</button></div>`
        : `<p class="why" style="margin-top:10px">${esc(LINES.why || "The AI answered, but with nothing this brand accepts.")}</p>`}
      <p class="why" data-bai-note></p></section>`;
  }

  function paint(host) {
    const old = host.querySelector("[data-bai]");
    const t = document.createElement("template");
    t.innerHTML = card();
    const node = t.content.firstElementChild;
    if (old) old.replaceWith(node); else host.appendChild(node);
    const go = node.querySelector("[data-bai-go]");
    if (go) go.addEventListener("click", () => ask(host));
    const ap = node.querySelector("[data-bai-apply]");
    if (ap) ap.addEventListener("click", () => apply(host, ap));
  }

  function note(host, text) {
    const n = host.querySelector("[data-bai] [data-bai-note]");
    if (n) n.textContent = text || "";
  }

  function ask(host) {
    const q = host.querySelector("[data-bai-q]");
    const said = q ? q.value.trim() : "";
    if (!said) { note(host, "Say what you post first, in a few words."); return; }
    note(host, "Asking the AI…");
    P.send("/api/brandai/suggest", { about: said }).then((got) => {
      LINES = { changes: got.changes || [], why: got.why || "", q: said, after: got.after || null };
      paint(host);
    }).catch((e) => note(host, (e && e.message) || "The suggestion did not finish."));
  }

  function apply(host, btn) {
    if (!LINES || !LINES.after) return;
    btn.disabled = true;
    btn.textContent = "Applying…";
    P.send("/api/brand", LINES.after, "PUT").then(() => {
      if (P.toast) P.toast("Brand changed. Clips made from now on use it.");
      LINES = null;
      paint(host);
    }).catch((e) => {
      btn.disabled = false;
      btn.textContent = "Apply these";
      note(host, (e && e.message) || "The brand could not be saved.");
    });
  }

  function fill(root) {
    const host = (root && root.querySelector ? root : document).querySelector("#view .lrn");
    if (!host || host.querySelector("[data-bai]")) return;
    paint(host);
  }

  P.add("brand-ai", { after: { drawSettings(root) { try { fill(root); } catch (e) { /* never break the page */ } } } });
})();
