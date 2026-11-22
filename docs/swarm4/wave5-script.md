export const meta = {
  name: "swarm8-wave5-polish",
  description: "Wave 5 of the 10x18 programme: polish. 16 build slots then reviewer and fixer.",
};

const HEAD = `
CONTEXT: PeakCut is a Windows clipping app. One page (peakcut/web/index.html, 7,000 lines) is FROZEN. Every new piece of UI is its own file in peakcut/web/feat/<slug>.js and peakcut/web/plugins.js loads it. 47 feature files exist already. Waves 1-4 built the features; this wave makes them feel finished.

FIRST, before writing anything, read these in this order:
1. peakcut/docs/swarm4/WAVE5-BRIEF.md  (the rules for this wave)
2. peakcut/docs/swarm3/CONTRACT.md     (the plug-in contract)
3. peakcut/web/feat/heard.js           (the smallest correct feature file)
4. peakcut/web/plugins.js              (which helpers actually exist, how routing works)

Then load ONE skill with the skill tool before you write: frontend-design, or design-taste-frontend, or make-interfaces-feel-better, or accessibility. Say which you loaded.

HARD RULES
- You own EXACTLY ONE file. Do not edit any other file. Never edit web/index.html, web/plugins.js, or anything in studio/.
- Handlers declared inside PeakCut.page(...) NEVER fire. Clicks and keys are routed only through PeakCut.add. Put your handlers in a PeakCut.add block.
- Run: node --check peakcut/web/feat/<your file>  and paste the output.
- Run: cd peakcut && python tests/test_feat_files.py  and confirm "All checks passed."
- Escape every server string with esc() before it goes into HTML.
- Plain English, short sentences. No emoji. NO EM DASH. No new dependencies. No shadows. Hover changes colour only. No !important. Respect prefers-reduced-motion.
- Never invent a number, a name or a page.
- BUDGET: 25 minutes. Read only what you need, then write. A working checked file beats a perfect plan. Write what you left out in your report.
- Write peakcut/docs/swarm4/wave5/<slug>.md (under 60 lines): what you added, the file you own, node --check output, what you measured with real numbers, what is still missing.
`;

