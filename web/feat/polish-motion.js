/* Motion that helps and never hurts, for the UI the feature files draw.
 *
 * The frozen page already moves: 44 transitions and 25 animations, most of them colour
 * at 150 ms. The feature files that Waves 1 to 4 added grew their own motion in 23 of
 * 52 files, and it drifted: 140 ms here, 200 ms there, 180 ms on a panel in another.
 * Nothing anchors the feature UI, so two cards side by side answer a hover at two speeds.
 *
 * This file adds a short scoped stylesheet with two rules and one guard.
 *   1. 120 ms colour transition on buttons and links inside feature surfaces.
 *   2. 160 ms opacity reveal for a dialog that opens, which is a panel appearing in
 *      front of the person, not content shifting under their eyes.
 *   3. Every rule off under prefers-reduced-motion: reduce.
 *
 * It does not slide, bounce or loop. It does not animate a property that moves content
 * the person is reading. Everything is scoped to #view, #toolsec and dialog, which are
 * the three places a feature file can draw into, so the page's own chrome keeps its own
 * 150 ms timing and this file never restyles the document.
 *
 * The stylesheet goes in as soon as this file loads, the same way heard.js does it, not
 * from load(): load() only runs when Settings > Tools is opened, and a hover on any
 * other page must not wait for that.
 */
(() => {
  const CSS = `
    /* Feature surfaces only. #view is where a feature page draws. #toolsec is where
       PeakCut.toolsHtml puts every feature's Tools card. dialog is a feature dialog. */
    #view button,#view a,#view .pill,#view label.ck,
    #toolsec button,#toolsec a,#toolsec .pill,#toolsec label.ck,
    dialog button,dialog a,dialog .pill,dialog label.ck{
      transition-property:background-color,border-color,color;
      transition-duration:120ms;
      transition-timing-function:ease;
    }

    /* One reveal, opacity only. A dialog only gets it when it is open, so it plays once
       per open and never re-plays on a redraw. No transform: nothing shifts sideways. */
    dialog[open]{animation:pcPolishIn 160ms ease both}
    @keyframes pcPolishIn{from{opacity:0}to{opacity:1}}

    /* Off, not shortened. A shorter version still moves. */
    @media (prefers-reduced-motion:reduce){
      #view button,#view a,#view .pill,#view label.ck,
      #toolsec button,#toolsec a,#toolsec .pill,#toolsec label.ck,
      dialog button,dialog a,dialog .pill,dialog label.ck{
        transition-property:none;
        transition-duration:0s;
      }
      dialog[open]{animation:none}
    }
  `;

  try {
    window.PeakCut.css("polish-motion", CSS);
  } catch (err) {
    // One quiet line, never a throw into the page.
    try { console.warn("[PeakCut] polish-motion could not add its stylesheet:", err); } catch {}
  }

  // The plug-in itself carries no Tools card and no handlers: its whole job is the
  // stylesheet above, and it registers so the loader and the test can see it.
  window.PeakCut.add("polish-motion", {});
})();
