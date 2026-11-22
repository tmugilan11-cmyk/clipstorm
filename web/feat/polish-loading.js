/* One way of showing work in progress, and one real fetch that uses it.
 *
 * Pages fetch, then draw. In between there is either a blank area or the words "Loading…" sitting in a box
 * that is a different size from what lands in it, so the page jumps when the answer arrives. This file adds a
 * placeholder made of neutral blocks, sized like the thing that is coming, and a helper that waits a third of
 * a second before drawing it. A fetch that answers in 20 ms never flashes a grey box, so the fast case looks
 * finished and the slow case looks calm instead of empty.
 *
 * The blocks carry no words, no numbers and no rows that could be mistaken for data. The only text is the
 * aria-label on the group, which a screen reader reads as "Reading the storage folder" and a sighted person
 * never sees. Nothing moves unless the person has not asked for less motion. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  // Every selector here starts at .pcl, which only this file ever writes, so nothing else on the page moves.
  P.css("polish-loading", `
    .pcl{display:grid;gap:9px;margin:2px 0 0;min-width:0}
    .pcl-bar{height:11px;border-radius:6px;background:var(--line);min-width:0}
    .pcl-bar.w90{width:90%}
    .pcl-bar.w70{width:70%}
    .pcl-bar.w45{width:45%}
    .pcl-block{height:72px;border-radius:10px;border:1px solid var(--line);background:var(--muted)}
    .pcl-row{display:grid;grid-template-columns:38px minmax(0,1fr);gap:10px;align-items:center;
      padding:9px 0;border-top:1px solid var(--line)}
    .pcl-row:first-of-type{border-top:0}
    .pcl-thumb{height:38px;border-radius:7px;background:var(--line)}
    .pcl-row .pcl-bar{height:9px}
    @media (prefers-reduced-motion: no-preference){
      .pcl-bar,.pcl-thumb,.pcl-block{animation:pclbreathe 1.7s ease-in-out infinite}
      .pcl-bar:nth-child(2){animation-delay:.18s}
      .pcl-bar:nth-child(3){animation-delay:.36s}
      @keyframes pclbreathe{0%,100%{opacity:1}50%{opacity:.55}}
    }
    @media (max-width:640px){.pcl-block{height:56px}}
  `);

  const line = (w) => `<div class="pcl-bar ${w}"></div>`;
  const SHAPES = {
    // Roughly the size of a paragraph that is about to arrive.
    text: () => line("w90") + line("w90") + line("w45"),
    // A number panel: one tall block, then a line under it.
    stat: () => `<div class="pcl-block"></div>` + line("w45"),
    // A short list: three rows with a thumbnail and two lines each.
    list: () => `<div class="pcl-row"><div class="pcl-thumb"></div><div class="pcl">${line("w90")}${line("w45")}</div></div>`
      .repeat(3),
  };

  /* The public helper. Other pages can call this without knowing anything about the markup.
   *   const done = PeakCut.loading.hold(box, "Reading the storage folder");
   *   ...await the fetch, draw the real thing...
   *   done();                            // clears the busy flag, leaves your content alone
   * and html("list") when a page builds its own markup. */
  P.loading = {
    html(kind) {
      const shape = SHAPES[String(kind || "text")] || SHAPES.text;
      return `<div class="pcl" aria-hidden="true">${shape()}</div>`;
    },
    hold(el, label, waitMs, kind) {
      if (!el) return () => {};
      const asked = Number(waitMs);
      const wait = Number.isFinite(asked) && asked >= 0 ? asked : 300;
      const shape = SHAPES[String(kind || "text")] || SHAPES.text;
      let drawn = false, stopped = false;
      const timer = setTimeout(() => {
        if (stopped || !el.isConnected) return;
        drawn = true;
        el.setAttribute("aria-busy", "true");
        // role="status" so the label is spoken once, without stealing focus.
        el.innerHTML = `<div class="pcl" role="status" aria-label="${esc(label || "Loading")}">${shape()}</div>`;
      }, wait);
      return () => {
        stopped = true;
        clearTimeout(timer);
        if (!el.isConnected) return;
        el.removeAttribute("aria-busy");
        const mine = el.querySelector(".pcl");
        if (drawn && mine) mine.remove();
      };
    },
  };

  // The one real fetch this file owns: the storage folder, asked for when the card is opened by hand.
  // Same route the Storage page reads, so the two never disagree.
  P.add("polish-loading", {
    about: "A calm placeholder while a page waits for the server.",
    tools() {
      return `<h2>Loading</h2>
        <p class="help">One way of showing work in progress. The placeholder waits a third of a second before it
          appears, so a fast answer never flashes a grey box. Under reduced motion it does not fade at all.</p>
        <div class="row"><button class="btn" data-act="pclstor">Check free space</button></div>
        <div id="pcl_stor"></div>`;
    },
    act: {
      async pclstor(btn) {
        const box = document.getElementById("pcl_stor");
        if (!box) return;
        btn.disabled = true;
        const done = P.loading.hold(box, "Reading the storage folder");
        try {
          const s = await P.api("/api/storage");
          const free = Number(s && s.free_gb);
          // A number with no unit is a rumour, so the unit travels with it.
          const text = Number.isFinite(free) ? `${esc(free.toFixed(1))} GB free` : "The server did not send a figure.";
          box.innerHTML = `<p class="help">${text} on this drive.</p>`;
        } catch (err) {
          const why = (err && err.message) || "The storage folder could not be read.";
          box.innerHTML = `<p class="help">${esc(why)} Try again in a moment.</p>`;
        } finally {
          done();
          btn.disabled = false;
        }
      },
    },
  });
})();
