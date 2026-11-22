/* One plain line under every option on the settings and menu pages, saying what changing it does.
 *
 * The Brand tab already explains most of itself, so this does not repeat it: it walks every control
 * on the page in front of you and adds a line only where the field has none. The words come from the
 * table below, keyed by the control's id, and each line answers "what happens if I change this", not
 * "what is this called". Nothing that is already written is replaced, so a second pass over the same
 * markup adds nothing at all, and a page that fails to draw leaves no trace behind.
 *
 * Settings draws into #setbody. The pages in the menu (Live, Improve, and so on) draw straight into
 * #view, so the same table serves both and a control is described wherever it appears. */
(() => {
  // The page hides every .hint on a narrow screen. These lines are the point of the page, so inside
  // the settings body they stay readable, and a line added under a checkbox row sits on its own.
  // .sx-under is a line that had to go inside a bare label. Most wrappers already stack, so a block
  // line drops under the field by itself; only a .sw row lays out sideways and needs the full width.
  window.PeakCut.css("settings-explain", `
    #setbody .hint,.set-body .hint,#view .hint{line-height:1.45}
    #setbody .sx-note,.set-body .sx-note,#view .sx-note{display:block;margin:-4px 0 10px 2px;max-width:56ch}
    #setbody .sx-under,.set-body .sx-under,#view .sx-under{display:block;margin-top:-2px;max-width:56ch}
    #setbody .sw .sx-under,.set-body .sw .sx-under,#view .sw .sx-under{flex-basis:100%}
    @media (max-width:560px){#setbody .hint,.set-body .hint,#view .hint{display:block}}
  `);

  const LINE = {
    // Brand: the look of every clip.
    br_theme: "Starts every colour below from one ready-made look. Colours you change after it stay.",
    br_style: "The biggest single change to the look: how the words move and where they sit.",
    br_font: "Swaps the font the style ships with. Blank keeps the style's own font.",
    br_c_text: "The colour of words that have not been said yet.",
    br_c_spoken: "The colour of the word being said right now.",
    br_c_outline: "The edge drawn behind every word. A dark edge keeps words readable on bright footage.",
    br_c_key: "The colour of a keyword Clipstorm thinks is worth shouting.",
    br_c_box: "The block behind the spoken word. Set it to the text colour to hide the block.",
    br_hook_text: "The colour of the hook line at the top of the clip.",
    br_hook_box: "The bar under the hook line. The text colour hides the bar.",
    br_position: "Where the hook line sits. Wherever the speaker is moves it off faces by itself.",
    br_watermark: "Puts a handle or a logo on every clip. Blank leaves the clip clean.",
    br_watermark_color: "The colour of a typed handle. A PNG logo keeps its own colours.",
    br_watermark_pos: "Where the handle sits. Moves around drifts it slowly, so it is harder to crop out.",
    br_watermark_opacity: "How solid the watermark is. Under 0.3 it is hard to see on a phone.",
    br_watermark_size: "How big it is against the 1080 width. 0.2 is a fifth of the frame.",
    br_progress: "Adds a thin bar along the bottom, so a viewer can see how much is left.",
    br_progress_color: "The colour of that bar.",
    br_endcard: "A last card carrying these words. Blank ends the clip on the footage.",
    br_lang: "Picks a font that can draw these letters. It changes the font, not the words.",
    br_fillers: "Drops um, uh and like from the captions, so a line reads tighter.",
    br_emoji: "Puts an emoji above a keyword. Off keeps the frame clean.",
    br_denoise: "Cleans background hiss before the loudness pass. Slower, and clearer.",
    br_blackfix: "Holds the last frame over a game-over flash instead of cutting to black.",
    br_lift: "Brightens very dark footage, so faces and game panels can be seen.",
    br_flash: "A quick white flash at the punch-in. Off is calmer.",
    br_flip: "Swaps the camera and the game panel in a stacked layout.",

    // AI: which service answers, and with what.
    ai_provider: "Which service answers. The key and the model below belong to the one picked here.",
    ai_key: "The key for that service. It stays on this server and is never shown again.",
    ai_base: "The address a custom service answers on. The named services do not need it.",
    ai_model: "The model asked first. A second one after a comma is used when the first fails.",

    // Transcription: where speech becomes text.
    tr_provider: "Local does the work on this machine and costs nothing. Logfare sends the audio away and is faster.",
    tr_key: "Your Logfare key. It stays on this server and goes to Logfare only.",
    tr_model: "Which speech model reads the audio. The faster ones drop more words.",
    tr_proxy: "Sends the speech calls through a relay you run yourself. Off unless you have one.",

    // Storage: where files live.
    stor_new: "Where the new folder goes. Type the full path, or press Browse.",
    stor_move: "Also copies what is already here into the new folder. Off starts an empty one.",

    // Security, apps and the tools tab.
    pw_cur: "Proves the change is you. Nothing happens if this is wrong.",
    pw_new: "At least 8 characters. Changing it signs you out on every other device.",
    app_id: "The client ID from the app you made on the platform's page.",
    app_secret: "The client secret from that same app. It stays on this server.",
    z_key: "One key for sixteen networks instead of four setups. Kept in this app's folder.",
    tl_platform: "The site the channel posts on. It decides where the rules are read from.",
    tl_handle: "The channel name on that site, without the at sign.",
    tl_wplatform: "The site the channel streams on.",
    tl_wident: "The channel name on that site. Clipstorm looks up whether it is live.",
    tl_times: "Times on a 24 hour clock, separated by commas. Each one becomes a line in the command.",
    tl_os: "The command syntax to write. Leave it alone unless you run the command elsewhere.",
    tl_video: "The full address of a video you own. Nothing is changed on YouTube.",
    tl_key: "Your own YouTube key. It goes to YouTube and nowhere else.",

    // Menu pages. These draw straight into #view, with no #setbody around them, so the same table
    // has to carry them or a control there gets no line at all.

    // Improve: what the learning pass is allowed to touch.
    lrn_days: "How far back the numbers go. A short window reacts fast; a long one is harder to fool.",
    la_target: "The first setting to change. Clipstorm runs it alone, so the next numbers show what it did.",
    la_value: "The value to try for that first setting, in the same words the field would take.",
    la_other: "The second setting, run after the first. Two changes at once would be impossible to read.",
    la_other_value: "The value to try for that second setting. Both values are saved as you type.",

    // Live: which channel to watch.
    pclive_platform: "The site the channel streams on. It decides which address Clipstorm asks.",
    pclive_ident: "The name in the channel's address, without the at sign or a full link.",
  };

  // Walk the controls, not the wrappers, so a field nested inside a .with row is still found.
  function explain(body) {
    for (const el of body.querySelectorAll("input[id], select[id], textarea[id]")) {
      const line = LINE[el.id];
      if (!line) continue;
      const lab = el.closest("label") || el.parentElement;
      if (!lab || lab.dataset.sxNote === "1") continue;
      // The page's own line wins, and so does a toggle's own caption.
      if (lab.querySelector(".hint") || lab.querySelector("small")) continue;
      lab.dataset.sxNote = "1";

      const note = document.createElement("span");
      note.className = "hint";
      note.textContent = line;      // text, never markup, so nothing here can inject anything

      if (lab.classList.contains("sw")) {
        // A toggle keeps its words beside the switch, in the same small style it already uses.
        const words = lab.querySelector("span");
        if (words) { const small = document.createElement("small"); small.textContent = line; words.append(small); }
        else { note.classList.add("sx-under"); lab.append(note); }   // a picker row, so its own line
      } else if (lab.classList.contains("ck")) {
        // A checkbox pill cannot hold a second line, so the line sits under it.
        note.classList.add("sx-note");
        lab.after(note);
      } else {
        // label.f already stacks its children, so the line lands under the field by itself. Every
        // other shape (a bare label, or a wrapping div holding a label and its field) lays out in a
        // row, and a plain span would be squeezed in beside the control: give it the full width.
        if (!lab.classList.contains("f")) note.classList.add("sx-under");
        lab.append(note);
      }
    }
  }

  // Settings draws into #setbody. A page in the menu draws the same form straight into its own box, which
  // has no such id, so whichever of the two is on screen is the one walked.
  const body = () => document.getElementById("setbody") || document.querySelector("#view .set-body, #view");

  // Switching tabs replaces #setbody outright, and a few panels (Storage's "Change folder") arrive on a
  // click with no render event at all, so a hook that only fires on a redraw would step over them.
  // Watching the settings box instead catches every one: it outlives the tab switches, and the body is
  // looked up again on each change so a replaced body is still described. A pass that finds everything
  // already described adds nothing, which is what keeps this quiet.
  let watching = null;
  function watchBox() {
    // #sform is Settings. #view is everything else, and pages replace its contents on every redraw.
    for (const box of [document.getElementById("sform"), document.getElementById("view")]) {
      if (!box || box === watching || box.dataset.sxWatch === "1") continue;
      box.dataset.sxWatch = "1";
      if (!watching) watching = box;
      try {
        new MutationObserver(() => {
          const el = body();
          if (el) { try { explain(el); } catch (e) {} }
        }).observe(box, { childList: true, subtree: true });
      } catch (e) { /* an older browser still gets the hook path */ }
    }
  }

  window.PeakCut.add("settings-explain", {
    after: {
      /** Runs whenever Settings is (re)drawn, on every tab, once the body markup is in the page. */
      drawSettings(root) {
        const inside = root && root.querySelector
          ? (root.querySelector("#setbody") || root.querySelector(".set-body") || root)
          : null;
        const el = inside || body();
        if (!el) return;
        try { explain(el); } catch (e) { /* a settings page that will not describe itself still works */ }
        watchBox();
      },
    },
  });
})();