const BUILD = [
  ["polish-type", `Build web/feat/polish-type.js: ONE type scale for the whole page.
The page currently mixes font sizes written by hand in many files. Add a scoped stylesheet through PeakCut.css("polish-type", ...) that gives h1/h2/h3, .sub, .help, .hint, small, table cells and buttons a consistent size and line-height across #view, without changing any layout width. Use the existing CSS variables. Set a readable line-height (1.5 for body text, 1.15 for headings). Do not touch the sidebar or the topbar. Measure: list the computed font-size of h1, h2, .help and small on /app/analytics and /app/improve before and after.`],

  ["polish-space", `Build web/feat/polish-space.js: one spacing rhythm.
Cards, sections, grids and form rows across the page use ad-hoc margins. Add a scoped stylesheet through PeakCut.css("polish-space", ...) that normalises vertical rhythm on the menu pages: a consistent gap between sections, a consistent card padding, and a consistent gap between a label and its field. Base the scale on multiples of 4px. Do not change the width of anything, and do not touch #app (the sidebar) or .topbar. Measure: list the computed margin-bottom of the first three sections on /app/creators and /app/formats before and after.`],

  ["polish-colour", `Build web/feat/polish-colour.js: one colour system, applied.
Read the :root variables at peakcut/web/index.html line ~30. Audit the 47 feature files for colours written as raw hex that are near-duplicates of the variables. In your file, add a scoped stylesheet that pulls those stray colours back to the variables, and nothing else. Do not restyle the brand accent. Report exactly how many raw hex colours you found across the feature files and how many you mapped. Keep it measurable: grep the feature files and print the counts.`],

  ["polish-icons", `Build web/feat/polish-icons.js: make every icon consistent.
peakcut/web/feat/icons-extra.js already adds icon names that the page's own I map lacked. Find any place in the feature files that calls ic(name) with a name that does not exist (it renders an empty or "undefined" glyph). Your file must fix the CALL SITES you can fix from inside your own file, and for the rest, register the missing names into the page's icon set if that is possible from a feature file; if it is not possible, say so plainly in your report and instead add a CSS fallback that hides an empty icon box rather than showing a gap. Measure: print the list of ic(...) names used across web/feat/*.js, and which of them the page actually knows.`],

  ["polish-empty", `Build web/feat/polish-empty.js: one way of saying "there is nothing here yet".
Right now different pages say it differently, and some say nothing at all. Add a scoped stylesheet plus a small helper on PeakCut that draws one consistent empty block: a short sentence, and one button when there is an obvious next step. Then use it in ONE place you can reach from your own file (through an after hook), and document in your report where the others should go. The sentence must never blame the person and must never invent a number. Measure: list every empty state you found across the 47 feature files, and which one you unified.`],

  ["polish-errors", `Build web/feat/polish-errors.js: one way of showing a failure.
Find every place in the feature files that swallows a failure (an empty catch, or a catch that only logs). There are several. Add a scoped style for an inline error line and a window-level helper through PeakCut that turns a caught error into one plain sentence plus a Retry button where a retry makes sense. Then wire the helper into as many of the silent catches as you can reach WITHOUT editing other agents' files: if they must be edited, list them precisely in your report instead. Plain English: say what failed and what to do, never "Something went wrong". Measure: report the count of empty catch blocks in web/feat/*.js before and after (grep).`],

  ["polish-loading", `Build web/feat/polish-loading.js: one way of showing work in progress.
Pages fetch data and show nothing until it lands. Add a scoped skeleton style and a helper on PeakCut that draws a calm placeholder (no spinner animation that ignores reduced motion, no fake numbers, no fake rows of text that look like data). Put it in front of ONE real fetch you can reach from your own file, and list in your report the other pages that should use it. Measure: report which menu pages currently show a blank area for more than 300 ms (time the /api calls from the browser and say which).`],

  ["polish-motion", `Build web/feat/polish-motion.js: motion that helps and never hurts.
The page has hover states and a few transitions. Add a scoped stylesheet with a short, restrained set: a 120 ms colour transition on buttons and links, a 160 ms reveal for a panel that opens, and nothing that slides, bounces or loops. Everything must be disabled under @media (prefers-reduced-motion: reduce). Do not animate anything that moves content the person is reading. Measure: list every transition and animation already declared in web/index.html and the feature files, and say which ones you deliberately left alone.`],

  ["polish-keyboard", `Build web/feat/polish-keyboard.js: the whole app reachable from the keyboard.
peakcut/web/feat/keys.js already handles some shortcuts. Read it first and do not duplicate it. Add: a visible "?" help panel listing every shortcut that actually exists (read them from the files, never invent one), Escape closing the newest open panel, and Tab order sanity so focus never lands on a hidden control. Register your handlers through PeakCut.add("polish-keyboard", { keys(e) {...} }) and return true only when you handled the key. Measure: press each shortcut you list and confirm it does what the panel says.`],

  ["polish-focus", `Build web/feat/polish-focus.js: a focus ring you can actually see, everywhere.
Add a scoped stylesheet giving :focus-visible a clear 2px ring in the brand colour with a 2px offset on every interactive element, and remove the ring for mouse users only (:focus:not(:focus-visible)). Never use outline: none without a replacement. Also add a skip-to-content link as the first tabbable element if one is not already present; if it is present, report where. Measure: tab through /app/analytics and /app/creators and list every element that receives focus and whether it has a visible ring, computed.`],

  ["polish-contrast", `Build web/feat/polish-contrast.js: text you can read.
Measure the real contrast ratio of the muted text colours (--dim #6D6159, --faint #A0948C) against the surfaces they actually sit on (--bg #FFFFFF, --muted #F7F4F1). Compute the WCAG 2.2 ratios yourself and print them. Then add a scoped stylesheet that lifts anything below 4.5:1 for body text and below 3:1 for large text up to a passing value, WITHOUT changing the brand accent or the look of the page. Document the exact before and after ratios for each token you changed.`],

  ["polish-mobile", `Build web/feat/polish-mobile.js: a phone-sized page that works.
Below 640 px the sidebar, the tables, the KPI grids and the clip dialog all need to behave. Add scoped media queries through PeakCut.css: one column where there are two, no horizontal scrolling anywhere (a wide table scrolls inside its own box), and every tap target at least 44 by 44 CSS pixels. Do not hide information that matters; stack it instead. Measure: at 390 by 844, list every element wider than the viewport (should be zero) and every interactive element whose box is under 44 by 44.`],

  ["polish-wide", `Build web/feat/polish-wide.js: a wide screen that is not a stretched phone.
Above 1600 px the content currently stretches. Add scoped media queries that cap the reading width of prose, let the KPI row show more cards per row, and keep the charts from becoming absurdly wide. Do not centre-cap the whole app shell; cap the content inside it. Measure: at 1920 by 1080 and at 2560 by 1440, report the measured width of the main content column and the KPI card grid columns before and after.`],

  ["polish-dark", `Build web/feat/polish-dark.js: a dark screen that is readable.
The page is light-only. Add a scoped dark theme driven by @media (prefers-color-scheme: dark) that redefines the surface, line and text tokens for the content area and the menu pages. Every combination you produce must reach 4.5:1 for body text. Do not invert images, do not touch video previews, and do not change the brand accent. Measure: print the computed background and text colour of a card, a table row, an input and a hint in dark mode with their contrast ratios.`],

  ["polish-copy", `Build web/feat/polish-copy.js: one voice, plain English, everywhere.
Read the visible strings in the 47 feature files and find: em dashes, sentences over 20 words, "Something went wrong" style non-answers, exclamation marks, and any label that names a thing differently from how another page names it (for example the same concept called "clip" and "short"). You cannot edit other files, so your deliverable is a precise table in your report plus, in your own file, a small runtime pass that rewrites the worst offenders it can reach through an after hook. Every rewrite must keep the meaning. Measure: report the count of em dashes, the count of sentences over 20 words, and the list of inconsistent names.`],

  ["test-a11y", `Write peakcut/tests/test_a11y_pages.py, a plain-assert test in the house style (look at tests/test_menu_pages.py and tests/test_feat_files.py first, then copy their shape: no pytest, no external libraries, prints "All checks passed. N ok" at the end).
It must check the ACCESSIBILITY of what is actually written on disk, statically:
1. every <img> in web/index.html and web/feat/*.js has an alt attribute;
2. every <button> that contains only an icon has an aria-label or a title;
3. every <input> has a label, an aria-label, or a placeholder;
4. no element uses tabindex with a value greater than 0 in the feature files;
5. no feature file sets outline: none without also setting a replacement in the same rule;
6. every clickable element built in a feature file is a <button> or <a>, never a bare <div data-act>;
7. html lang is present in index.html.
Report the real counts per rule. Where a rule legitimately has an exception, encode the exception in the test with a comment naming why, never by deleting the check.`],
];

