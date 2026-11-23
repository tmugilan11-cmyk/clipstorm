/* One shared look for the whole app: calmer type, one button system, one form-field system, one card.
 *
 * The page grew rule by rule, so buttons were 32, 38 or 44 tall depending on who wrote them, field borders were so
 * faint on the black page that a box looked like empty space, the small print was 12px, and a few hover colours
 * were still the light-page values (#D4CAC3 and #EAE7F7 glare on black). This sheet puts all of that on one scale
 * and changes nothing else: no new class, no markup, no motion. It styles the classes index.html already has.
 *
 * Scope: every selector is written for the main area (#main), dialogs and the sidebar (.side) only, with a
 * `html body` prefix so it wins over the older rules without !important. Nothing leaks to the login page or the tour.
 *
 * Colours. Only the page's own variables are used, plus three new ones, each measured (WCAG 2.2, (L1+.05)/(L2+.05)):
 *   --sk-edge    #666666  the border of a field or switch. On --field #141414 3.21:1, on --bg #0A0A0A 3.45:1.
 *                         WCAG 1.4.11 asks 3:1 for the outline of a control; the old --line-2 #2A2A2A was 1.3:1.
 *   --sk-edge-hi #8A8A8A  the same border on hover. 5.34:1 on --field, 5.73:1 on --bg.
 *   --sk-gap     20px     the one distance between two sections or cards (not a colour).
 * Text pairs used, all passing 4.5:1:
 *   --brand-ink #100929 on --brand #AF9BFF          8.22   (primary button; 9.12 on its hover #B8A7FF)
 *   --bad #F87171 on --bad-soft #2B1416             6.25   (danger button)
 *   --dim #A3A3A3 on --field #141414                7.30   (labels, placeholder-grade help)
 *   --faint #A0948C on --field #141414              6.24, on --line #1E1E1E 5.64   (hints)
 *   --text #F5F5F5 on --line #1E1E1E                15.29  (disabled button label is exempt but readable)
 *   --brand #AF9BFF on --brand-soft #20183F         7.12   (warn pill);  --good on --good-soft 8.01;  white on #C81E28 5.72
 * Switch knob: --dim on the off track, --brand-ink on the orange on-track (8.22), because white on orange is 2.34.
 *
 * Type scale (px): title 24, section 18, card 16, body 15, help 14, hint and label 13. Line height 1.55 for reading,
 * 1.25 for headings. Help text is held to 62 characters a line. The heights are 30 (sm), 38, 44 (lg).
 */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.css !== "function" || typeof P.add !== "function") return;

  // One selector, written once, wanted in three places.
  const SCOPES = ["html body #main", "html body dialog", "html body .side"];
  const sc = (...sels) => sels.flatMap(s => SCOPES.map(p => `${p} ${s}`)).join(",\n");
  const main = (...sels) => sels.map(s => `html body #main ${s}`).join(",\n");
  const dlg = (...sels) => sels.map(s => `html body dialog ${s}`).join(",\n");
  const mainAndDlg = (...sels) => sels.flatMap(s => ["html body #main", "html body dialog"].map(p => `${p} ${s}`)).join(",\n");

  const FIELD = "input:not([type=checkbox],[type=radio],[type=file],[type=range],[type=color],[type=hidden])";

  P.css("skin", `
    #main, dialog, .side { --sk-edge:#666666; --sk-edge-hi:#8A8A8A; --sk-gap:20px; }

    /* ---------------------------------------------------------------- type */
    html body #main, html body dialog { font-size:15px; line-height:1.55; }
    ${main("h1")} { font-size:24px; line-height:1.25; font-weight:600; letter-spacing:-.01em; text-wrap:balance; }
    ${mainAndDlg(".set-sec h2", ".dlg h2", ".hero h2")} { font-size:18px; line-height:1.3; font-weight:600; margin-bottom:6px; text-wrap:balance; }
    ${mainAndDlg(".card > h2", ".card-head h2", ".card > h3", ".editor h3")} { font-size:16px; line-height:1.3; font-weight:600; color:var(--text); }
    ${mainAndDlg(".editor h3", ".ed-side h3")} { font-size:13px; font-weight:600; letter-spacing:.02em; color:var(--dim); margin-top:8px; }
    ${mainAndDlg(".help", ".sub")} { font-size:14px; line-height:1.55; color:var(--dim); max-inline-size:62ch; text-wrap:pretty; }
    ${mainAndDlg(".hint", "label.f small", "label.f .hint")} { font-size:13px; line-height:1.5; color:var(--faint); max-inline-size:62ch; font-weight:400; margin-right:0; text-wrap:pretty; }
    ${mainAndDlg("label.f > .hint", "label.f > small.sub")} { display:block; }
    ${mainAndDlg("p")} { line-height:1.55; }

    /* ---------------------------------------------------------------- buttons
       primary = orange, secondary = outlined (.btn), quiet = .ghost, danger = .danger. Heights 30 / 38 / 44. */
    ${sc(".btn")} {
      height:38px; padding:0 16px; gap:8px; font-size:14px; font-weight:600; line-height:1; border-radius:var(--r);
      background:transparent; border:1px solid var(--sk-edge); color:var(--text);
    }
    ${sc(".btn:hover")} { background:var(--muted); border-color:var(--sk-edge-hi); }
    ${sc(".btn:active")} { background:var(--line); }
    ${sc(".btn.primary")} { background:var(--brand); border-color:var(--brand); color:var(--brand-ink); }
    ${sc(".btn.primary:hover")} { background:#B8A7FF; border-color:#B8A7FF; }
    ${sc(".btn.primary:active")} { background:var(--brand-press); border-color:var(--brand-press); }
    ${sc(".btn.ghost")} { background:transparent; border-color:transparent; color:var(--dim); }
    ${sc(".btn.ghost:hover")} { background:var(--muted); border-color:transparent; color:var(--text); }
    ${sc(".btn.danger")} { background:var(--bad-soft); border-color:transparent; color:var(--bad); }
    ${sc(".btn.danger:hover")} { background:#3A1A1E; border-color:transparent; color:var(--bad); }
    ${sc(".btn.dark")} { background:var(--brand-ink); border:1px solid var(--brand-ink); color:var(--text); }
    ${sc(".btn.dark:hover")} { background:#3A2C25; border-color:#3A2C25; }
    ${sc(".btn.sm")} { height:30px; padding:0 12px; font-size:13px; gap:6px; }
    ${sc(".btn.lg")} { height:44px; padding:0 22px; font-size:15px; }
    ${sc(".btn.icon")} { width:38px; padding:0; }
    ${sc(".btn.icon.sm", ".btn.sm.icon")} { width:30px; }
    ${sc(".btn:disabled", ".btn[disabled]", ".btn.primary:disabled")} {
      opacity:1; cursor:not-allowed; pointer-events:none; background:var(--line); border-color:var(--line); color:var(--faint);
    }
    ${sc(".btn:focus-visible", ".icon-btn:focus-visible", "label.ck:focus-within", "label.sw input:focus-visible")} {
      outline:2px solid var(--brand-deep); outline-offset:2px;
    }

    /* ---------------------------------------------------------------- form fields
       Label above, hint below, one height, one radius, a border that can be seen. */
    ${sc("label.f")} { display:flex; flex-direction:column; gap:8px; font-size:13px; line-height:1.3; font-weight:600; color:var(--dim); }
    ${sc(FIELD, "select")} {
      height:40px; padding:0 12px; font-size:15px; line-height:1.3; color:var(--text);
      background:var(--field); border:1px solid var(--sk-edge); border-radius:var(--r-sm);
    }
    ${sc("select")} { padding-right:34px; text-overflow:ellipsis; }
    ${sc("textarea")} {
      min-height:88px; padding:10px 12px; font-size:15px; line-height:1.5; color:var(--text);
      background:var(--field); border:1px solid var(--sk-edge); border-radius:var(--r-sm);
    }
    ${sc(FIELD + ":hover", "select:hover", "textarea:hover")} { border-color:var(--sk-edge-hi); }
    ${sc(FIELD + ":focus", "select:focus", "textarea:focus", FIELD + ":focus-visible", "select:focus-visible", "textarea:focus-visible")} {
      background:var(--field); border-color:var(--brand); outline:2px solid var(--brand); outline-offset:0;
    }
    ${sc(FIELD + ":disabled", "select:disabled", "textarea:disabled")} { opacity:1; color:var(--faint); background:var(--bg); border-color:var(--line-2); cursor:not-allowed; }
    ${sc("input::placeholder", "textarea::placeholder")} { color:var(--faint); opacity:1; }
    /* The big URL box and the stepper inputs are drawn by their own parents; do not box them twice. */
    ${main(".composer-input input", ".composer-input input:focus", ".nstep input", ".nstep input:focus", ".range input", ".range input:focus")} {
      height:auto; border:0; outline:0; background:transparent; border-radius:0;
    }
    ${main(".composer-input input", ".composer-input input:focus")} { height:60px; }

    /* Switches: 40 x 24, a visible edge when off, a dark knob on the orange when on. */
    ${sc("label.sw")} { display:flex; align-items:center; gap:12px; min-height:40px; font-size:15px; font-weight:600; color:var(--text); }
    ${sc("label.sw input")} { width:40px; height:24px; background:var(--line-2); border:1px solid var(--sk-edge); }
    ${sc("label.sw input::after")} { top:3px; left:3px; width:16px; height:16px; background:var(--dim); }
    ${sc("label.sw input:checked")} { background:var(--brand); border-color:var(--brand); }
    ${sc("label.sw input:checked::after")} { background:var(--brand-ink); transform:translateX(16px); }
    ${sc("label.sw small")} { font-size:13px; color:var(--faint); }
    ${sc("label.ck")} { min-height:38px; height:auto; padding:0 14px; border-color:var(--sk-edge); }
    ${sc("label.ck:hover")} { border-color:var(--sk-edge-hi); }

    /* Range sliders: the same orange track, a thumb with a ring when focused. */
    ${sc("input[type=range]")} { height:6px; margin:12px 0 10px; }
    ${sc("input[type=range]:focus-visible")} { outline:2px solid var(--brand-deep); outline-offset:6px; }

    ${main(".fields")} { gap:16px 20px; }
    ${dlg(".two")} , ${main(".two")} { gap:12px 16px; }

    /* ---------------------------------------------------------------- cards, sections, tables */
    ${main(".card")} { padding:20px; border:1px solid var(--line); border-radius:var(--r); background:var(--bg); margin-bottom:var(--sk-gap); }
    ${main(".card > h2 + .help")} { margin-bottom:16px; }
    ${main(".card-head")} { margin-bottom:16px; gap:12px 16px; }
    ${main(".set-sec")} { padding:0 0 24px; margin-bottom:24px; border-bottom:1px solid var(--line); }
    ${main(".set-sec:last-child")} { border-bottom:0; margin-bottom:0; }
    ${main(".set-sec .help")} { margin-bottom:16px; }
    ${main(".content")} { padding:28px 32px 72px; }
    ${main("th")} { font-size:13px; font-weight:600; color:var(--faint); padding:0 12px 10px; }
    ${main("td")} { padding:12px; font-size:14px; line-height:1.5; }
    ${main("tr:hover > td")} { background:var(--muted); }
    ${main(".tabbtn")} { font-size:14px; }

    /* ---------------------------------------------------------------- empty states and pills */
    ${main(".empty")} { padding:40px 20px; gap:6px; border:1px dashed var(--sk-edge); border-radius:var(--r); font-size:14px; line-height:1.55; }
    ${main(".empty b")} { font-size:16px; font-weight:600; color:var(--text); }
    ${mainAndDlg(".pill")} { height:24px; padding:0 10px; font-size:12px; font-weight:600; line-height:1; border-radius:999px; }
    ${mainAndDlg(".pill.ok")} { color:var(--good); background:var(--good-soft); }
    ${mainAndDlg(".pill.warn")} { color:var(--brand); background:var(--brand-soft); }
    ${mainAndDlg(".pill.bad")} { color:var(--bad); background:var(--bad-soft); }
    ${mainAndDlg(".pill.live")} { color:#fff; background:#C81E28; }

    /* ---------------------------------------------------------------- dialogs */
    ${dlg(".dlg")} { padding:24px; gap:16px; }
    /* A footer of buttons stays in view when a long dialog scrolls. The negative margins cancel the dialog's own
       padding so the bar reaches the edges and the page behind it does not show through. */
    ${dlg(".dlg-foot")} {
      position:sticky; bottom:0; z-index:2; margin:8px -24px -24px; padding:14px 24px; gap:10px;
      background:var(--bg); border-top:1px solid var(--line);
    }
    ${dlg(".ed-panes")} { padding:0 20px 20px; gap:16px; }
    ${dlg(".ed-pane")} { gap:16px; }
    ${dlg(".editor .panel .job-head")} { padding:20px 20px 12px; }
    ${dlg(".ed-foot")} { padding:14px 20px; gap:10px; border-top:1px solid var(--line); background:var(--bg); }

    /* ---------------------------------------------------------------- phones */
    @media (max-width:700px) {
      ${main(".content")} { padding:20px 16px 72px; }
      ${main(".fields", ".two", ".split", ".home-grid")} { grid-template-columns:1fr; }
      ${main(".card")} { padding:16px; }
      ${sc(".btn", ".btn.sm", ".btn.lg", ".icon-btn")} { min-height:40px; }
      ${sc(".btn.icon", ".btn.icon.sm", ".btn.sm.icon")} { min-width:40px; }
      ${sc(FIELD, "select")} { height:44px; font-size:16px; }
      ${sc("textarea")} { font-size:16px; }
      ${sc("label.ck", "label.sw")} { min-height:44px; }
      ${main(".tabbtn")} { height:44px; }
      ${dlg(".dlg")} { padding:20px 16px; }
      ${dlg(".dlg-foot")} { margin:8px -16px -20px; padding:12px 16px; flex-wrap:wrap; }
      ${dlg(".dlg-foot .btn")} { flex:1 1 auto; }
    }
    @media (prefers-reduced-motion: reduce) {
      ${sc(".btn", "label.sw input", "label.sw input::after")} { transition:none; }
    }
  `);

  /* No click, no key, no markup: the stylesheet above is the whole feature. It is registered so plugins.js finds one
     plug-in in this file, named after the file, as the contract asks. */
  P.add("skin", {});
})();
