/* The spine the wave-1 pages lean on: menu headings with an order, and every registered
 * page as one flat row in the order the menu should show it. Nothing is drawn here.
 * The menu, the quick filter and the page guard all read this one list, so no heading
 * can be printed twice and no row can sit in two places.
 *
 *   PeakCut.menuGroup("Understand", 20);   // a heading. Lower number sits higher.
 *   PeakCut.menuGroups();                  // ["Make", "Understand", ...] in menu order
 *   PeakCut.pageRows();                    // [{name, nav, icon, tip, group, order}, ...]
 *   PeakCut.groupFor("analytics");          // "Understand", or "" when the page has no heading
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  const groups = (P._menuGroups = P._menuGroups || {});

  // The headings this wave uses. A file may add its own, or move one, with menuGroup.
  const BASE = [["Make", 10], ["Understand", 20], ["Look and sound", 30], ["Set up", 35], ["Connect", 40], ["Account", 60], ["Help", 90]];

  // Where a heading sorts: its number, the top group at 0, an unknown heading after the rest.
  const rank = (g) => {
    const hit = groups[g];
    return hit && Number.isFinite(hit.order) ? hit.order : (g ? 500 : 0);
  };

  // A number that can be compared, or the fallback when the value is missing.
  const num = (v, fallback) => (Number.isFinite(Number(v)) ? Number(v) : fallback);

  // Registers one heading and its place; calling it again with the same name only moves it.
  function menuGroup(name, order) {
    const key = String(name || "").trim();
    if (!key) return "";
    const old = groups[key];
    P._menuAt = (P._menuAt || 0) + 1;
    groups[key] = { name: key, order: num(order, 50), at: old ? old.at : P._menuAt };
    return key;
  }

  // Every heading in menu order. The top group "" leads, but only when a page really sits there.
  function menuGroups() {
    const rows = Object.keys(groups)
      .map((k) => groups[k])
      .sort((a, b) => a.order - b.order || a.at - b.at || a.name.localeCompare(b.name));
    const top = (P._pages || []).some((p) => !p.group);
    return (top ? [""] : []).concat(rows.map((r) => r.name));
  }

  // Every registered page as one row, sorted by heading, then the page's own number, then arrival.
  function pageRows() {
    const pages = (P._pages || []).slice();
    return pages
      .map((p, at) => ({
        name: p.name,
        nav: p.nav || p.name,
        icon: p.icon || "",
        tip: p.tip || "",
        group: p.group || "",
        order: num(p.order, 50),
        at,
      }))
      .sort((a, b) => rank(a.group) - rank(b.group)
        || (a.group === b.group ? 0 : a.group.localeCompare(b.group))
        || a.order - b.order || a.at - b.at)
      .map(({ at, ...row }) => row);
  }

  // The heading one page sits under; "" when the page has none or was never registered.
  function groupFor(name) {
    const page = (P._pages || []).find((p) => p.name === name);
    return page ? (page.group || "") : "";
  }

  /* ---- The sidebar: five plain sections -------------------------------------------------------------------
   * Each page still says its own group in its own file. The sidebar ignores that and uses this table instead:
   * page name -> [section, place in the section, words in the menu ("" keeps the page's own)].
   * A page that is not in the table goes under Settings, after the known ones. */
  const SECTIONS = [
    { id: "start", name: "Start", open: true },
    { id: "live", name: "Record live", open: true },
    { id: "look", name: "Look and sound", open: false },
    { id: "grow", name: "Grow", open: false },
    { id: "settings", name: "Settings", open: false },
  ];
  const SIDEBAR = {
    overview: ["start", 1, ""], library: ["start", 2, ""], review: ["start", 3, ""],
    live: ["live", 1, "Live recording"], streamer: ["live", 2, "Streamer mode"], creators: ["live", 3, ""],
    formats: ["look", 1, "Caption styles"], brand: ["look", 2, "Brand template"], pictures: ["look", 3, "Asset library"], sounds: ["look", 4, "Audio"],
    // The old "audio" and "audio-edit" pages are not rows any more: one Audio row, and clip audio is edited in the clip editor.
    analytics: ["grow", 1, "Analytics"], week: ["grow", 2, ""], improve: ["grow", 3, ""], schedule: ["grow", 4, "Calendar"],
    ai: ["settings", 1, ""], transcribe: ["settings", 2, ""], apps: ["settings", 3, ""], "ai-usage": ["settings", 4, ""],
    storage: ["settings", 5, ""], account: ["settings", 6, ""], tools: ["settings", 7, ""], help: ["settings", 8, ""],
  };
  const BUILT_IN = ["overview", "library", "review"];   // rows index.html draws itself

  const KEY = "peakcut_nav_sections";
  const saved = () => {
    try { const v = JSON.parse(localStorage.getItem(KEY) || "{}"); return v && typeof v === "object" ? v : {}; }
    catch (e) { return {}; }
  };
  const remember = (id, open) => {
    try { const v = saved(); v[id] = !!open; localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) { /* no storage: it just forgets */ }
  };
  // What the person last chose for a section, or its default when they never touched it.
  const chosen = (sec) => { const v = saved()[sec.id]; return typeof v === "boolean" ? v : sec.open; };

  // The section the open page belongs to; the creator pages belong to "Record live".
  function sectionOf(view) {
    const v = String(view || "");
    if (v.startsWith("c:")) return "live";
    if (SIDEBAR[v]) return SIDEBAR[v][0];
    if (v === "settings" || (P._pages || []).some((p) => p.name === v)) return "settings";
    return "";
  }

  // Marks every row of a section so folding and the quick filter can find them.
  const tag = (html, id, folded) => String(html || "").replace(/class="nav-item(?=[" ])/g,
    'data-sec="' + id + '" class="nav-item' + (folded ? " nv-fold" : ""));

  function pageRow(p, label, view) {
    const draw = typeof ic === "function" && typeof I === "object" && I && I[p.icon || "grid"] ? ic(p.icon || "grid") : "";
    let badge = "";
    try {
      const n = typeof p.badge === "function" ? p.badge() : p.badge;
      if (n) badge = `<span class="count">${Number(n) > 99 ? "99+" : Number(n)}</span>`;
    } catch (e) { /* a badge that fails is just left off */ }
    const on = view === p.name;
    return `<button class="nav-item${on ? " on" : ""}"${on ? ' aria-current="page"' : ""} data-act="pcpage" data-v="${esc(p.name)}" title="${esc(p.tip || label)}">${draw}<span class="label">${esc(label)}</span>${badge}</button>`;
  }

  /* core = the rows index.html draws: {overview, library, review, creators, newCreator, admin} as markup. */
  function sidebarHtml(core) {
    core = core || {};
    const view = typeof S === "object" && S ? S.view : "";
    const amOwner = typeof S === "object" && S && S.status && S.status.user && S.status.user.is_admin;
    const here = sectionOf(view);
    const pages = (P._pages || []).filter((p) => !p.hidden || SIDEBAR[p.name])
      .filter((p) => !(p.admin && !amOwner));
    const out = [];
    for (const sec of SECTIONS) {
      const entries = [];   // [place, markup]
      for (const name of BUILT_IN) if (SIDEBAR[name][0] === sec.id && core[name]) entries.push([SIDEBAR[name][1], core[name]]);
      for (const p of pages) {
        const m = SIDEBAR[p.name];
        if (m && m[0] === sec.id) {
          let row = pageRow(p, m[2] || p.nav || p.name, view);
          if (p.name === "creators") row += (core.creators || "") + (core.newCreator || "");
          entries.push([m[1], row]);
        }
      }
      if (sec.id === "settings") {
        for (const p of pages) if (!SIDEBAR[p.name]) entries.push([100, pageRow(p, p.nav || p.name, view)]);
      }
      entries.sort((a, b) => a[0] - b[0]);
      let rows = entries.map((e) => e[1]).join("");
      if (sec.id === "settings") rows += core.admin || "";
      if (!rows) continue;
      const open = sec.id === here || chosen(sec);
      const tip = sec.id === here ? "Stays open while you are on a page in this section" : "Show or hide this section";
      out.push(`<h4 class="nv-h"><button type="button" class="nv-head" data-act="navsec" data-sec="${sec.id}" aria-expanded="${open}" title="${tip}"><span>${esc(sec.name)}</span><i class="nv-chev" aria-hidden="true"></i></button></h4>`
        + tag(rows, sec.id, !open));
    }
    return out.join("");
  }

  // Opens or closes one section without redrawing the menu, so the keyboard focus stays on its heading.
  function toggleSection(btn) {
    const id = btn.dataset.sec;
    const sec = SECTIONS.find((x) => x.id === id);
    const nav = document.getElementById("nav");
    if (!sec || !nav) return;
    remember(id, !chosen(sec));
    const open = !!nav.querySelector('.nav-item.on[data-sec="' + id + '"]') || chosen(sec);
    btn.setAttribute("aria-expanded", String(open));
    for (const row of nav.querySelectorAll('.nav-item[data-sec="' + id + '"]')) row.classList.toggle("nv-fold", !open);
  }

  if (typeof P.css === "function") P.css("menu-sections", `
    .nav h4.nv-h{padding:6px 0 1px}
    .nv-head{display:flex;align-items:center;justify-content:space-between;width:100%;min-height:26px;padding:0 10px;border:0;border-radius:6px;background:transparent;color:var(--frame-dim);font:inherit;font-size:12px;font-weight:600;cursor:pointer;text-align:left}
    .nv-head:hover{color:var(--frame-text)}
    .nv-head:focus-visible{outline:2px solid var(--brand);outline-offset:1px}
    .nv-chev{display:block;width:6px;height:6px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(45deg);margin:-3px 2px 0 0;transition:transform .15s ease}
    .nv-head[aria-expanded="false"] .nv-chev{transform:rotate(-45deg);margin:0 3px 0 0}
    .nav-item.nv-fold{display:none}
    #nav:has(#pc_navsearch input:not(:placeholder-shown)) .nav-item.nv-fold{display:flex}
    .nav-item.nv-sub{padding-left:28px}
    .nav-item.nv-new{min-height:24px;font-size:13px;color:var(--frame-dim)}
    @media (min-width:901px){.app.mini .nav-item.nv-fold{display:flex}.app.mini .nav-item.nv-sub{padding-left:0}}
  `);

  // Fill in the default headings, never over one another file has already placed.
  for (const [name, order] of BASE) if (!groups[name]) menuGroup(name, order);

  P.menuGroup = menuGroup;
  P.menuGroups = menuGroups;
  P.pageRows = pageRows;
  P.groupFor = groupFor;
  P.sidebarHtml = sidebarHtml;

  // This file owns no Tools card and no page; it still declares itself, like every feature.
  // This file may load after the pages that already asked for a redraw, so draw the menu once more with the sections.
  // The menu is first drawn before the feature files are in, so wait (briefly) for the page to finish starting.
  (function redraw(tries) {
    if (typeof drawShell === "function" && P._booted) { try { drawShell(); } catch (e) { /* the next redraw will do it */ } return; }
    if (tries < 40) setTimeout(() => redraw(tries + 1), 150);
  })(0);

  if (typeof P.add === "function") P.add("menu", { label: "Menu spine", act: { navsec: (el) => toggleSection(el) } });
})();
