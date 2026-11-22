/* One colour system, applied.
 *
 * The page already declares its palette once, in :root at the top of the shell:
 * --bg, --line, --line-2, --brand-soft, --brand-line, --bad-soft and friends.
 * The feature files were written at different times by different agents, so a
 * few of them spelled those same colours out as literals: #fff for a card
 * surface, #D4CAC3 for a hover border, #FFF7F0 for the soft brand tint.
 *
 * This file is a corrections sheet, nothing else. It re-declares only the
 * colour properties that were carrying a literal, and points them at the
 * variable that already meant the same thing. Layout, type, spacing and the
 * brand accent are untouched. Without a variable, nothing here.
 *
 * Why the selectors start with `body`: these rules compete with single-class
 * rules in 19 other files whose stylesheets are appended in whatever order the
 * loader finishes them. One extra element selector wins on specificity, so the
 * result does not depend on network order, and no override flag is needed.
 */
(() => {
  window.PeakCut.css("polish-colour", `
    /* ---- surfaces painted with a literal white ---- */
    /* #fff is exactly --bg, so this is a swap with no visible change. Every
       one of these was a card, popover, chip or field that sits on the page. */
    body .ac-chart,
    body .ac-tip,
    body .akhelp,
    body .akhelp-s,
    body .akpi,
    body .annow,
    body .an-ret .rpick select,
    body .an-ret .rwrap,
    body .an-ret .rtip,
    body .arv,
    body .ant-pick select,
    body .ant-tools input,
    body .atr-chip,
    body .cr-card,
    body .day-sun,
    body .day .day-who,
    body .pcf-pill,
    body .pcf-search input[type="search"]:focus,
    body .fmt-card,
    body .pclive-row,
    body .pclive-field select,
    body .pclive-field input,
    body .stilegrid .stile,
    body .usg-ledger,
    body .usg-plot{background:var(--bg)}

    /* ---- the run pill ---- */
    /* Its border was the exact brand line, and its fill was two shades off the
       soft brand tint. Base state only: the hover step stays its own lighter
       value so hovering still visibly changes the button. */
    body .pcrun.btn{border-color:var(--brand-line);background:var(--brand-soft)}

    /* Recording state: #FFF3F3 was the red tint by another name. The deeper
       hover step below it is left alone so the two states stay distinct. */
    body .pcrun.btn.is-rec{background:var(--bad-soft)}
  `);

  // No page, no tools card, no handlers: the stylesheet above is the whole
  // feature. It is registered so the loader has an owner for the name.
  window.PeakCut.add("polish-colour", {});
})();
