/* Live: who is streaming right now, and the channels PeakCut keeps asking about.
 *
 * Two halves on one page, because they answer one question. The watch list says which channels are worth
 * asking about; the check asks one platform about one channel and writes the answer beside that channel's
 * name. Both routes already exist (studio/api_preview.py holds the routes, studio/hunt.py does the asking),
 * so nothing here is guessed: a row the server could not check keeps the server's own sentence, and a row
 * that is genuinely off air says so without ever claiming a number it was not given. */
(() => {
  window.PeakCut.css("live", `
    .pclive{max-width:820px}
    .pclive-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--text);margin:0 0 6px}
    .pclive-lede{margin:0 0 20px;max-width:62ch;color:var(--dim);font-size:13px;line-height:1.55}
    .pclive-bar{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:0 0 10px}
    .pclive-bar h2{font-size:15px;font-weight:600;color:var(--text);margin:0}
    .pclive-count{margin:0;font-size:12px;color:var(--faint)}
    .pclive-list{list-style:none;margin:0;padding:0}
    .pclive-row{position:relative;display:grid;gap:7px;padding:13px 14px 13px 17px;border-bottom:1px solid var(--line);background:var(--bg)}
    .pclive-row:first-child{border-top:1px solid var(--line)}
    .pclive-row::before{content:"";position:absolute;left:0;top:13px;bottom:13px;width:3px;border-radius:99px;background:var(--line-2)}
    .pclive-row.on::before{background:var(--live);animation:pclivepulse 2.6s ease-in-out infinite}
    @keyframes pclivepulse{0%,100%{opacity:1}50%{opacity:.4}}
    .pclive-head{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap}
    .pclive-name{font-weight:600;font-size:14px;color:var(--text);overflow-wrap:anywhere}
    .pclive-handle{font-size:12px;color:var(--faint);overflow-wrap:anywhere}
    .pclive-say{margin:0;font-size:13px;color:var(--dim);line-height:1.5;overflow-wrap:anywhere}
    .pclive-say b{color:var(--text);font-weight:600}
    .pclive-say .pill{margin-right:7px}
    .pclive-more{font-size:12px;color:var(--faint)}
    .pclive-row .row{margin-top:1px;gap:7px}
    .pclive-empty{padding:20px 16px;border:1px dashed var(--line-2);border-radius:var(--r-sm);background:var(--muted)}
    .pclive-empty p{margin:0 0 7px}
    .pclive-empty p:last-child{margin:0}
    .pclive-wait{margin:0;padding:16px 2px;font-size:13px;color:var(--faint)}
    .pclive-form{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap;margin:18px 0 0;padding-top:16px;border-top:1px solid var(--line)}
    .pclive-field{display:flex;flex-direction:column;gap:5px}
    .pclive-field label{font-size:12px;font-weight:600;color:var(--dim)}
    .pclive-field select,.pclive-field input{height:38px;padding:0 10px;border:1px solid var(--line-2);border-radius:var(--r-sm);
      background:var(--bg);color:var(--text);font:inherit;font-size:14px}
    .pclive-field input{min-width:210px}
    .pclive .btn:focus-visible,.pclive select:focus-visible,.pclive input:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
    @media (prefers-reduced-motion: reduce){.pclive-row.on::before{animation:none}}
    @media (max-width:560px){
      .pclive-h{font-size:20px}
      .pclive-field input{min-width:0;width:100%}
      .pclive-form .btn{width:100%;justify-content:center}
    }
  `);

  // The three platforms hunt.py accepts. The picker therefore cannot offer one that would come back a 400.
  const NAME = { twitch: "Twitch", kick: "Kick", youtube: "YouTube" };

  // A number the server sent, or null. Nothing is rounded or guessed: null means "this page has no number".
  const num = (v) => {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const count = (n) => (n === null ? "" : n.toLocaleString());

  // The channel key is built the way hunt.py builds its own, so one channel is one row whatever case it was typed in.
  const keyOf = (platform, ident) => String(platform || "") + ":" + String(ident || "").toLowerCase();

  // One answer per channel, kept while the page is open: redrawing the list must not throw away the answer
  // somebody just asked for.
  const answers = new Map();

  // Rows the list request returned, so a check can redraw the list without asking twice.
  let rows = [];

  const at = (id) => document.getElementById(id);

  // The platforms send a start time in different shapes. A date the browser understands is shown in local
  // time; anything else is shown exactly as it arrived, cut to a readable length.
  function since(v) {
    const raw = String(v || "").trim();
    if (!raw) return "";
    if (/\d{4}-\d{2}-\d{2}/.test(raw)) {
      const when = new Date(raw);
      if (!isNaN(when.getTime())) return when.toLocaleString();
    }
    return raw.slice(0, 40);
  }

  function clock(stamp) {
    const n = num(stamp);
    if (n === null) return "";
    const when = new Date(n * 1000);
    return isNaN(when.getTime()) ? "" : when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  /* What this row currently knows: a fresh answer from /api/hunt/live when there is one, otherwise exactly
   * what /api/hunt/watching said. `fresh` is true only for the first, so the page can say when it asked. */
  function mark(r) {
    const got = answers.get(keyOf(r.platform, r.ident));
    if (got) return Object.assign({ fresh: true }, got);
    return {
      fresh: false,
      live: !!r.live,
      title: r.title || "",
      viewers: r.viewers,
      started: r.started || "",
      error: r.error || "",
      note: "",
      checked: r.checked !== false,
    };
  }

  function said(r) {
    const m = mark(r);
    if (m.error) return `<p class="pclive-say err">${esc(m.error)}</p>`;
    if (!m.fresh && !m.checked) {
      return `<p class="pclive-say">Not checked yet. Press Look again and this fills in.</p>`;
    }
    const seen = m.fresh && clock(m.at) ? `<p class="pclive-more">Asked at ${esc(clock(m.at))}.</p>` : "";
    if (m.live) {
      const title = String(m.title || "").trim();
      const shown = title
        ? `<b>${esc(title)}</b>`
        : `The platform says they are on air but sent no title.`;
      const watchers = num(m.viewers);
      const began = since(m.started);
      const bits = [];
      if (watchers !== null) bits.push(`${esc(count(watchers))} watching`);
      if (began) bits.push(`on since ${esc(began)}`);
      return `<p class="pclive-say"><span class="pill live">On air</span>${shown}</p>`
        + (bits.length ? `<p class="pclive-say pclive-more">${bits.join(", ")}.</p>` : "")
        + seen;
    }
    const why = m.note || "Not on air.";
    return `<p class="pclive-say"><span class="pill">Off air</span>${esc(why)}</p>${seen}`;
  }

  function row(r) {
    const platform = String(r.platform || "");
    const ident = String(r.ident || "");
    const label = String(r.name || ident || "Unnamed channel");
    const m = mark(r);
    return `<li class="pclive-row${m.live ? " on" : ""}" data-key="${esc(keyOf(platform, ident))}">
      <div class="pclive-head">
        <span class="pclive-name">${esc(label)}</span>
        <span class="pill">${esc(NAME[platform] || platform)}</span>
        <span class="pclive-handle">${esc(ident)}</span>
      </div>
      ${said(r)}
      <div class="row">
        <button class="btn sm" data-act="pclive_check" data-p="${esc(platform)}" data-i="${esc(ident)}">Check now</button>
        <button class="btn sm danger" data-act="pclive_remove" data-p="${esc(platform)}" data-i="${esc(ident)}">Remove</button>
      </div>
    </li>`;
  }

  function summary() {
    const total = rows.length;
    const live = rows.filter((r) => mark(r).live).length;
    const unknown = rows.filter((r) => {
      const m = mark(r);
      return !m.fresh && (!m.checked || !!m.error);
    }).length;
    // Both counts are counted here, not sent to us, so there is nothing to be honest about beyond saying them.
    if (unknown) {
      return `${count(live)} of ${count(total)} on air. ${count(unknown)} not checked yet.`;
    }
    return `${count(live)} of ${count(total)} on air.`;
  }

  function paint() {
    const box = at("pclive_list");
    if (!box) return;
    const line = at("pclive_count");
    if (line) line.textContent = rows.length ? summary() : "";
    if (!rows.length) {
      box.innerHTML = `<div class="pclive-empty">
        <p class="help">Nobody is on the watch list yet.</p>
        <p class="hint">Add a channel below. Clipstorm then asks that platform whether the channel is streaming,
          so you can see it here without opening the site.</p>
      </div>`;
      return;
    }
    box.innerHTML = `<ul class="pclive-list">${rows.map(row).join("")}</ul>`;
  }

  function showErr(sentence) {
    const box = at("pclive_err");
    if (box) box.innerHTML = sentence ? `<p class="err">${esc(sentence)}</p>` : "";
  }

  function sentence(err, fallback) {
    const text = err && err.message ? String(err.message) : "";
    return text.trim() || fallback;
  }

  /* Reads the watch list. `quiet` keeps the current rows on screen while it asks, which is what a Remove or an
   * Add wants: the list refreshes underneath instead of flashing a loading line. */
  async function loadList(quiet) {
    const box = at("pclive_list");
    if (box && !quiet) {
      box.innerHTML = `<p class="pclive-wait">Asking each platform. A long list can take a few seconds.</p>`;
    }
    try {
      const got = await window.PeakCut.api("/api/hunt/watching");
      rows = Array.isArray(got && got.watching) ? got.watching : [];
      paint();
    } catch (err) {
      rows = [];
      if (box) {
        box.innerHTML = `<p class="err">${esc(sentence(err, "The watch list could not be read. Try Look again."))}</p>`;
      }
      const line = at("pclive_count");
      if (line) line.textContent = "";
    }
  }

  async function check(btn) {
    const platform = String(btn.dataset.p || "");
    const ident = String(btn.dataset.i || "");
    if (!platform || !ident) {
      showErr("That row does not say which channel to ask about. Press Look again.");
      return;
    }
    // The route requires both query parameters; a missing one is a 422, so they are always both sent.
    const path = "/api/hunt/live?platform=" + encodeURIComponent(platform)
      + "&ident=" + encodeURIComponent(ident);
    btn.disabled = true;
    try {
      const got = await window.PeakCut.api(path);
      answers.set(keyOf(platform, ident), {
        at: num(got && got.looked_at),
        live: !!(got && got.live),
        title: (got && got.title) || "",
        viewers: got && got.viewers,
        started: (got && got.started) || "",
        note: (got && got.note) || "",
        error: "",
        checked: true,
      });
      showErr("");
      paint();
    } catch (err) {
      // One sentence, shown beside the channel it is about. Nothing else is claimed about that channel.
      answers.set(keyOf(platform, ident), {
        live: false, title: "", viewers: null, started: "", note: "", checked: true,
        error: sentence(err, "That platform could not be asked just now."),
      });
      paint();
    } finally {
      btn.disabled = false;
    }
  }

  async function remove(btn) {
    const platform = String(btn.dataset.p || "");
    const ident = String(btn.dataset.i || "");
    if (!platform || !ident) {
      showErr("That row does not say which channel to remove. Press Look again.");
      return;
    }
    btn.disabled = true;
    try {
      const got = await window.PeakCut.send("/api/hunt/unwatch", { platform: platform, ident: ident });
      answers.delete(keyOf(platform, ident));
      showErr("");
      window.PeakCut.toast(got && got.removed === false
        ? "That channel was not on the watch list any more."
        : "Removed from the watch list.", got && got.removed === false ? "bad" : "ok");
      await loadList(true);
    } catch (err) {
      showErr(sentence(err, "That channel could not be removed."));
    } finally {
      btn.disabled = false;
    }
  }

  async function add() {
    const picker = at("pclive_platform");
    const kind = at("pclive_ident");
    const platform = picker ? String(picker.value || "") : "";
    const ident = kind ? String(kind.value || "").trim() : "";
    if (!NAME[platform]) {
      showErr("Pick the platform that channel is on.");
      return;
    }
    if (!ident) {
      showErr("Type the channel name first.");
      return;
    }
    const button = at("pclive_addbtn");
    if (button) button.disabled = true;
    try {
      const got = await window.PeakCut.send("/api/hunt/watch", { platform: platform, ident: ident });
      if (kind) kind.value = "";
      showErr("");
      window.PeakCut.toast("Added " + String((got && got.name) || ident) + " to the watch list.", "ok");
      await loadList(true);
    } catch (err) {
      // The route answers 400 with a sentence a person can act on, so it is shown as it arrived.
      showErr(sentence(err, "That channel could not be added."));
    } finally {
      if (button) button.disabled = false;
    }
  }

  /* ---- the recordings: start, stop, watch ------------------------------------------------------------
   * Everything here is read from the jobs the page already keeps (the page asks /api/sync by itself, faster
   * while something is recording). This file only reads that list from memory every few seconds and redraws
   * when something changed, so it adds no requests of its own. */
  window.PeakCut.css("live-rec", `
    .pcrec-top{margin:0 0 22px;padding:18px;border:1px solid var(--brand-line);border-radius:var(--r-lg);background:var(--brand-soft)}
    .pcrec-top h2{font-size:17px;margin:0 0 4px;color:var(--text)}
    .pcrec-top p{margin:0 0 12px;font-size:13px;color:var(--dim);line-height:1.5}
    .pcrec-start{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap}
    .pcrec-start select{height:46px;min-width:230px;padding:0 10px;border:1px solid var(--line-2);border-radius:var(--r-sm);background:var(--bg);color:var(--text);font:inherit;font-size:15px}
    .pcrec-big{height:46px;padding:0 26px;font-size:16px;font-weight:600}
    .pcrec-ctl{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 10px}
    .pcrec-ctl:last-child{margin:0}
    .pcrec-ctl .nm{flex:1 1 180px;font-weight:600;color:var(--text);overflow-wrap:anywhere}
    .pcrec-card{margin:0 0 18px;padding:16px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--bg)}
    .pcrec-card.on{border-color:var(--brand-line)}
    .pcrec-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 4px}
    .pcrec-head b{font-size:15px;color:var(--text);overflow-wrap:anywhere}
    .pcrec-state{margin:0 0 12px;font-size:14px;color:var(--text);line-height:1.5}
    .pcrec-rail{height:8px;border-radius:99px;background:var(--line);overflow:hidden}
    .pcrec-rail i{display:block;height:100%;background:var(--brand)}
    .pcrec-prog{margin:0 0 12px}
    .pcrec-prog p{margin:6px 0 0;font-size:12.5px;color:var(--dim)}
    .pcrec-facts{display:flex;gap:8px 22px;flex-wrap:wrap;margin:0 0 12px;font-size:13px;color:var(--dim)}
    .pcrec-facts b{color:var(--text);font-weight:600}
    .pcrec-lvl{display:block;width:100%;max-width:420px;height:34px;margin:0 0 4px}
    .pcrec-lvl rect{fill:var(--brand)}
    .pcrec-cap{margin:0 0 12px;font-size:12px;color:var(--faint)}
    .pcrec-sub{margin:12px 0 5px;font-size:12px;font-weight:600;color:var(--dim)}
    .pcrec-lines,.pcrec-why{margin:0;padding:0 0 0 16px;font-size:13px;color:var(--dim);line-height:1.55}
    .pcrec-lines li,.pcrec-why li{overflow-wrap:anywhere}
    .pcrec-why b{color:var(--text);font-weight:600}
    .pcrec-err{margin:12px 0 0;padding:10px 12px;border:1px solid var(--bad);border-radius:var(--r-sm);background:var(--bad-soft);color:var(--bad);font-size:13px;line-height:1.5}
    .pcrec-clips{display:flex;gap:10px;overflow-x:auto;padding:2px 0 8px}
    .pcrec-clip{flex:0 0 150px;display:grid;gap:5px;text-align:left;padding:0;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--muted);color:var(--text);font:inherit;cursor:pointer;overflow:hidden;transition:border-color .18s ease}
    .pcrec-clip:hover{border-color:var(--brand-line)}
    .pcrec-clip .pic{display:flex;align-items:center;justify-content:center;aspect-ratio:9/16;max-height:190px;width:100%;background:var(--line);color:var(--dim);font-size:12px;text-align:center;padding:6px;box-sizing:border-box}
    .pcrec-clip img{display:block;width:100%;height:100%;object-fit:cover;max-height:190px}
    .pcrec-clip .tx{padding:0 8px 8px;display:grid;gap:3px;font-size:12px;color:var(--dim)}
    .pcrec-clip .tx b{font-size:13px;color:var(--text);overflow-wrap:anywhere}
    .pcrec-steps{margin:0;padding:0 0 0 20px;font-size:14px;color:var(--text);line-height:1.7}
    .pcrec-top .pcrec-steps{color:var(--dim)}
    .pcrec .btn:focus-visible,.pcrec select:focus-visible{outline:2px solid var(--brand-deep);outline-offset:2px}
  `);

  // h:mm:ss, the same way everywhere on this page. Only called with a number the server sent.
  const clock3 = (s) => {
    s = Math.max(0, Math.round(Number(s) || 0));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), q = s % 60;
    return h + ":" + String(m).padStart(2, "0") + ":" + String(q).padStart(2, "0");
  };
  // "2 h 40 min" for a gap in the stream, so a long wait reads as a wait.
  const gap = (s) => {
    s = Math.max(0, Math.round(Number(s) || 0));
    if (s < 60) return s + " s";
    const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
    return h ? h + " h " + m + " min" : m + " min";
  };

  const stateOf = () => { try { return window.PeakCut.state() || {}; } catch (e) { return {}; } };
  const liveJobs = () => {
    const s = stateOf();
    const all = Array.isArray(s.jobs) ? s.jobs : [];
    const mine = all.filter((j) => j && String(j.kind || "") === "live");
    const on = mine.filter((j) => j.status === "live");
    const off = mine.filter((j) => j.status !== "live").sort((a, b) => (Number(b.created) || 0) - (Number(a.created) || 0)).slice(0, 2);
    return { on: on, shown: on.concat(off) };
  };
  const nameOf = (j) => String(j.title || (j.source && j.source.name) || "A stream");

  function statusWords(j) {
    if (j.status === "error") return "Stopped with a problem.";
    if (j.status !== "live") return String(j.stage || "Stopped.");
    const behind = Number(j.behind);
    if (Number.isFinite(behind) && behind >= 30) return "Catching up: " + gap(behind) + " behind live.";
    if (/connect/i.test(String(j.stage || ""))) return "Connecting to the stream.";
    return "Recording live.";
  }

  function verdictLine(v) {
    const t = Number(v && v.t);
    const when = Number.isFinite(t) ? clock3(t) : "";
    const what = String((v && (v.result || v.trigger)) || "").trim() || "Checked, no result was sent";
    return `<li>${when ? `<b>${esc(when)}</b> - ` : ""}${esc(what)}</li>`;
  }

  function strip(level) {
    const pts = Array.isArray(level) ? level.filter((n) => Number.isFinite(Number(n))).map(Number) : [];
    if (!pts.length) return "";
    const w = 4;
    const bars = pts.map((lv, i) => {
      const h = Math.max(1, Math.round(Math.min(1, Math.max(0, (lv + 60) / 60)) * 32));
      return `<rect x="${i * w}" y="${34 - h}" width="3" height="${h}" rx="1"></rect>`;
    }).join("");
    return `<svg class="pcrec-lvl" viewBox="0 0 ${pts.length * w} 34" preserveAspectRatio="none" role="img" aria-label="How loud the last minute was">${bars}</svg>
      <p class="pcrec-cap">How loud the last minute was.</p>`;
  }

  function clipCard(j, c) {
    const done = c.status === "done" && c.cover;
    const pic = done
      ? `<img src="/media/${esc(j.id)}/${esc(c.cover)}?v=${esc(c.version)}" alt="" loading="lazy">`
      : c.status === "error" ? "Could not make this clip. Open it to try again."
      : c.status === "rendering" ? "Making this clip" : "Waiting its turn";
    const score = Number(c.score);
    const len = Math.round(Number(c.end) - Number(c.start));
    const bits = [];
    if (Number.isFinite(score) && score > 0) bits.push("Score " + score);
    if (Number.isFinite(len) && len > 0) bits.push(len + " s");
    return `<button type="button" class="pcrec-clip" data-act="openclip" data-j="${esc(j.id)}" data-c="${esc(c.id)}" aria-label="${esc("Open clip: " + (c.title || c.hook || "clip"))}">
      <span class="pic">${pic}</span>
      <span class="tx"><b>${esc(c.hook || c.title || "Untitled clip")}</b><span>${esc(bits.join(", "))}</span></span>
    </button>`;
  }

  function monitor(j) {
    const on = j.status === "live";
    const lv = j.live || {};
    const dur = Number(j.duration), heard = Number(j.heard_to);
    const haveBar = Number.isFinite(dur) && dur > 0 && Number.isFinite(heard);
    const pct = haveBar ? Math.max(0, Math.min(100, (heard / dur) * 100)) : 0;
    const behind = Number(j.behind);
    const facts = [];
    if (on && Number.isFinite(behind)) facts.push(`Behind live: <b>${esc(gap(behind))}</b>`);
    if (lv.words !== null && lv.words !== undefined && Number.isFinite(Number(lv.words))) facts.push(`Words heard: <b>${esc(Number(lv.words).toLocaleString())}</b>`);
    const clips = Array.isArray(j.clips) ? j.clips.slice().sort((a, b) => (Number(b.start) || 0) - (Number(a.start) || 0)) : [];
    facts.push(`Clips made: <b>${clips.length}</b>`);
    const lines = Array.isArray(lv.lines) ? lv.lines.slice(-3).reverse() : [];
    const verdicts = Array.isArray(lv.verdicts) ? lv.verdicts.slice(0, 3) : [];
    const err = j.error
      ? `<p class="pcrec-err">${esc(String(j.error))} What to do: press Start recording again. If it keeps happening, check the creator's channel link.</p>` : "";
    return `<section class="pcrec-card${on ? " on" : ""}" data-job="${esc(j.id)}">
      <div class="pcrec-head"><span class="pill${on ? " live" : ""}">${esc(on ? "Recording" : j.status === "error" ? "Problem" : "Stopped")}</span><b>${esc(nameOf(j))}</b></div>
      <p class="pcrec-state">${esc(statusWords(j))}</p>
      ${haveBar ? `<div class="pcrec-prog"><div class="pcrec-rail" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"><i style="width:${pct.toFixed(1)}%"></i></div>
        <p>Listened to <b>${esc(clock3(heard))}</b> of ${esc(clock3(dur))}</p></div>` : ""}
      <div class="pcrec-facts">${facts.map((f) => `<span>${f}</span>`).join("")}</div>
      ${on ? strip(lv.level) : ""}
      ${lines.length ? `<p class="pcrec-sub">What was just said</p><ul class="pcrec-lines">${lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : ""}
      ${verdicts.length ? `<p class="pcrec-sub">What the AI decided</p><ul class="pcrec-why">${verdicts.map(verdictLine).join("")}</ul>` : ""}
      ${err}
      ${clips.length ? `<p class="pcrec-sub">Clips from this recording, newest first</p><div class="pcrec-clips">${clips.map((c) => clipCard(j, c)).join("")}</div>` : ""}
    </section>`;
  }

  let chosen = "";            // the creator picked in the box, kept across redraws
  let lastTop = "", lastMon = "";

  function topHtml(on) {
    if (on.length) {
      return `<h2>Recording now</h2><p>Stop it when the stream ends, or press a clip button to keep the last moments right away.</p>
        ${on.map((j) => `<div class="pcrec-ctl"><span class="nm">${esc(nameOf(j))}</span>
          <button class="btn pcrec-big danger" data-act="pclive_stop" data-j="${esc(j.id)}">Stop</button>
          <button class="btn" data-act="pclive_clip" data-j="${esc(j.id)}" data-s="30">Clip the last 30 s</button>
          <button class="btn" data-act="pclive_clip" data-j="${esc(j.id)}" data-s="60">Clip the last 60 s</button></div>`).join("")}`;
    }
    const people = Array.isArray(stateOf().creators) ? stateOf().creators : [];
    if (!people.length) {
      return `<h2>Record a stream</h2><p>There is nobody to record yet. Add a creator first:</p>
        <ol class="pcrec-steps"><li>Add a creator with their channel link.</li><li>Press Start recording here.</li><li>Clips appear on this page while the stream runs.</li></ol>`;
    }
    if (!people.some((c) => String(c.id) === chosen)) chosen = String(people[0].id);
    const opts = people.map((c) => `<option value="${esc(c.id)}"${String(c.id) === chosen ? " selected" : ""}>${esc(c.name || c.id)}</option>`).join("");
    return `<h2>Record a stream</h2><p>Pick a creator and press Start. A stream that is already running is recorded from its first minute and caught up on.</p>
      <div class="pcrec-start"><select id="pclive_creator" aria-label="Creator to record">${opts}</select>
      <button class="btn primary pcrec-big" id="pclive_startbtn" data-act="pclive_start">Start recording</button></div>`;
  }

  function paintRec() {
    const top = at("pclive_top"), box = at("pclive_rec");
    if (!top || !box) return;
    const { on, shown } = liveJobs();
    const sel = at("pclive_creator");
    if (sel && sel.value) chosen = String(sel.value);
    const a = topHtml(on);
    // The box a person is choosing from is only rewritten when the list of creators or recordings changed.
    if (a !== lastTop) { lastTop = a; top.innerHTML = a; }
    const b = shown.length
      ? shown.map(monitor).join("")
      : `<div class="pclive-empty"><p class="help">How live recording works</p>
          <ol class="pcrec-steps"><li>Add a creator with their channel link.</li><li>Press Start recording above.</li>
          <li>Clips appear here while the stream runs. A stream that was already running is recorded from its first minute and caught up on.</li></ol></div>`;
    if (b !== lastMon) { lastMon = b; box.innerHTML = b; }
  }

  function recErr(text) {
    const box = at("pclive_recerr");
    if (box) box.innerHTML = text ? `<p class="err">${esc(text)}</p>` : "";
  }

  async function startRec() {
    const sel = at("pclive_creator");
    const cid = sel ? String(sel.value || "") : "";
    if (!cid) { recErr("Pick the creator to record first."); return; }
    const btn = at("pclive_startbtn");
    if (btn) { btn.disabled = true; btn.textContent = "Starting"; }
    try {
      const job = await window.PeakCut.send("/api/creators/" + encodeURIComponent(cid) + "/live", {});
      recErr("");
      window.PeakCut.toast("Recording " + String((job && job.title) || "the stream") + ".", "ok");
    } catch (err) {
      recErr(sentence(err, "That recording could not start. Check the creator is on air and their channel link is set."));
    } finally {
      lastTop = ""; paintRec();
    }
  }

  async function stopRec(btn) {
    const jid = String(btn.dataset.j || "");
    if (!jid) { recErr("That button does not say which recording to stop. Reload the page."); return; }
    btn.disabled = true;
    try {
      await window.PeakCut.send("/api/live/" + encodeURIComponent(jid) + "/stop", {});
      recErr("");
      window.PeakCut.toast("Recording stopped. The clips are cut from what was kept.", "ok");
    } catch (err) {
      recErr(sentence(err, "That recording could not be stopped just now."));
      btn.disabled = false;
    }
  }

  async function clipRec(btn) {
    const jid = String(btn.dataset.j || "");
    const secs = Number(btn.dataset.s) || 30;
    if (!jid) { recErr("That button does not say which recording to clip. Reload the page."); return; }
    btn.disabled = true;
    try {
      await window.PeakCut.send("/api/live/" + encodeURIComponent(jid) + "/clip", { seconds: secs });
      recErr("");
      window.PeakCut.toast("Clipping the last " + secs + " seconds.", "ok");
    } catch (err) {
      recErr(sentence(err, "That recording could not take a clip just now."));
    } finally {
      btn.disabled = false;
    }
  }

  // Reads the jobs the page already holds in memory. No request is made here: the page itself asks the server
  // (every 2 seconds while something records), and this only redraws when what it was handed has changed.
  let recTimer = 0;
  function watchRec() {
    if (recTimer) return;
    recTimer = setInterval(() => { if (at("pclive_rec")) paintRec(); else { clearInterval(recTimer); recTimer = 0; } }, 2500);
  }

  window.PeakCut.page("live", {
    nav: "Live",
    icon: "video",
    tip: "Record a stream, watch what it is doing, and see its clips",
    path: "live",
    group: "Make",
    order: 14,
    view() {
      const options = Object.keys(NAME)
        .map((k) => `<option value="${esc(k)}">${esc(NAME[k])}</option>`)
        .join("");
      return `<div class="pclive pcrec">
        <section class="set-sec">
          <h1 class="pclive-h">Live</h1>
          <p class="pclive-lede">Record a stream while it runs, watch what Clipstorm hears and decides, and get
            clips as they happen.</p>
          <div class="pcrec-top" id="pclive_top"></div>
          <div id="pclive_recerr"></div>
          <div id="pclive_rec" role="status" aria-live="polite"></div>
        </section>
        <section class="set-sec">
          <div class="pclive-bar">
            <h2>Channels Clipstorm watches</h2>
            <p class="pclive-count" id="pclive_count"></p>
          </div>
          <div id="pclive_list" role="status" aria-live="polite"></div>
          <p class="hint">Check now asks one platform about that one channel and shows the stream title if they
            are on air. Remove takes the channel off this list, not off the platform.</p>
          <div class="row" style="margin-top:10px">
            <button class="btn" data-act="pclive_look">Look again</button>
          </div>
          <p class="hint">Asks every platform on this list again. Nothing is saved by looking.</p>
          <div class="pclive-form">
            <div class="pclive-field">
              <label for="pclive_platform">Platform</label>
              <select id="pclive_platform">${options}</select>
            </div>
            <div class="pclive-field">
              <label for="pclive_ident">Channel name</label>
              <input id="pclive_ident" autocomplete="off" spellcheck="false" placeholder="shroud">
            </div>
            <button class="btn primary" id="pclive_addbtn" data-act="pclive_add">Add to the watch list</button>
          </div>
          <p class="hint">The name in the channel's address, for example shroud for twitch.tv/shroud. Letters,
            digits, dots, hyphens and underscores only.</p>
          <div id="pclive_err"></div>
        </section>
      </div>`;
    },
    load() {
      // Enter in the channel box adds the channel, because typing a name and then reaching for a button is a
      // longer way to do the same thing. Bound once per visit: the box is rebuilt with the page.
      const kind = at("pclive_ident");
      if (kind && kind.dataset.pcBound !== "1") {
        kind.dataset.pcBound = "1";
        kind.addEventListener("keydown", (e) => {
          if (e.key === "Enter") { e.preventDefault(); add(); }
        });
      }
      showErr("");
      lastTop = ""; lastMon = "";
      paintRec();
      watchRec();
      return loadList(false);
    },
  });

  // The buttons live on the plug-in, not on the page: web/plugins.js routes every [data-act] click through the
  // feature objects it registered with add(), so an act map on a page object would never be consulted.
  window.PeakCut.add("live", {
    about: "The Live page: who is streaming now, and the watch list behind it.",
    act: {
      pclive_start() { return startRec(); },
      pclive_stop(el) { return stopRec(el); },
      pclive_clip(el) { return clipRec(el); },
      pclive_look() {
        showErr("");
        return loadList(false);
      },
      pclive_check(el) {
        return check(el);
      },
      pclive_remove(el) {
        return remove(el);
      },
      pclive_add() {
        return add();
      },
    },
  });
})();
