/* What worked on your channel: the clips you posted, best to worst, with the numbers they really got, the
 * sentences the clip judge is told because of them, and a step-by-step "Connect your YouTube channel" guide.
 *
 * It only draws what the server sends (/api/own-results and /api/own-results/youtube). It never shows a number
 * it was not given: a clip with no watch figure says so instead of showing 0%. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.page !== "function") return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icon = (n) => { try { return typeof ic === "function" ? ic(n) : ""; } catch { return ""; } };

  P.css("own-results", `
    .own{max-width:980px;display:flex;flex-direction:column;gap:16px}
    .own h2{margin:0;font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--text)}
    .own h3{margin:0 0 6px;font-size:16px;color:var(--text)}
    .own .lead{margin:0;color:var(--dim);max-width:70ch}
    .own .box{border:1px solid var(--line);background:var(--card);border-radius:var(--r);padding:16px 18px}
    .own .head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px}
    .own .state{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--dim)}
    .own .dot{width:9px;height:9px;border-radius:50%;background:var(--faint);flex:none}
    .own .dot.ok{background:var(--good)}.own .dot.bad{background:var(--bad)}
    .own ol.steps{margin:8px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:10px;counter-reset:ownstep}
    .own ol.steps>li{counter-increment:ownstep;display:grid;grid-template-columns:28px 1fr;gap:10px;align-items:start;color:var(--text)}
    .own ol.steps>li::before{content:counter(ownstep);display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;border:1px solid var(--line-2);color:var(--dim);font-weight:600;font-size:13px}
    .own ol.steps>li.done::before{content:"\\2713";background:var(--good-soft);border-color:var(--good);color:var(--good)}
    .own ol.steps>li.now::before{background:var(--brand);border-color:var(--brand);color:var(--brand-ink)}
    .own .st small{display:block;color:var(--dim);margin-top:3px;font-size:13px}
    .own .copyrow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:8px}
    .own .copyrow code{flex:1 1 260px;min-width:0;overflow-wrap:anywhere;padding:8px 10px;border:1px solid var(--line-2);border-radius:var(--r-sm);background:var(--field);color:var(--text)}
    .own .fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:8px}
    .own .fields label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--dim)}
    .own .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
    .own .note{margin:8px 0 0;padding:8px 10px;border-radius:var(--r-sm);background:var(--brand-soft);color:var(--text);font-size:13px}
    .own .note.bad{background:var(--bad-soft)}.own .note.good{background:var(--good-soft)}
    .own .scroll{overflow-x:auto}
    .own table{width:100%;border-collapse:collapse;font-size:13px}
    .own th{text-align:left;color:var(--dim);font-weight:600;padding:6px 8px;border-bottom:1px solid var(--line-2);white-space:nowrap}
    .own td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top;color:var(--text)}
    .own td.n,.own th.n{text-align:right;white-space:nowrap}
    .own td small{display:block;color:var(--dim)}
    .own tr:hover td{background:var(--muted)}
    .own .x.up{color:var(--good)}.own .x.down{color:var(--bad)}
    .own .none{color:var(--dim)}
    .own ul.told{margin:6px 0 0;padding-left:18px;display:flex;flex-direction:column;gap:6px;color:var(--text)}
    .own a{color:var(--brand-deep)}
    @media (max-width:640px){.own h2{font-size:20px}}
  `);

  let DATA = null, YT = null, TEST = null, BUSY = false, HELP = null, FAILED = "";
  const root = () => document.getElementById("own_root");

  const num = (v) => (typeof v === "number" && isFinite(v) ? v : null);
  const short = (v) => {
    const n = num(v);
    if (n === null) return "";
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1e4) return Math.round(n / 1e3) + "k";
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
    return String(Math.round(n));
  };
  const ago = (t) => {
    const n = num(t);
    if (!n) return "never";
    const m = Math.max(0, Math.round((Date.now() / 1000 - n) / 60));
    if (m < 2) return "just now";
    if (m < 90) return m + " minutes ago";
    const h = Math.round(m / 60);
    return h < 36 ? h + " hours ago" : Math.round(h / 24) + " days ago";
  };

  /* ---- the guide ---------------------------------------------------------------------------------------- */
  function guide() {
    const y = YT || {};
    const ready = !!y.app_ready, connected = !!y.connected;
    const tested = !!(TEST && TEST.ok);
    // The first five steps happen on Google's site; the page only knows they are done once the keys are saved.
    const at = tested ? 8 : connected ? 7 : ready ? 6 : 1;
    const cls = (i) => (i < at ? "done" : i === at ? "now" : "");
    const redirect = String(y.redirect || "");
    const loopback = /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(redirect);
    const odd = redirect && !loopback && !/^https:\/\//.test(redirect);
    const pill = connected
      ? `<span class="state"><span class="dot ${y.token_ok === false || y.analytics_scope === false ? "bad" : "ok"}"></span>Connected as <b>${esc(y.name || "your channel")}</b></span>`
      : `<span class="state"><span class="dot"></span>Not connected yet</span>`;
    const problem = connected && y.token_ok === false
      ? `<p class="note bad">${esc(y.error || "Google no longer accepts the saved sign-in.")} Press <b>Connect YouTube</b> again.</p>`
      : connected && y.analytics_scope === false
        ? `<p class="note bad">Google did not give permission to read your numbers. Press <b>Connect YouTube</b> again and leave every tick box ticked.</p>` : "";
    const result = TEST ? `<p class="note ${TEST.ok ? "good" : "bad"}">${esc(TEST.message || "")}</p>` : "";
    const open = HELP === null ? !connected : HELP;
    return `<section class="box" aria-label="Connect your YouTube channel">
      <div class="head"><h3>Connect your YouTube channel</h3>${pill}</div>
      <p class="lead">Connecting lets Clipstorm read how your clips did (views, how much people watched, who stayed past the first seconds) so the clip judge can learn from your own results. It can only read numbers and post the clips you send. It never sees your password. You do this once.</p>
      ${problem}${result}
      <div class="row">
        ${ready ? `<a class="btn primary" href="/oauth/youtube/start">${icon("plug")}${connected ? "Connect again" : "Connect YouTube"}</a>` : ""}
        ${connected ? `<button class="btn" type="button" data-act="owntest">${icon("check")}Test the connection</button>` : ""}
        <button class="btn ghost" type="button" data-act="ownhelp">${open ? "Hide the steps" : "Show the steps"}</button>
      </div>
      ${open ? `<ol class="steps">
        <li class="${cls(1)}"><div class="st">Open <a href="https://console.cloud.google.com/projectcreate" target="_blank" rel="noopener">Google Cloud</a> and sign in with the Google account that owns your YouTube channel. Name the project <b>Clipstorm</b> and press <b>Create</b>.<small>This is a free page. It is only used to give Clipstorm its own key.</small></div></li>
        <li class="${cls(2)}"><div class="st">In the left menu choose <b>APIs &amp; Services</b>, then <b>Library</b>. Search for <b>YouTube Data API v3</b>, open it and press <b>Enable</b>. Then do the same for <b>YouTube Analytics API</b>.<small>You need both. They are two separate switches, and the numbers do not work if one is off.</small></div></li>
        <li class="${cls(3)}"><div class="st">Open <a href="https://console.cloud.google.com/apis/credentials/consent" target="_blank" rel="noopener">the consent screen</a> (it may be called <b>Google Auth Platform</b>). Choose <b>External</b>, call the app <b>Clipstorm</b>, type your own email where it asks, and save. Under <b>Test users</b> (or <b>Audience</b>) add your own Google email address.<small>Optional but handy: press <b>Publish app</b>. Left on Testing, Google signs you out every 7 days and you press Connect again.</small></div></li>
        <li class="${cls(4)}"><div class="st">Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener">Credentials</a>, press <b>Create credentials</b>, then <b>OAuth client ID</b>. For the type choose <b>Web application</b>. Under <b>Authorised redirect URIs</b> press <b>Add URI</b> and paste this exact address, then press <b>Create</b>.
          <div class="copyrow"><code>${esc(redirect)}</code><button class="btn sm" type="button" data-act="owncopy" data-t="${esc(redirect)}">${icon("copy")}Copy</button></div>
          ${odd ? `<p class="note bad">Google only accepts this address if it starts with https, or is a local one (127.0.0.1 or localhost). Set PEAKCUT_PUBLIC_URL to your https address first.</p>` : ""}</div></li>
        <li class="${cls(5)}"><div class="st">Google now shows a <b>Client ID</b> and a <b>Client secret</b>. Paste them here and press <b>Save</b>.
          <div class="fields"><label>Client ID<input id="own_cid" autocomplete="off" spellcheck="false" placeholder="${ready ? "Saved. Paste a new one to replace it" : "123456789-abc.apps.googleusercontent.com"}"></label>
            <label>Client secret<input id="own_csecret" type="password" autocomplete="off" spellcheck="false" placeholder="${ready ? "Saved. Paste a new one to replace it" : "GOCSPX-..."}"></label></div>
          <div class="row"><button class="btn" type="button" data-act="ownsave">Save</button></div></div></li>
        <li class="${cls(6)}"><div class="st">Press <b>Connect YouTube</b> above and sign in. Google may say <b>Google hasn't verified this app</b>. That is normal, because the app is yours: press <b>Advanced</b>, then <b>Go to Clipstorm</b>. Leave every tick box ticked and press <b>Continue</b>.</div></li>
        <li class="${cls(7)}"><div class="st">You land back on Connected apps. Open <b>What worked</b> again and press <b>Test the connection</b>. It should say it can read your views and watch time.</div></li>
      </ol>` : ""}
    </section>`;
  }

  /* ---- the results ---------------------------------------------------------------------------------------- */
  function times(r) {
    const x = num(r.vs_median);
    if (r.young) return `<span class="none">too new</span>`;
    if (x === null) return `<span class="none">-</span>`;
    return `<span class="x ${x >= 1.5 ? "up" : x <= 0.5 ? "down" : ""}">${esc(String(x))}x</span>`;
  }
  function row(r) {
    const name = esc(r.title || r.hook || "A clip");
    const link = /^https?:\/\//.test(String(r.url || "")) ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${name}</a>` : name;
    const bits = [r.kind, num(r.length) ? Math.round(r.length) + " s" : "", r.platform].filter(Boolean).map(esc).join(" / ");
    const watched = num(r.avg_view_pct) !== null ? Math.round(r.avg_view_pct) + "%" : `<span class="none">-</span>`;
    const held = num(r.kept_3s) !== null ? Math.round(r.kept_3s * 100) + "%" : `<span class="none">-</span>`;
    return `<tr><td>${link}<small>${bits}</small></td>
      <td class="n">${r.judge_score ? esc(String(r.judge_score)) : `<span class="none">-</span>`}</td>
      <td class="n">${esc(short(r.views) || "0")}</td>
      <td class="n">${num(r.likes) !== null ? esc(short(r.likes) || "0") : `<span class="none">-</span>`}</td>
      <td class="n">${watched}</td><td class="n">${held}</td><td class="n">${times(r)}</td></tr>`;
  }
  function results() {
    const d = DATA;
    if (!d) return `<section class="box"><p class="lead">${esc(FAILED || "Reading your results...")}</p></section>`;
    const rows = d.rows || [];
    const status = `${rows.length} clip${rows.length === 1 ? "" : "s"} measured. Updated ${esc(ago(d.updated))}.${d.youtube ? "" : " YouTube is not connected, so watch time is missing."}`;
    const table = rows.length ? `<div class="scroll"><table><thead><tr><th>Clip</th><th class="n">Judge gave</th><th class="n">Views</th><th class="n">Likes</th><th class="n">Watched</th><th class="n">At 3 s</th><th class="n">vs usual</th></tr></thead><tbody>${rows.map(row).join("")}</tbody></table></div>`
      : `<p class="lead">Nothing is measured yet. Post some clips from Clipstorm and come back: numbers appear once a clip has been up for a day or two.</p>`;
    const lines = d.lines || [];
    const told = lines.length ? `<ul class="told">${lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>`
      : `<p class="lead">Nothing yet. The judge needs at least 3 clips that have been up for two days or more, each with a view count, before it is told anything.</p>`;
    const err = d.error ? `<p class="note bad">${esc(d.error)}</p>` : "";
    return `<section class="box"><div class="head"><h3>What worked on your channel</h3>
        <button class="btn" type="button" data-act="ownrefresh" ${BUSY || d.refreshing ? "disabled" : ""}>${icon("refresh")}${BUSY || d.refreshing ? "Reading..." : "Refresh"}</button></div>
        <p class="lead">${status} Best first. "vs usual" is the clip's views divided by your own typical clip on the same site.</p>${err}${table}</section>
      <section class="box"><h3>What the judge will be told</h3>
        <p class="lead">These short sentences go to the AI that picks moments, so it leans toward what your own audience watched.</p>${told}</section>`;
  }

  function paint() {
    const el = root();
    if (!el) return;
    el.innerHTML = `<h2>What worked</h2><p class="lead">See which of your posted clips did well and badly, in your own numbers, and teach the clip judge from them.</p>${results()}${guide()}`;
  }

  async function load() {
    paint();
    const [a, b] = await Promise.all([
      P.api("/api/own-results").catch((e) => { FAILED = String((e && e.message) || "Could not read your results."); return null; }),
      P.api("/api/own-results/youtube").catch(() => null),
    ]);
    DATA = a; YT = b;
    paint();
  }

  // After "Refresh" the pass runs on the server on its own: look again a few times until it says it is done.
  async function follow() {
    for (let i = 0; i < 20 && root(); i++) {
      await new Promise((r) => setTimeout(r, 2500));
      try { DATA = await P.api("/api/own-results"); } catch { break; }
      paint();
      if (!DATA.refreshing) break;
    }
    try { YT = await P.api("/api/own-results/youtube"); } catch {}
    BUSY = false;
    paint();
  }

  P.page("worked", {
    nav: "What worked",
    icon: "chart",
    group: "Understand",
    order: 24,
    path: "what-worked",
    tip: "Which of your posted clips did well, and connect YouTube so the judge can learn from them",
    view() { return `<div class="own" id="own_root"></div>`; },
    load,
  });

  P.add("own-results", {
    act: {
      async ownrefresh() {
        BUSY = true; paint();
        try { DATA = await P.send("/api/own-results/refresh", {}, "POST"); } catch (e) { BUSY = false; paint(); throw e; }
        paint();
        follow();
      },
      async owncopy(btn) {
        try { await navigator.clipboard.writeText(btn.dataset.t || ""); P.toast("Copied", "ok"); }
        catch { P.toast("Select the address and copy it by hand.", "bad"); }
      },
      async ownsave() {
        const id = (document.getElementById("own_cid") || {}).value || "";
        const secret = (document.getElementById("own_csecret") || {}).value || "";
        if (!id.trim() && !secret.trim()) { P.toast("Paste the Client ID and the Client secret first.", "bad"); return; }
        await P.send("/api/apps", { platform: "youtube", client_id: id, client_secret: secret }, "PUT");
        P.toast("Saved. Now press Connect YouTube.", "ok");
        try { YT = await P.api("/api/own-results/youtube"); } catch {}
        paint();
      },
      async owntest() {
        TEST = { ok: false, message: "Testing..." }; paint();
        try { TEST = await P.send("/api/own-results/youtube/test", {}, "POST"); }
        catch (e) { TEST = { ok: false, message: String((e && e.message) || "The test could not run.") }; }
        try { YT = await P.api("/api/own-results/youtube"); } catch {}
        paint();
      },
      ownhelp() {
        const y = YT || {};
        HELP = HELP === null ? !!y.connected : !HELP;
        paint();
      },
    },
  });
})();
