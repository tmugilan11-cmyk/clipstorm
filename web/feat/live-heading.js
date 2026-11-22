// Live previews inside the clip editor.
//
// Two things in the clip dialog were blind, and both were complained about in the same words: "rebuild them with live
// previews". Typing a heading and pressing "Save and re-make clip" meant waiting for a whole render to find out the
// words did not fit. Typing a title and a description meant not seeing the post until it was posted.
//
// So this file puts two real previews in the dialog:
//
//   * under "Big text", a real frame of this clip with the heading drawn on it, made by the server from the clip's own
//     video in the clip's own look and brand (`/api/jobs/{jid}/clips/{cid}/preview/heading`);
//   * on the Text tab, the post exactly as it will be written, assembled as the person types.
//
// Nothing here renders a video and nothing costs money. The frame is drawn once per pause in typing, and the last
// picture is kept on screen while a new one is on its way, so the panel never flashes empty.
(() => {
  const P = window.PeakCut;
  if (!P) return;

  const NAME = "live-heading";
  const WAIT = 700;          // a pause in typing, not every key

  P.css(NAME, `
    .lh{margin:2px 0 4px}
    /* The picture is sized to be readable, not to fill the rail: a 9/16 frame at the rail's full 333 px would be
       592 px tall and push the caption style and layout pickers off the screen, while a 150 px one is too small to
       check a heading's wording. About 200 px wide is the point where the words are legible and the controls it
       belongs to stay reachable with one short scroll. */
    .lh-shot{display:block;margin:0 auto;max-width:100%;height:auto;max-height:356px;object-fit:contain;
      background:#000;border:1px solid var(--line);border-radius:10px}
    .lh-note{margin:6px 0 0;font-size:12px;line-height:1.45;color:var(--dim);text-align:center}
    .lh-note.bad{color:var(--bad)}
    .lh-wait{position:relative}
    .lh-wait .lh-shot{opacity:.55}
    .ltx{margin:2px 0 4px;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--muted)}
    .ltx-h{margin:0 0 6px;font-size:12px;color:var(--dim)}
    .ltx-b{margin:0;white-space:pre-wrap;font-size:13px;line-height:1.5;color:var(--text)}
    .ltx-b:empty::after{content:"Nothing yet.";color:var(--faint)}
  `);

  let timer = 0;             // the pending frame
  let shown = "";            // the address of the picture already on screen
  let box = null;            // the live panel, so a redraw can reuse it

  function dialog() {
    const root = document.querySelector("#clipdlg");
    if (!root || !root.querySelector(".editor")) return null;
    return root;
  }

  // Which clip the open dialog is showing. `D` is a top-level const in the page's own script, so it is in the shared
  // global scope rather than on `window`; read it carefully rather than assuming.
  function ids() {
    try {
      if (typeof D === "undefined" || !D || !D.jid) return null;
      return { jid: D.jid, cid: D.cid };
    } catch (e) {
      return null;
    }
  }

  function headingBox(root) {
    const look = root.querySelector('.ed-pane[data-pane="look"]');
    if (!look) return null;
    let host = look.querySelector(".lh");
    if (host) return host;
    const field = look.querySelector('[data-f="hook"]');
    if (!field) return null;
    host = document.createElement("div");
    host.className = "lh";
    host.innerHTML =
      '<img class="lh-shot" alt="This clip with the heading on it">' +
      '<p class="lh-note">Drawn from this clip\'s own video, in this clip\'s look.</p>';
    field.closest("label").insertAdjacentElement("afterend", host);
    return host;
  }

  function paint(src) {
    if (!box) return;
    const img = box.querySelector(".lh-shot");
    const note = box.querySelector(".lh-note");
    if (!img) return;
    img.onload = () => {
      box.classList.remove("lh-wait");
      note.classList.remove("bad");
      note.textContent = "Drawn from this clip's own video, in this clip's look.";
    };
    img.onerror = () => {
      box.classList.remove("lh-wait");
      note.classList.add("bad");
      note.textContent = "That frame could not be drawn. The clip's own words still save as usual.";
    };
    box.classList.add("lh-wait");
    shown = src;
    img.src = src;
  }

  function want(root) {
    const here = ids();
    const field = root.querySelector('[data-f="hook"]');
    if (!here || !field || !box) return;
    const said = String(field.value || "").slice(0, 120);
    const src =
      "/api/jobs/" + encodeURIComponent(here.jid) + "/clips/" + encodeURIComponent(here.cid) +
      "/preview/heading?hook=" + encodeURIComponent(said);
    if (src === shown) return;         // the same words: the picture on screen is already right
    wait();
    const go = () => paint(src + (src.indexOf("?") >= 0 ? "&" : "?") + "t=" + Date.now());
    timer = window.setTimeout(go, WAIT);
  }

  function wait() {
    if (timer) {
      window.clearTimeout(timer);
      timer = 0;
    }
  }

  // ---- the post, as it will be written

  function postBox(root) {
    const pane = root.querySelector('.ed-pane[data-pane="text"]');
    if (!pane) return null;
    let host = pane.querySelector(".ltx");
    if (host) return host;
    const field = pane.querySelector('[data-f="description"]');
    if (!field) return null;
    host = document.createElement("div");
    host.className = "ltx";
    host.innerHTML = '<p class="ltx-h">The post, exactly as it will be written.</p><p class="ltx-b"></p>';
    field.closest("label").insertAdjacentElement("afterend", host);
    return host;
  }

  function paintPost(root) {
    const host = postBox(root);
    if (!host) return;
    const body = host.querySelector(".ltx-b");
    if (!body) return;
    const val = (f) => {
      const el = root.querySelector('[data-f="' + f + '"]');
      return el ? String(el.value || "").trim() : "";
    };
    // The same order `posting._caption` writes, so what is shown is what goes out rather than a guess at it.
    const parts = [val("title"), val("description")].filter(Boolean);
    const tags = (() => {
      // The hashtags are already on the clip the page holds: read them from there rather than guessing, so the box
      // shows the same words "Copy post text" copies.
      try {
        const who = ids();
        const job = who && typeof jobOf === "function" ? jobOf(who.jid) : null;
        const clip = job ? (job.clips || []).find((c) => c.id === who.cid) : null;
        const list = (clip && clip.hashtags) || [];
        return list.map((h) => "#" + String(h).replace(/^#+/, "")).join(" ");
      } catch (e) {
        return "";
      }
    })();
    if (tags) parts.push(tags);
    body.textContent = parts.join("\n\n");
  }

  function attach(root) {
    const here = ids();
    if (!here) return;
    box = headingBox(root);
    if (box) {
      // Draw only when the Look tab is on screen: a hidden pane would spend a render on a picture nobody can see.
      const look = root.querySelector('.ed-pane[data-pane="look"]');
      if (look && !look.hasAttribute("hidden")) want(root);
    }
    paintPost(root);
    if (root.dataset.lhWired === "1") return;
    root.dataset.lhWired = "1";
    root.addEventListener("input", (e) => {
      const t = e.target;
      if (!t || !t.dataset) return;
      if (t.dataset.f === "hook") want(root);
      if (t.dataset.f === "title" || t.dataset.f === "description") paintPost(root);
    });
    root.addEventListener("change", (e) => {
      const t = e.target;
      if (t && t.dataset && t.dataset.f === "hook") want(root);
    });
    // Switching to the Look tab asks for a frame if the words changed while it was hidden.
    root.addEventListener("click", (e) => {
      const tab = e.target && e.target.closest ? e.target.closest('.ed-railnav button[data-pane="look"]') : null;
      if (tab) window.setTimeout(() => want(root), 30);
    });
  }

  P.add("live-heading", {
    after: {
      drawClipDlg(root) {
        // The paint hook hands over the `#clipdlg` element itself, so look for the dialog *in* it only when what was
        // passed is something else. (Getting this wrong is silent: the hook runs, finds nothing, and returns.)
        const host = !root ? dialog()
          : root.id === "clipdlg" ? root
            : (root.querySelector && root.querySelector("#clipdlg")) || dialog();
        if (!host) return;
        attach(host);
      },
    },
  });
})();
