/* One spacing rhythm for the menu pages.
 *
 * Cards, sections, grids and form rows were each given their own margins and their own
 * padding, so two pages that read the same place their blocks 26, 24 or 18 pixels apart.
 * This file puts every vertical distance on one scale built from multiples of 4, and
 * changes nothing else.
 *
 * What it does not do, on purpose:
 *   - it never sets a width, a horizontal padding, a max-width or a grid template, so no
 *     element gets wider or narrower. Only block padding, block margin and row gaps move.
 *   - it never touches the sidebar or the top bar. Every selector starts at #view, which
 *     is the menu page container and nothing else.
 *   - it adds no motion, so there is nothing here that prefers-reduced-motion would have
 *     to switch off.
 *
 * Why margins collapse to one gap: each section gets a bottom margin of 20 and a top
 * margin of 0, so two sections in a row sit exactly 20 apart however many of them a page
 * has, instead of 26 on one page and 24 plus 18 on the next. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.css !== "function") return;

  P.css("polish-space", `
    /* The scale. Named so a later file can use the same numbers instead of typing 14. */
    #view{--ps-1:4px;--ps-2:8px;--ps-3:12px;--ps-4:16px;--ps-5:20px;--ps-6:24px;--ps-8:32px}

    /* One gap between any two sections: 20 below the last line, 0 above the next, so the
       pair always reads as 20 and never as the sum of two rules written weeks apart. */
    #view section{margin-block:0 var(--ps-5);padding-block:0}

    /* The rule under a section keeps its 16 of air, which is the same 16 a card uses. */
    #view .set-sec{padding-block-end:var(--ps-4)}

    /* A bordered section keeps the border and starts its content 16 below it. */
    #view .fmtp-sec{padding-block-start:var(--ps-4)}

    /* Cards. One card padding, top and bottom, on every page that has cards. */
    #view .card{padding-block:var(--ps-5);margin-block:0 var(--ps-4)}
    #view .card>h2+.help{margin-block-end:var(--ps-4)}

    /* A label and the field under it. 7 became 8, which is on the scale. */
    #view label.f{gap:var(--ps-2)}

    /* Form rows were 18 apart. 16 is the same distance a grid uses. */
    #view .fields{row-gap:var(--ps-4)}

    /* Grids already sat on 16. Restated so a later rule cannot drift off the scale. */
    #view .grid{gap:var(--ps-4)}
  `);

  /* A stylesheet needs no handlers. Registering the name keeps the loader's order list
     honest, and gives the file the same shape as every other feature file. */
  P.add("polish-space", {
    about: "One spacing rhythm: sections, cards, grids and form rows on a 4px scale.",
  });
})();