const script = `const HEAD = args.head;
const BUILD = args.build;
const out = [];

phase("build");
const built = await parallel(BUILD.map(([slug, task]) => async () => {
  try {
    const answer = await agent(
      HEAD + "\\n\\nYOUR JOB:\\n" + task + "\\n\\nWhen you are done, answer with one JSON object: {\\"slug\\":\\"" + slug + "\\",\\"file\\":\\"...\\",\\"nodeCheck\\":\\"pass\\"|\\"fail\\",\\"checks\\":\\"pass\\"|\\"fail\\",\\"measured\\":\\"one line of real numbers\\",\\"left\\":\\"one line\\"}",
      { label: slug, phase: "build" }
    );
    return { slug, ok: true, answer };
  } catch (e) {
    return { slug, ok: false, answer: String(e && e.message || e) };
  }
}));
out.push(...built.filter(Boolean));

phase("review");
let review = null;
try {
  review = await agent(
    HEAD +
    "\\n\\nYOUR JOB (you are the reviewer, read only, you own ONE file: peakcut/docs/swarm4/wave5/REVIEW.md):\\n" +
    "Review what the 16 polish agents actually wrote to disk. Do not trust their messages; open the files.\\n" +
    "For each file in peakcut/web/feat/polish-*.js and tests/test_a11y_pages.py check:\\n" +
    "1. node --check passes;\\n" +
    "2. it registers exactly one plug-in named after itself, and any handler lives in PeakCut.add not PeakCut.page;\\n" +
    "3. every interpolated server string goes through esc(;\\n" +
    "4. no !important, no shadows, no em dash, no new dependency, no web font;\\n" +
    "5. no rule that restyles the whole document (a bare html/body/* selector);\\n" +
    "6. prefers-reduced-motion is respected by anything that moves;\\n" +
    "7. no invented number, name or page;\\n" +
    "8. the claim in the agent's report matches the file.\\n" +
    "Also run cd peakcut && python tests/test_feat_files.py and record the result.\\n" +
    "Rank every problem Critical (breaks the page or loses data), Important (a person would notice and be misled), or Minor (cosmetic). For each one give the file, the line, the exact problem, and the smallest fix. Write the verdict at the top: 'Critical: none' or the count. Write it all to peakcut/docs/swarm4/wave5/REVIEW.md. Answer with JSON {\\"critical\\":n,\\"important\\":n,\\"minor\\":n,\\"checks\\":\\"pass\\"|\\"fail\\"}",
    { label: "reviewer", phase: "review" }
  );
} catch (e) {
  review = "REVIEWER FAILED: " + String(e && e.message || e);
}
out.push({ slug: "reviewer", ok: true, answer: review });

phase("fix");
let fix = null;
try {
  fix = await agent(
    HEAD +
    "\\n\\nYOUR JOB (you are the fixer, and the reviewer's file is your input):\\n" +
    "Read peakcut/docs/swarm4/wave5/REVIEW.md. If it does not exist, review the files yourself first and write it, saying at the top that the reviewer slot failed.\\n" +
    "Fix every Critical and every Important finding that can be fixed by editing the file it belongs to. You MAY edit the polish-*.js files and tests/test_a11y_pages.py for this, and only those. Never edit web/index.html or web/plugins.js: if a fix needs them, describe the exact edit in your report instead of making it.\\n" +
    "Re-run node --check on every file you touched and paste the output. Re-run cd peakcut && python tests/test_feat_files.py and confirm it passes. Then write peakcut/docs/swarm4/wave5/FIXES.md: each finding, what you did, and the proof. Say plainly what you did NOT fix and why.\\n" +
    "Answer with JSON {\\"fixed\\":n,\\"left\\":n,\\"checks\\":\\"pass\\"|\\"fail\\"}",
    { label: "fixer", phase: "fix" }
  );
} catch (e) {
  fix = "FIXER FAILED: " + String(e && e.message || e);
}
out.push({ slug: "fixer", ok: true, answer: fix });

return {
  wave: 5,
  agents: out.length,
  built: out.filter(o => o.slug !== "reviewer" && o.slug !== "fixer" && o.ok).length,
  failed: out.filter(o => !o.ok).map(o => o.slug),
  review,
  fix,
  results: out,
};
`;

return {
  head: HEAD,
  build: BUILD,
  script,
};
