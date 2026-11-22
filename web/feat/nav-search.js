/* A small find box at the top of the left menu. Type part of a row's name and the menu
 * keeps only the rows that match; a heading whose rows have all gone goes too. Escape
 * empties the box. The menu is redrawn from scratch on every refresh, so the box puts
 * itself back with whatever was typed still in it, caret and all. */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  const BOX = "#pc_navsearch";

  let query = "";      // the words in the box, kept across a redraw
  let held = false;    // the box last had the caret, so it should get it back
  let watched = null;  // the #nav element the observer sits on
  let listening = false;

  P.css("nav-search", `
    ${BOX}{position:sticky;top:0;z-index:2;background:var(--frame);padding:0 2px 8px}
    ${BOX} input{width:100%;height:32px;font-size:13px;color:var(--frame-text);background:var(--frame-2);border:1px solid var(--frame-line);border-radius:8px;padding:0 10px}
    ${BOX} input::placeholder{color:var(--frame-dim)}
    ${BOX} input:focus{border-color:var(--brand)}
    ${BOX} input:focus-visible{outline:2px solid var(--brand);outline-offset:1px}
    ${BOX} .nv-none{margin:7px 2px 2px;font-size:12px;line-height:1.45;color:var(--frame-dim)}
    .app.mini ${BOX}{display:none}
  `);

  // What a row answers to: the words in its label, or all its text when it has none.
  const name = (row) => {
    const l = row.querySelector(".label");
    return (l ? l.textContent : row.textContent).trim().toLowerCase();
  };
  // Hide what does not match. Only rows this box hid are shown again, so another
  // feature's own hiding is left alone.
  function apply(nav) {
    const box = nav.querySelector(BOX);
    if (!box) return;
    const q = query.trim().toLowerCase();
    let shown = 0;
    for (const row of nav.querySelectorAll(".nav-item")) {
      const hit = !q || name(row).includes(q);
      if (hit && row.dataset.nvh) { row.hidden = false; delete row.dataset.nvh; }
      else if (!hit && !row.hidden) { row.hidden = true; row.dataset.nvh = "1"; }
      if (!row.hidden) shown++;
    }
    for (const h of nav.querySelectorAll("h4")) {
      let any = false;
      for (let n = h.nextElementSibling; n && n.tagName !== "H4"; n = n.nextElementSibling) {
        if (n.classList.contains("nav-item") && !n.hidden) { any = true; break; }
      }
      if (any && h.dataset.nvh) { h.hidden = false; delete h.dataset.nvh; }
      else if (!any && !h.hidden) { h.hidden = true; h.dataset.nvh = "1"; }
    }
    const none = box.querySelector(".nv-none");
    if (none) none.hidden = !q || shown > 0;
  }

  function build(nav) {
    const box = document.createElement("div");
    box.id = "pc_navsearch";
    box.setAttribute("role", "search");
    box.innerHTML = `<input type="text" aria-label="Find a page in the menu" autocomplete="off" spellcheck="false" placeholder="Find a page or creator"><p class="nv-none" hidden>No page or creator has that name.</p>`;
    const field = box.firstElementChild;
    field.value = query;
    field.addEventListener("input", () => { held = true; query = field.value; apply(nav); });
    field.addEventListener("keydown", (e) => {
      held = true;
      if (e.key !== "Escape") return;
      e.stopPropagation();              // Escape here empties the box, it does not close a panel
      query = field.value = "";
      held = false;
      apply(nav);
      field.blur();
    });
    if (!listening) {
      listening = true;
      // Someone working somewhere else is not someone the box should pull the caret from.
      document.addEventListener("pointerdown", (e) => {
        held = !!(e.target.closest && e.target.closest(BOX));
      });
    }
    nav.insertBefore(box, nav.firstElementChild);   // above the first row
    return box;
  }

  // Put the box in, or take over the one already there and just refilter it.
  function mount(nav) {
    let box = nav.querySelector(BOX);
    const fresh = !box;
    if (fresh) box = build(nav);
    const field = box.querySelector("input");
    if (field && field.value !== query) field.value = query;
    apply(nav);
    // The browser clears the caret as the old box leaves, so ask for it back on a timer
    // that runs after the menu has settled. Nothing else on the page wants the caret.
    if (fresh && held && field) setTimeout(() => {
      if (!field.isConnected || document.activeElement === field) return;
      field.focus({ preventScroll: true });
      field.setSelectionRange(field.value.length, field.value.length);
    }, 0);
  }

  function start() {
    const nav = document.getElementById("nav");
    if (!nav) return;
    if (watched !== nav) {
      watched = nav;
      // A redraw replaces the menu's markup only, so watching the menu is enough.
      new MutationObserver(() => { const n = document.getElementById("nav"); if (n) mount(n); })
        .observe(nav, { childList: true });
    }
    mount(nav);
  }

  start();

  P.add("nav-search", {
    after: {
      /** Runs after the shell was drawn, so the box comes back where it belongs. */
      drawShell() { start(); },
    },
  });
})();
