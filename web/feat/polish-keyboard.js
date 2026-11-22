/* PeakCut · polish-keyboard
 *
 * Three jobs, all about the keyboard:
 *
 *   1. "?" opens one panel that lists every shortcut PeakCut really has. Every row
 *      below was read out of the file that answers that key, so the list cannot
 *      promise a key nothing handles. keys.js owns the review and clip-dialog keys,
 *      index.html owns a / x / s and the pop-up menus; this file only prints them.
 *   2. Escape closes the newest open panel. keys.js already closes the clip dialog,
 *      index.html already closes its pop-ups and dropdowns, so this adds the one
 *      panel nothing closed: the composer's Options row. It also closes this panel.
 *   3. Focus never lands on a control the person cannot see. If the page focuses
 *      something hidden, inside [inert], or with no box at all, focus moves on.
 *
 * Handlers live in the PeakCut.add block: a handler declared inside PeakCut.page
 * never fires, because only PeakCut.add is wired to the page's listeners.
 */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  P.css("polish-keyboard", `
    .pckb-panel{position:fixed;z-index:80;top:14px;right:14px;width:min(430px,calc(100vw - 28px));
      max-height:min(76vh,640px);overflow:auto;overscroll-behavior:contain;
      background:var(--bg);color:var(--text);border:1px solid var(--line-2);border-radius:var(--r-lg);
      padding:16px 18px 18px;animation:pckb-in .16s ease}
    .pckb-panel[hidden]{display:none}
    @keyframes pckb-in{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
    .pckb-head{display:flex;align-items:flex-start;gap:12px;margin:0 0 12px}
    .pckb-title{flex:1;margin:0;font-size:16px;line-height:1.35;font-weight:650;letter-spacing:-.01em}
    .pckb-x{display:grid;place-items:center;width:30px;height:30px;margin:-4px -6px 0 0;border:0;border-radius:var(--r-sm);
      background:transparent;color:var(--dim);font:inherit;font-size:19px;line-height:1;cursor:pointer}
    .pckb-x:hover{background:var(--muted);color:var(--text)}
    .pckb-g{margin:14px 0 0}
    .pckb-g:first-of-type{margin-top:0}
    .pckb-gh{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--faint);margin:0 0 7px}
    .pckb-list{list-style:none;margin:0;padding:0;display:grid;gap:2px}
    .pckb-list li{display:grid;grid-template-columns:minmax(64px,auto) 1fr;align-items:baseline;gap:10px;padding:5px 0}
    .pckb-list kbd{justify-self:start;font:inherit;font-size:12px;font-weight:600;line-height:19px;
      min-width:22px;padding:0 6px;text-align:center;color:var(--dim);
      background:var(--muted);border:1px solid var(--line-2);border-bottom-width:2px;border-radius:6px;white-space:nowrap}
    .pckb-list span{font-size:13px;line-height:1.5;color:var(--dim)}
    .pckb-note{margin:14px 0 0;padding-top:12px;border-top:1px solid var(--line);font-size:12px;line-height:1.6;color:var(--faint)}
    .pckb-panel :focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
    .pckb-tools{margin:0}
    @media (max-width:640px){
      .pckb-panel{top:auto;bottom:10px;left:10px;right:10px;width:auto;max-height:72vh;padding:14px}
      .pckb-x{width:44px;height:44px;margin:-8px -8px 0 0;font-size:21px}
    }
    @media (prefers-reduced-motion:reduce){.pckb-panel{animation:none}}
  `);

  /* Every row below is a key some file answers. The right-hand column names the file
     when more than one page shares the wording, so a reader can go and look. */
  const GROUPS = [
    ["Anywhere", [
      ["?", "Open and close this list"],
      ["Esc", "Close the newest open panel"],
    ]],
    ["Reviewing clips", [
      ["A  Enter", "Say yes to the next clip"],
      ["X  Backspace", "Say no to the next clip"],
      ["S", "Skip to the next undecided clip"],
      ["Right", "Go to the next clip"],
    ]],
    ["The clip window", [
      ["Esc", "Close the clip window"],
    ]],
    ["Menus and pop-ups", [
      ["Esc", "Close the notifications or account menu"],
      ["Esc", "Put an open dropdown away"],
      ["Up  Down", "Step through an open dropdown"],
      ["Esc", "Empty the menu search box"],
      ["Esc", "Close the menu on a narrow window"],
    ]],
    ["The tour", [
      ["Right  Left", "Next or previous step"],
      ["Esc", "End the tour"],
    ]],
    ["Typing in a field", [
      ["Enter", "Add the link in the link box"],
      ["Enter", "Add the word on the Live page"],
      ["Enter", "Run the day on the Day page"],
      ["Enter", "Read the key on the Stats page"],
      ["Esc", "Empty the filter box on All videos"],
    ]],
    ["Charts", [
      ["Left  Right", "Step one point at a time"],
      ["Up  Down", "Step one point at a time"],
      ["Home  End", "First or last point"],
      ["Esc", "Hide the read-out"],
    ]],
    ["Explainers", [
      ["Esc", "Close an open note on Analytics"],
    ]],
  ];

  const PANEL_ID = "pckb_panel";
  let open = false;
  let returnTo = null;

  function build() {
    const panel = document.createElement("div");
    panel.id = PANEL_ID;
    panel.className = "pckb-panel";
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "false");
    panel.setAttribute("aria-labelledby", "pckb_title");
    // The shell is a fixed string, so no server text can reach it.
    panel.innerHTML =
      '<div class="pckb-head">' +
        '<h2 class="pckb-title" id="pckb_title">Every key Clipstorm answers</h2>' +
        '<button type="button" class="pckb-x" data-pckb="close" aria-label="Close the key list">&#215;</button>' +
      "</div>" +
      '<p class="pckb-note" style="margin:0 0 4px;padding:0;border:0">Press ? at any time to bring this back.</p>' +
      '<div class="pckb-body"></div>' +
      '<p class="pckb-note">Keys are ignored while you type in a field. Anything that runs also has a button you can press.</p>';

    const body = panel.querySelector(".pckb-body");
    for (const [title, rows] of GROUPS) {
      const group = document.createElement("section");
      group.className = "pckb-g";
      const head = document.createElement("h3");
      head.className = "pckb-gh";
      head.textContent = title;                     // own text, still set as text, never as markup
      group.append(head);
      const list = document.createElement("ul");
      list.className = "pckb-list";
      for (const [keys, what] of rows) {
        const li = document.createElement("li");
        const kbd = document.createElement("kbd");
        kbd.textContent = keys;
        const span = document.createElement("span");
        span.textContent = what;
        li.append(kbd, span);
        list.append(li);
      }
      group.append(list);
      body.append(group);
    }
    document.body.append(panel);
    return panel;
  }

  const panel = () => document.getElementById(PANEL_ID) || build();

  function show() {
    const el = panel();
    returnTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    el.hidden = false;
    open = true;
    const x = el.querySelector("[data-pckb]");
    if (x) x.focus({ preventScroll: true });
    el.scrollTop = 0;
  }

  function hide(restore) {
    const el = document.getElementById(PANEL_ID);
    if (!el) return false;
    if (el.hidden) return false;
    el.hidden = true;
    open = false;
    if (restore && returnTo && returnTo.isConnected) {
      try { returnTo.focus({ preventScroll: true }); } catch { returnTo = null; }
    }
    returnTo = null;
    return true;
  }

  /* ---- 2. the newest open panel ---------------------------------------- */

  /* Every panel this file may close. keys.js closes the clip window and
     index.html closes its own pop-ups and dropdowns, so neither is listed. */
  function closeOptions() {
    const box = document.querySelector(".composer-opts.open");
    if (!box) return false;
    box.classList.remove("open");
    box.inert = true;                                  // its fields leave the Tab order with it
    const btn = document.querySelector('[data-act="toggleopts"]');
    if (btn) {
      btn.classList.remove("on");
      btn.setAttribute("aria-expanded", "false");
      try { btn.focus({ preventScroll: true }); } catch { /* the button may be gone */ }
    }
    return true;
  }

  // On a narrow window the sidebar is a drawer and nav-responsive answers Escape
  // itself. Closing a second thing on the same press would be wrong.
  function drawerOpen() {
    const app = document.getElementById("app");
    if (!app || !app.classList.contains("open")) return false;
    return window.matchMedia("(max-width: 900px)").matches;
  }

  // The page already closes these on Escape. Newest first means one press closes
  // one thing, so this stands back and lets the page do it.
  function pagePopupOpen() {
    for (const id of ["bellpop", "acctpop"]) {
      const p = document.getElementById(id);
      if (p && !p.hidden) return true;
    }
    return !!document.querySelector(".pick.open");
  }

  /* The page closes its own pop-ups from a listener that was added before this
     file loads, so on one Escape press it closes first and my check below would
     already see "nothing open". The capture phase runs before every bubble
     listener, so it is the only place that can see the truth at the moment the
     key went down. One press then closes one thing, newest first. */
  let pageTookEscape = false;
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") pageTookEscape = drawerOpen() || pagePopupOpen();
  }, true);

  function escape() {
    if (open) {
      if (pageTookEscape) { pageTookEscape = false; return false; }   // the page's own panel wins this press
      return hide(true);
    }
    pageTookEscape = false;
    if (drawerOpen() || pagePopupOpen()) return false;
    return closeOptions();
  }

  /* ---- 3. focus never lands on a hidden control ------------------------ */

  const TABBABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])';

  function seen(el) {
    if (!el || !el.isConnected) return false;
    if (el.closest("[inert]")) return false;
    if (el.closest('[aria-hidden="true"]')) return false;
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      const cs = window.getComputedStyle(n);
      if (cs.display === "none" || cs.visibility === "hidden" || cs.visibility === "collapse") return false;
    }
    // A control with no box at all cannot be seen, so it cannot keep the caret.
    return typeof el.getClientRects === "function" && el.getClientRects().length > 0;
  }

  let fixing = false;
  function rescue(el) {
    if (fixing) return;
    fixing = true;
    try {
      const all = Array.from(document.querySelectorAll(TABBABLE)).filter(seen);
      const at = all.indexOf(el);
      const next = at >= 0 ? all[at + 1] || all[0] : all[0];
      if (next && next !== el) next.focus({ preventScroll: true });
      else if (el.blur) el.blur();
    } catch { /* a focus guard that throws would be worse than the bad focus */ }
    finally { fixing = false; }
  }

  function onFocusIn(e) {
    const el = e.target;
    if (!el || el === document.body || el === document.documentElement) return;
    if (el.tagName !== "INPUT" && el.tagName !== "TEXTAREA" && el.tagName !== "SELECT" &&
        !el.isContentEditable && el.tabIndex < 0) return;   // programmatic focus, not the Tab order
    if (!seen(el)) rescue(el);
  }

  /* ---- 1 and 2 again, from the one entry point the loader calls -------- */

  function typing(e) {
    const t = e.target;
    if (!t || !t.tagName) return false;
    if (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT") return true;
    return !!t.isContentEditable;
  }

  function dialogOpen() {
    for (const d of document.querySelectorAll("dialog[open]")) return true;
    return false;
  }

  function keys(e) {
    if (!e || e.ctrlKey || e.metaKey || e.altKey || e.repeat) return false;

    if (e.key === "Escape") {
      // A dialog closes itself: the browser does it, and keys.js already answers the clip window.
      if (dialogOpen()) return false;
      return escape();
    }

    if (e.key !== "?") return false;
    if (typing(e)) return false;                       // a question mark in a field is a question mark
    if (dialogOpen()) return false;
    /* Shift is already part of "?" on every keyboard that has one, so it is not
       tested here. The guided tour reads keys in the capture phase and stops them,
       and it is gone by the time this runs. Nothing else claims this key. */
    if (open) { hide(true); return true; }
    show();
    return true;
  }

  /* The panel's own close button. A click listener here, not inside the markup:
     a handler written into the markup string is never wired. */
  document.addEventListener("click", (e) => {
    const btn = e.target && e.target.closest ? e.target.closest("[data-pckb]") : null;
    if (!btn) return;
    e.preventDefault();
    hide(true);
  });

  document.addEventListener("focusin", onFocusIn);

  P.add("polish-keyboard", {
    keys,
    // Settings > Tools gets one row, so the list is findable without knowing the key.
    tools() {
      return '<div class="pckb-tools"><h2>Keyboard</h2>' +
        '<p class="help">Every shortcut Clipstorm answers, in one list. Press ? anywhere, or use this button.</p>' +
        '<button class="btn" data-act="pckbopen">Show all keys</button></div>';
    },
    act: {
      pckbopen() { show(); },
    },
  });
})();
