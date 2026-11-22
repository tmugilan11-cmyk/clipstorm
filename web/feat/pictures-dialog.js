/* The Pictures pane inside the clip editor.
 *
 * Split out of pictures.js because the contract in docs/swarm3/CONTRACT.md is one plug-in per file, and the editor's
 * pane is a different thing from the editor of the pictures themselves: one fills a tab inside the clip dialog, the
 * other is a page of its own with a canvas to drag on.
 *
 * What this draws: what the open clip will draw, the thumbnails of those pictures, and the switch that puts one saved
 * layout on every clip of the video. It reads `D` and `S` by bare name on purpose: they are `const` at the top level of
 * the page's own classic script, which puts them in the shared global scope rather than on `window`.
 */
(() => {
  "use strict";
  const P = window.PeakCut;
  if (!P) return;

  const esc = window.esc || ((v) => String(v == null ? "" : v).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])));

  P.add("pictures-dialog", {
    after: {
      drawClipDlg() {
        const dlg = document.getElementById("clipdlg");
        const box = dlg && dlg.querySelector("#ed_picbox");
        if (!box || !dlg || typeof D === "undefined" || !D.jid) return;
        if (box.dataset.key === D.jid + "/" + D.cid) return;      // already drawn for this clip
        box.dataset.key = D.jid + "/" + D.cid;
        box.innerHTML = `<p class="help">Reading this clip…</p>`;
        P.api(`/api/jobs/${encodeURIComponent(D.jid)}/clips/${encodeURIComponent(D.cid)}/overlay`)
          .then((got) => {
            const items = (got.clip && got.clip.items) || [];
            const tpl = (got.clip && got.clip.template) || "";
            const name = (got.clip && got.clip.template_name) || "";
            const tpls = (got.templates || []).map((t) =>
              `<option value="${esc(t.id)}"${t.id === tpl ? " selected" : ""}>${esc(t.name)}</option>`).join("");
            box.innerHTML = `
              <p class="help">${items.length
                ? "This clip draws " + esc(got.clip.line) + "."
                : "This clip draws no pictures yet."}</p>
              ${items.length ? `<div class="ed-picnow">${items.map((it) =>
                `<img src="/api/overlays/image/${encodeURIComponent(it.name)}" alt="" title="${esc(it.name)}">`).join("")}</div>` : ""}
              <label class="f">Layout for every clip
                <select data-dlg-tpl>
                  <option value=""${tpl ? "" : " selected"}>None: each clip draws its own</option>
                  ${tpls}
                </select></label>
              <p class="hint">${tpl
                ? "Every clip of this video wears " + esc(name) + ", unless a clip was given its own pictures."
                : "Pick a layout and every clip of this video wears it."}</p>`;
            const sel = box.querySelector("[data-dlg-tpl]");
            if (sel) {
              sel.addEventListener("change", () => {
                P.send(`/api/jobs/${encodeURIComponent(D.jid)}/overlay-template`, { template: sel.value })
                  .then((out) => P.toast(out.note || "Saved.", "good"))
                  .catch((e) => P.toast("Could not set the layout: " + e.message, "bad"));
              });
            }
          })
          .catch((e) => { box.innerHTML = `<p class="help">The pictures could not be read: ${esc(e.message)}</p>`; });
      },
    },
  });
})();
