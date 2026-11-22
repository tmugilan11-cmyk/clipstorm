/* A wide screen is not a stretched phone.
 *
 * Above 1600 px the page had room it never used: the column inside the shell stopped at
 * 1280, the number rows stayed at their narrow fixed slots, and a chart was free to grow
 * to whatever the window allowed. Three fixes, all inside one media query, all naming
 * classes the page already draws.
 *
 * The shell is not touched. `.app`, `.side`, `#main` and the topbar keep their width, so
 * the sidebar stays put and the page keeps its scrollbar. Only the column inside the
 * shell is capped, and only above 1600 px, so nothing below that size moves at all.
 *
 * Nothing here animates: the query changes widths and text wrapping only, so there is no
 * motion for prefers-reduced-motion to turn off.
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  if (typeof P.css !== "function") return;

  P.css("polish-wide", `
  @media (min-width:1600px){
    /* ---- the column inside the shell ---- */
    /* 1480 is the 1280 the page already had, plus the room a 1920 screen leaves once the
       240 sidebar and the page padding are taken. It stops growing there, so at 2560 the
       column no longer trails off into two screens of empty margin. */
    #main>.content{max-width:1480px}

    /* ---- prose stops at a readable measure ---- */
    /* An em cap holds where a ch cap does not: this font measures one ch at 8.74 px, so
       76ch came out at 111 characters. 34em is about 70 characters at any text size, which
       is where the eye still finds the start of the next line. Only running text is capped.
       Numbers, tables, controls and the bordered .note and .empty boxes keep full width. */
    #view :is(p,.help,.sub,.an-hint,.hint){max-width:34em;text-wrap:pretty}
    #view :is(h1,h2,h3){max-width:26em;text-wrap:balance}

    /* ---- the number rows use the width they are given ---- */
    /* The four numbers sat beside the card title in one 275 px strip, 61 px each, so the
       labels wrapped. They get their own line under the title now, and the 140 px floor
       means a card never shrinks below its label. The row wraps instead of squeezing, so
       a wide window fits five numbers across where four used to be crushed together. */
    #view .card-head>.kpis{flex:1 1 100%;gap:20px 32px}
    #view .kpis>.kpi{flex:1 1 140px;min-width:0}

    /* The analytics row was six fixed columns. auto-fit with a 200 px floor takes as many
       as the width allows, so a seventh key number joins the row instead of starting a
       second one, and six cards share 1480 instead of 1280. */
    #view .akpi{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}

    /* ---- a chart keeps its shape ---- */
    /* A 30 day line drawn 1400 wide is flat: every rise is invisible. 920 is as wide as a
       run of days reads without the shape disappearing into the axis. */
    #view .chart,#view .ac-svg{max-width:920px}
  }
  `);

  /* A stylesheet needs no handlers. Registering the name keeps the loader's order list
     honest and gives the file the same shape as every other feature file. */
  P.add("polish-wide", {
    about: "Above 1600px: a capped reading measure, number rows that fill the width, charts that stop at 920.",
  });
})();
