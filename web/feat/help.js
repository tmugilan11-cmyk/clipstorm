/* Help, as its own row in the main menu: the questions a first-run person actually asks, each folded into a
 * <details> so the page stays short, and each answer ending where the setting really lives.
 *
 * This page calls no route and shows no numbers. Everything it says is a sentence about how PeakCut already
 * behaves, taken from the code that behaves that way: creators.autopost and post_min_score plus REVIEW_FIRST in
 * studio/posting.py, the five setting names in studio/learn.py, usage.brief() counting tokens and never money,
 * and jobs.delete() removing a job's folder with its clips. A help page that guessed a price would be worse than
 * no help page, so there is no price and no count anywhere below.
 *
 * The links are plain anchors, so they work with no script at all. The one listener here turns a click into
 * go() only when the target page is already registered, which keeps the address bar and a reload in step; if the
 * page is missing it lets the browser load the address instead of quietly landing on the home page.
 */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  P.css("help", `
    .hlp{max-width:700px}
    .hlp-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--text);margin-bottom:8px}
    .hlp-lede{max-width:60ch;margin:0 0 4px}
    .hlp-open{display:block;margin:10px 0 0}

    .hlp-list{margin:22px 0 0;border-top:1px solid var(--line)}
    .hlp-item{border-bottom:1px solid var(--line)}
    .hlp-item>summary{display:grid;grid-template-columns:1fr auto;align-items:start;gap:14px;
      padding:17px 0;cursor:pointer;list-style:none}
    .hlp-item>summary::-webkit-details-marker{display:none}
    .hlp-item>summary::marker{content:""}
    .hlp-q{font-size:15px;line-height:1.45;font-weight:600;color:var(--text);margin:0;text-wrap:balance}
    .hlp-item>summary:hover .hlp-q{color:var(--brand-deep)}
    .hlp-car{width:15px;height:15px;margin-top:2px;color:var(--faint);transition:transform .18s ease,color .18s ease}
    .hlp-item[open]>summary .hlp-car{transform:rotate(180deg);color:var(--brand-deep)}
    .hlp-item[open]>summary{padding-bottom:12px}

    .hlp-a{border-left:2px solid var(--brand-line);padding:0 0 20px 16px;margin-left:1px}
    .hlp-a p{max-width:60ch;font-size:14px;line-height:1.68;color:var(--dim)}
    .hlp-where{margin-top:14px;display:flex;flex-direction:column;align-items:flex-start;gap:0}
    .hlp-where .btn{text-decoration:none}
    .hlp-hint{display:block;margin:7px 0 0;max-width:52ch;line-height:1.5}

    .hlp-foot{margin-top:24px;max-width:60ch}

    @media (max-width:560px){
      .hlp-h{font-size:20px}
      .hlp-a{padding-left:12px}
      /* The frame hides every .hint on a phone. These are the sentences that say where to go, so they stay. */
      .hlp-hint{display:block}
    }
  `);

  // The page's own caret, so the fold looks like the rest of the app. An older shell without ic() still works.
  const car = () => (typeof ic === "function" ? ic("caret") : "");

  /** One folded question. `href` is the page that holds the setting the answer can only point at. */
  const item = (q, answer, href, label, hint) => `<details class="hlp-item">
      <summary><h2 class="hlp-q">${esc(q)}</h2><span class="hlp-car">${car()}</span></summary>
      <div class="hlp-a">
        <p>${esc(answer)}</p>
        <div class="hlp-where">
          <a class="btn" href="${esc(href)}" data-hlp-go="${esc(href)}">${esc(label)}</a>
          <span class="hint hlp-hint">${esc(hint)}</span>
        </div>
      </div>
    </details>`;

  // What the page says, in the order a first-run person asks it. Every sentence is about behaviour that already
  // exists; nothing here is a promise about a number or a future version.
  const ITEMS = [
    ["Where do clips come from?",
      "You add a video first: paste a link from YouTube, Twitch or Kick, or drop in a file. Clipstorm writes out the speech, the AI marks the moments worth keeping, and the cutter turns each of those into a short with the caption look set on Brand. No video means no clips, and a video that is still being read has nothing to show yet.",
      "/app/videos", "All videos",
      "Opens the page with the link box and the drop area. This is where a video is added."],

    ["Why is nothing posting?",
      "Posting has to clear four gates, and each one is quiet on purpose. A creator needs at least one connected account, auto-post has to be on for that creator, the clip has to score above that creator's own bar, and review-first means a clip waits until you approve it. There is also one switch that pauses posting for the whole account while recording and clipping carry on. Start with Connected apps: an account that was never signed in is the usual answer.",
      "/app/apps", "Connected apps",
      "Opens the page where a platform account is signed in. Nothing can be posted until an account is added here."],

    ["What does an Improve round actually change?",
      "A round reads how your clips have done and proposes changes to five settings: the caption look, the words at the top of a clip, the longest a clip may be, a sound under a clip, and whether captions are burned in every time. Each proposal is checked against the values Clipstorm will accept, so a suggestion outside them is dropped rather than applied. If your numbers do not support a change, the round says so and changes nothing, which is a real answer and not a failure. Press What would it change to get that same answer without a setting being touched.",
      "/app/improve", "Improve",
      "Opens Improve, where a round is started and every change it made is listed."],

    ["What does it cost?",
      "Clipstorm counts calls and tokens, not money. The AI service that owns the key bills you at its own rates, so a dollar figure printed here would be a guess, and this page will not print one. Usage shows what was really used, and the AI page is where the key and the model live. Improve rounds also draw on a daily allowance, and the Improve page says what is left of it.",
      "/app/ai-usage", "Usage",
      "Opens Usage: the calls, the tokens and the days, with no price guessed."],

    ["What happens to my videos?",
      "Your videos stay on this machine, in the folder shown on Storage, together with the clips cut from them. The file itself is not uploaded anywhere; what leaves is the text the AI reads, a cloud transcript if you move transcription off this machine, and each clip you choose to post. Deleting a video deletes its folder and every clip in it, so delete from the card in All videos rather than from Explorer. Storage shows the room left and is the page to open when the disk fills.",
      "/app/storage", "Storage",
      "Opens Storage: the folder, the room left, and what to delete when it runs low."],

    ["How do I make it run by itself?",
      "The Schedule page writes the exact text that puts Clipstorm on a Windows timer: one task that clips and one that runs an Improve round. You paste it into Task Scheduler yourself, or press Install on that page, which only arms on a second press. For a channel nobody is watching by hand, the Live page holds the watch list. Clipstorm cannot switch auto-cut on for a channel by itself yet.",
      "/app/schedule", "Schedule",
      "Opens Schedule: the text to paste, and Install, which needs two presses."],
  ];

  // A click on one of these links goes through go(), so the address bar, the menu and the page agree without a
  // reload. Anything unexpected falls through to the plain href, which is why the anchor carries it.
  document.addEventListener("click", (e) => {
    const a = e.target && e.target.closest ? e.target.closest("a[data-hlp-go]") : null;
    if (!a) return;
    const to = a.getAttribute("data-hlp-go") || "";
    if (!to || typeof fromPath !== "function" || typeof go !== "function") return;
    let name = "";
    try {
      const got = fromPath(to);
      name = got && got[0] ? String(got[0]) : "";
    } catch { return; }
    // fromPath answers "overview" for anything it does not know. Only take over when the page really exists,
    // otherwise let the browser load the address and say what is wrong there.
    if (!name || !P.hasPage || !P.hasPage(name)) return;
    e.preventDefault();
    go(name);
  });

  P.add("help", {
    about: "The first-run questions, folded up, each pointing at the page that holds the setting.",
  });

  P.page("help", {
    nav: "Help",
    icon: "help",
    tip: "Where clips come from, why nothing posted, and what a round changes",
    path: "help",
    group: "Help",
    order: 90,
    view() {
      return `<div class="hlp">
        <section>
          <h1 class="hlp-h">Help</h1>
          <p class="help hlp-lede">The questions people ask on the first day. Each answer ends on the page that
          holds the setting it mentions.</p>
          <span class="hint hlp-open">Press a question to open its answer. Nothing is loaded or changed by reading.</span>
        </section>
        <div class="hlp-list">${ITEMS.map((it) => item(it[0], it[1], it[2], it[3], it[4])).join("")}</div>
        <p class="help hlp-foot">This page reads nothing: not your videos, not your numbers. It only points at the
        pages that do, so nothing here can drift out of date with what is on this machine.</p>
      </div>`;
    },
  });
})();
