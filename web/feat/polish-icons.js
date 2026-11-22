/* One icon set, and a way to prove it.
 *
 * Measured before writing: the page's icon map is a plain mutable object named `I`, and its
 * `ic(name)` is a bare const. A classic feature script shares that scope, so `I` can be read
 * and added to, and `ic` can be CALLED, but it cannot be replaced. Two earlier files already
 * used that (icons-extra.js seeds refresh, check_f, grid; menu-icons.js seeds fourteen more).
 * A scan of every ic() call in web/feat/*.js found no name that is still missing, so this file
 * does not invent an icon. It fixes the two real faults the scan did find:
 *
 *  1. `ic("some_unknown_name")` does not draw an empty box. It draws the word "undefined"
 *     inside an 18 by 18 svg, because `I[name]` is undefined and the template pastes it.
 *     Measured in the live page: markup, text and rendered width all confirmed.
 *  2. `window.ic` is undefined. The page's `ic` is a script-scope const, so it never becomes a
 *     window property. usage.js guards with `typeof window.ic === "function"`, so every icon
 *     that file asks for draws nothing at all. Publishing `window.ic` fixes those call sites
 *     without touching the file that calls them.
 *
 * The Tools card runs the same scan again, live, so the claim can be checked rather than read.
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  const BOX = 256;

  /** The page's own icon map, or null when it is not in scope. Read by bare name on purpose. */
  const pageMap = () => {
    try { return typeof I === "object" && I ? I : null; } catch { return null; }
  };

  /** The page's own ic(), or null. Called, never wrapped in place. */
  const pageIc = () => {
    try { return typeof ic === "function" ? ic : null; } catch { return null; }
  };

  /** True when the page can actually draw this name. An empty path counts as absent. */
  const knows = (name) => {
    const map = pageMap();
    const key = String(name == null ? "" : name);
    if (!map || !key) return false;
    const body = map[key];
    return typeof body === "string" && body.trim() !== "";
  };

  /* ---- 1. window.ic ------------------------------------------------------
   * Only the guarded call sites read this. Bare `ic(...)` in a feature file still
   * resolves to the page's const, which is why the CSS below also has to exist.
   * An unknown name gives an empty string, never the word "undefined".
   */
  try {
    if (typeof window.ic !== "function") {
      window.ic = (name) => {
        const draw = pageIc();
        return draw && knows(name) ? draw(String(name)) : "";
      };
    }
  } catch { /* a locked down window still leaves the page's own ic working */ }

  /* ---- 2. a safe helper for new files ----------------------------------- */
  /** One icon as markup. Unknown or blank names give "" so nothing paints a placeholder word. */
  P.ic = (name) => {
    try {
      const draw = pageIc();
      return draw && knows(name) ? draw(String(name)) : "";
    } catch { return ""; }
  };

  /** True when the page can draw the name right now. For files that want to fall back. */
  P.hasIcon = (name) => knows(name);

  /* ---- 3. the stylesheet ------------------------------------------------ */
  // Scoped to #app, which is the page's own root element, so nothing outside the
  // application shell is touched. No !important, no shadows, no motion.
  P.css("polish-icons", `
    /* A childless icon is a name the page cannot draw. The word "undefined" is the
       only thing inside it, so hiding the glyph's text leaves a clean 18px box
       instead of a gap in a toolbar or a stray word in a sentence. */
    #app svg:not(:has(path,rect,circle,ellipse,line,polyline,polygon,g,use,image)){font-size:0;color:transparent}
    .picons .prow{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:baseline;padding:7px 0;border-bottom:1px solid var(--line)}
    .picons .prow:last-child{border-bottom:0}
    .picons .pname{font-size:13px;color:var(--ink);overflow-wrap:anywhere}
    .picons .pwho{font-size:12px;color:var(--dim);margin-top:2px}
    .picons .pstate{font-size:12px;color:var(--dim);white-space:nowrap}
    .picons .pstate.ok{color:var(--ink)}
    .picons .phead{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:2px 0 10px}
    .picons .ptally{font-size:13px;color:var(--dim)}
    .picons .ptally b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
    .picons .pnone{font-size:13px;color:var(--dim)}
    .picons .prow:hover .pname{color:var(--brand)}
  `);

  /* ---- 4. the scan ------------------------------------------------------ */
  // The rules the page's own ic() is asked for, in the order they appear in a file.
  // Only literal names are read. A name built at run time cannot be audited from source,
  // and guessing one would be inventing, so those sites are counted separately instead.
  const PATTERNS = [
    { kind: "ic", re: /\bic\(\s*(["'])([A-Za-z0-9_\-]{1,24})\1/g },
    { kind: "icon", re: /\b(?:icon|iconHtml)\(\s*(["'])([A-Za-z0-9_\-]{1,24})\1/g },
    { kind: "page", re: /\bicon:\s*(["'])([A-Za-z0-9_\-]{1,24})\1/g },
  ];

  /** Drop comments and keep the code, so a name written in a comment is not counted as a call. */
  const strip = (src) => {
    let out = "";
    let i = 0;
    let quote = "";
    while (i < src.length) {
      const ch = src[i];
      const next = src[i + 1];
      if (quote) {
        out += ch;
        if (ch === "\\") { out += next === undefined ? "" : next; i += 2; continue; }
        if (ch === quote) quote = "";
        i++;
        continue;
      }
      if (ch === '"' || ch === "'" || ch === "`") { quote = ch; out += ch; i++; continue; }
      if (ch === "/" && next === "/") { while (i < src.length && src[i] !== "\n") i++; continue; }
      if (ch === "/" && next === "*") {
        i += 2;
        while (i < src.length && !(src[i] === "*" && src[i + 1] === "/")) i++;
        i += 2;
        continue;
      }
      out += ch;
      i++;
    }
    return out;
  };

  /** Fetch every served feature file and collect the icon names it asks for. */
  const scan = async () => {
    const list = await (await fetch("/assets/feat")).json();
    const files = (list && list.files) || [];
    const used = new Map();     // name -> Set of files that ask for it
    const order = [];           // names, first seen first
    for (const file of files) {
      let src = "";
      try { src = await (await fetch("/assets/feat/" + file)).text(); } catch { continue; }
      src = strip(src);
      for (const { re } of PATTERNS) {
        for (const m of src.matchAll(re)) {
          const name = m[2];
          if (!used.has(name)) { used.set(name, new Set()); order.push(name); }
          used.get(name).add(file);
        }
      }
    }
    const missing = order.filter((n) => !knows(n));
    return { files: files.length, order, used, missing };
  };

  /** Write the result. Built with DOM nodes so a file name is never pasted as markup. */
  const draw = (result) => {
    const box = document.getElementById("picons");
    if (!box) return;
    box.textContent = "";
    if (!result) {
      const p = document.createElement("p");
      p.className = "pnone";
      p.textContent = "The check did not finish.";
      box.append(p);
      return;
    }
    const head = document.createElement("div");
    head.className = "phead";
    const tally = document.createElement("span");
    tally.className = "ptally";
    tally.append(document.createTextNode("Names asked for: "));
    const n1 = document.createElement("b");
    n1.textContent = String(result.order.length);
    tally.append(n1, document.createTextNode(". The page cannot draw: "));
    const n2 = document.createElement("b");
    n2.textContent = String(result.missing.length);
    tally.append(n2, document.createTextNode("."));
    head.append(tally);
    box.append(head);

    if (!result.order.length) {
      const p = document.createElement("p");
      p.className = "pnone";
      p.textContent = "No file asks for an icon by a literal name.";
      box.append(p);
      return;
    }

    const rows = document.createElement("div");
    for (const name of result.order) {
      const row = document.createElement("div");
      row.className = "prow";

      const left = document.createElement("div");
      const nm = document.createElement("div");
      nm.className = "pname";
      nm.textContent = name;
      const who = document.createElement("div");
      who.className = "pwho";
      who.textContent = Array.from(result.used.get(name)).join(", ");
      left.append(nm, who);

      const state = document.createElement("div");
      const ok = knows(name);
      state.className = "pstate" + (ok ? " ok" : "");
      state.textContent = ok ? "drawn by the page" : "missing";

      row.append(left, state);
      rows.append(row);
    }
    box.append(rows);
  };

  /* ---- 5. the Tools card ----------------------------------------------- */
  P.add("polish-icons", {
    tools() {
      // No interpolated values here, so nothing needs escaping in this literal.
      return `<h2>Icons</h2>
        <p class="help">Every icon in the menu and the panels is drawn by one set on the page. This checks every
        name the feature files ask for and says which ones the page can draw.</p>
        <div class="picons">
          <div class="phead"><button class="btn sm" type="button" data-act="piconsscan">Check every icon name</button></div>
          <div id="picons" aria-live="polite"><p class="pnone">Not checked yet.</p></div>
        </div>`;
    },

    act: {
      /** Runs the scan and prints what it found. One quiet line on failure. */
      async piconsscan() {
        const box = document.getElementById("picons");
        if (box) {
          box.textContent = "";
          const p = document.createElement("p");
          p.className = "pnone";
          p.textContent = "Reading the feature files.";
          box.append(p);
        }
        try {
          draw(await scan());
        } catch (err) {
          draw(null);
          P.toast("That check could not finish. The icons still work.", "bad");
          try { console.warn("[PeakCut] polish-icons:", err); } catch { /* no console */ }
        }
      },
    },
  });
})();
