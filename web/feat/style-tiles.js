/* This file used to draw a second grid of caption looks on Settings > Brand.
 *
 * The caption look is now chosen in one place only: look-picker.js draws a single picker, with real frames, plain
 * headings and a search box, for every caption-look list in the page, Settings > Brand included. Drawing a second
 * grid here would show two pickers for the one setting, so this plug-in now draws nothing. It stays registered so the
 * feature list, and anything that names it, keeps working. The choice is still the Brand select in the
 * page; nothing here reads or writes it. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;
  P.add("style-tiles", {});
})();
