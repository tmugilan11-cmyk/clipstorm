/* PeakCut · keys
   Shortcuts for the clip dialog and the review page, plus a quiet hint line
   so people know the keys exist. One plug-in, one file.

   Every key here clicks a button the page already renders, so the shortcut
   can never drift from the real logic. The page's own a / x / s on the review
   page are left alone on purpose: index.html wires those before plug-ins load,
   and binding them again would send two decisions for one key press. */
(() => {
  const P = window.PeakCut;
  if (!P) return;

  P.css("keys", `
    .pckeys{display:flex;flex-wrap:wrap;align-items:center;gap:4px 9px;margin:12px 0 0;color:var(--faint);font-size:12px;line-height:1.7}
    .pckeys>span{display:inline-flex;align-items:center;gap:6px}
    .pckeys>span+span::before{content:"";display:inline-block;width:1px;height:11px;margin-right:2px;background:var(--line-2)}
    .pckeys kbd{font:inherit;font-size:11px;font-weight:600;line-height:18px;min-width:20px;padding:0 5px;text-align:center;color:var(--dim);background:var(--muted);border:1px solid var(--line-2);border-bottom-width:2px;border-radius:6px}
    .pckeys .lead{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--faint)}
    .pckeys.in-dlg{margin:8px 0 0}
  `);

  /* Own text, no server strings, so nothing here needs escaping. */
  const HINT_REVIEW =
    `<span class="lead">Keys</span>` +
    `<span><kbd>Enter</kbd>approve</span>` +
    `<span><kbd>Backspace</kbd>reject</span>` +
    `<span><kbd>Right</kbd>next clip</span>`;

  const HINT_DLG =
    `<span class="lead">Keys</span><span><kbd>Esc</kbd>close</span>`;

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => [...(root || document).querySelectorAll(sel)];

  function hint(html, extra) {
    const p = document.createElement("p");
    p.className = "pckeys" + (extra ? " " + extra : "");
    p.innerHTML = html;
    return p;
  }

  /* ---------- guards: nothing fires while someone is typing or in a dialog */

  function typing(e) {
    const t = e.target;
    if (!t || !t.tagName) return false;
    if (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT") return true;
    if (t.isContentEditable) return true;
    /* Enter and Space on a focused button are the browser's own click, so leave
       them alone. Escape is not, and has to keep working from anywhere. */
    if (e.key === "Enter" || e.key === " ") {
      return !!(t.closest && t.closest("button, a, [role='button'], summary"));
    }
    return false;
  }

  function formOpen() {
    const f = document.getElementById("formdlg");
    return !!(f && f.open);
  }

  function otherDialogOpen() {
    for (const d of $$("dialog[open]")) if (d.id !== "clipdlg") return true;
    return false;
  }

  /* The guided tour reads keys in the capture phase and stops them, but check
     for it anyway so the tour never fights a shortcut. */
  function touring() {
    return !!document.getElementById("tour");
  }

  /* ---------- review page */

  /* The page treats the first card without a decision as the cursor, so read
     the same thing off the rendered pills instead of guessing. */
  function cursorCard(root) {
    return $$(".rv-card[data-cid]", root).find(c => !$(".pill.ok, .pill.bad", c)) || null;
  }

  function reviewKey(e, root) {
    /* Holding a key must not walk down the list deciding clip after clip. */
    if (e.repeat) return false;
    const card = cursorCard(root);
    if (!card) return false;
    const act = e.key === "Enter" ? "rvapprove"
      : e.key === "Backspace" ? "rvreject"
      : e.key === "ArrowRight" ? "rvskip"
      : "";
    if (!act) return false;
    const btn = $(`[data-act="${act}"]`, card);
    if (!btn) return false;
    btn.click();
    return true;
  }

  /* ---------- clip dialog */

  function clipKey(e, dlg) {
    if (e.key !== "Escape") return false;
    const btn = $('[data-act="closedlg"]', dlg);
    if (btn) { btn.click(); return true; }
    dlg.close();
    return true;
  }

  /* ---------- the one entry point the loader calls */

  function keys(e) {
    if (!e || e.ctrlKey || e.metaKey || e.altKey) return false;
    if (typing(e) || formOpen() || otherDialogOpen() || touring()) return false;

    const dlg = document.getElementById("clipdlg");
    if (dlg && dlg.open) return clipKey(e, dlg);

    const root = document.getElementById("rvroot");
    if (root && root.getClientRects().length) return reviewKey(e, root);
    return false;
  }

  /* ---------- hint lines */

  /* In the clip dialog: the dialog is repainted from scratch every time the
     clip changes, so drop the line back in whenever it went away. */
  function syncDlg() {
    const dlg = document.getElementById("clipdlg");
    if (!dlg || !dlg.open) return;
    const panel = $(".panel", dlg);
    if (!panel || $(".pckeys", panel)) return;
    panel.appendChild(hint(HINT_DLG, "in-dlg"));
  }

  function drawClipDlg(root) {
    const panel = root && $(".panel", root);
    if (!panel || $(".pckeys", panel)) return;
    panel.appendChild(hint(HINT_DLG, "in-dlg"));
  }

  /* On the review page, right under the list it describes, whenever there are
     clips to look at. It stays put with every clip decided: that is exactly
     when someone wants to know the keys exist. */
  function syncReview() {
    const root = document.getElementById("rvroot");
    if (!root || !root.getClientRects().length) return;
    if ($(".pckeys", root)) return;
    const list = $(".rv-list", root);
    if (!list) return;
    list.insertAdjacentElement("afterend", hint(HINT_REVIEW));
  }

  /* A plain timeout, not a frame: this has to work the same in a background
     tab, where frames do not run. */
  let queued = false;
  function queueSync() {
    if (queued) return;
    queued = true;
    setTimeout(() => { queued = false; syncReview(); syncDlg(); }, 0);
  }

  try {
    if (window.MutationObserver) {
      const mo = new MutationObserver(queueSync);
      const view = document.getElementById("view");
      const dlg = document.getElementById("clipdlg");
      if (view) mo.observe(view, {childList: true, subtree: true});
      if (dlg) mo.observe(dlg, {childList: true, subtree: true});
    }
  } catch {}

  queueSync();

  P.add("keys", { keys, after: { drawClipDlg } });
})();
