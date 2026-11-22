/* The AI spend, as its own row in the main menu: how many calls, how many tokens, what a day looked like,
 * which model answered, and a straight answer about the money.
 *
 * Reads GET /api/usage (in studio/server.py, built by studio/usage.py summary()). That route records calls,
 * tokens, purposes, creators and a daily series. It records no price, so this page never does the arithmetic
 * for a bill: it says the cost is not known and who does know it. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  P.css("usage", `
    .usg{max-width:880px}
    .usg-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--text);margin-bottom:6px}
    .usg-lede{max-width:62ch;margin:0}
    .usg-svc{margin:14px 0 0;padding:0;font-size:13px;line-height:1.6;color:var(--dim)}
    .usg-svc b{color:var(--text);font-weight:600}
    .usg-svc .pill{margin-left:6px}

    .usg-ledger{display:grid;grid-template-columns:1fr 1fr 1.5fr;margin-top:20px;border:1px solid var(--line);
      border-radius:12px;background:var(--bg);overflow:hidden}
    .usg-cell{padding:15px 17px 16px;min-width:0;border-left:1px solid var(--line)}
    .usg-cell:first-child{border-left:0}
    .usg-k{display:block;font-size:12px;font-weight:600;color:var(--dim)}
    .usg-v{margin-top:7px;font-size:26px;font-weight:600;line-height:1.1;letter-spacing:-.03em;
      color:var(--text);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
    .usg-v.txt{margin-top:6px;font-size:14px;line-height:1.5;font-weight:400;letter-spacing:0;color:var(--text)}
    .usg-sub{margin-top:6px;font-size:12px;line-height:1.45;color:var(--faint)}

    .usg-sec{margin-top:26px}
    .usg-sec h2{font-size:15px;line-height:1.3;font-weight:600;color:var(--text);margin:0}
    .usg-sec p.sub{margin:3px 0 0;font-size:13px;line-height:1.5;color:var(--dim);max-width:62ch}
    .usg-plot{margin-top:12px;border:1px solid var(--line);border-radius:12px;background:var(--bg);padding:14px 14px 10px}
    .usg-plot svg{display:block;width:100%;height:auto;overflow:visible}
    .usg-plot .bar{fill:var(--brand)}
    /* The zero-tick and the chart baseline are meaningful graphics, so WCAG 1.4.11 wants 3:1. --line-2 #2A2A2A
       measures 1.38:1 on the chart's --bg #0A0A0A, invisible; --faint #A0948C measures 6.70:1, so both use it. */
    .usg-plot .none{fill:var(--faint)}
    .usg-plot .base{stroke:var(--faint);stroke-width:1}
    .usg-axis{display:flex;justify-content:space-between;gap:10px;margin-top:6px;font-size:12px;color:var(--faint);
      font-variant-numeric:tabular-nums}
    .usg-peak{margin:0 0 10px;font-size:13px;color:var(--dim)}
    .usg-peak b{color:var(--text);font-weight:600;font-variant-numeric:tabular-nums}

    .usg-brow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 14px;align-items:baseline;
      padding:10px 2px;border-top:1px solid var(--line);font-size:13px}
    .usg-brow:first-of-type{border-top:0}
    .usg-bname{min-width:0;overflow-wrap:anywhere;color:var(--text)}
    .usg-bmeta{font-size:12px;color:var(--faint);font-variant-numeric:tabular-nums;white-space:nowrap}
    .usg-track{grid-column:1/-1;height:3px;border-radius:99px;background:var(--line);overflow:hidden}
    .usg-track i{display:block;height:100%;background:var(--brand);border-radius:99px}

    .usg-empty{margin:18px 0 0;padding:20px 18px;border:1px solid var(--line);border-radius:12px;background:var(--muted)}
    .usg-empty b{display:block;font-size:14px;font-weight:600;color:var(--text);margin-bottom:5px}
    .usg-empty span{display:block;font-size:13px;line-height:1.55;color:var(--dim);max-width:60ch}
    .usg-wait{margin-top:22px;font-size:13px;color:var(--dim)}
    .usg-line{margin-top:14px;font-size:13px;line-height:1.5;color:var(--dim);max-width:66ch}
    .usg-line b{color:var(--text);font-weight:600}
    .usg-foot{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:26px;padding-top:16px;border-top:1px solid var(--line)}
    .usg-foot .hint{display:block;flex:1 1 220px;margin:0}

    @media (max-width:700px){
      .usg-ledger{grid-template-columns:1fr}
      .usg-cell{border-left:0;border-top:1px solid var(--line)}
      .usg-cell:first-child{border-top:0}
      .usg-h{font-size:20px}.usg-v{font-size:23px}
    }
  `);

  const BOX = "usg_body";
  const fill = (html) => { const box = document.getElementById(BOX); if (box) box.innerHTML = html; };

  // The page's icon map, when the frame has one. An empty string leaves the words readable either way.
  const icon = (n) => (typeof window.ic === "function" ? window.ic(n) : "");

  // Every string from the server goes through here before it reaches markup.
  const esc = (v) => (typeof window.esc === "function"
    ? window.esc(v == null ? "" : v)
    : String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])));

  // A number, or null. Never a silent zero for a value the route did not send.
  const num = (v) => { if (v === null || v === undefined || v === "") return null;
    const n = Number(v); return Number.isFinite(n) ? n : null; };
  const text = (v) => (typeof v === "string" && v.trim()) ? v.trim() : "";
  const list = (v) => Array.isArray(v) ? v : [];

  // True when the signed-in user may change the AI settings: the same check menu-pages.js makes.
  const mayChangeAI = () => {
    try {
      const s = P.state();
      return !!(s && s.status && s.status.user && s.status.user.is_admin);
    } catch { return false; }
  };

  const count = (n) => Number(n).toLocaleString("en-US");
  // Long token counts stay readable in a 26px figure.
  const tokens = (n) => { if (n === null) return "not known"; if (n < 10000) return count(n);
    if (n < 1000000) return (n / 1000).toFixed(n < 100000 ? 1 : 0) + "k";
    return (n / 1000000).toFixed(1) + "m"; };
  const exact = (n) => n === null ? "not known" : count(n);

  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  // "2026-11-20" reads as "20 Nov". Split by hand: a Date would move the day across a time zone.
  function dayLabel(v) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v || ""));
    if (!m) return text(v);
    const d = num(m[3]), mo = num(m[2]);
    if (d === null || mo === null || mo < 1 || mo > 12) return text(v);
    return d + " " + MONTHS[mo - 1];
  }

  /* ---- the three figures ------------------------------------------------- */
  function ledger(k) {
    const calls = num(k.calls_total), toks = num(k.tokens_total);
    const todayCalls = num(k.today_calls), todayToks = num(k.today_tokens);
    // A null here is a day the route said nothing about, so it is named as missing rather than counted as zero.
    const sayCalls = (n) => n === null ? "calls not sent" : count(n) + (n === 1 ? " call" : " calls");
    const sayToks = (n) => n === null ? "tokens not sent" : tokens(n) + " tokens";
    const today = todayCalls || todayToks
      ? sayCalls(todayCalls) + " today, " + sayToks(todayToks)
      : "None today";

    // The route sends no price, so there is no arithmetical way to a dollar figure. Say that, out loud.
    return `<div class="usg-ledger">
      <div class="usg-cell">
        <span class="usg-k">AI calls</span>
        <div class="usg-v">${calls === null ? "not known" : count(calls)}</div>
        <div class="usg-sub">${esc(today)}</div>
      </div>
      <div class="usg-cell">
        <span class="usg-k">Tokens</span>
        <div class="usg-v">${esc(tokens(toks))}</div>
        <div class="usg-sub">${toks === null ? "Read in and written out together"
          : esc(exact(toks)) + " exactly, read in and written out together"}</div>
      </div>
      <div class="usg-cell">
        <span class="usg-k">What it cost</span>
        <div class="usg-v txt">Not known</div>
        <div class="usg-sub">Clipstorm measures tokens, not money. The AI service bills whoever owns the key, on its own rates, so any figure printed here would be a guess.</div>
      </div>
    </div>`;
  }

  /* ---- the per-day bars -------------------------------------------------- */
  function plot(series) {
    // A day the route did not send a count for keeps its null. It is not zero: a day with no AI calls is a fact the
    // server states, and a day it said nothing about is a gap in the answer. The chart draws those differently.
    const rows = list(series).map((d) => ({
      day: text(d && d.day),
      tokens: num(d && d.tokens),
      calls: num(d && d.calls),
    }));
    if (!rows.length) {
      return `<div class="usg-line">This route sent no daily series, so there is no chart to draw. Calls and tokens above are still the real totals.</div>`;
    }

    const said = rows.filter((r) => r.tokens !== null);
    const gaps = rows.length - said.length;
    const max = said.reduce((a, r) => Math.max(a, r.tokens), 0);
    const n = rows.length, W = 720, H = 160, PL = 3, PR = 3, PT = 12, PB = 8;
    const inner = W - PL - PR, step = inner / n, base = H - PB;
    const bw = Math.max(2.2, Math.min(16, step * 0.58));
    const bars = rows.map((r, i) => {
      const x = PL + step * i + (step - bw) / 2;
      // null is a day the route said nothing about, so nothing is drawn for it: a tick would claim a zero.
      if (r.tokens === null) return "";
      const h = max > 0 ? (r.tokens / max) * (base - PT) : 0;
      if (!h) {
        // A day the route did report as zero still gets a tick: the row of days must not read as a shorter week.
        return `<rect class="none" x="${(PL + step * i + (step - 2) / 2).toFixed(1)}" y="${base - 1}" width="2" height="1"></rect>`;
      }
      const y = base - Math.max(2, h);
      const say = dayLabel(r.day) + ": " + exact(r.tokens) + (r.tokens === 1 ? " token" : " tokens") +
        ", " + (r.calls === null ? "calls not sent" : count(r.calls) + (r.calls === 1 ? " call" : " calls"));
      return `<rect class="bar" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${(base - y).toFixed(1)}" rx="1.5"><title>${esc(say)}</title></rect>`;
    }).join("");

    let peak = "";
    if (max > 0) {
      const top = said.filter((r) => r.tokens === max)[0];
      const calls = top.calls === null ? "calls not sent" : count(top.calls) + (top.calls === 1 ? " call" : " calls");
      peak = `<p class="usg-peak">Busiest day: <b>${esc(dayLabel(top.day))}</b>, ${esc(exact(max))} tokens in ${esc(calls)}.</p>`;
    }
    const aria = max > 0
      ? `Tokens per day over ${n} days. Highest day ${exact(max)} tokens.`
      : said.length
        ? `Tokens per day over ${n} days. No tokens recorded in any of them.`
        : `Tokens per day over ${n} days. The route did not send a count for any of them.`;
    const gapLine = gaps
      ? `<p class="usg-peak">${gaps === 1 ? "One day in this range has" : gaps + " days in this range have"} no count from the route, so ${gaps === 1 ? "it is" : "they are"} left out of the chart rather than drawn as zero.</p>`
      : "";

    // Label the first, middle and last day, not just the two ends. The per-bar dates live in hover-only
    // titles, so on a touch screen the middle days carried no readable date at all.
    const axisIdx = [0];
    if (n > 2) {
      const mid = Math.floor((n - 1) / 2);
      if (mid > 0 && mid < n - 1) axisIdx.push(mid);
    }
    if (n > 1) axisIdx.push(n - 1);
    const axis = axisIdx.map((i) => `<span>${esc(dayLabel(rows[i].day))}</span>`).join("");

    return `${peak}<div class="usg-plot">
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">
        <line class="base" x1="${PL}" y1="${base}" x2="${W - PR}" y2="${base}"></line>${bars}
      </svg>
      <div class="usg-axis">${axis}</div>
    </div>${gapLine}`;
  }

  /* ---- what the tokens went on ------------------------------------------- */
  function purposes(rows) {
    const got = list(rows).filter((r) => Array.isArray(r) && text(r[0]));
    if (!got.length) return "";
    const top = got.reduce((a, r) => Math.max(a, num(r[1]) === null ? 0 : num(r[1])), 0) || 1;
    // The server sends every purpose, ordered by tokens; the eight largest are drawn and the rest are named
    // here rather than vanishing silently.
    const shown = got.slice(0, 8);
    const smaller = got.length - shown.length;
    return `<div class="usg-sec"><h2>What the AI worked on</h2>
      <p class="sub">All time, by the purpose Clipstorm recorded for each call.</p>
      ${shown.map((r) => {
        // A purpose the route sent no numbers for still gets a row: it happened, and its bar is simply empty.
        const t = num(r[1]), c = num(r[2]);
        const width = t === null ? 0 : Math.max(1.5, (t / top) * 100);
        return `<div class="usg-brow">
          <span class="usg-bname">${esc(text(r[0]))}</span>
          <span class="usg-bmeta">${esc(exact(c))} ${c === 1 ? "call" : "calls"} / ${esc(exact(t))} tokens</span>
          <span class="usg-track"><i style="width:${width.toFixed(1)}%"></i></span>
        </div>`;
      }).join("")}
      ${smaller ? `<p class="sub">and ${smaller} smaller ${smaller === 1 ? "purpose" : "purposes"}, still counted in the totals above.</p>` : ""}
    </div>`;
  }

  /* ---- the page body ----------------------------------------------------- */
  function body(k) {
    const calls = num(k.calls_total), toks = num(k.tokens_total);
    const nothingYet = (calls === null || calls === 0) && (toks === null || toks === 0);

    const service = (() => {
      const model = text(k.model), provider = text(k.provider);
      if (k.ready === false) {
        // /api/ai is owner-only, so a standard user is told who to ask instead of being sent to a form they cannot save.
        const how = mayChangeAI()
          ? `Add one under <a class="lnk" href="/app/settings/ai">AI in Settings</a>.`
          : `Ask the owner to add one under <a class="lnk" href="/app/settings/ai">AI in Settings</a>.`;
        return `<p class="usg-svc">${icon("bolt")}<span class="pill warn">Not set up</span> No AI key is saved, so no call has been possible. ${how}</p>`;
      }
      const modelBit = model ? `Model <b>${esc(model)}</b>` : `The service did not name a model`;
      const provBit = provider ? `Service <b>${esc(provider)}</b>` : `The service did not name itself`;
      // Call rows persist across provider switches, so an older row may have been answered by another service.
      return `<p class="usg-svc">${provBit}. ${modelBit}. The service in use now answers new calls.</p>`;
    })();

    // The route really did send zeros, so the totals stay on the page: a counted zero is a fact.
    // What goes away is the chart and the split, which have nothing to draw yet.
    if (nothingYet) {
      return `${service}
        ${ledger(k)}
        <div class="usg-empty">
          <b>No AI call has been made yet.</b>
          <span>This account has none of its calls, tokens or daily bars to show. The first one appears here within
          a few seconds of Clipstorm asking the AI to read a transcript and pick the moments.</span>
        </div>
        <p class="usg-line"><b>About the money:</b> this page never prints a price it was not given. When calls do
        start, you will see tokens; the bill comes from the AI service that owns the key, at its own rates.</p>`;
    }

    const problem = text(k.problem);
    const warn = problem ? `<p class="err">The AI reported a problem: ${esc(problem)}</p>` : "";

    return `${service}
      ${ledger(k)}
      ${warn}
      <div class="usg-sec"><h2>Tokens per day</h2>
        <p class="sub">The ${list(k.daily).length || 0} days the server sent, ending today. A taller bar means more of
        the AI's attention went to that day.</p>
        ${plot(k.daily)}
      </div>
      ${purposes(k.by_purpose)}`;
  }

  async function load() {
    fill(`<div class="usg-wait">Reading what the AI has been used for.</div>`);
    let k;
    try {
      k = await P.api("/api/usage");
    } catch (err) {
      const why = text(err && err.message) || "the request failed";
      fill(`<div class="err">Could not read the AI usage: ${esc(why)}</div>
        <p class="usg-line">The rest of Clipstorm keeps working. Press Refresh to ask again.</p>`);
      return;
    }
    try {
      fill(body(k && typeof k === "object" ? k : {}));
    } catch (err) {
      fill(`<div class="err">The usage figures arrived but could not be drawn: ${esc(text(err && err.message) || "unknown reason")}</div>`);
    }
  }

  P.add("usage", {
    about: "The AI spend: calls, tokens, the model, and a chart of the days.",
    act: { usgload() { return load(); } },
  });

  P.page("ai-usage", {
    nav: "Usage",
    icon: "chart",
    tip: "How much AI was used, in calls and tokens",
    path: "ai-usage",
    group: "Set up",
    order: 48,
    view() {
      return `<div class="usg">
        <section class="set-sec"><h1 class="usg-h">Usage</h1>
          <p class="help usg-lede">Every AI call this account has made: how many, how many tokens, which model, and how
          the days compare.</p></section>
        <div id="${BOX}"></div>
        <div class="usg-foot">
          <button class="btn" data-act="usgload">Refresh</button>
          <span class="hint">Asks the server again. Nothing is charged by pressing this.</span>
        </div>
      </div>`;
    },
    load() { return load(); },
  });
})();
