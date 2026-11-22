/* Creators: every streamer PeakCut works for, one card each.
 *
 * A creator is the workspace, not the person: their channels, clip rules, connected accounts and folder all hang
 * off one creator. The home page can only ever show a list of names, so this page gives each one its own card and
 * says the four things you actually came to check - where they post, which accounts are attached, what track they
 * are on, and how much PeakCut has cut for them.
 *
 * Every value below arrived from a route that exists: GET /api/creators (the creator itself, its channels, its
 * account ids), GET /api/accounts (so an account id can be shown as a name) and GET /api/overview (clips_total,
 * the only place a clip count is sent). Nothing is counted here by hand and no placeholder row is drawn: when a
 * number did not arrive, the card says which number is missing and why. */
(() => {
  const P = window.PeakCut;

  P.css("creators", `
    .cr{max-width:1000px}
    .cr-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--text);margin:0 0 6px}
    .cr-lede{margin:0 0 18px;max-width:64ch;color:var(--dim);font-size:13px;line-height:1.55}
    .cr-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 4px}
    .cr-bar .grow{flex:1 1 auto}
    .cr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px;margin:14px 0 0;padding:0;list-style:none}
    .cr-card{display:flex;flex-direction:column;gap:11px;padding:15px 16px 14px;border:1px solid var(--line);
      border-radius:var(--r);background:var(--bg);min-width:0;transition:border-color .15s ease}
    .cr-card:hover{border-color:var(--brand-line)}
    .cr-top{display:flex;align-items:center;gap:10px;min-width:0}
    .cr-av{flex:0 0 auto;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;overflow:hidden;
      background:var(--brand-soft);color:var(--brand-deep);font-size:15px;font-weight:600;line-height:1}
    .cr-av img{width:100%;height:100%;object-fit:cover;display:block}
    .cr-who{min-width:0;display:flex;flex-direction:column;gap:2px}
    .cr-name{font-size:14px;font-weight:600;color:var(--text);overflow-wrap:anywhere;line-height:1.3}
    .cr-handle{font-size:12px;color:var(--faint);overflow-wrap:anywhere;line-height:1.35}
    .cr-live{margin-left:auto;flex:0 0 auto}
    .cr-rows{display:grid;gap:7px;margin:0}
    .cr-row{display:grid;grid-template-columns:74px minmax(0,1fr);gap:8px;align-items:start}
    .cr-k{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);padding-top:2px}
    .cr-v{margin:0;font-size:13px;line-height:1.5;color:var(--text);overflow-wrap:anywhere;min-width:0}
    .cr-v.mute{color:var(--faint)}
    .cr-at{color:var(--dim);overflow-wrap:anywhere}
    .cr-v b{font-weight:600;color:var(--text)}
    .cr-v.cr-also{font-size:13px;color:var(--dim);margin-top:-1px}
    .cr-vs{min-width:0;display:grid;gap:2px}
    .cr-vs .cr-v{margin:0}
    .cr-miss{display:inline-block;font-size:12px;color:var(--faint);line-height:1.5}
    .cr-chans{display:flex;flex-wrap:wrap;gap:6px;min-width:0}
    .cr-chip{display:inline-flex;align-items:baseline;gap:5px;flex:0 0 auto;max-width:100%;padding:2px 9px;
      border:1px solid var(--line-2);border-radius:99px;background:var(--muted);font-size:12px;color:var(--dim);
      line-height:1.55;white-space:normal;overflow-wrap:anywhere}
    .cr-chip b{font-weight:600;color:var(--text);min-width:0;overflow-wrap:anywhere}
    .cr-chip i{font-style:normal;font-size:11px;color:var(--faint);flex:0 0 auto}
    .cr-chip.txt{align-self:flex-start}
    .cr-chip.main{border-color:var(--brand-line);background:var(--brand-soft);color:var(--brand-deep)}
    .cr-chip.main b{color:var(--brand-deep)}
    .cr-chip.txt{white-space:normal;text-overflow:clip;font-size:12px;color:var(--faint)}
    .cr-acts{display:flex;gap:7px;flex-wrap:wrap;margin-top:auto;padding-top:3px}
    .cr-empty{padding:20px 16px;border:1px dashed var(--line-2);border-radius:var(--r-sm);background:var(--muted)}
    .cr-empty p{margin:0 0 8px;max-width:62ch}
    .cr-empty p:last-child{margin-bottom:0}
    .cr-wait{margin:0;padding:16px 2px;font-size:13px;color:var(--faint)}
    .cr-foot{margin:16px 0 0;font-size:12px;color:var(--faint);max-width:70ch;line-height:1.55}
    .cr .btn:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
    @media (max-width:560px){
      .cr-h{font-size:20px}
      .cr-grid{grid-template-columns:1fr}
      .cr-row{grid-template-columns:1fr;gap:2px}
      .cr-k{padding-top:0}
    }
  `);

  // A number the server sent, or null. null means "no number", never zero.
  const num = (v) => {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const count = (n) => (n === null ? "" : n.toLocaleString());

  const at = (id) => document.getElementById(id);
  const PLATNAME = { youtube: "YouTube", twitch: "Twitch", kick: "Kick" };

  const sentence = (err, fallback) => {
    const text = err && err.message ? String(err.message) : "";
    return text.trim() || fallback;
  };

  // "https://www.youtube.com/@name" and "https://twitch.tv/name" both end in the name people recognise.
  function handleOf(url) {
    const raw = String(url || "").trim();
    if (!raw) return "";
    const tail = raw.replace(/[?#].*$/, "").replace(/\/+$/, "").split("/").pop() || raw;
    return tail.replace(/^@/, "");
  }

  // The creator's picture when the server has one for the channel it records from; otherwise the first letter.
  function face(c) {
    const who = String(c.name || "?").trim();
    const letter = esc((who[0] || "?").toUpperCase());
    const prof = c.profile;
    const has = prof && prof.pic && prof.channel && prof.channel === c.channel && c.id;
    if (!has) return `<span class="cr-av" aria-hidden="true">${letter}</span>`;
    const src = `/api/creators/${encodeURIComponent(c.id)}/avatar?v=${Math.round(Number(prof.at) || 0)}`;
    return `<span class="cr-av"><img src="${esc(src)}" alt="" loading="lazy"></span>`;
  }

  // What is on screen right now. Kept between redraws so pressing Reload does not blank the list first.
  let rows = [];
  let counts = new Map();      // creator id -> clips_total, from /api/overview
  let accounts = new Map();    // account id -> {label, name}, from /api/accounts
  let note = "";               // a sentence about a part that could not be read
  let failed = false;          // the creator list itself did not arrive, so "none yet" would be a guess
  let loaded = false;

  function chips(c) {
    const chs = c.channels && typeof c.channels === "object" ? c.channels : {};
    const keys = Object.keys(chs).filter((k) => chs[k]);
    if (!keys.length) {
      return `<p class="cr-v mute">No channel connected yet</p>`;
    }
    // The one it records from is a sentence, because it is the one that matters; the rest follow as words.
    const key = keys.find((k) => chs[k] === c.channel);
    const from = key
      ? `<p class="cr-v">Records from <b>${esc(PLATNAME[key] || key)}</b> <span class="cr-at">@${esc(handleOf(chs[key]))}</span></p>`
      : "";
    const rest = keys.filter((k) => k !== key);
    // One channel per line: the value column is narrow, so a second handle gets its own line, not a long wrap.
    const also = rest.map((k) =>
      `<p class="cr-v cr-also">${from ? "Also " : "Linked "}<b>${esc(PLATNAME[k] || k)}</b> <span class="cr-at">@${esc(handleOf(chs[k]))}</span></p>`).join("");
    // One box, so every line stays inside the value column instead of wrapping into the label strip.
    return `<div class="cr-vs">${from}${also}</div>`;
  }

  function accountLine(c) {
    const ids = Array.isArray(c.accounts) ? c.accounts.filter(Boolean) : [];
    if (!ids.length) return `<p class="cr-v mute">No accounts picked, so nothing is posted for them</p>`;
    const named = ids.map((id) => {
      const row = accounts.get(String(id));
      if (!row) return `<span class="cr-miss" title="This account is no longer in the connected apps list">one account is no longer connected</span>`;
      const label = String(row.label || row.platform || "Account");
      const name = String(row.name || "").trim();
      return `<span class="cr-chip" title="${esc(name ? `${label} ${name}` : label)}"><i>${esc(label)}</i><b>${esc(name || "unnamed")}</b></span>`;
    });
    return `<div class="cr-chans">${named.join("")}</div>`;
  }

  function trackLine(c) {
    // No route stores a track yet, so this is only ever what the creator file itself carries.
    const t = c.track === null || c.track === undefined ? "" : String(c.track).trim();
    return t ? `<p class="cr-v">${esc(t)}</p>` : `<p class="cr-v mute">Not set</p>`;
  }

  function clipsLine(c) {
    const n = num(counts.get(String(c.id)));
    if (n === null) return `<p class="cr-v mute">Not known yet</p>`;
    return `<p class="cr-v">${esc(count(n))} clip${n === 1 ? "" : "s"} made</p>`;
  }

  function card(c) {
    const id = String(c.id || "");
    const name = String(c.name || "").trim() || "Untitled creator";
    // The handle under the name is the one it records from; the Channels row spells out which platform that is.
    const main = handleOf(c.channel);
    const handle = main ? `@${main}` : "";
    const live = c.live_job ? `<span class="pill live cr-live">Recording</span>` : "";
    return `<li class="cr-card">
      <div class="cr-top">${face(c)}
        <div class="cr-who"><span class="cr-name">${esc(name)}</span>
          <span class="cr-handle">${esc(handle || "No channel linked")}</span></div>
        ${live}</div>
      <div class="cr-rows">
        <div class="cr-row"><span class="cr-k">Channels</span>${chips(c)}</div>
        <div class="cr-row"><span class="cr-k">Accounts</span>${accountLine(c)}</div>
        <div class="cr-row"><span class="cr-k">Track</span>${trackLine(c)}</div>
        <div class="cr-row"><span class="cr-k">Clips</span>${clipsLine(c)}</div>
      </div>
      <div class="cr-acts">
        <button class="btn sm" data-act="go" data-v="c:${esc(id)}" data-tab="setup">${ic("cog")}Setup</button>
        <button class="btn sm" data-act="go" data-v="c:${esc(id)}" data-tab="clips">${ic("film")}Clips</button>
      </div>
    </li>`;
  }

  function paintEmpty() {
    const box = at("cr_list");
    if (!box) return;
    box.innerHTML = `<div class="cr-empty">
      <p class="help">No creators yet.</p>
      <p class="hint">A creator is one streamer's own workspace: the channels Clipstorm watches for them, the rules
        it cuts with, the accounts their clips are posted to, and the folder their files are kept in. Two streamers
        means two creators, and nothing is shared between them.</p>
      <div class="row"><button class="btn primary" data-act="newcreator">${ic("plusc")}New creator</button></div>
      <p class="hint" style="margin-top:8px">Opens the New creator box. Paste their channel link and Clipstorm fills
        in the name for you.</p>
    </div>`;
  }

  function paint() {
    const box = at("cr_list");
    if (!box) return;
    const line = at("cr_count");
    if (line) line.textContent = rows.length ? `${count(rows.length)} creator${rows.length === 1 ? "" : "s"}` : "";
    const err = at("cr_err");
    if (err) err.innerHTML = note ? `<p class="err">${esc(note)}</p>` : "";
    if (!loaded) return;                        // first paint happens when the answers are in
    if (!rows.length) {
      // A list that could not be read is not an empty list: say so instead of inviting a second workspace.
      if (failed) {
        box.innerHTML = `<div class="cr-empty">
          <p class="help">Your creators could not be read just now.</p>
          <p class="hint">The page asked and did not get an answer. Press Refresh in a moment. Nothing has been
            lost: the creators are still on the server.</p>
          <div class="row"><button class="btn" data-act="creators_reload">${ic("arrowr")}Try again</button></div>
        </div>`;
        return;
      }
      paintEmpty();
      return;
    }
    box.innerHTML = `<ul class="cr-grid">${rows.map(card).join("")}</ul>`;
  }

  async function load() {
    const box = at("cr_list");
    if (box && !rows.length) {
      box.innerHTML = `<p class="cr-wait">Reading your creators.</p>`;
    }
    // Three routes, all of them live. One failing must not hide the others, so each is allowed to answer null.
    const [list, over, accs] = await Promise.all([
      P.api("/api/creators").catch((err) => ({ __err: sentence(err, "The creator list could not be read.") })),
      P.api("/api/overview").catch(() => null),
      P.api("/api/accounts").catch(() => null),
    ]);
    note = "";
    failed = !Array.isArray(list);
    if (Array.isArray(list)) {
      rows = list;
    } else {
      rows = [];
      note = (list && list.__err) || "The creator list could not be read.";
    }
    counts = new Map();
    if (over && Array.isArray(over.creators)) {
      for (const r of over.creators) counts.set(String(r.id), r.clips_total);
    } else if (rows.length && !note) {
      note = "How many clips each creator has made could not be read, so that number is missing from the cards.";
    }
    accounts = new Map();
    if (accs && Array.isArray(accs)) {
      for (const a of accs) accounts.set(String(a.id), a);
    } else if (rows.some((c) => Array.isArray(c.accounts) && c.accounts.length)) {
      note = note || "The connected accounts could not be read, so some account names are missing.";
    }
    loaded = true;
    paint();
    if (!rows.length && note) P.toast(note, "bad");
  }

  P.page("creators", {
    nav: "Creators",
    icon: "user",
    tip: "Every streamer, their channels and the accounts they post to",
    path: "creators",
    group: "Make",
    order: 10,
    view() {
      return `<div class="cr">
        <section class="set-sec">
          <h1 class="cr-h">Creators</h1>
          <p class="cr-lede">Each creator is one streamer's workspace. Everything Clipstorm makes for them - the
            clips, the rules, the accounts they are posted to - belongs to that creator and nobody else.</p>
          <div class="cr-bar">
            <button class="btn primary" data-act="newcreator">${ic("plusc")}New creator</button>
            <span class="grow"></span>
            <button class="btn ghost sm" data-act="creators_reload">Refresh</button>
          </div>
          <p class="hint">New creator asks for their channel link once and sets up the workspace. Refresh reads the
            list again - nothing is saved by looking.</p>
          <p class="hint" id="cr_count"></p>
        </section>
        <div id="cr_list" role="status" aria-live="polite"></div>
        <div id="cr_err"></div>
        <p class="cr-foot">Setup opens that creator's own page: their channels, clip rules and connected accounts.
          Clips shows what Clipstorm has cut for them. Clipstorm does not keep a track (gaming, IRL, music) for a
          creator yet, so that row stays empty on every card until the server stores one.</p>
      </div>`;
    },
    load() {
      return load();
    },
  });

  P.add("creators", {
    about: "The Creators page: one card per streamer, with their channels, accounts, track and clip count.",
    pages: ["creators"],
    act: {
      creators_reload() {
        return load();
      },
    },
  });
})();
