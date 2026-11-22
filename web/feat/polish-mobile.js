/* The phone layout, in one scoped block.
 *
 * Below 640 px the page has three jobs: stop the page scrolling sideways, turn
 * every two-column block into one column, and make everything you can tap at
 * least 44 by 44. A wide table keeps its width and scrolls inside its own box,
 * so no column is dropped or hidden. Everything here is inside one media query,
 * and it only names things the page already draws. */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});

  P.css("polish-mobile", `
  @media (max-width:640px){
    /* ---- nowhere to scroll sideways ---- */
    #main,#view,.content{min-width:0;max-width:100%}
    .card,.scroll,.home-grid,.split,.grid,.tiles,.kpis,.fields,.row,.two{min-width:0}
    .card{max-width:100%}
    .card-head{flex-wrap:wrap;gap:10px}
    .job-head{flex-wrap:wrap;gap:8px}
    .row{flex-wrap:wrap}
    img,video,svg,.chart{max-width:100%}
    .log div{flex-wrap:wrap;gap:6px 12px}
    .log time{width:auto}
    td,th{overflow-wrap:anywhere}

    /* ---- one column where the page had two ---- */
    .two{grid-template-columns:1fr}
    .split,.home-grid{grid-template-columns:1fr}
    .kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 14px}
    .kpi b{font-size:18px}

    /* ---- the shell ---- */
    .side{padding:12px 10px calc(12px + env(safe-area-inset-bottom))}
    .topbar{padding:8px 12px;min-height:56px;gap:8px}
    .topbar h1{font-size:16px;line-height:1.3}
    .content{padding:16px 12px calc(56px + env(safe-area-inset-bottom))}
    .card{padding:14px}
    /* The tab strip is allowed to scroll inside itself rather than push the bar wide. */
    .utabs{overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
    .utabs::-webkit-scrollbar{display:none}
    .utabs .tabbtn{flex:0 0 auto;padding:0 12px}

    /* ---- a wide table scrolls in its own box, never in the page ---- */
    .scroll{max-width:100%;overflow-x:auto;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch;scrollbar-width:thin}
    .scroll table{max-width:none}

    /* ---- every tap target is 44 by 44 ---- */
    .btn,.btn.sm{min-height:44px}
    /* A button that holds only an icon still needs a full finger. */
    .btn.sm{min-width:44px}
    .btn.primary,.btn.dark{min-height:44px}
    .btn.icon{width:44px;min-width:44px;height:44px;padding:0}
    .icon-btn{width:44px;height:44px}
    .nav-item{min-height:44px}
    .chip{min-height:44px}
    .tabbtn{min-height:46px}
    label.ck{min-height:44px}
    .step{padding:14px 12px}
    button.pill,a.pill{min-height:44px;padding:0 14px}
    :where(input:not([type=checkbox],[type=radio],[type=file],[type=range]),select){min-height:44px}
    :where(textarea){min-height:88px}
    input[type=checkbox],input[type=radio]{width:22px;height:22px;min-width:22px}
    /* A bare checkbox is 22 px on its own. The label around it becomes the target. */
    label:has(>input[type=checkbox]),label:has(>input[type=radio]){display:inline-flex;align-items:center;gap:8px;min-height:44px}
    /* The small stepper either side of a number field. */
    .nstep .ctl button{width:44px;height:44px}
    .nstep .ctl button svg{width:16px;height:16px}
    /* The round question mark beside a KPI title. It stays 16 px of ink and gets a 44 px box. */
    .akhelp{width:44px;height:44px;margin:-11px -14px -11px 0}
    .akhelp svg{width:16px;height:16px}
    .akhelp-w{min-height:44px}
    label.sw{min-height:44px}
    /* The switch keeps its shape and grows inside a 44 high row. */
    label.sw input{width:44px;height:26px;align-self:center}
    label.sw input::after{width:20px;height:20px;top:3px;left:3px}
    label.sw input:checked::after{transform:translateX(18px)}

    /* ---- the clip dialog: one scroller, and it fits the phone ---- */
    dialog{width:calc(100vw - 20px);max-width:calc(100vw - 20px);max-height:calc(100dvh - 20px)}
    dialog .dlg{padding:16px;gap:12px}
    #clipdlg .editor{display:flex;flex-direction:column;max-height:calc(100dvh - 20px);overflow-y:auto;overscroll-behavior:contain}
    #clipdlg .editor .stage{min-height:0;flex:none}
    #clipdlg .editor video{max-height:40vh;width:100%}
    #clipdlg .editor .panel{overflow:visible;padding:14px;gap:12px}
    #clipdlg .editor .panel h3{margin-top:4px}
    #clipdlg .dlg-foot{flex-wrap:wrap}
    #clipdlg .dlg-foot .btn{flex:1 1 auto}
    .pop{max-width:calc(100vw - 24px)}
    #toasts{left:10px;right:10px;bottom:10px}
    .toast{max-width:none}
  }
  `);

  // A table or a tab strip wider than its box is a scroll region. Keyboard users can only
  // reach it if it is focusable, so it becomes focusable only while it really scrolls.
  // Anything the page already declared (its own role, its own label) is left alone, and
  // only what was added here is ever taken away.
  const TABLE_LABEL = "Table. Scroll sideways to see every column.";
  const TABS_LABEL = "Scrolls sideways to show more.";

  function mark(root) {
    if (!root || !root.querySelectorAll) return;
    const narrow = window.matchMedia("(max-width:640px)").matches;
    for (const box of root.querySelectorAll(".scroll, .tabs, .utabs, .set-nav")) {
      const wide = narrow && box.scrollWidth > box.clientWidth + 1;
      if (wide) {
        if (box.getAttribute("tabindex") !== "0") {
          box.setAttribute("tabindex", "0");
          box.dataset.pmTab = "1";
        }
        if (!box.hasAttribute("role")) {
          box.setAttribute("role", "region");
          box.dataset.pmRole = "1";
        }
        if (!box.hasAttribute("aria-label")) {
          box.setAttribute("aria-label", box.classList.contains("scroll") ? TABLE_LABEL : TABS_LABEL);
          box.dataset.pmLabel = "1";
        }
      } else {
        if (box.dataset.pmTab) { box.removeAttribute("tabindex"); delete box.dataset.pmTab; }
        if (box.dataset.pmRole) { box.removeAttribute("role"); delete box.dataset.pmRole; }
        if (box.dataset.pmLabel) { box.removeAttribute("aria-label"); delete box.dataset.pmLabel; }
      }
    }
  }

  // A rotation or a window resize changes which boxes are wide, so re-run on both.
  let pending = 0;
  function soon() {
    if (pending) return;
    pending = window.setTimeout(() => { pending = 0; try { mark(document); } catch {} }, 180);
  }
  window.addEventListener("resize", soon, { passive: true });
  window.addEventListener("orientationchange", soon, { passive: true });

  P.add("polish-mobile", {
    after: {
      drawJobs: mark,
      drawOverview: mark,
      drawSettings: mark,
      drawClipDlg: mark,
    },
  });
})();
