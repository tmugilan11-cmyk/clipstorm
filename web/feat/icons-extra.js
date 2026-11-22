/* The icon names the page asks for but never defined, drawn here instead.
 *
 * The page's icon map is a plain mutable object named `I` inside its own script, and its
 * `ic(name)` reads that object by bare name. A classic script shares the page's global
 * scope, so this file can read the same object and add keys to it. That is the whole
 * trick: nothing here wraps `ic`, patches the page, or watches the document. After this
 * file has run, `I["refresh"]` holds a path, so the page's own `ic("refresh")` draws it.
 *
 * The names are also published on `window.PeakCutIcons` so anything written later can
 * read them without knowing about the page. `PeakCutIcons` is a copy, not the source of
 * truth: if a name were added there and not mirrored into the page's map, the page's
 * `ic()` would still draw nothing, because it never looks at `PeakCutIcons`.
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  const BOX = 256;

  // Path data only. The page pastes icon markup in unescaped, so nothing that is not a
  // path may reach it. Same guard the other icon file uses.
  const OK = /^[Mm][0-9A-Za-z.,+\- ]*$/;

  /* Each entry says where the page asks for it, so the Tools card can be specific. */
  const EXTRA = {
    // The Zernio card's Refresh button. Without this the button has a 256-unit box and no
    // shape in it, so it reads as a button with a blank spot on the left.
    refresh: {
      d: "M128,32A96,96 0 0 1 128,224L128,200A72,72 0 0 0 128,56Z "
       + "M128,224A96,96 0 0 1 32,128L56,128A72,72 0 0 0 128,200Z "
       + "M128,8L128,56L76,32Z",
      used: "Refresh button on the Zernio card",
    },
    // The filled twin of "check", which the menu asks for when Review is the open page.
    // The menu falls back to the outline when this is absent, so Review alone never lit up.
    check_f: {
      d: "M128,24A104,104 0 1 1 128,232A104,104 0 1 1 128,24Z "
       + "M60,150L112,202L196,118L180,102L112,170L76,134Z",
      used: "Review row in the menu, when that page is open",
    },
    // The loader's stated default for a menu page that names no icon. It only draws when
    // the name is in the map, so without this an iconless page gets a blank square.
    grid: {
      d: "M48,48H120V120H48Z M136,48H208V120H136Z M48,136H120V208H48Z M136,136H208V208H136Z",
      used: "Any menu page that names no icon",
    },
    // The Pictures page names this icon. Without it the sidebar row has a 256-unit box and nothing drawn in it,
    // which reads as a broken menu rather than a missing picture.
    image: {
      d: "M40,56H216V200H40Z M64,80H96V112H64Z M40,200L104,136L144,176L176,144L216,184",
      used: "The Pictures page, and the Pictures tab in the clip editor",
    },
  };

  // The published copy. Merged, never replaced, so a second file can add to it.
  window.PeakCutIcons = Object.assign(window.PeakCutIcons || {}, Object.fromEntries(
    Object.entries(EXTRA).map(([n, v]) => [n, v.d])
  ));

  /** The page's own icon map, or null when it is not in scope. Read by bare name on purpose. */
  const pageMap = () => {
    try { return typeof I === "object" && I ? I : null; } catch { return null; }
  };

  /** What happened on the last pass: added, already there, or refused as not-a-path. */
  const report = { added: [], present: [], refused: [] };

  /**
   * Put every missing name into the page's map. Safe to run more than once: a name the
   * page already defines is left alone, because restyling a built-in icon is not this
   * file's job and another file may own it.
   */
  const seed = () => {
    report.added = []; report.present = []; report.refused = [];
    const map = pageMap();
    for (const name of Object.keys(EXTRA)) {
      const d = EXTRA[name].d;
      if (!OK.test(d)) { report.refused.push(name); continue; }
      if (!map) { report.refused.push(name); continue; }
      if (map[name]) { report.present.push(name); continue; }
      try { map[name] = `<path d="${d}"/>`; report.added.push(name); } catch { report.refused.push(name); }
    }
    return report;
  };

  seed();

  P.css("icons-extra", `
    .iconsx{display:grid;gap:8px;margin:10px 0 12px}
    .iconsx .ix{display:flex;align-items:center;gap:11px;padding:9px 11px;border:1px solid var(--line);border-radius:10px}
    .iconsx .ix svg{width:22px;height:22px;flex:none;fill:currentColor;color:var(--brand)}
    .iconsx .ix b{font-size:13px;font-weight:600;color:var(--ink)}
    .iconsx .ix span{font-size:12px;color:var(--dim);display:block;margin-top:2px}
    .iconsx .ix .st{margin-left:auto;font-size:11px;letter-spacing:.02em;padding:2px 7px;border-radius:99px;background:var(--line);color:var(--dim);flex:none}
    .iconsx .ix .st.ok{background:var(--brand);color:var(--brand-ink)}
    .iconsx .ix .miss svg{color:var(--dim)}
    .iconsx .none{font-size:13px;color:var(--dim)}
  `);

  /** Draw the card body from the last pass. Plain DOM, so no icon name is ever interpolated. */
  const draw = () => {
    const box = document.getElementById("iconsx");
    if (!box) return;
    box.textContent = "";
    const map = pageMap();
    if (!map) {
      const p = document.createElement("p");
      p.className = "none";
      p.textContent = "The page's icon map is not reachable from here, so nothing was added.";
      box.append(p);
      return;
    }
    for (const name of Object.keys(EXTRA)) {
      const d = EXTRA[name].d;
      const row = document.createElement("div");
      row.className = "ix" + (map[name] ? "" : " miss");

      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", `0 0 ${BOX} ${BOX}`);
      svg.setAttribute("aria-hidden", "true");
      if (map[name] && OK.test(d)) {
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d);
        svg.append(path);
      }
      row.append(svg);

      const text = document.createElement("div");
      const b = document.createElement("b");
      b.textContent = name;
      const s = document.createElement("span");
      s.textContent = EXTRA[name].used;
      text.append(b, s);

      const st = document.createElement("span");
      const there = !!map[name];
      st.className = "st" + (there ? " ok" : "");
      st.textContent = there ? "drawn" : "missing";

      row.append(text, st);
      box.append(row);
    }
  };

  // A redraw makes the page pick the new names up straight away instead of on its next
  // visit. The loader already listens for this event, so no timer and no watcher is needed.
  // No try/catch: dispatching a plain event on document does not throw, and a catch with an
  // empty block would hide the day it does instead of letting the console say so.
  const ping = () => document.dispatchEvent(new Event("peakcut:render"));
  ping();

  P.add("icons-extra", {
    icons: EXTRA,

    tools() {
      return `<h2 class="h">Icons</h2>
        <p class="help">Some icons the page asks for were never drawn, so buttons and menu rows showed a blank square. This file fills them in; nothing else on the page changes. Below is what the page can draw right now.</p>
        <div id="iconsx" class="iconsx"></div>
        <button class="btn sm" type="button" data-act="iconsx-run">Check again</button>
        <p class="hint">Press Check again after updating Clipstorm. It re-checks every icon and marks each one drawn or missing.</p>`;
    },

    load() { seed(); draw(); },

    act: {
      "iconsx-run"() {
        const got = seed();
        draw();
        const msg = got.added.length
          ? `Added ${got.added.length} icon${got.added.length === 1 ? "" : "s"}: ${got.added.join(", ")}.`
          : got.refused.length
            ? `${got.refused.length} icon${got.refused.length === 1 ? "" : "s"} could not be drawn: ${got.refused.join(", ")}.`
            : "Every icon was already drawn in the page.";
        if (P.toast) P.toast(msg, got.refused.length ? "bad" : "ok");
        ping();
      },
    },
  });
})();
