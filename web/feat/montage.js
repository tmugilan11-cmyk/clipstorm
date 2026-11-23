/* Montages: one Short made of several moments of one video (a countdown, Strike 1-2-3, Then vs Now, a Callback),
 * and the Chat clip type, whose lines the person types because Clipstorm never keeps what chat wrote.
 *
 * The server does the work (studio/api_montage.py). This page only asks, then shows the finished videos. Every word
 * that came from the server or from a video is escaped before it is drawn. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.page !== "function") return;

  P.css("montage", `
    .mt{max-width:1040px}
    .mt-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--ink);margin:0 0 6px}
    .mt .help{max-width:64ch;margin:0}
    .mt-sec{margin-top:22px;border-top:1px solid var(--line);padding-top:16px}
    .mt-sub{margin:0 0 8px;font-size:15px;font-weight:600;color:var(--ink)}
    .mt-hint{margin:0 0 10px;font-size:13px;line-height:1.5;color:var(--dim);max-width:64ch}
    .mt-types{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
    .mt-type{display:flex;flex-direction:column;gap:4px;text-align:left;padding:12px 13px;border:1px solid var(--line);
      border-radius:var(--r-sm);background:var(--bg);color:var(--ink);cursor:pointer;transition:border-color .14s ease}
    .mt-type:hover{border-color:var(--line-2)}
    .mt-type[aria-pressed="true"]{border-color:var(--brand);background:var(--brand-soft)}
    .mt-type b{font-size:14px;font-weight:600}
    .mt-type span{font-size:12.5px;line-height:1.45;color:var(--dim)}
    .mt-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:0 0 10px}
    .mt-row label{font-size:13px;color:var(--ink)}
    .mt select,.mt input[type=text]{min-height:34px;padding:0 10px;border:1px solid var(--line);border-radius:var(--r-sm);
      background:var(--bg);color:var(--ink);font:inherit;font-size:13px}
    .mt input[type=text]{width:min(100%,340px)}
    .mt-clips{display:grid;gap:6px;margin:8px 0 0;max-height:340px;overflow:auto}
    .mt-clip{display:flex;gap:10px;align-items:flex-start;padding:8px 10px;border:1px solid var(--line);
      border-radius:var(--r-sm);background:var(--bg);font-size:13px;line-height:1.4;cursor:pointer}
    .mt-clip:hover{border-color:var(--line-2)}
    .mt-clip input{margin-top:3px;flex:none}
    .mt-clip em{font-style:normal;color:var(--dim)}
    .mt-status{min-height:20px;margin:8px 0 0;font-size:13px;color:var(--dim)}
    .mt-status[data-k="bad"]{color:var(--ink);font-weight:600}
    .mt-results{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;margin-top:10px}
    .mt-res{display:flex;flex-direction:column;gap:6px;min-width:0}
    .mt-res video,.mt-res .mt-wait{width:100%;aspect-ratio:9/16;max-height:420px;border-radius:var(--r-sm);
      border:1px solid var(--line);background:var(--muted);object-fit:contain}
    .mt-res .mt-wait{display:grid;place-items:center;padding:10px;text-align:center;font-size:12.5px;color:var(--dim)}
    .mt-res h3{margin:0;font-size:13.5px;font-weight:600;color:var(--ink)}
    .mt-res p{margin:0;font-size:12.5px;line-height:1.4;color:var(--dim)}
    .mt-chat{display:grid;gap:6px;max-width:420px}
    .mt-chat input[type=text]{width:100%}
    @media (max-width:560px){.mt-h{font-size:20px}.mt-types{grid-template-columns:1fr}}
  `);

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const why = (err, what) => (err && err.message ? `${what}: ${err.message}` : `${what}.`);
  const mmss = (s) => {
    s = Math.max(0, Math.round(Number(s) || 0));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), q = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(q).padStart(2, "0")}` : `${m}:${String(q).padStart(2, "0")}`;
  };

  // What the page remembers between visits. The markup is drawn fresh each time, so everything is painted from this.
  const st = { jid: "", shape: "", mode: "best", count: 0, picked: [], hook: "", types: null, typesWhy: "",
    made: {}, status: "", statusKind: "", sending: false, chatClip: "", chat: ["", "", "", "", ""], timer: 0 };

  const state = () => { try { return P.state() || {}; } catch { return {}; } };
  const jobsWithClips = () => (state().jobs || []).filter((j) => Array.isArray(j.clips) && j.clips.length >= 2);
  const jobNow = () => (state().jobs || []).find((j) => j.id === st.jid) || null;
  const typeNow = () => (st.types || []).find((t) => t.id === st.shape) || null;
  const root = () => document.getElementById("mt_root");

  function paintStatus() {
    const box = document.getElementById("mt_status");
    if (!box) return;
    box.textContent = st.status;
    box.dataset.k = st.statusKind;
  }

  function resultCard(m) {
    const base = `/api/montage/${encodeURIComponent(st.jid)}/${encodeURIComponent(m.id)}`;
    let body;
    if (m.status === "done") {
      body = `<video controls preload="metadata" playsinline poster="${esc(base)}/cover.jpg" src="${esc(base)}/video.mp4"></video>`;
    } else if (m.status === "error") {
      body = `<div class="mt-wait">${esc(m.error || "It could not be made.")}</div>`;
    } else {
      body = `<div class="mt-wait">${esc(m.stage || "Making it")}...</div>`;
    }
    const facts = m.status === "done"
      ? `${esc(mmss(m.length))} long, ${esc(String((m.parts || []).length))} moments` : "";
    const notes = (m.notes || []).map((n) => `<p>${esc(n)}</p>`).join("");
    const gone = m.status === "queued" || m.status === "making" ? "" :
      `<button class="btn sm" type="button" data-m="drop" data-id="${esc(m.id)}">Delete</button>`;
    return `<article class="mt-res">${body}<h3>${esc(m.label || m.format)}${m.hook ? `: ${esc(m.hook)}` : ""}</h3>
      ${facts ? `<p>${facts}</p>` : ""}${notes}${gone}</article>`;
  }

  function momentList(job, type) {
    const clips = (job.clips || []).filter((c) => c.status !== "error");
    if (!clips.length) return `<p class="mt-hint">This video has no clips to use.</p>`;
    const items = clips.slice().sort((a, b) => (b.score || 0) - (a.score || 0)).map((c) => {
      const on = st.picked.includes(c.id) ? " checked" : "";
      return `<label class="mt-clip"><input type="checkbox" data-m="pick" value="${esc(c.id)}"${on}>
        <span><b>${esc(c.hook || c.title || c.id)}</b><br><em>score ${esc(String(c.score ?? "?"))}, ${esc(mmss(c.start))} to
        ${esc(mmss(c.end))}</em></span></label>`;
    });
    return `<div class="mt-clips">${items.join("")}</div>`;
  }

  function paint() {
    const box = root();
    if (!box) return;
    const jobs = jobsWithClips();
    if (st.jid && !jobs.some((j) => j.id === st.jid)) st.jid = "";
    if (!st.jid && jobs.length) st.jid = jobs[0].id;
    const job = jobNow();
    if (st.types === null) {
      box.innerHTML = `<p class="mt-hint">Loading montage types...</p>`;
      return;
    }
    if (!st.types.length) {
      box.innerHTML = `<p class="mt-hint">${esc(st.typesWhy || "This Clipstorm offers no montage types.")}</p>`;
      return;
    }
    if (!st.shape) st.shape = st.types[0].id;
    const type = typeNow();
    const lo = type ? type.min_parts : 2, hi = type ? type.max_parts : 2;
    if (!st.count || st.count < lo || st.count > hi) st.count = lo;
    if (!jobs.length) {
      box.innerHTML = `<p class="mt-hint">A montage needs a video with at least two clips. Make clips from a video first,
        then come back here.</p>${chatSection(null)}`;
      return;
    }
    const jobOpts = jobs.map((j) => `<option value="${esc(j.id)}"${j.id === st.jid ? " selected" : ""}>${esc(j.title || j.id)}
      (${j.clips.length} clips)</option>`).join("");
    const typeBtns = st.types.map((t) => `<button class="mt-type" type="button" data-m="kind" data-id="${esc(t.id)}"
      aria-pressed="${t.id === st.shape}"><b>${esc(t.label)}</b><span>${esc(t.line)}</span>
      <span>Takes ${t.min_parts === t.max_parts ? t.min_parts : `${t.min_parts} to ${t.max_parts}`} moments.</span></button>`).join("");
    const counts = [];
    for (let n = lo; n <= hi; n++) counts.push(`<option value="${n}"${n === st.count ? " selected" : ""}>${n}</option>`);
    const best = st.mode === "best";
    const made = (st.made[st.jid] || []).map(resultCard).join("");
    box.innerHTML = `
      <section class="mt-sec"><h2 class="mt-sub">1. Pick a video</h2>
        <div class="mt-row"><select data-m="job" aria-label="Video">${jobOpts}</select></div></section>
      <section class="mt-sec"><h2 class="mt-sub">2. Pick a type</h2><div class="mt-types">${typeBtns}</div></section>
      <section class="mt-sec"><h2 class="mt-sub">3. Pick the moments</h2>
        <p class="mt-hint">Moments are this video's own clips. Clipstorm keeps the total within the longest clip length
          set for this video, shortening each moment if it has to.</p>
        <div class="mt-row">
          <label><input type="radio" name="mt_mode" data-m="mode" value="best"${best ? " checked" : ""}> Use the best clips</label>
          ${hi > lo ? `<label>How many <select data-m="count">${counts.join("")}</select></label>` : ""}
          <label><input type="radio" name="mt_mode" data-m="mode" value="pick"${best ? "" : " checked"}> I will choose</label></div>
        ${best ? "" : momentList(job, type)}</section>
      <section class="mt-sec"><h2 class="mt-sub">4. A heading (optional)</h2>
        <div class="mt-row"><input type="text" data-m="hook" maxlength="60" value="${esc(st.hook)}"
          placeholder="Leave empty for a plain one" aria-label="Heading"></div>
        <button class="btn primary" type="button" data-m="make"${st.sending ? " disabled" : ""}>Make montage</button>
        <p class="mt-status" id="mt_status" role="status"></p></section>
      <section class="mt-sec"><h2 class="mt-sub">Made from this video</h2>
        ${made ? `<div class="mt-results">${made}</div>` : `<p class="mt-hint">Nothing yet.</p>`}</section>
      ${chatSection(job)}`;
    paintStatus();
  }

  function chatSection(job) {
    if (!job) return "";
    const clips = (job.clips || []).filter((c) => c.status === "done");
    if (!clips.length) return "";
    if (!st.chatClip || !clips.some((c) => c.id === st.chatClip)) st.chatClip = clips[0].id;
    const opts = clips.map((c) => `<option value="${esc(c.id)}"${c.id === st.chatClip ? " selected" : ""}>${esc(c.hook || c.id)}</option>`).join("");
    const lines = st.chat.map((t, i) => `<input type="text" data-m="chatline" data-i="${i}" maxlength="40" value="${esc(t)}"
      placeholder="Chat line ${i + 1}" aria-label="Chat line ${i + 1}">`).join("");
    return `<section class="mt-sec"><h2 class="mt-sub">Chat clip: lines popping up after the big moment</h2>
      <p class="mt-hint">Clipstorm only counts how busy a stream's chat was. It does not keep what chat wrote, so the lines
        are yours to type, up to five. They pop up one after another right after the clip's biggest moment. Pressing the
        button makes that one clip again as a Chat clip.</p>
      <div class="mt-row"><select data-m="chatclip" aria-label="Clip">${opts}</select></div>
      <div class="mt-chat">${lines}</div>
      <p><button class="btn" type="button" data-m="chatgo">Make this clip with chat lines</button></p></section>`;
  }

  /* ---- talking to the server ------------------------------------------- */
  function loadTypes() {
    if (st.types !== null) return Promise.resolve();
    return Promise.resolve().then(() => P.api("/api/montage/types")).then((j) => {
      st.types = (j && Array.isArray(j.types) ? j.types : []).filter((t) => t && t.id).map((t) => ({
        id: String(t.id), label: String(t.label || t.id), line: String(t.line || ""),
        min_parts: Math.max(2, Number(t.min_parts) || 2), max_parts: Math.max(2, Number(t.max_parts) || 2),
        ready: t.state === "montage" }));
      st.types = st.types.filter((t) => t.ready);
      if (!st.types.length) st.typesWhy = "Montages are not available in this Clipstorm.";
    }).catch((err) => { st.types = []; st.typesWhy = why(err, "The montage types could not be read"); });
  }

  function loadMade() {
    const jid = st.jid;
    if (!jid) return Promise.resolve();
    return Promise.resolve().then(() => P.api(`/api/montage/${encodeURIComponent(jid)}`)).then((j) => {
      st.made[jid] = j && Array.isArray(j.montages) ? j.montages : [];
    }).catch(() => { st.made[jid] = st.made[jid] || []; }).then(() => {
      // A person typing in a box must not lose their place to the redraw that follows each check.
      const typing = document.activeElement && root() && root().contains(document.activeElement)
        && document.activeElement.type === "text";
      if (!typing) paint();
      clearTimeout(st.timer);
      // While one is being made the page asks again every few seconds, and stops when none is left or the page is gone.
      if ((st.made[jid] || []).some((m) => m.status === "queued" || m.status === "making") && root()) {
        st.timer = setTimeout(loadMade, 3000);
      }
    });
  }

  function say(text, kind) { st.status = text; st.statusKind = kind || ""; paintStatus(); }

  async function make() {
    if (st.sending || !st.jid) return;
    const type = typeNow();
    const body = { format: st.shape, hook: st.hook.trim() };
    if (st.mode === "pick") {
      const n = st.picked.length;
      if (type && (n < type.min_parts || n > type.max_parts)) {
        say(`A ${type.label} takes ${type.min_parts === type.max_parts ? type.min_parts : `${type.min_parts} to ${type.max_parts}`} moments. You ticked ${n}.`, "bad");
        return;
      }
      body.clips = st.picked.slice();
    } else {
      body.count = st.count;
    }
    st.sending = true; paint(); say("Checking the request...", "");
    try {
      await P.send(`/api/montage/${encodeURIComponent(st.jid)}`, body);
      st.sending = false;
      say("It is being made. This takes a minute or two, and it appears below when it is ready.", "");
      await loadMade();
      say("It is being made. This takes a minute or two, and it appears below when it is ready.", "");
    } catch (err) {
      st.sending = false; paint();
      say(why(err, "The montage was not started"), "bad");
    }
  }

  async function drop(id) {
    try {
      await P.api(`/api/montage/${encodeURIComponent(st.jid)}/${encodeURIComponent(id)}`, { method: "DELETE" });
      await loadMade();
    } catch (err) { say(why(err, "The montage was not deleted"), "bad"); }
  }

  async function chatGo() {
    const lines = st.chat.map((t) => t.trim()).filter(Boolean);
    if (!lines.length) { say("Write at least one line of chat.", "bad"); return; }
    try {
      await P.send(`/api/montage/${encodeURIComponent(st.jid)}/chat`, { clip: st.chatClip, lines });
      say("That clip is being made again with your chat lines. It shows in the video's clip list when it is done.", "");
      P.toast("Re-making the clip with chat lines.", "ok");
    } catch (err) { say(why(err, "The chat clip was not started"), "bad"); }
  }

  /* ---- the page's own clicks and changes -------------------------------- */
  function wire(box) {
    box.addEventListener("click", (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      const act = b.dataset.m;
      if (act === "kind") { st.shape = b.dataset.id; st.picked = []; paint(); }
      else if (act === "make") make();
      else if (act === "drop") drop(b.dataset.id);
      else if (act === "chatgo") chatGo();
    });
    box.addEventListener("change", (e) => {
      const t = e.target;
      const act = t && t.dataset ? t.dataset.m : "";
      if (act === "job") { st.jid = t.value; st.picked = []; paint(); loadMade(); }
      else if (act === "mode") { st.mode = t.value; paint(); }
      else if (act === "count") { st.count = Number(t.value) || st.count; }
      else if (act === "pick") {
        st.picked = Array.from(box.querySelectorAll('[data-m="pick"]:checked')).map((i) => i.value);
      } else if (act === "chatclip") { st.chatClip = t.value; }
    });
    box.addEventListener("input", (e) => {
      const t = e.target;
      const act = t && t.dataset ? t.dataset.m : "";
      if (act === "hook") st.hook = t.value;
      else if (act === "chatline") st.chat[Number(t.dataset.i) || 0] = t.value;
    });
  }

  P.add("montage", {
    about: "Join several moments of a video into one Short, and give a clip typed chat lines.",
  });

  P.page("montage", {
    nav: "Montages",
    icon: "film",
    tip: "Join several moments of a video into one Short: a countdown, strikes, then vs now",
    path: "montage",
    group: "Make",
    order: 20,
    view() {
      return `<div class="mt"><h1 class="mt-h">Montages</h1>
        <p class="help">One Short made of several moments of the same video, with a numbered card between them, a flash at each
          cut and captions on every part. Your clips are not changed.</p>
        <div id="mt_root"></div></div>`;
    },
    load() {
      const box = root();
      if (box && !box.dataset.wired) { box.dataset.wired = "1"; wire(box); }
      paint();
      return loadTypes().then(() => { paint(); return loadMade(); });
    },
  });
})();
