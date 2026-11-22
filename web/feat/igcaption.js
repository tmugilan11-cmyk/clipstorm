/* The editable plain-text caption sent with an Instagram upload. Never a video effect. */
(() => {
  "use strict";
  const P = window.PeakCut;
  if (!P) return;
  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g,
    (c) => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
  const drafts = new Map();
  P.css("igcaption", `
    .igbox:empty{display:none}
    .igbox{border:1px solid var(--line);border-radius:10px;padding:12px;display:grid;gap:12px;background:var(--card)}
    .igbox h4,.igbox p{margin:0}
    .igbox h4{font-size:14px}
    .igbox p,.igbox output{font-size:12px;line-height:1.5;color:var(--dim)}
    .igbox .ig-controls{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .igbox .ig-buttons{display:flex;flex-wrap:wrap;gap:8px}
    .igbox textarea{width:100%;min-height:160px;resize:vertical;line-height:1.6;white-space:pre-wrap}
    .igbox .ig-status[data-error="true"]{color:var(--bad)}
    .igbox .ig-enabled{display:flex;gap:8px;align-items:flex-start;font-size:12px}
    .igbox .ig-enabled input{margin-top:2px}
    .igbox [hidden]{display:none}
  `);

  function identity() {
    return typeof D === "undefined" || !D.jid || !D.cid ? null : {jid:D.jid, cid:D.cid};
  }
  function url(who) {
    return `/api/jobs/${encodeURIComponent(who.jid)}/clips/${encodeURIComponent(who.cid)}/igcaption`;
  }
  function status(box, text, error=false) {
    const out=box.querySelector(".ig-status");
    if (out) { out.textContent=text; out.dataset.error=String(error); }
  }
  function sync(box, draft) {
    const custom=box.querySelector("[data-ig-custom]");
    const area=box.querySelector("[data-ig-caption]");
    const enabled=box.querySelector("[data-ig-enabled]");
    if (custom) custom.hidden=!draft.enabled;
    if (enabled) enabled.checked=draft.enabled;
    if (area && area.value!==draft.caption) area.value=draft.caption;
    const count=box.querySelector("[data-ig-count]");
    // The limit is the one the API sends with the caption, so the counter cannot drift from the server's maximum.
    // The count is code points (Array.from), the same unit the server counts with, and the textarea no longer blocks
    // input itself: a person who types past the limit sees the numbers here and gets the server's clear message
    // when saving.
    if (count) {
      const used=Array.from(draft.caption).length.toLocaleString("en-US");
      count.textContent=typeof draft.limit==="number"
        ? used+" / "+draft.limit.toLocaleString("en-US")+" characters"
        : used+" characters";
    }
    for (const button of box.querySelectorAll("[data-ig-save],[data-ig-generate],[data-ig-default]")) button.disabled=draft.busy;
  }
  function paint(box, who, draft) {
    box.innerHTML=`<h4>Instagram post caption</h4>
      <p>Shown under the Reel after upload. Instagram controls its font and appearance.</p>
      <label class="ig-enabled"><input type="checkbox" data-ig-enabled ${draft.enabled?"checked":""}>Use a separate caption for Instagram</label>
      <div data-ig-custom ${draft.enabled?"":"hidden"}>
        <div class="ig-controls">
          <label class="f">Writing language<select data-ig-lang>
            ${[["original","Original language"],["ja","Japanese"],["zh","Chinese"]].map(([v,label])=>`<option value="${esc(v)}" ${draft.lang===v?"selected":""}>${esc(label)}</option>`).join("")}
          </select></label>
          <label class="f">Writing style<select data-ig-format>
            ${[["natural","Natural"],["short","Short and direct"],["story","Short story"],["question","Ask the audience"]].map(([v,label])=>`<option value="${esc(v)}" ${draft.format===v?"selected":""}>${esc(label)}</option>`).join("")}
          </select></label>
        </div>
        <label class="f">Caption and hashtags<textarea data-ig-caption rows="6">${esc(draft.caption)}</textarea></label>
        <output data-ig-count></output>
        <div class="ig-buttons"><button class="btn sm" type="button" data-ig-generate>Generate draft</button><button class="btn sm" type="button" data-ig-copy>Copy</button></div>
      </div>
      <div class="ig-buttons"><button class="btn sm primary" type="button" data-ig-save>Save Instagram caption</button>
        <button class="btn sm" type="button" data-ig-default>Use regular post text</button></div>
      <p class="ig-status" role="status">${esc(draft.dirty?"Unsaved changes":draft.enabled?"Saved for Instagram":"Uses the regular title, description and hashtags")}</p>`;
    sync(box,draft);
    box.oninput=(ev)=>{
      if (!ev.target.matches("[data-ig-caption]")) return;
      draft.caption=ev.target.value; draft.dirty=true; draft.revision++;
      sync(box,draft); status(box,"Unsaved changes");
    };
    box.onchange=(ev)=>{
      if (ev.target.matches("[data-ig-enabled]")) draft.enabled=ev.target.checked;
      else if (ev.target.matches("[data-ig-lang]")) draft.lang=ev.target.value;
      else if (ev.target.matches("[data-ig-format]")) draft.format=ev.target.value;
      else return;
      draft.dirty=true; draft.revision++; sync(box,draft); status(box,"Unsaved changes");
    };
    box.onclick=async(ev)=>{
      const button=ev.target.closest("button");
      if (!button || !box.contains(button) || draft.busy) return;
      if (button.hasAttribute("data-ig-copy")) {
        try { await navigator.clipboard.writeText(draft.caption); status(box,"Caption copied"); }
        catch { status(box,"Copy was unavailable. Select the text in the box to copy it.",true); }
        return;
      }
      const rev=draft.revision;
      draft.busy=true; sync(box,draft);
      try {
        if (button.hasAttribute("data-ig-generate")) {
          status(box,"Writing a draft…");
          const got=await P.send(url(who)+"/generate", {lang:draft.lang, format:draft.format});
          if (draft.revision!==rev) { status(box,"You edited the text while the AI was working. Your edits were kept."); return; }
          draft.caption=got.caption; draft.enabled=true; draft.dirty=true; draft.revision++;
          status(box,"Draft ready. Edit it, then save when you are happy with it.");
        } else if (button.hasAttribute("data-ig-save") || button.hasAttribute("data-ig-default")) {
          const regular=button.hasAttribute("data-ig-default");
          status(box,"Saving…");
          const got=await P.send(url(who), {enabled:regular?false:draft.enabled,
            caption:draft.caption, lang:draft.lang, format:draft.format}, "PUT");
          if (draft.revision===rev) {
            Object.assign(draft,got,{dirty:false});
            status(box,got.enabled?"Saved for Instagram":"Uses the regular title, description and hashtags");
          } else status(box,"Earlier draft saved. Save again to include your latest edits.");
        }
      } catch(e) { status(box,e.message||"The caption could not be saved. Your draft is still here.",true); }
      finally { draft.busy=false; sync(box,draft); }
    };
  }
  async function mount() {
    const box=document.querySelector("#clipdlg #ed_igbox");
    const who=identity();
    if (!box || !who) return;
    const key=who.jid+"/"+who.cid;
    if (box.dataset.key===key) return;
    box.dataset.key=key;
    if (drafts.has(key)) { paint(box,who,drafts.get(key)); return; }
    box.textContent="Loading Instagram caption…";
    try {
      const got=await P.api(url(who));
      if (!box.isConnected || box.dataset.key!==key) return;
      const draft={...got,dirty:false,busy:false,revision:0};
      drafts.set(key,draft); paint(box,who,draft);
    } catch(e) { box.textContent="The Instagram caption could not be loaded. "+e.message; box.dataset.key=""; }
  }
  P.add("igcaption", {after:{drawClipDlg:mount}});
})();
