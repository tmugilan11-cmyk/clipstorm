/* One way of saying "there is nothing here yet".
 *
 * The page says it in many shapes: a big dashed box with the favicon, a bare grey
 * paragraph, a row of dashes, a line of 12px text, or nothing at all. This file gives
 * the empty block one shape: a short lead, one plain sentence, and one button when
 * there is an obvious next step. The sentence never blames the reader and never
 * states a number.
 *
 * It repaints the first empty block it can reach through an after hook: the one
 * the frozen page draws into #jobs when no video has been added yet. The words stay the
 * page's own; only the spacing, the text size and the button are new. */
(() => {
  const P = window.PeakCut;
  if (!P) return;

  P.css("polish-empty", `
    #jobs > .empty.pe-empty{gap:9px;padding:36px 18px 38px}
    .pe-empty b{text-wrap:balance}
    .pe-empty .pe-say{max-width:46ch;font-size:13px;line-height:1.55;color:var(--dim);text-wrap:pretty}
    .pe-empty .pe-go{margin-top:5px;display:inline-flex;align-items:center;justify-content:center;
      min-height:36px;padding:0 15px;border:1px solid var(--line-2);border-radius:var(--r-sm);
      background:transparent;color:var(--text);font:inherit;font-size:13px;font-weight:600;
      cursor:pointer;transition:background-color .15s ease,border-color .15s ease,color .15s ease}
    .pe-empty .pe-go:hover{background:var(--muted);border-color:var(--brand);color:var(--brand-deep)}
    .pe-empty .pe-go:active{color:var(--brand-deep)}
    .pe-empty .pe-go:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
    @media (max-width:639px){.pe-empty .pe-go{min-height:44px;min-width:44px;padding:0 18px}}
    @media (prefers-reduced-motion:reduce){.pe-empty .pe-go{transition:none}}
  `);

  // The page's own esc() is global, but this file can be read before it is in scope.
  const say = (v) => {
    const s = String(v == null ? "" : v);
    return typeof esc === "function" ? esc(s)
      : s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  };

  /* No P.empty helper: nothing ever called it, so the empty-block markup is built
     inline in unify() below. One builder, not two. */

  /** Puts the cursor in the link box. Returns false when that box is not on screen. */
  function toLinkBox() {
    const box = document.getElementById("url");
    if (!box) return false;
    const calm = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    try { box.focus({ preventScroll: true }); } catch (e) { box.focus(); }
    try { box.scrollIntoView({ block: "center", behavior: calm ? "auto" : "smooth" }); }
    catch (e) { /* no scroll support: the box is still focused */ }
    return true;
  }

  /** The bare text the page put straight into the block, so no word is invented here. */
  function tail(el) {
    return Array.from(el.childNodes)
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent.replace(/\s+/g, " ").trim())
      .join(" ")
      .trim();
  }

  function unify(root) {
    const own = root.querySelector(":scope > .empty");
    if (!own || own.classList.contains("pe-empty")) return;   // nothing there, or already ours
    const lead = ((own.querySelector("b") || {}).textContent || "").trim();
    const line = tail(own);
    const mark = own.querySelector("img");
    const canPaste = !!document.getElementById("url");
    own.className = "empty pe-empty";
    own.innerHTML = (mark ? mark.outerHTML : "")
      + (lead ? `<b>${say(lead)}</b>` : "")
      + (line ? `<span class="pe-say">${say(line)}</span>` : "")
      + (canPaste ? `<button type="button" class="pe-go" data-act="peemptyfocus">Paste a link</button>` : "");
  }

  P.add("polish-empty", {
    act: {
      /** [data-act="peemptyfocus"]: the one button on an empty block. */
      peemptyfocus() { toLinkBox(); },
    },
    after: {
      drawJobs(root) {
        if (root) unify(root);
      },
    },
  });
})();
