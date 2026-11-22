/* Every empty box in Insights says what is missing, and offers a way forward.
 *
 * Four other files fill the four boxes on this page, and each has its own answer for an empty one: a row of
 * dashes, a sentence of its own, or nothing at all. A box that holds nothing tells the reader nothing and gives
 * them nothing to do. This file adds one line to a box that is still empty after the other files have had their
 * turn: what is missing, and a link to the page that connects a channel. It never writes over a box that has real
 * content, and it never adds a second line to a box that already has one.
 */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-empty", `
    .an-empty{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:12px 0 0;padding:11px 13px;
      border:1px dashed var(--line-2);border-radius:var(--r);background:var(--muted);
      font-size:13px;line-height:1.5;color:var(--dim)}
    .an-empty:first-child{margin-top:0}
    .an-empty b{font-weight:600;color:var(--text)}
    .an-empty a{display:inline-flex;align-items:center;gap:3px;padding-bottom:1px;
      border-bottom:1px solid var(--brand-line);color:var(--brand-deep);font-weight:600;text-decoration:none;white-space:nowrap}
    .an-empty a:hover{border-bottom-color:var(--brand);color:var(--text)}
    .an-empty a svg{width:12px;height:12px;flex:none}
  `);

  const BOXES = ["an_kpi", "an_charts", "an_table", "an_body"];
  const APPS = "/app/apps", LINK = "Connect a channel";
  // How long a box has to stay empty before it is called empty. A request that is still out there is not an
  // empty answer, and a line saying "nothing arrived" while the number is in flight is worse than no line.
  const WAIT = 1300;
  // Spaces, punctuation, or a dash, and nothing else. A box holding one dash is as empty as a box holding nothing.
  const EMPTY = /^[\s.,:;\/\\|()\-_\u2010-\u2015\u2212]*$/;
  const INVISIBLE = /[\u200b-\u200f\ufeff]/g;

  const say = (s) => {
    const text = String(s == null ? "" : s);
    try { return esc(text); } catch (err) {
      return text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }
  };
  const icon = (n) => { try { return typeof ic === "function" ? ic(n) : ""; } catch (err) { return ""; } };
  const tab = () => {
    try { const A = window.PeakCutAnalytics; return A && typeof A.tab === "function" ? String(A.tab() || "") : ""; }
    catch (err) { return ""; }
  };

  /** What is missing, in the words of the box it went missing from. No numbers, because none arrived. */
  function missing(id, t) {
    if (id === "an_kpi") return ["No key numbers yet.", "The analytics answer for this range did not arrive."];
    if (id === "an_charts") return ["The charts are empty.", "No daily views or watch time arrived for this range."];
    if (id === "an_table") return ["No videos are listed.", "Nothing came back for this range."];
    if (t === "audience") return ["The audience is missing.",
      "Viewer types, countries and hours come from YouTube, and none of them arrived for this range."];
    if (t === "traffic") return ["Traffic sources are missing.",
      "The searches and pages that sent these views come from YouTube, and none of them arrived for this range."];
    return ["Nothing to show yet.", "No answer arrived for this range."];
  }

  function line(id, t) {
    const [lead, why] = missing(id, t);
    return `<p class="an-empty" data-an-empty="1"><span><b>${say(lead)}</b> ${say(why)}</span>`
      + `<a href="${say(APPS)}" data-act="go" data-v="apps"><span>${say(LINK)}</span>${icon("arrowr")}</a></p>`;
  }

  /** The words in a box, leaving out one node: the line this file added. */
  function words(box, skip) {
    let out = "";
    for (const n of box.childNodes) if (n !== skip) out += " " + (n.textContent == null ? "" : n.textContent);
    return out;
  }

  // A box first seen empty, and when. It has to survive the wait below before anything is written to it.
  const seen = new Map();

  function look(id, t) {
    const box = document.getElementById(id);
    if (!box) { seen.delete(id); return; }
    const panel = box.closest ? box.closest("[data-an-panel]") : null;
    if (panel && panel.hidden) { seen.delete(id); return; }   // nobody can see it; the tab switch asks again
    const mine = box.querySelector(".an-empty");
    if (mine) {
      // Anything beside our line means another file filled this box, so the line no longer belongs there.
      if (!EMPTY.test(words(box, mine).replace(INVISIBLE, ""))) { mine.remove(); delete box.dataset.anEmpty; }
      return;                                                // one line per box, which is where a second would go
    }
    if (box.dataset.anEmpty === "1") delete box.dataset.anEmpty;   // the line that mark stood for is gone
    if (!EMPTY.test(String(box.textContent || "").replace(INVISIBLE, ""))) { seen.delete(id); return; }  // real content
    if (!seen.has(id)) { seen.set(id, Date.now()); return; }  // newly empty: it may still be loading
    if (Date.now() - seen.get(id) < WAIT) return;             // still loading, so wait
    box.insertAdjacentHTML("beforeend", line(id, t));
    box.dataset.anEmpty = "1";
    seen.delete(id);
  }

  function scan() {
    const t = tab();
    for (const id of BOXES) {
      try { look(id, t); } catch (err) { /* one box must not stop the other three */ }
    }
    // A box waiting out its settle time needs a second look, or it stays empty for the rest of the visit.
    if (seen.size) schedule(WAIT);
  }

  // The page repaints often, and a plain debounce that pushes its timer back on every change would never fire.
  // So one scan is queued at a time and a later change does not postpone it.
  let queued = 0;
  function schedule(ms) {
    if (queued) return;
    queued = setTimeout(() => { queued = 0; scan(); }, ms);
  }
  // The boxes are painted by other files, so let them settle before deciding a box holds nothing.
  function ping() { schedule(220); }

  document.addEventListener("peakcut:render", ping);
  if (typeof MutationObserver === "function") {
    try {
      const view = document.getElementById("view") || document.body;
      new MutationObserver(ping).observe(view, { childList: true, subtree: true });
    } catch (err) { /* the render signal below still runs the scan */ }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ping);
  else ping();

  // The shell calls load() on every analytics-* file when a range or a tab changes, so this is the second way in.
  // The two collapse into one scan.
  P.add("analytics-empty", { label: "Empty Insights boxes", load() { ping(); } });
})();
