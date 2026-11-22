/* Lifts the one quiet grey that failed on the page PeakCut has now, and leaves everything else alone.
 *
 * This sheet was written when the page was white. The page is black now (--bg #0A0A0A), and the value it chose for
 * a white page is the wrong direction on a black one: #75695F measures 3.72:1, which fails 4.5 for body text. Every
 * number below is the WCAG 2.2 contrast ratio (L1 + 0.05) / (L2 + 0.05), worked out from the hex values in the
 * frozen page's :root block. None of them are estimates.
 *
 * On the dark page the quiet levels run the other way: a quiet grey has to be LIGHTER than the body ink, not darker.
 *
 *   --text  #F5F5F5  on --bg #0A0A0A   18.16   the body ink
 *   --dim   #A3A3A3  on --bg #0A0A0A    7.85   the first quiet level, passes untouched
 *   --faint #7C7C7C  on --bg #0A0A0A    4.74   the second quiet level, passes 4.5 but barely
 *   --faint #A0948C  on --bg #0A0A0A    6.70   the old light-page value, a warm grey that now reads well
 *   --faint #75695F  on --bg #0A0A0A    3.72   what the previous version of this sheet forced: fails
 *   --faint #A0948C  on --muted #111111 6.39   on --brand-soft #2A1B10  5.63
 *
 * The unread count on the bell sits in `web/index.html` (.bell .dotn, white on the dark red #C81E28 at 5.72:1,
 * index.html:715), not overridden from here: a colour written in two places drifts.
 *
 * So the warm grey the palette was built around is put back, which is both the readable choice on black and the one
 * that keeps the page's warmth. The brand orange, the type scale, the spacing and the layout do not move.
 *
 * Scope: #main holds every view, and the top bar lives inside it. The two dialogs sit outside it, so they are named
 * too. The sidebar uses its own --frame-dim (#8A8A8A), which measures 6.08 on its black ground (.side uses
 * var(--frame)) and needs nothing.
 */
(() => {
  window.PeakCut.css("polish-contrast", `
    #main, dialog { --faint: #A0948C; }
  `);

  /* No click, no key, no markup: the stylesheet above is the whole feature. It is registered so plugins.js finds one
     plug-in in this file, as the contract asks. */
  window.PeakCut.add("polish-contrast", {
    /** Returns one measured pair, so the numbers can be checked from the console. */
    ratio(a, b) {
      const lum = (hex) => {
        const v = String(hex).replace("#", "");
        const parts = [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16) / 255);
        const lin = parts.map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
      };
      const x = lum(a), y = lum(b);
      const hi = Math.max(x, y), lo = Math.min(x, y);
      return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
    },
  });
})();
