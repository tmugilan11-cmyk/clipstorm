/* A question mark beside each of the six numbers at the top of Analytics.
 *
 * The six cards say "Views, Watch time, Impressions, Click-through rate, Average view duration,
 * Subscribers gained" and nothing on the page says what any of them means or how it was counted.
 * Each question mark opens one sentence that does, worded from `yt-studio-analytics-spec.md`
 * (section 7, "Exact definitions") and from the metric the route actually reads, so the sentence
 * never promises a number this PeakCut cannot send.
 *
 * The cards belong to `analytics-kpi.js`, which this file does not touch. It finds them by their
 * own label text and puts a button and a panel beside that label, so a card is described wherever
 * it is drawn, and a card that is not drawn has nothing added to it.
 *
 * What it reads on Analytics (no request, no number):
 *   "Views"                -> yt-studio-analytics-spec.md 7.1   (what counts as a view)
 *   "Watch time"           -> yt-studio-analytics-spec.md 7.3   (watch time, hours vs minutes)
 *   "Impressions"          -> yt-studio-analytics-spec.md 7.2   (thumbnail impressions)
 *   "Click-through rate"   -> yt-studio-analytics-spec.md 7.9   (CTR, and the sum it is not)
 *   "Average view duration"-> yt-studio-analytics-spec.md 7.4   (AVD over engaged views)
 *   "Subscribers gained"   -> yt-studio-analytics-spec.md 7.8   (gained minus lost)
 */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-help", `
    .akhelp{flex:none;display:inline-grid;place-items:center;width:16px;height:16px;padding:0;margin:0 0 0 5px;
      border:1px solid var(--line-2);border-radius:50%;background:var(--bg);color:var(--dim);
      font:600 10.5px/1 system-ui,-apple-system,"Segoe UI",sans-serif;cursor:pointer;vertical-align:middle;
      transition:background .15s ease,color .15s ease,border-color .15s ease}
    /* The label grows to fill the row, so a mark placed beside it would sit at the far end. This wrapper
       holds the words and the mark together and takes the growing for them, and a long label still ends
       in an ellipsis instead of pushing the mark out of the card. */
    .akhelp-w{flex:1 1 auto;min-width:0;display:inline-flex;align-items:center}
    .akhelp-w .akpi-l{flex:0 1 auto;min-width:0}
    .akhelp:hover,.akhelp:focus-visible{background:var(--brand-soft);color:var(--brand-deep);border-color:var(--brand-line)}
    .akhelp[aria-expanded="true"]{background:var(--brand-ink);border-color:var(--brand-ink);color:#fff}
    .akhelp-s{position:fixed;z-index:68;width:min(320px,calc(100vw - 24px));margin:0;padding:11px 13px 12px;
      border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--ink);
      font:400 12.5px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;text-align:left;font-weight:400;
      white-space:normal;max-height:min(320px,60vh);overflow:auto;animation:akhelp-in .14s ease}
    @keyframes akhelp-in{from{opacity:0;transform:translateY(-3px)}to{opacity:1;transform:none}}
    @media (prefers-reduced-motion:reduce){.akhelp-s{animation:none}}
  `);

  /* ---- the six sentences -------------------------------------------------
   * One sentence each, and every clause in it is traceable to the spec section named above. Where the
   * spec warns that a number is not what it looks like (CTR is not total views over impressions, watch
   * time is minutes in the API but hours in Studio), the sentence says so instead of smoothing it over. */
  const REALMS = [
    { // The shape /api/analytics/summary sends once a YouTube channel is connected.
      name: "youtube",
      cards: [
        { raw: "views", label: "Views", name: "views",
          // 7.1: "The number of legitimate views ... counted the moment a video starts to play across all
          // formats ... This metric incorporates co-viewing estimates for viewers watching together on TV screens."
          say: "The number of legitimate views: one is counted when a video starts to play, in any format including " +
               "Shorts and live streams, with an estimate added when people watch together on a TV." },
        { raw: "watch_time", label: "Watch time", name: "watch time",
          // 7.3: "The amount of time viewers have watched your video. This includes watch time from co-views."
          say: "The total time people spent watching, added up and shown in hours, including the time of people " +
               "who watched together on a TV screen." },
        { raw: "impressions", label: "Impressions", name: "impressions",
          // 7.2: "Impressions are counted if the thumbnail is shown for more than 1 second and at least 50%
          // of the thumbnail is visible on the screen."
          say: "The number of times your thumbnails were shown on YouTube, counted only when a thumbnail was on " +
               "screen for more than one second and at least half of it was visible." },
        { raw: "ctr", label: "Click-through rate", name: "click-through rate",
          // 7.9: "The percentage of impressions that resulted in a click to watch the video. This is calculated
          // as clicks divided by impressions", and "Never compute total views / impressions".
          say: "How often a viewer watched after seeing a thumbnail: views that began from a counted impression " +
               "divided by the counted impressions, so it is not total views divided by impressions." },
        { raw: "average_view_duration", label: "Average view duration", name: "average view duration",
          // 7.4: "Average minutes watched among those who stayed to watch ... calculated with engaged views and
          // the corresponding watch time." Formula: AVD = watch time / engaged views.
          say: "The average time one view lasted, worked out as watch time divided by engaged views, which " +
               "count the times someone stayed to watch past the first seconds and leave out loops." },
        { raw: "subscribers", label: "Subscribers gained", name: "subscribers",
          // 7.8: net change = subscribersGained - subscribersLost.
          say: "The change in subscribers over the range, worked out as subscribers gained minus subscribers lost, " +
               "and it counts everyone who subscribed anywhere on YouTube, not just under one video." },
      ],
    },
    { // The shape the same route sends when no channel is connected: Clipstorm's own counters.
      name: "peakcut",
      cards: [
        { raw: "tracks", label: "Views Clipstorm tracked", name: "tracked views",
          say: "The views Clipstorm itself recorded on the posts it sent out, added up for this range, so it is " +
               "smaller than the view count YouTube would show for the same videos." },
      ],
    },
  ];

  const CELL = ".akpi-c", OPEN = ".akhelp";
  let shown = null;          // the button and panel on screen, or null
  let watched = null;        // the box the observer is already watching

  /** Lowercase words and single spaces, so "Late 28 days" and a line break cannot break a match. */
  function norm(s) {
    return String(s === null || s === undefined ? "" : s)
      .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  // Every (card, phrase) pair, worked out once. The longest phrase that fits a card wins, so a card
  // called "Average view duration" is not mistaken for one called "Views".
  const NEEDLES = [];
  for (const realm of REALMS) {
    for (const card of realm.cards) {
      for (const phrase of [card.label, card.name]) {
        const text = norm(phrase);
        if (text) NEEDLES.push({ card, text, size: text.length });
      }
    }
  }

  /** Which card this cell shows, judged by the words in its label, and the label node to sit beside. */
  function which(cell) {
    const label = cell.querySelector(".akpi-l");
    if (!label) return null;                          // no label box: nothing to sit a mark beside
    // Only the label is read. The sentence this file adds also passes through the cell, and matching on
    // the whole cell would let a sentence decide which card it belongs to.
    const text = norm(label.textContent);
    if (!text) return null;
    let hit = null;
    for (const it of NEEDLES) {
      if (text.indexOf(it.text) < 0) continue;
      if (!hit || it.size > hit.size) hit = it;         // the longest match is the most specific one
    }
    return hit ? { card: hit.card, label } : null;
  }

  function close(refocus) {
    if (!shown) return;
    const pair = shown;
    shown = null;
    try { pair.panel.hidden = true; } catch (e) { /* the cell went away with the page */ }
    try { pair.button.setAttribute("aria-expanded", "false"); } catch (e) { /* same */ }
    if (refocus) { try { pair.button.focus(); } catch (e) { /* focus is not worth an error */ } }
  }

  /** The panel, directly under the question mark when there is room, above it when there is not. */
  function place(button, panel) {
    try {
      const box = button.getBoundingClientRect();
      const vw = window.innerWidth || 1024, vh = window.innerHeight || 768;
      if (!box || (!box.width && !box.height)) {       // not laid out yet: a corner it can still be read in
        panel.style.left = "12px"; panel.style.right = "auto";
        panel.style.top = "auto"; panel.style.bottom = "16px";
        return;
      }
      const width = Math.min(320, Math.max(200, vw - 24));
      panel.style.width = Math.round(width) + "px";
      let left = box.left;
      if (left + width > vw - 12) left = vw - 12 - width;
      if (left < 12) left = 12;
      panel.style.left = Math.round(left) + "px";
      panel.style.right = "auto";
      // Three lines are about 140 tall; that is enough to choose a side and nothing else.
      if (box.bottom + 8 + 140 > vh && box.top > 180) {
        panel.style.top = "auto";
        panel.style.bottom = Math.round(vh - box.top + 8) + "px";
      } else {
        panel.style.top = Math.round(box.bottom + 8) + "px";
        panel.style.bottom = "auto";
      }
    } catch (e) { /* the stylesheet's own placement still stands */ }
  }

  function open(pair) {
    if (shown && shown.panel !== pair.panel) close(false);
    pair.panel.hidden = false;
    pair.button.setAttribute("aria-expanded", "true");
    shown = pair;
    place(pair.button, pair.panel);
  }

  /** The button and its panel, built once per card and put beside that card's label. */
  function dress(cell, got) {
    const card = got.card;
    const id = "akhelp-" + card.raw;
    const panel = document.createElement("div");
    panel.className = "akhelp-s";
    panel.id = id;
    panel.hidden = true;
    panel.setAttribute("role", "note");
    panel.textContent = card.say;                     // text, never markup: nothing here can inject anything

    const button = document.createElement("button");
    button.type = "button";
    button.className = "akhelp";
    button.textContent = "?";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", id);
    button.setAttribute("aria-label", "What the " + card.name + " number means");
    // No title attribute: a native tooltip would open on hover and sit over the first line of the very
    // panel this button opens. The aria-label still names the button for a screen reader.

    const pair = { button, panel };
    button.addEventListener("click", (e) => {
      e.preventDefault();
      if (panel.hidden) open(pair); else close(false);
    });
    // Escape closes it wherever the focus is; the loader asks the same question of `keys` below, and
    // closing twice is harmless because the second call finds nothing open.
    button.addEventListener("keydown", (e) => {
      if (e.key === "Escape" || e.key === "Esc") { e.preventDefault(); close(true); }
    });

    // The label is the wide, growing child of the card's top row, so a mark placed after it would land
    // at the far end of the row, an inch from the words it explains. A small wrapper holds the words and
    // the mark together and does the growing instead. The button and its panel go inside it as siblings
    // of each other, and the panel is taken out of the flow while it is open, so it adds no height.
    const label = got.label, row = label.parentElement;
    try {
      const wrap = document.createElement("span");
      wrap.className = "akhelp-w";
      row.insertBefore(wrap, label);
      wrap.append(label, button, panel);
    } catch (e) {                                     // a different card shape still gets the plain version
      label.after(button, panel);
    }
  }

  /** Walk the cards on screen and describe any that are not described yet. Safe to call every frame. */
  function describe() {
    const page = document.getElementById("view");
    if (!page) return;
    let cells;
    try { cells = page.querySelectorAll(CELL); } catch (e) { return; }
    for (const cell of cells) {
      if (cell.querySelector(OPEN)) continue;         // this card has its question mark already
      const got = which(cell);
      if (got) { try { dress(cell, got); } catch (e) { /* one card failing does not stop the others */ } }
    }
    // A redrawn card takes its panel with it, so a panel that left the page is forgotten here.
    if (shown && !page.contains(shown.panel)) { shown = null; }
  }

  /** The cards are redrawn on every paint, so the box is watched instead of the cards. */
  function watch() {
    describe();
    const page = document.getElementById("view");
    if (!page || page === watched || typeof MutationObserver !== "function") return;
    watched = page;
    try {
      new MutationObserver(() => { try { describe(); } catch (e) { /* a paint is never worth an error */ } })
        .observe(page, { childList: true, subtree: true });
    } catch (e) { /* the hook below still describes the first draw */ }
  }

  // A click anywhere else closes the sentence. The button's own handler runs first, so its click has
  // already opened the panel by the time this sees it, and both cases are skipped.
  document.addEventListener("click", (e) => {
    if (!shown) return;
    const t = e.target;
    if (t && t.closest && (t.closest(OPEN) || shown.panel.contains(t))) return;
    close(false);
  });
  // The same panel is measured again when the window changes size under it.
  window.addEventListener("resize", () => { if (shown) place(shown.button, shown.panel); });

  P.add("analytics-help", {
    /** Called when the Analytics page is drawn, and again by the page on every range change. */
    load() { watch(); },
    // The loader only offers key handling for pages, so Escape is answered here as well as on the button.
    keys(e) {
      if (!e || (e.key !== "Escape" && e.key !== "Esc")) return false;
      if (!shown) return false;
      close(true);
      return true;
    },
    after: {
      /** Fires once the page's markup is in the DOM, before any request has answered. */
      drawSettings() { watch(); },
    },
  });
})();
