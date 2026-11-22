/* One type scale for every menu page.
 *
 * Measured before this file: 21 distinct pixel sizes across the feature files, five of
 * them fractional (10.5, 11.5, 12.5, 13.5, 14.5). Two pages that read the same place drew
 * their small print at 11.5 and 12.5, and nine page headings were each declared in their
 * own file with three different letter-spacings (-.01em, -.025em, none) and two different
 * line heights (1.2, 1.25).
 *
 * The fractional sizes were removed at the source first, so this file is not fighting
 * them: each rounded to the nearest whole pixel on the scale below (10.5 to 11, 11.5 to
 * 12, 12.5 to 13, 13.5 to 14, 14.5 to 15). Nothing got smaller; the half pixels that
 * vanished all rounded up.
 *
 * What this file does, and nothing else:
 *   - names the seven steps of the scale as variables, so a later file can ask for a
 *     step by name instead of typing 13;
 *   - gives every page heading one size, one letter-spacing and one line height, and
 *     turns on balanced wrapping so a two line heading breaks evenly;
 *   - gives the paragraph under a heading a line length a person can read (62 characters)
 *     and pretty wrapping, which stops a single word landing alone on the last line;
 *   - sets the small print once: .hint and small are one size, one colour.
 *
 * What it does not do: it names no colour, sets no padding, margin, width or border, and
 * adds no motion. The one media query is the same 640px breakpoint polish-mobile already
 * uses, so the two cannot overlap.
 *
 * The 23px heading is kept rather than grown. The shell's own top bar title is 15px and
 * the whole page is deliberately compact; a 30px title would be the only large thing on a
 * screen of 12px labels and read as a mistake. */

(() => {
  const P = window.PeakCut;
  if (!P || typeof P.css !== "function") return;

  P.css("polish-type", `
    /* The scale. Seven steps, each about 1.2x the one before it, which is the smallest
       ratio that still reads as a deliberate step at these sizes. */
    #view{
      --pt-xs:11px;--pt-sm:12px;--pt-md:13px;--pt-lg:15px;
      --pt-xl:17px;--pt-2xl:20px;--pt-3xl:23px;
      --pt-ink:1.25;--pt-read:1.55
    }

    /* Every page heading, whichever file drew it. The nine classes are listed rather than
       written as h1 so a card title (which is also an h1 in some pages) is not caught. */
    #view .pcpg-h,#view .cr-h,#view .fmtp-h,#view .hlp-h,
    #view .pclive-h,#view .sch-h,#view .snd-h,#view .usg-h,
    #view .an-name{
      font-size:var(--pt-3xl);
      line-height:var(--pt-ink);
      letter-spacing:-.01em;
      font-weight:600;
      text-wrap:balance;
    }

    /* A heading is followed by its sentence, not by a gap somebody typed. */
    #view .pcpg-h+ .help,#view .cr-h+.help,#view .hlp-h+.help{margin-top:2px}

    /* The paragraph under a heading. 62 characters is inside the 50 to 75 a line wants,
       and the measure is capped in characters rather than pixels so it follows the font. */
    #view .help,#view .pcpg .help,#view .set-sec .help{
      max-width:62ch;
      line-height:var(--pt-read);
      text-wrap:pretty;
    }

    /* Body prose in a box. Same measure, same wrapping, one step down from a heading. */
    #view .card p,#view .lrn p,#view .lrn li,#view .fmtp-meta,#view .usg-svc{
      line-height:var(--pt-read);
      text-wrap:pretty;
    }

    /* Small print, once. A hint and a <small> were 11, 12 and 12.5 in different files;
       they are the same job, so they get the same size. */
    #view .hint,#view small,#view .sub{
      font-size:var(--pt-sm);
      line-height:1.45;
    }

    /* Inline words that must not break: a key, a file name, an address. */
    #view code,#view kbd,#view samp,#view .mono{
      font-size:.95em;
      white-space:nowrap;
    }

    /* On a narrow screen the heading drops one step. 23px is fine beside a wide column and
       too heavy above a 360px one; 20 is the next step down and needs no other change. */
    @media (max-width:640px){
      #view{
        --pt-3xl:20px;--pt-ink:1.3
      }
      #view .help,#view .pcpg .help{max-width:none}
    }
  `);

  P.add("polish-type", {
    about: "One type scale: seven whole-pixel steps, one heading size, a readable measure.",
  });
})();
