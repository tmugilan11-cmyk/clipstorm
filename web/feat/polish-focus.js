/* A focus ring that is the same shape everywhere, and never invisible.
 *
 * Measured before this file, on the live page at 127.0.0.1:8798:
 *
 *   #view button      outline 2px var(--brand)          (a ring, from the shell)
 *   #view select      outline none; border turns brand  (no ring, only a border colour)
 *   #view input       outline none; border turns brand  (no ring, only a border colour)
 *   #view a[href]     no ring at all, and no border      (nothing)
 *   #view summary     no ring at all                    (nothing)
 *   #view textarea    outline none; border turns brand   (no ring)
 *
 * So three quarters of what a keyboard can reach had no ring. `web/index.html:218` sets
 * `outline:none` on inputs, selects and textareas and replaces it with a border colour,
 * and `:285` sets `outline:none` on everything inside the link composer. Neither is
 * touched here: index.html is frozen, and a border that changes colour IS a visible sign,
 * so those controls are already usable. What they lack is consistency with a button, and
 * that is what this file adds for everything the shell did not cover.
 *
 * The colour is --brand-deep (#6541F4) rather than --brand (#AF9BFF). --brand on white
 * measures 2.34:1, under the 3:1 WCAG 1.4.11 asks of a focus indicator. --brand-deep
 * measures 5.80:1 on white and 5.55:1 on the card, and the dark theme already re-points
 * it to #C8BAFF, which measures 10.47:1 on the dark ground, so one declaration covers both
 * themes. The 2px width and 2px offset match the ring the shell already draws on buttons,
 * so a button and a link now look focused in the same way.
 *
 * Also handled: the ring must be visible where the ground is not white. Links inside a
 * card, a row, the sidebar and the two floating panels all get it, because the rule names
 * elements rather than a container.
 *
 * What this file does not do: it changes no colour of any element at rest, sets no size,
 * padding or margin, and adds no transition. A ring that fades in is a ring that has not
 * arrived yet. */

(() => {
  const P = window.PeakCut;
  if (!P || typeof P.css !== "function") return;

  P.css("polish-focus", `
    /* Everything a keyboard can reach, with one ring. :focus-visible, not :focus, so a
       mouse click does not leave a ring behind on a button somebody just pressed. */
    #view a:focus-visible,
    #view summary:focus-visible,
    #view [tabindex]:not([tabindex="-1"]):focus-visible,
    #view .chip:focus-visible,
    #view .tabbtn:focus-visible,
    #view .pcf-pill:focus-visible,
    #view .stile:focus-visible,
    #view .rv-thumb:focus-visible,
    #view audio:focus-visible,
    #view video:focus-visible,
    .side a:focus-visible,
    .side button:focus-visible,
    .pop:focus-visible,
    dialog a:focus-visible,
    dialog summary:focus-visible{
      outline:2px solid var(--brand-deep);
      outline-offset:2px;
      border-radius:4px;
    }

    /* A control that sits on a coloured ground needs the ring to survive it. On the
       dark theme --brand-line is #362676, a dark brown that measures 1.70:1 on the
       black sidebar (--frame #000000), 1.60:1 inside a dialog (--bg #0A0A0A) and
       1.35:1 on a pick menu (#1F1939), all under the 3:1 that WCAG 1.4.11 asks of a
       focus indicator. So the ring keeps --brand-deep here: #C8BAFF in the dark theme,
       measured 11.9:1 on the black sidebar, 11.22:1 in a dialog and 9.48:1 on a pick
       menu. */
    .side a:focus-visible,
    .side button:focus-visible,
    .side [tabindex]:not([tabindex="-1"]):focus-visible,
    dialog:focus-within [data-f]:focus-visible,
    .pick-opt:focus-visible{
      outline-color:var(--brand-deep);
    }

    /* A big card, if one is ever made focusable. Neither .job nor .rv-card carries a
       tabindex today, so this matches nothing right now; it is here because the ring for
       something the size of a card has to go on the inside, and working that out again
       later is the sort of detail that gets missed. outline-offset:-2px keeps the ring
       from overlapping the card beside it. */
    #view .job:focus-visible,
    #view .rv-card:focus-visible{
      outline:2px solid var(--brand-deep);
      outline-offset:-2px;
    }

    /* The three inputs the shell silently un-outlines get a ground change as well as a
       border change, so the sign is not colour alone. This is deliberately weaker than the
       ring: the ring says "the keyboard is here", the wash says "this is the field you are
       typing in", and they are different questions. */
    #view input:focus-visible,
    #view select:focus-visible,
    #view textarea:focus-visible{
      background:var(--brand-soft);
    }
  `);

  P.add("polish-focus", {
    about: "One focus ring for links, rows, chips and panels, at a colour that measures 5.8:1.",
  });
})();
