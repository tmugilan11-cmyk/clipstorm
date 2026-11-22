/* Mood for a clip: one word that adds a sound or music, picked before the clip is re-made.
 *
 * The server can build nine meme sounds and four music beds (studio/meme.py, studio/music.py) and lists them at
 * GET /api/moods. A mood is the one-word automatic choice: funny, fail, shock, hype, win, embarrassing, awkward,
 * cringe and suspense each add a short meme sound (and a small picture trick) at the payoff; chill and tense add music
 * under the voice. The words funny and hype also exist as music, but the meme sound wins (see _add_sound in
 * studio/jobs.py), so the cards say what really happens.
 *
 * The choice is drawn as labelled cards. Underneath them is still the plain `<select data-f="mood">` (hidden), which
 * the page's own re-make collector reads, so the pick rides the existing save path: no new request, no second copy
 * of the clip body. Pressing a card sets that select and fires its `change`, as a person choosing in it would.
 *
 * The hook fires on every repaint of `#clipdlg`, so the whole thing has to be cheap and safe to call again: it does
 * nothing when the dialog is closed or empty, and when its own row is already there it leaves the row alone rather
 * than adding a second one. The mood list is fetched once, then reused for every clip. */
(() => {
  window.PeakCut.css("mood", `
    .moodpick{display:grid;gap:8px}
    .moodpick .moodhead{margin:0;font-size:13px;line-height:1.5;color:var(--dim)}
    .moodpick .moodhead b{color:var(--text);font-size:14px}
    .moodpick .moodgroup{margin:4px 0 0;font-size:12px;font-weight:700;color:var(--text)}
    .moodpick .moodcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
    .moodpick .moodcard{display:grid;gap:3px;align-content:start;text-align:left;padding:9px 11px;border:1px solid var(--line-2);
      border-radius:var(--r-sm);background:var(--bg);color:var(--text);font:inherit;cursor:pointer;min-width:0;
      transition:border-color .15s ease,background-color .15s ease}
    .moodpick .moodcard:hover{border-color:var(--brand)}
    .moodpick .moodcard[aria-checked="true"]{border-color:var(--brand);background:var(--brand-soft)}
    .moodpick .moodcard:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
    .moodpick .moodcard b{font-size:13px;font-weight:700}
    .moodpick .moodcard[aria-checked="true"] b{color:var(--brand-deep)}
    .moodpick .moodcard span{font-size:11.5px;line-height:1.4;color:var(--dim)}
    .moodpick .moodcard em{font-style:normal;font-size:11px;color:var(--faint)}
    .moodpick .moodnote{margin:0;color:var(--dim);font-size:12px;line-height:1.5;min-height:18px}
  `);

  const MEME = "Meme sounds", MUSIC = "Music";
  const NOTE_IDLE = "Meme sounds are off. The clip keeps its own audio.";

  let moods = null;     // the rows from /api/moods, tidied; null until the first look
  let pending = null;   // one request at a time, shared by every clip dialog that opens meanwhile
  let dead = false;     // the list could not be read: stop asking, keep the page usable

  /* ---------------------------------------------------------------- the clip on screen */
  /** The clip the dialog is showing, or null. Read from the page's own state rather than from the DOM. */
  function clipNow() {
    try {
      const st = window.PeakCut.state && window.PeakCut.state();
      const d = typeof D !== "undefined" ? D : null;
      if (!st || !d || !d.jid || !d.cid) return null;
      const job = (st.jobs || []).find(j => j.id === d.jid);
      return (job && (job.clips || []).find(c => c.id === d.cid)) || null;
    } catch { return null; }
  }

  function currentName() {
    const c = clipNow();
    return c && typeof c.mood === "string" ? c.mood : "";
  }

  /* ---------------------------------------------------------------- the mood list */
  /** Fetches /api/moods once. A failure is quiet: the row keeps "No sound" and says it could not load the rest. */
  function ensure() {
    if (moods || dead) return Promise.resolve(moods);
    if (pending) return pending;
    pending = (async () => {
      try {
        const got = await window.PeakCut.api("/api/moods");
        const rows = got && Array.isArray(got.moods) ? got.moods : [];
        moods = rows.filter(r => r && r.name).map(r => ({
          name: String(r.name),
          kind: r.kind === "music" ? "music" : "meme",
          note: typeof r.note === "string" ? r.note : "",
          ready: r.ready === true,      // a row that says nothing about itself is treated as not built yet,
                                        // the same reading the Sounds page uses (web/feat/sounds.js)
        }));
      } catch {
        dead = true;                    // fail soft: no toast, no retry loop, no thrown error
      }
      pending = null;
      sync(document.getElementById("clipdlg"));
      return moods;
    })();
    return pending;
  }

  /** The first row with this name, or null. A name can exist as a meme noise and as a music bed. */
  function rowFor(name) {
    if (!moods || !name) return null;
    return moods.find(m => m.name === name) || null;
  }

  const groups = kind => (moods || []).filter(m => m.kind === kind);

  /** The option list. The empty first option is "No sound"; the two kinds are grouped; a missing file is marked. */
  function optionHtml(want) {
    let taken = false;                  // only the first name match is preselected: the value alone cannot say which kind
    const one = m => {
      const on = !taken && m.name === want;
      if (on) taken = true;
      return `<option value="${esc(m.name)}"${on ? " selected" : ""}>${esc(m.name)}${m.ready ? "" : esc(" (not built yet)")}</option>`;
    };
    const group = (kind, label) => {
      const rows = groups(kind);
      return rows.length ? `<optgroup label="${esc(label)}">${rows.map(one).join("")}</optgroup>` : "";
    };
    const none = want && rowFor(want) ? "" : " selected";
    return `<option value=""${none}>No sound</option>${group("meme", MEME)}${group("music", MUSIC)}`;
  }

  /** The plain words for a mood: the shared table in meme-timeline.js, else a general line. */
  function infoFor(row) {
    const sx = window.PeakCut.snd;
    if (sx && typeof sx.moodInfo === "function") return sx.moodInfo(row.name, row.kind);
    return row.kind === "music"
      ? ["Music mixed under the voice.", "Adds music under the voice"]
      : ["A short sound laid over the clip.", "Adds a short sound over the clip"];
  }

  const cap = n => n.charAt(0).toUpperCase() + n.slice(1);

  /** The line under the cards: what the picked mood adds, and whether its file is on disk yet. */
  function say(note, name) {
    if (!note) return;
    const row = rowFor(name);
    if (!name || !row) {
      const on = note.closest("[data-mood-pick]") && note.closest("[data-mood-pick]").querySelector("[data-mood-onoff]");
      note.textContent = on && on.checked ? "Meme sounds are on. Pick a mood above, or the clip keeps its own audio." : NOTE_IDLE;
      return;
    }
    const bits = [`${cap(row.name)}: ${infoFor(row)[0]}`];
    if (!row.ready) bits.push("Its file is not built yet. Open Sounds in the menu and press Build the missing sounds first, or the clip keeps its own audio.");
    bits.push("It is added the next time the clip is re-made.");
    note.textContent = bits.join(" ");
  }

  /** One card per mood word: the first row of a name decides its kind, because the meme sound wins over the bed. */
  function cardsHtml(want) {
    const seen = new Set();
    const list = [];
    for (const kind of ["meme", "music"]) {
      for (const m of groups(kind)) { if (!seen.has(m.name)) { seen.add(m.name); list.push(m); } }
    }
    const card = (value, title, line, extra) => {
      const on = (value === want) || (!value && !(want && rowFor(want)));
      return `<button type="button" class="moodcard" role="radio" aria-checked="${on ? "true" : "false"}" data-mood-card="${esc(value)}">`
        + `<b>${esc(title)}</b><span>${esc(line)}</span>${extra ? `<em>${esc(extra)}</em>` : ""}</button>`;
    };
    const part = (kind, heading) => {
      const mine = list.filter(m => m.kind === kind);
      if (!mine.length) return "";
      return `<p class="moodgroup">${esc(heading)}</p><div class="moodcards" role="radiogroup" aria-label="${esc(heading)}">`
        + mine.map(m => card(m.name, cap(m.name), infoFor(m)[1] + ".", m.ready ? "" : "Not built yet")).join("") + "</div>";
    };
    return `<div class="moodcards" role="radiogroup" aria-label="No mood">${card("", "No sound", "The clip keeps its own audio.", "")}</div>`
      + part("meme", MEME + " at the payoff") + part("music", MUSIC + " under the voice");
  }

  /** Redraws the cards from the select's value, so the cards and the select can never disagree. */
  function paintCards(wrap, sel) {
    const host = wrap.querySelector("[data-mood-cards]");
    if (!host || !moods) return;
    const html = cardsHtml(sel.value);
    if (host.__html !== html) { host.innerHTML = html; host.__html = html; }
    // The on/off switch follows the pick: a mood on the clip means meme sounds are on. Off hides the cards.
    const sw = wrap.querySelector("[data-mood-onoff]");
    if (sw) {
      if (sel.value) sw.checked = true;
      host.hidden = !sw.checked;
    }
  }

  /* ---------------------------------------------------------------- drawing it in */
  /** Brings a row that is already in the dialog up to date. Never adds a second one. */
  function sync(root) {
    if (!root) return;
    const sel = root.querySelector('[data-f="mood"]');
    if (!sel) return;
    const wrap = sel.closest("[data-mood-pick]") || root;
    const note = wrap.querySelector("[data-mood-note]");

    if (!moods) {
      sel.disabled = true;
      if (note) note.textContent = dead ? "The list of moods could not be read. The clip can still be re-made without one." : "Reading the moods...";
      return;
    }
    // The list arrived after the row was drawn, so fill it now. Once it is filled, leave the person's pick alone:
    // redrawing the options under an open dropdown would close it and could move the pick to the other group.
    if (sel.options.length < 2) {
      const keep = sel.value || currentName();
      sel.disabled = false;
      sel.innerHTML = optionHtml(keep);
      if (keep && rowFor(keep)) sel.value = keep;   // a name that is gone from the list falls back to "No sound"
    }
    sel.disabled = false;
    paintCards(wrap, sel);
    say(note, sel.value);
  }

  /** Puts the row at the end of the main fields, which is right before the "Post text" heading. */
  function mount(root) {
    const panel = root.querySelector(".panel");
    if (!panel) return;
    ensure();                                                   // the list may not have been asked for yet
    if (root.querySelector('[data-f="mood"]')) return sync(root);   // never a second row
    const html = `<div class="moodpick" data-mood-pick>
        <label class="sw"><input type="checkbox" data-mood-onoff>Meme sounds on this clip</label>
        <p class="moodhead">When this is on, the AI only adds a sound which properly fits the context, and prefers popular sounds. Pick a mood below to say what kind. Off means the clip keeps its own audio.</p>
        <div data-mood-cards></div>
        <select data-f="mood" data-mood-select hidden aria-hidden="true" tabindex="-1">${optionHtml(currentName())}</select>
        <p class="moodnote" data-mood-note aria-live="polite"></p>
      </div>`;
    // The rail has one tab per subject, so the sound row belongs on the Sound tab. Anchoring to the "Post text"
    // heading would now drop it on the Text tab, where nobody looking for a sound would go.
    const soundPane = panel.querySelector('.ed-pane[data-pane="sound"]');
    const postHead = Array.from(panel.querySelectorAll("h3"))
      .find(h => /^post text$/i.test((h.textContent || "").trim()));
    const remake = panel.querySelector('button[data-act="remake"]');
    if (soundPane) {
      const open = soundPane.querySelector('button[data-act="openaudio"]');
      if (open) open.insertAdjacentHTML("beforebegin", html);
      else soundPane.insertAdjacentHTML("afterbegin", html);
    } else if (postHead) postHead.insertAdjacentHTML("beforebegin", html);
    else if (remake) remake.insertAdjacentHTML("beforebegin", html);
    else panel.insertAdjacentHTML("beforeend", html);

    const sel = panel.querySelector('[data-f="mood"]');
    if (sel) {
      sel.addEventListener("change", () => {
        paintCards(sel.closest("[data-mood-pick]") || panel, sel);
        say(panel.querySelector("[data-mood-note]"), sel.value);
      });
      // A card is the visible choice: it sets the select and fires its change, so everything that listens to the
      // select (the dialog's unsaved-changes mark, the re-make collector) sees a normal pick.
      const onoff = panel.querySelector("[data-mood-onoff]");
      if (onoff) onoff.addEventListener("change", ev => {
        ev.stopPropagation();
        if (!onoff.checked && sel.value) {
          sel.value = "";
          sel.dispatchEvent(new Event("change", { bubbles: true }));
        }
        paintCards(sel.closest("[data-mood-pick]") || panel, sel);
        say(panel.querySelector("[data-mood-note]"), sel.value);
      });
      const cards = panel.querySelector("[data-mood-cards]");
      if (cards) cards.addEventListener("click", ev => {
        const b = ev.target.closest("[data-mood-card]");
        if (!b || sel.disabled) return;
        sel.value = b.getAttribute("data-mood-card");
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      });
    }
    sync(root);
  }

  /* The page only asks a feature for a redraw when the dialog's markup changes length, and it remembers the last
   * length it painted. A feature that finishes loading after the dialog was already drawn would therefore wait
   * forever for a change that never comes. So this listens for the dialog opening by itself, and does one catch-up
   * draw when it loads. One listener, added once; it does the same small job the hook does. */
  const armed = new WeakSet();
  function arm(root) {
    if (!root || armed.has(root) || !root.addEventListener) return false;
    armed.add(root);
    root.addEventListener("toggle", ev => {
      try {
        if ((ev && ev.newState === "open") || root.open) mount(root);
      } catch { /* a redraw happening right now is not worth an error on the page */ }
    });
    return true;
  }

  window.PeakCut.add("mood", {
    after: {
      /** Runs whenever the clip dialog is drawn. Adds the row once, then only keeps it current. */
      drawClipDlg(root) {
        if (!root) return;
        arm(root);                                       // harmless after the first time
        if (!root.open) return;                          // closed: nothing to draw into
        if (!root.querySelector(".panel")) return;       // opened but not filled yet
        ensure();                                        // cheap after the first call: a settled promise
        if (root.querySelector('[data-f="mood"]')) return sync(root);   // already there: update, never a second row
        mount(root);
      },
    },
  });

  /* Catch up in case the dialog was already drawn before this file finished loading. */
  try {
    const dlg = document.getElementById("clipdlg");
    if (arm(dlg) && dlg.open) mount(dlg);
  } catch { /* no dialog on this page: nothing to do */ }
})();
