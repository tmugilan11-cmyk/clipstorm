/* Icons for the new menu pages, added without touching the frozen page.
 *
 * The page's icon map and its ic() are bare consts inside the page's own script, so they
 * cannot be wrapped or replaced from here. They can be added to, though: a const object is
 * still mutable, and plugins.js already reads that map by bare name when it draws the menu.
 * So PeakCut.icon(name, d) records the path here and also puts it in the page's live map, on
 * the same 256 grid and at the same weight as the icons already there. The menu rows that
 * PeakCut.navHtml draws then show it, with no change to the page at all.
 *
 * A page that needs a new icon calls PeakCut.icon(name, d) once, at load, before it
 * registers with PeakCut.page. Anything holding a name instead of markup calls
 * PeakCut.iconHtml(name), which returns the same <svg> shape ic() returns.
 *
 * Holes are made the way the page's own icons make them: one path, an inner subpath wound
 * the other way, and the default nonzero fill. Nothing here sets a fill-rule, so these
 * behave exactly like the icons beside them. A subpath drawn right-then-down is a hole
 * inside a body; drawn down-then-right it is solid.
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  const BOX = 256;
  // Path data only: a moveto, then letters, digits, signs, dots, commas, spaces. The page
  // pastes icon markup in unescaped, so nothing that is not a path may get through here.
  const OK = /^[Mm][0-9A-Za-z.,+\- ]*$/;

  P._icons = P._icons || {};

  /** The page's own icon map, or null when it is not in scope. Read by bare name on purpose. */
  const pageIcons = () => {
    try { return typeof I === "object" && I ? I : null; } catch { return null; }
  };

  /**
   * Remember one extra icon. `box` is the width of its viewBox and defaults to the page's
   * 256 grid. Returns true when the path was accepted.
   */
  P.icon = (name, d, box) => {
    name = String(name || "");
    d = String(d || "");
    if (!name || !OK.test(d)) return false;
    box = Number(box) > 0 ? Number(box) : BOX;
    P._icons[name] = { d, box };
    const page = pageIcons();
    // The menu draws from the page's map, so the name has to land there too. A name the
    // page already defines is left alone: restyling existing rows is not this file's job.
    // A page map that refuses the write means the icon did not reach the menu, so this
    // reports false instead of claiming an icon that the menu will never draw.
    if (page && box === BOX && !page[name]) {
      try { page[name] = `<path d="${d}"/>`; } catch (err) { return false; }
    }
    return true;
  };

  /** One icon as markup, in the shape ic() returns. An unknown name gives an empty svg. */
  P.iconHtml = (name) => {
    name = String(name || "");
    const mine = P._icons[name];
    if (mine) return `<svg viewBox="0 0 ${mine.box} ${mine.box}" aria-hidden="true"><path d="${mine.d}"/></svg>`;
    const page = pageIcons();
    const inner = page && page[name] ? String(page[name]) : "";
    return `<svg viewBox="0 0 ${BOX} ${BOX}" aria-hidden="true">${inner}</svg>`;
  };

  /** Every name that can be drawn right now: ours first, then the page's own. */
  P.iconNames = () => {
    const page = pageIcons();
    return Array.from(new Set([...Object.keys(P._icons), ...Object.keys(page || {})])).sort();
  };

  const SET = {
    // Three bars rising off one baseline. Numbers over time.
    analytics: "M40,152H76V216H40Z M110,112H146V216H110Z M180,72H216V216H180Z",
    // A curved bottom and one long arm. The first second of a video.
    hook: "M182,140A62,62 0 0 1 58,140L82,140A38,38 0 0 0 158,140ZM158,60H182V142H158Z",
    // Three steps, joined by two links that run into them.
    pipeline: "M56,104A24,24 0 1 1 56,152A24,24 0 1 1 56,104ZM128,104A24,24 0 1 1 128,152A24,24 0 1 1 128,104ZM200,104A24,24 0 1 1 200,152A24,24 0 1 1 200,104ZM78,120H110V136H78ZM150,120H182V136H150Z",
    // A spark, and a smaller one clear of it. The model, not the hardware.
    ai: "M96,72C104,124 120,140 172,148C120,156 104,172 96,224C88,172 72,156 20,148C72,140 88,124 96,72ZM206,32C209,47 211,50 236,62C211,74 209,77 206,92C203,77 201,74 176,62C201,50 203,47 206,32Z",
    // A page with a cut corner, three lines cut out of it.
    report: "M56,32H152L200,80V224H56ZM80,104V120H176V104ZM80,136V152H176V136ZM80,168V184H152V168Z",
    // One person in front, two behind, over one wide shoulder.
    audience: "M128,96A26,26 0 1 1 128,148A26,26 0 1 1 128,96ZM58,110A20,20 0 1 1 58,150A20,20 0 1 1 58,110ZM198,110A20,20 0 1 1 198,150A20,20 0 1 1 198,110ZM34,214V184A34,34 0 0 1 68,150H188A34,34 0 0 1 222,184V214Z",
    // Where people came from: one wide mouth, one narrow spout.
    traffic: "M40,48H216L152,120V216H104V120Z",
    // A lens, and a handle that starts at its edge.
    search: "M112,56A56,56 0 1 0 112,168A56,56 0 1 0 112,56ZM112,72A40,40 0 1 1 112,152A40,40 0 1 1 112,72ZM156,148L216,208L208,216L148,156Z",
    // Three lines of narrowing length.
    filter: "M40,64H216V88H40Z M68,112H188V136H68Z M96,160H160V184H96Z",
    // Two rings on top, four days cut out of the body.
    calendar: "M40,64H216V216H40ZM96,24H120V72H96ZM136,24H160V72H136ZM72,96V124H104V96ZM120,96V124H152V96ZM168,96V124H200V96ZM72,140V168H104V140ZM120,140V168H152V140ZM168,140V168H200V140Z",
    // A stopwatch: crown, two buttons, a ring, two hands inside it.
    "clock-extra": "M128,56A88,88 0 1 1 128,232A88,88 0 1 1 128,56ZM128,72A72,72 0 1 0 128,216A72,72 0 1 0 128,72ZM112,20H144V56H112ZM20,84H44V108H20ZM212,84H236V108H212ZM120,96H136V144H120ZM128,136H192V152H128Z",
    // A ring, with a question mark sitting inside it.
    help: "M128,24A104,104 0 1 1 128,232A104,104 0 1 1 128,24ZM128,40A88,88 0 1 0 128,216A88,88 0 1 0 128,40ZM102,110A26,26 0 0 1 154,110H146A18,18 0 0 0 110,110H102ZM146,110H154V150H146ZM150,163A13,13 0 1 1 150,189A13,13 0 1 1 150,163Z",
    // Five points.
    star: "M128,32L150,97L219,98L164,140L184,206L128,166L72,206L92,140L37,98L106,97Z",
    // Four points, the quiet one.
    sparkle: "M128,24C138,96 160,118 232,128C160,138 138,160 128,232C118,160 96,138 24,128C96,118 118,96 128,24Z",
  };
  for (const n in SET) P.icon(n, SET[n]);

  // The plug-in body is deliberately inert: no Tools card, no click handler, no keys.
  // Settings keeps only settings, and these names exist for menu rows to draw with.
  P.add("menu-icons", { icons: SET });
})();
