/* A feature file. Loaded by /assets/feat.js as: /assets/feat/<name>.js  ->  name must match [a-z0-9-]+. */
window.PeakCut.add("example", {
  tools() { return `<h2>Example</h2><p class="help">A card in Settings > Tools.</p>`; },
  act: { examplebtn() { window.PeakCut.toast("It works.", "ok"); } },
});
