/* One button on the home page: make ten clips from the newest video of the creator in front of you.
 *
 * PeakCut has no route that lists a channel's uploads (the only one, /api/stats/channel, needs a personal
 * YouTube API key), so this asks for the newest video's link in one small line instead of guessing an
 * address. The link is checked with /api/preview, which returns the real title, and that title is what the
 * confirm names. Nothing is sent to /api/jobs before that confirm comes back yes.
 *
 * The overview is repainted by the page itself, so the card is put back when it is missing and every value
 * lives in `M` below: a redraw never takes away a half-typed link. */
(() => {
  const PC = window.PeakCut;
  const CLIPS = 10;

  PC.css("day", `
    .day{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:14px 16px;margin-bottom:16px;
      border:1px solid var(--brand-line);border-radius:var(--r);
      /* Dark warm ground, both stops from the palette. The light cream gradient this replaced was left over
         from when the page was white and made the help sentence and the status line unreadable where the
         ground went light: the card's inks measure 1.03 to 2.65:1 on #FFF9F4 and #FFF7F0. On the lightest
         point of this ground (var(--brand-soft), top-left) the same inks measure 15.25:1 under --text,
         6.59:1 under --dim and 6.01:1 under --bad, all above the 4.5:1 floor for 13 to 14px text. */
      background:radial-gradient(130% 190% at 0% 0%,var(--brand-soft) 0%,var(--brand-ink) 100%)}
    .day-sun{flex:none;width:34px;height:34px;border-radius:50%;background:var(--bg);border:1px solid var(--brand-line);
      display:grid;place-items:center;color:var(--brand-deep)}
    .day-sun svg{width:19px;height:19px}
    .day-help{flex:1 1 260px;min-width:0;font-size:14px;line-height:1.45;color:var(--text)}
    .day-help b{font-weight:600}
    .day .day-who{width:auto;height:28px;padding:0 8px;font-size:13px;font-weight:600;color:var(--text);
      background:var(--bg);border:1px solid var(--brand-line);border-radius:8px;vertical-align:baseline}
    .day-act{display:flex;align-items:center;gap:8px;margin-left:auto}
    .day-url{width:300px;max-width:100%;height:38px}
    .day-note{flex-basis:100%;font-size:13px;line-height:1.4;color:var(--dim)}
    .day-note:empty{display:none}
    .day-note.bad{color:var(--bad)}
    @media (max-width:680px){.day-act{width:100%;margin-left:0}.day-url{flex:1 1 auto;width:auto}}
  `);

  // What the person typed or picked, kept here so a repaint of the overview does not throw it away.
  const M = { typed: "", open: false, picked: "", memo: "", bad: false, busy: false };
  let LIST = [];          // creators that have a channel, as of the last paint

  const mmss = (s) => {
    s = Math.max(0, Math.round(Number(s) || 0));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), q = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(q).padStart(2, "0")}`
             : `${m}:${String(q).padStart(2, "0")}`;
  };
  const nameOf = (c) => (c && c.name ? String(c.name) : "this creator");

  // "At least one creator with a channel": `channels` is the current shape, `channel` the older one.
  function withChannel(state) {
    const all = (state && state.creators) || [];
    return all.filter((c) => {
      if (!c || !c.id) return false;
      const ch = c.channels || {};
      return Object.keys(ch).some((k) => ch[k]) || !!c.channel;
    });
  }

  function markup(list) {
    const who = list.length === 1
      ? `<b>${esc(nameOf(list[0]))}</b>`
      : `<select class="day-who" aria-label="Whose video is this?">${list.map((c) =>
            `<option value="${esc(c.id)}">${esc(nameOf(c))}</option>`).join("")}</select>`;
    return `<section class="day" aria-label="Make my day">
      <span class="day-sun" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.7" stroke-linecap="round"><path d="M3.5 17.5h17"/><path d="M7.6 17.5a4.4 4.4 0 0 1 8.8 0"/>
        <path d="M12 5.4v2.3"/><path d="M5.9 8.6l1.6 1.6"/><path d="M18.1 8.6l-1.6 1.6"/></svg></span>
      <p class="day-help">Ten clips from the newest video of ${who}.</p>
      <div class="day-act">
        <input class="day-url" type="url" inputmode="url" autocomplete="off" spellcheck="false"
          aria-label="Newest video link" placeholder="Paste the newest video link" hidden>
        <button class="btn primary day-go" type="button">Make my day</button>
      </div>
      <p class="day-note" role="status" aria-live="polite"></p>
    </section>`;
  }

  // One owner of every value on screen, so the card is never half updated.
  function sync(card) {
    if (!card) return;
    const sel = card.querySelector(".day-who");
    if (sel) {
      const want = M.picked || (LIST[0] && LIST[0].id) || "";
      if (want && sel.value !== String(want)) sel.value = String(want);
    }
    const input = card.querySelector(".day-url");
    if (input) {
      if (input.value !== M.typed) input.value = M.typed;
      input.hidden = !M.open;
    }
    const btn = card.querySelector(".day-go");
    if (btn) btn.disabled = !!M.busy;
    const note = card.querySelector(".day-note");
    if (note) {
      if (note.textContent !== M.memo) note.textContent = M.memo;
      note.className = "day-note" + (M.bad ? " bad" : "");
    }
  }

  function live() { return document.querySelector("#ov .day"); }
  function say(text, bad) { M.memo = String(text || ""); M.bad = !!bad; sync(live()); }

  function mount(card) {
    const input = card.querySelector(".day-url");
    const sel = card.querySelector(".day-who");
    card.querySelector(".day-go").addEventListener("click", () => run(card));
    if (sel) sel.addEventListener("change", () => { M.picked = sel.value; });
    if (input) {
      input.addEventListener("input", () => { M.typed = input.value; });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); run(card); }
      });
    }
  }

  // The page's own dialog, which returns true or false when it is closed. A real window.confirm only when that
  // dialog cannot be reached: a feature file must still work if the page's helpers ever move.
  async function confirm2(title, text) {
    const own = window.ask;
    if (typeof own === "function") {
      try { return await own(title, text, "Make them"); } catch { /* fall through */ }
    }
    return window.confirm(title + " " + text);
  }

  function chosen(card) {
    const sel = card.querySelector(".day-who");
    const id = sel ? sel.value : (M.picked || (LIST[0] && LIST[0].id));
    return LIST.find((c) => String(c.id) === String(id)) || LIST[0] || null;
  }

  async function run(card) {
    if (M.busy) return;
    const creator = chosen(card);
    if (!creator) { say("Add a creator with a channel first.", true); return; }
    const input = card.querySelector(".day-url");
    const url = ((input && input.value) || "").trim();
    if (!url) {
      // The first press asks for the one thing PeakCut cannot read on its own.
      M.open = true; sync(card);
      if (input) input.focus();
      say(`Paste the newest video link from ${nameOf(creator)}. Ten clips are made from it.`);
      return;
    }
    if (!/^https?:\/\//i.test(url)) { say("That should be a full link, starting with https://", true); return; }

    M.busy = true; sync(card);
    try {
      say("Looking that link up.");
      let p;
      try {
        p = await PC.api("/api/preview?url=" + encodeURIComponent(url));
      } catch (e) {
        say(String((e && e.message) || e || "That link could not be read."), true);
        return;
      }
      if (p && p.is_live) {
        say("That link is live right now. Add the creator and press Start recording to clip a stream.", true);
        return;
      }
      const title = (p && p.title) || url;
      const length = p && Number(p.duration) > 0 ? ` The video is ${mmss(p.duration)} long.` : "";
      const ok = await confirm2("Make my day?",
        `Ten clips from "${title}" for ${nameOf(creator)}.${length}`);
      if (!ok) { say("Nothing was started."); return; }

      await PC.send("/api/jobs", { url, options: { max_clips: CLIPS }, creator: creator.id });
      M.typed = ""; M.open = false; sync(card);
      say(`Ten clips from "${title}" are being made.`);
      try { PC.toast(`Making ten clips from "${title}".`, "ok"); } catch { /* nothing to say */ }
    } catch (e) {
      say(String((e && e.message) || e || "The job did not start."), true);
    } finally {
      M.busy = false; sync(card);
    }
  }

  PC.add("day", {
    after: {
      /** Runs whenever the home view is drawn. Puts the band back if it is missing, otherwise only syncs it. */
      drawOverview(root) {
        if (!root) return;
        const state = PC.state && PC.state();
        const list = withChannel(state);
        const card = root.querySelector(".day");
        if (!list.length) {
          if (card) card.remove();
          LIST = [];
          return;
        }
        LIST = list;
        if (M.picked && !list.some((c) => String(c.id) === String(M.picked))) M.picked = "";
        if (list.length < 2) M.picked = "";
        // The picker is rebuilt only when the set of creators really changed, so typing is never disturbed.
        const sig = list.map((c) => `${c.id}:${nameOf(c)}`).join("|") + (list.length > 1 ? "|multi" : "|one");
        if (card && card.dataset.day === sig) { sync(card); return; }
        // The band sits above the tiles. #ov is empty for a moment while /api/overview loads, so the band is
        // drawn again on the next paint rather than being lost with the rest of the children.
        if (card) card.remove();
        root.insertAdjacentHTML("afterbegin", markup(list));
        const fresh = root.querySelector(".day");
        if (!fresh) return;
        fresh.dataset.day = sig;
        mount(fresh);
        sync(fresh);
      },
    },
  });
})();
