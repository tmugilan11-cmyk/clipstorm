/* The picture editor: put a poster, a logo or a sticker on a clip, and save the arrangement as a template.

   One page and one canvas. The canvas shows the clip's own middle frame, so the arrangement is judged against the
   picture it will sit on. A picture is dragged with the pointer, resized and turned with buttons as well as with the
   corner handles, because a hand on a trackpad and a hand on a mouse want different things.

   Everything is stored as fractions of the frame (x, y as the picture's CENTRE, w as its width). A template made in a
   540-wide editor therefore lands in the same place in a 1080-wide render. */
(function () {
  "use strict";
  const P = window.PeakCut;
  if (!P) return;

  const NAME = "pictures";
  const esc = window.esc || ((v) => String(v == null ? "" : v).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])));

  const empty = () => ({
    jid: "", cid: "", cidName: "", secs: 0,
    items: [],           // what this clip will draw
    sel: -1,             // which one the buttons act on
    shelf: [],           // every picture kept on this machine
    templates: [],
    tplName: "",         // the template this clip uses, if any
    dirty: false,
    saving: null,
    previewAt: 0,
    revision: 0,
    pending: false,
    ready: false,
    loadId: 0,
    failed: false,
  });
  let S = empty();
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const turn = (angle) => ((angle + 180) % 360 + 360) % 360 - 180;
  const current = () => S.items[S.sel];
  const positions = ["Top left", "Top", "Top right", "Left", "Center", "Right", "Bottom left", "Bottom", "Bottom right"];
  function positionButtons() {
    return positions.map((label, i) => `<button class="pics-align" type="button" data-align="${i}" title="${label}" aria-label="${label}"><span aria-hidden="true"></span></button>`).join("");
  }

  P.css(NAME, `
    .pics-page{display:flex;flex-direction:column;gap:14px;min-width:0}
    .pics-body{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px;align-items:start}
    .pics-stage{position:relative;background:var(--field);border:1px solid var(--line);border-radius:12px;
      padding:14px;display:flex;justify-content:center;min-width:0}
    .pics-canvas{position:relative;width:405px;max-width:100%;aspect-ratio:9/16;background:#000;border-radius:8px;
      overflow:hidden;touch-action:none;cursor:default;user-select:none}
    .pics-canvas img.frame{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none}
    .pics-item{position:absolute;transform:translate(-50%,-50%);cursor:grab;touch-action:none;
      outline:1px dashed transparent;will-change:left,top,width}
    .pics-item img{display:block;width:100%;height:auto;pointer-events:none}
    .pics-item.sel{outline-color:var(--brand)}
    .pics-item:active{cursor:grabbing}
    .pics-item.is-template{pointer-events:none}
    .pics-item .pics-handle{display:none;position:absolute;width:28px;height:28px;border-radius:7px;
      border:1px solid var(--brand);background:var(--bg);color:var(--text);font-size:16px;place-items:center;padding:0;touch-action:none}
    .pics-item.sel .pics-handle{display:grid}
    .pics-handle[data-mode=size]{right:-14px;bottom:-14px;cursor:nwse-resize}
    .pics-handle[data-mode=turn]{left:50%;top:-36px;transform:translateX(-50%);cursor:grab}
    .pics-transform{border:0;padding:0;margin:10px 0 0;min-width:0;display:grid;gap:12px}
    .pics-transform:disabled{opacity:.45}
    .pics-position{display:grid;grid-template-columns:112px 1fr;align-items:center;gap:14px}
    .pics-align-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;padding:4px;border:1px solid var(--line-2);
      border-radius:9px;background:var(--bg)}
    .pics-align{display:grid;place-items:center;min-height:30px;color:var(--dim);background:var(--field);
      border:1px solid var(--line);border-radius:4px;cursor:pointer}
    .pics-align span{width:5px;height:5px;background:currentColor;border-radius:50%}
    .pics-align:hover,.pics-align:focus-visible{color:var(--brand-deep);border-color:var(--brand)}
    .pics-control-title{display:block;font-size:12px;font-weight:600;color:var(--text)}
    .pics-range{display:grid;grid-template-columns:1fr auto;gap:5px 10px;align-items:center;font-size:13px}
    .pics-range input{grid-column:1/-1;width:100%;accent-color:var(--brand);margin:0;min-height:22px}
    .pics-range output{color:var(--dim);font-variant-numeric:tabular-nums}
    .pics-precise{border-top:1px solid var(--line);padding-top:10px}
    .pics-precise > summary{cursor:pointer;color:var(--dim);min-height:26px;font-size:13px}
    .pics-status{margin-left:auto;color:var(--dim);font-size:12px}
    @media (max-width:640px){.pics-position{grid-template-columns:148px 1fr}.pics-align,.pics-precise > summary{min-height:44px}
      .pics-item .pics-handle{width:44px;height:44px}.pics-handle[data-mode=size]{bottom:-22px;right:-22px}.pics-handle[data-mode=turn]{top:-50px}}
    .pics-col{display:flex;flex-direction:column;gap:12px;min-width:0}
    .pics-card{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:14px}
    .pics-card h3{margin:0 0 4px;font-size:14px;color:var(--text)}
    .pics-card p.help{margin:0 0 10px}
    .pics-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:8px;margin-top:8px}
    .pics-thumb{position:relative;border:1px solid var(--line);border-radius:8px;background:var(--field);
      padding:6px;cursor:pointer;color:var(--text);font:inherit;display:flex;flex-direction:column;gap:4px;align-items:center}
    .pics-thumb:hover{border-color:var(--brand-line);background:var(--brand-soft)}
    .pics-thumb img{width:100%;height:48px;object-fit:contain;pointer-events:none}
    .pics-thumb b{font-size:10px;font-weight:500;color:var(--faint);max-width:100%;overflow:hidden;
      text-overflow:ellipsis;white-space:nowrap}
    .pics-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
    .pics-row button{flex:0 0 auto}
    .pics-fields{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
    .pics-fields label{display:flex;flex-direction:column;gap:3px;font-size:11px;color:var(--dim)}
    .pics-fields input{width:100%}
    .pics-note{font-size:12px;color:var(--faint);margin:6px 0 0}
    .pics-tpls{display:flex;flex-direction:column;gap:6px;margin-top:8px}
    .pics-tpl{display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:8px;padding:7px 9px;
      background:var(--field);font-size:12px}
    .pics-tpl.on{border-color:var(--brand);background:var(--brand-soft)}
    .pics-tpl b{flex:1;font-weight:500;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    @media (max-width:1000px){.pics-body{grid-template-columns:minmax(0,1fr)}.pics-canvas{width:100%;max-width:405px}}
  `);

  function api(path, opt) { return P.api(path, opt); }
  function send(path, body, method) { return P.send(path, body, method || "PUT"); }
  function toast(m, k) { if (P.toast) P.toast(m, k); }

  function state() {
    const st = P.state ? P.state() : null;
    const from = (st && st.picturesFrom) || window.__picsFrom || null;
    if (from?.jid && (S.jid !== from.jid || S.cid !== from.cid)) {
      S = {...empty(), jid: from.jid, cid: from.cid, previewAt: Date.now()};
    }
    return st;
  }

  function body() {
    return `<div class="pics-page">
      <header class="pcpg">
        <button class="btn sm" type="button" data-act="pics_back">Back to clip</button>
        <h1 class="pcpg-h">Pictures</h1>
        <p class="help">Add a logo, poster or sticker. Pictures are put on a clip from that clip's editor: open a clip in My videos, then Look, then Add or remove pictures.</p>
      </header>
      <div class="pics-body">
        <section class="pics-stage" aria-label="Picture preview">
          <div class="pics-canvas" id="pics_canvas"><img class="frame" id="pics_frame" alt=""></div>
        </section>
        <aside class="pics-col">
          <div class="pics-card">
            <div class="pics-row"><h3>On this clip</h3><span class="pics-status" id="pics_status" role="status"></span></div>
            <p class="help" id="pics_on">Select a picture to move or resize it.</p>
            <div class="pics-row" id="pics_layers" aria-label="Pictures on this clip"></div>
            <fieldset class="pics-transform" id="pics_transform" aria-label="Selected picture" disabled>
              <div class="pics-position">
                <div class="pics-align-grid" role="group" aria-label="Align in frame">${positionButtons()}</div>
                <div><span class="pics-control-title">Position</span><p class="pics-note">Pick a spot or drag the picture.</p></div>
              </div>
              <div class="pics-row"><button class="btn sm" type="button" data-act="pics_center">Center picture</button>
                <button class="btn sm" type="button" data-act="pics_reset">Reset position and size</button></div>
              <label class="pics-range"><span>Size</span><output id="pics_size_value" aria-hidden="true"></output>
                <input id="pics_size" type="range" min="2" max="150" step="1" data-transform="w"></label>
              <label class="pics-range"><span>Rotation</span><output id="pics_angle_value" aria-hidden="true"></output>
                <input id="pics_angle" type="range" min="-180" max="180" step="1" data-transform="rot"></label>
              <details class="pics-precise"><summary>Precision</summary>
                <div class="pics-fields">
                  <label>Across (%)<input id="pics_x" type="number" min="-50" max="150" step="1" data-transform="x"></label>
                  <label>Down (%)<input id="pics_y" type="number" min="-50" max="150" step="1" data-transform="y"></label>
                  <label>Width (%)<input id="pics_w" type="number" min="2" max="150" step="1" data-transform="w"></label>
                  <label>Rotation (°)<input id="pics_rot" type="number" min="-180" max="180" step="1" data-transform="rot"></label>
                </div>
                <label class="pics-range"><span>Opacity</span><output id="pics_opacity_value" aria-hidden="true"></output>
                  <input id="pics_opacity" type="range" min="0" max="100" step="1" data-transform="alpha"></label>
              </details>
              <div class="pics-row">
                <button class="btn sm" type="button" data-act="pics_nudgedown">Bring to front</button>
                <button class="btn sm" type="button" data-act="pics_drop">Remove picture</button>
              </div>
            </fieldset>
            <button class="btn sm" type="button" data-act="pics_retry" id="pics_retry" hidden>Retry save</button>
          </div>
          <div class="pics-card">
            <h3>Every picture on this machine</h3>
            <p class="help">Adding one keeps it here for every clip.</p>
            <div class="pics-row">
              <label class="btn sm" style="cursor:pointer">Add a picture
                <input id="pics_file" type="file" accept="image/png,image/jpeg,image/webp" hidden></label>
            </div>
            <div class="pics-grid" id="pics_shelf"></div>
          </div>
          <div class="pics-card">
            <h3>Layouts</h3>
            <p class="help">An arrangement saved under a name. The toggle in the clip dialog puts one on every clip.</p>
            <div class="pics-row">
              <input id="pics_tname" type="text" placeholder="Name this layout" maxlength="60" style="flex:1;min-width:0">
              <button class="btn sm" type="button" data-act="pics_save">Save</button>
            </div>
            <div class="pics-tpls" id="pics_tpls"></div>
          </div>
        </aside>
      </div>
    </div>`;
  }

  // ---------------------------------------------------------------- drawing

  function frameUrl() {
    if (!S.jid || !S.cid) return "";
    return `/api/jobs/${encodeURIComponent(S.jid)}/clips/${encodeURIComponent(S.cid)}/overlay/preview?base=true&t=${S.previewAt}`;
  }

  function place(el, it) {
    el.style.left = (it.x * 100) + "%";
    el.style.top = (it.y * 100) + "%";
    el.style.width = (it.w * 100) + "%";
    el.style.transform = `translate(-50%,-50%) rotate(${it.rot}deg)`;
    // Keep the editing handles visible even for a transparent picture.
    if (el.firstElementChild) el.firstElementChild.style.opacity = String(it.alpha);
  }

  function pictureName(name) {
    return name.replace(/-[a-f0-9]{6}(?=\.)/i, "").replace(/\.[a-z]+$/i, "").replace(/-/g, " ") || name;
  }

  function syncControls(skip = null) {
    const it = current();
    const controls = document.getElementById("pics_transform");
    if (controls) controls.disabled = !it || !S.ready;
    const on = document.getElementById("pics_on");
    if (on) on.textContent = it ? pictureName(it.name) : "Choose or upload a picture from the library below.";
    const values = {x:"x", y:"y", w:"w", rot:"rot", size:"w", angle:"rot", opacity:"alpha"};
    for (const [field, key] of Object.entries(values)) {
      const box = document.getElementById("pics_" + field);
      const v = it ? Math.round(it[key] * (key === "rot" ? 1 : 100)) : "";
      if (box && box !== skip) box.value = String(v);
      const out = document.getElementById(`pics_${field}_value`);
      if (out) out.textContent = it ? `${v}${key === "rot" ? "°" : "%"}` : "";
    }
  }

  function selectPicture(index) {
    S.sel = index;
    const canvas = document.getElementById("pics_canvas");
    canvas?.querySelectorAll(".pics-item[data-i]").forEach(el => el.classList.toggle("sel", Number(el.dataset.i) === index));
    document.getElementById("pics_layers")?.querySelectorAll("[data-layer]").forEach(el => {
      el.setAttribute("aria-pressed", String(Number(el.dataset.layer) === index));
    });
    syncControls();
  }

  function drawCanvas() {
    const cv = document.getElementById("pics_canvas");
    if (!cv) return;
    const frame = document.getElementById("pics_frame");
    if (frame) {
      const url = frameUrl();
      if (url && frame.getAttribute("src") !== url) frame.src = url;
    }
    cv.querySelectorAll(".pics-item").forEach((n) => n.remove());
    const paint = (it, index) => {
      const editable = index >= 0;
      const el = document.createElement("div");
      el.className = "pics-item" + (editable ? (index === S.sel ? " sel" : "") : " is-template");
      if (editable) el.dataset.i = String(index);
      const img = document.createElement("img");
      img.src = `/api/overlays/image/${encodeURIComponent(it.name)}`;
      img.alt = "";
      img.draggable = false;
      el.appendChild(img);
      if (editable) {
        for (const [mode, label, symbol] of [["size", "Drag to resize", "↘"], ["turn", "Drag to rotate", "↻"]]) {
          const handle = document.createElement("span");
          handle.className = "pics-handle";
          handle.dataset.mode = mode;
          handle.title = label;
          handle.textContent = symbol;
          handle.setAttribute("aria-hidden", "true");
          el.appendChild(handle);
        }
      }
      place(el, it);
      cv.appendChild(el);
    };
    const inherited = S.templates.find(t => t.id === S.tplName);
    (inherited?.items || []).forEach(it => paint(it, -1));
    S.items.forEach(paint);
    const layers = document.getElementById("pics_layers");
    if (layers) {
      layers.replaceChildren();
      S.items.forEach((it, index) => {
        const button = document.createElement("button");
        button.className = "btn sm pics-layer";
        button.type = "button";
        button.dataset.layer = String(index);
        button.setAttribute("aria-pressed", String(index === S.sel));
        button.textContent = `${index + 1}. ${pictureName(it.name)}`;
        layers.appendChild(button);
      });
    }
    syncControls();
  }

  function drawShelf() {
    const grid = document.getElementById("pics_shelf");
    if (!grid) return;
    if (!S.shelf.length) {
      grid.innerHTML = `<p class="pics-note">No pictures yet. Add a logo or a poster and it stays here.</p>`;
      return;
    }
    grid.innerHTML = S.shelf.map((im) =>
      `<button class="pics-thumb" type="button" data-picadd="${esc(im.name)}" title="${esc(im.name)}">
         <img src="/api/overlays/image/${encodeURIComponent(im.name)}" alt="">
         <b>${esc(im.name.replace(/\.[a-z]+$/, ""))}</b></button>`).join("");
  }

  function drawTemplates() {
    const box = document.getElementById("pics_tpls");
    if (!box) return;
    if (!S.templates.length) {
      box.innerHTML = `<p class="pics-note">No layouts yet.</p>`;
      return;
    }
    box.innerHTML = S.templates.map((t) =>
      `<div class="pics-tpl${t.id === S.tplName ? " on" : ""}">
         <b title="${esc(t.name)}">${esc(t.name)}</b>
         <span class="pics-note" style="margin:0">${(t.items || []).length} picture${(t.items || []).length === 1 ? "" : "s"}</span>
         <button class="btn xs" type="button" data-tpluse="${esc(t.id)}">${t.id === S.tplName ? "In use" : "Use"}</button>
         <button class="btn xs" type="button" data-tplget="${esc(t.id)}">Load</button>
         <button class="btn xs" type="button" data-tpldrop="${esc(t.id)}">Delete</button>
       </div>`).join("");
  }

  function drawAll() {
    drawCanvas();
    drawShelf();
    drawTemplates();
  }

  // ---------------------------------------------------------------- data

  async function load() {
    state();
    const active = S;
    const loadId = ++active.loadId;
    const isCurrent = () => S === active && active.loadId === loadId;
    if (!active.jid || !active.cid) {
      const box = document.getElementById("pics_canvas");
      if (box) box.innerHTML = `<p class="pics-note" style="padding:20px">Open a clip and select Edit pictures.</p>`;
    }
    try {
      const shelf = api("/api/overlays").catch(() => null);
      if (active.jid && active.cid && !active.ready) {
        const got = await api(`/api/jobs/${encodeURIComponent(active.jid)}/clips/${encodeURIComponent(active.cid)}/overlay`);
        if (!isCurrent()) return;
        active.items = got.clip?.items || [];
        active.tplName = got.clip?.template || "";
        active.templates = got.templates || [];
        active.sel = active.items.length ? active.items.length - 1 : -1;
        active.ready = true;
      }
      const got = await shelf;
      if (!isCurrent()) return;
      if (got) {
        active.shelf = got.images || [];
        active.templates = got.templates || active.templates;
      }
      drawAll();
      showStatus(active.saving ? "Saving…" : active.failed ? "Save failed" : active.dirty ? "Unsaved changes" : "");
    } catch (e) {
      if (isCurrent()) toast("The pictures could not be opened: " + e.message, "bad");
    }
  }

  function showStatus(text) {
    const status = document.getElementById("pics_status");
    if (status) status.textContent = text;
    const retry = document.getElementById("pics_retry");
    if (retry) retry.hidden = !S.failed;
  }

  function changed() {
    S.revision++;
    S.dirty = true;
    S.failed = false;
    showStatus(S.saving ? "Saving…" : "Unsaved changes");
  }

  function save() {
    const active = S;
    if (!active.ready || !active.dirty) return active.saving || Promise.resolve(true);
    active.pending = true;
    if (active.saving) return active.saving;
    active.failed = false;
    showStatus("Saving…");
    const path = `/api/jobs/${encodeURIComponent(active.jid)}/clips/${encodeURIComponent(active.cid)}/overlay`;
    active.saving = (async () => {
      try {
        while (active.pending) {
          active.pending = false;
          const revision = active.revision;
          const template = active.tplName;
          const result = await send(path, {items: active.items.map(it => ({...it})), template});
          const savedTemplate = result?.clip?.template;
          if (active.tplName === template && typeof savedTemplate === "string" && savedTemplate !== template) {
            active.tplName = savedTemplate;
            active.templates = active.templates.filter(layout => layout.id !== template);
            if (active === S) drawTemplates();
          }
          if (revision === active.revision) active.dirty = false;
        }
        if (active === S) showStatus(active.dirty ? "Unsaved changes" : "Saved");
        return true;
      } catch (e) {
        active.failed = true;
        if (active === S) {
          showStatus("Save failed");
          toast("Could not save the pictures: " + e.message, "bad");
        }
        return false;
      } finally {
        active.saving = null;
      }
    })();
    return active.saving;
  }

  function align(index) {
    const item = current();
    if (!item || !Number.isInteger(index) || index < 0 || index > 8) return;
    const image = S.shelf.find(im => im.name === item.name);
    const ratio = image?.width && image.height ? image.height / image.width : 1;
    const h = item.w * ratio * 9 / 16;
    const angle = item.rot * Math.PI / 180;
    const x = Math.min(.5, .04 + (item.w * Math.abs(Math.cos(angle)) + h * 16 / 9 * Math.abs(Math.sin(angle))) / 2);
    const y = Math.min(.5, .04 + (h * Math.abs(Math.cos(angle)) + item.w * 9 / 16 * Math.abs(Math.sin(angle))) / 2);
    nudge(it => { it.x = [x, .5, 1 - x][index % 3]; it.y = [y, .5, 1 - y][Math.floor(index / 3)]; });
  }

  function wire() {
    const cv = document.getElementById("pics_canvas");
    if (!cv || cv.dataset.wired === "1") return;
    cv.dataset.wired = "1";
    let drag = null;

    cv.addEventListener("pointerdown", e => {
      const el = e.target.closest(".pics-item[data-i]");
      if (!el || e.button !== 0 || drag) return;
      selectPicture(Number(el.dataset.i));
      const it = current();
      if (!it) return;
      const rect = cv.getBoundingClientRect();
      const cx = rect.left + it.x * rect.width;
      const cy = rect.top + it.y * rect.height;
      drag = {el, it, rect, cx, cy, start: {...it}, id: e.pointerId, x: e.clientX, y: e.clientY,
        mode: e.target.closest("[data-mode]")?.dataset.mode || "move", moved: false};
      cv.setPointerCapture(e.pointerId);
      e.preventDefault();
    });

    cv.addEventListener("pointermove", e => {
      if (!drag || e.pointerId !== drag.id) return;
      const {el, it, rect, cx, cy, start, mode, x, y} = drag;
      const dx = e.clientX - x;
      const dy = e.clientY - y;
      if (!drag.moved && Math.hypot(dx, dy) < 2) return;
      drag.moved = true;
      if (mode === "move") {
        it.x = clamp(start.x + dx / rect.width, -.5, 1.5);
        it.y = clamp(start.y + dy / rect.height, -.5, 1.5);
      } else if (mode === "size") {
        const radius = Math.hypot(x - cx, y - cy);
        if (radius > 0) it.w = clamp(start.w * Math.hypot(e.clientX - cx, e.clientY - cy) / radius, .02, 1.5);
      } else {
        const angle = Math.atan2(e.clientY - cy, e.clientX - cx) - Math.atan2(y - cy, x - cx);
        it.rot = turn(Math.round(start.rot + angle * 180 / Math.PI));
      }
      changed();
      place(el, it);
      syncControls();
    });

    const finish = e => {
      if (!drag || e.pointerId !== drag.id) return;
      const moved = drag.moved;
      drag = null;
      if (moved) save();
    };
    for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) cv.addEventListener(name, finish);

    const edit = e => {
      const field = e.target;
      const key = field.getAttribute?.("data-transform");
      const valid = {x: [-.5, 1.5], y: [-.5, 1.5], w: [.02, 1.5], rot: [-180, 180], alpha: [0, 1]};
      const it = current();
      if (!Object.hasOwn(valid, key) || !it || field.value === "" || !Number.isFinite(Number(field.value))) return;
      const v = clamp(Number(field.value) / (key === "rot" ? 1 : 100), ...valid[key]);
      if (it[key] === v) return;
      it[key] = v;
      changed();
      cv.querySelectorAll(".pics-item[data-i]").forEach(el => {
        if (Number(el.dataset.i) === S.sel) place(el, it);
      });
      syncControls(field);
    };
    const form = document.getElementById("pics_transform") || cv;
    form.addEventListener("input", edit);
    form.addEventListener("change", e => {
      if (!e.target.getAttribute?.("data-transform")) return;
      edit(e);
      syncControls();
      save();
    });

    const file = document.getElementById("pics_file");
    if (file && file.dataset.wired !== "1") {
      file.dataset.wired = "1";
      file.addEventListener("change", async () => {
        const f = file.files && file.files[0];
        if (!f) return;
        const fd = new FormData();
        fd.append("file", f);
        try {
          const r = await fetch("/api/overlays/upload", { method: "POST", body: fd, credentials: "same-origin" });
          const got = await r.json();
          if (!r.ok) throw new Error(got.detail || "The picture could not be kept.");
          S.shelf.unshift(got.image);
          file.value = "";
          drawShelf();
          addPicture(got.image.name);
        } catch (e) {
          toast(e.message, "bad");
        }
      });
    }
  }

  function commit() {
    changed();
    drawCanvas();
    save();
  }

  function addPicture(name) {
    if (!name || !S.ready) return;
    if (S.items.length >= 8) { toast("A clip draws at most eight pictures.", "warn"); return; }
    S.items.push({name, x: .5, y: .5, w: .34, rot: 0, alpha: 1});
    S.sel = S.items.length - 1;
    commit();
  }

  function nudge(fn) {
    const it = current();
    if (!it) return;
    fn(it);
    commit();
  }

  // ---------------------------------------------------------------- actions

  P.page("pictures", {
    nav: "Pictures",
    icon: "image",
    group: "Make",
    order: 21,
    path: "pictures",
    hidden: true,
    tip: "Posters, logos and stickers drawn onto a clip",
    view: body,
    load: load,
  });

  P.add("pictures", {
    after: { drawSettings() { wire(); } },
    act: {
      openpics() {
        const st = P.state ? P.state() : null;
        const dlg = (typeof D !== "undefined") ? D : null;
        if (!st || !dlg || !dlg.jid) { toast("Open a clip first.", "warn"); return; }
        st.picturesFrom = {jid: dlg.jid, cid: dlg.cid, view: st.view, tab: st.ctab};
        window.__picsFrom = st.picturesFrom;
        const box = document.getElementById("clipdlg");
        if (box?.open) box.close();
        if (typeof go === "function") go("pictures");
      },
      async pics_back() {
        const from = state()?.picturesFrom || window.__picsFrom;
        if (!(await save())) return;
        if (typeof go === "function") go(from?.view || "library", from?.tab);
        if (from?.jid && from.cid && typeof openClip === "function") openClip(from.jid, from.cid);
      },
      pics_center() { align(4); },
      pics_reset() { nudge(it => Object.assign(it, {x: .5, y: .5, w: .34, rot: 0})); },
      pics_retry() { save(); },
      pics_nudgedown() {
        if (!current() || S.sel === S.items.length - 1) return;
        S.items.push(S.items.splice(S.sel, 1)[0]);
        S.sel = S.items.length - 1;
        commit();
      },
      pics_drop() {
        if (!current()) return;
        S.items.splice(S.sel, 1);
        S.sel = Math.min(S.sel, S.items.length - 1);
        commit();
      },
      pics_save() {
        const name = (document.getElementById("pics_tname") || {}).value || "";
        if (!name.trim()) { toast("Give the layout a name first.", "warn"); return; }
        if (!S.items.length) { toast("There is nothing to save yet. Add a picture first.", "warn"); return; }
        send("/api/overlays/templates", { id: "", name: name.trim(), items: S.items })
          .then((got) => {
            S.templates.unshift(got.template);
            drawTemplates();
            toast(`Saved the layout "${got.template.name}".`, "good");
          })
          .catch((e) => toast("Could not save the layout: " + e.message, "bad"));
      },
    },
  });

  // clicks inside the page that are not on the act registry: the shelf, the layouts
  document.addEventListener("click", (ev) => {
    if (!ev.target.closest?.(".pics-page")) return;
    const point = ev.target.closest("[data-align]");
    if (point) { align(Number(point.dataset.align)); return; }
    const layer = ev.target.closest("[data-layer]");
    if (layer) { selectPicture(Number(layer.dataset.layer)); return; }
    const add = ev.target.closest("[data-picadd]");
    if (add) { addPicture(add.getAttribute("data-picadd")); return; }
    const use = ev.target.closest && ev.target.closest("[data-tpluse]");
    if (use && S.ready) {
      const tid = use.getAttribute("data-tpluse");
      S.tplName = (S.tplName === tid) ? "" : tid;
      drawTemplates();
      commit();
      return;
    }
    const get = ev.target.closest && ev.target.closest("[data-tplget]");
    if (get && S.ready) {
      const t = S.templates.find((x) => x.id === get.getAttribute("data-tplget"));
      if (t) {
        S.items = (t.items || []).map(x => ({...x}));
        if (S.tplName === t.id) S.tplName = "";
        S.sel = S.items.length - 1;
        drawTemplates();
        commit();
      }
      return;
    }
    const drop = ev.target.closest && ev.target.closest("[data-tpldrop]");
    if (drop) {
      const tid = drop.getAttribute("data-tpldrop");
      send(`/api/overlays/templates/${encodeURIComponent(tid)}`, null, "DELETE")
        .then(() => {
          S.templates = S.templates.filter((x) => x.id !== tid);
          if (S.tplName === tid) { S.tplName = ""; commit(); }
          drawTemplates();
          toast("Layout deleted.", "good");
        })
        .catch((e) => toast("Could not delete: " + e.message, "bad"));
    }
  });

})();
