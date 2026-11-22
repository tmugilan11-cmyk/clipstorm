/* Brand, transcription, tools and connected apps are their own rows in the menu, with their own addresses,
 * and each one draws the real form rather than a link back to Settings.
 *
 * The form is not copied: index.html exposes drawSettingTab(tab, box), so Settings and the menu page draw the
 * same code into different boxes and cannot drift apart. A save inside the page redraws the page it is on. */
(() => {
  window.PeakCut.css("menu-pages", `
    /* 880, the Usage page's own cap (.usg in web/feat/usage.js), so the menu family keeps one width
     * measured against the same container (#main>.content is 1480px in web/feat/polish-wide.js). */
    .pcpg{max-width:880px}
    .pcpg-h{font-size:23px;line-height:1.25;letter-spacing:-.01em;color:var(--ink);margin-bottom:6px}
    .pcpg .card{display:flex;flex-direction:column;align-items:flex-start;gap:12px}
    .pcpg .help{max-width:62ch;margin:0}
    .pcpg .hint{display:block}
    @media (max-width:560px){.pcpg-h{font-size:20px}}
  `);

  // What each moved setting is and what the page promises. One table, seven pages, no drift.
  const MOVED = {
    brand: {
      where: "Brand",
      tab: "brand",
      icon: "palette",
      what: "Caption style, the hook at the top, the watermark and the closing card. Save once and every clip made after that uses it.",
    },
    transcribe: {
      where: "Transcription",
      tab: "transcribe",
      icon: "microphone",
      admin: true,
      what: "A local model on this machine is the default. Logfare, a cloud service, is there for a slow machine or a better transcript.",
    },
    tools: {
      where: "Tools",
      tab: "tools",
      icon: "wand",
      what: "Scheduling and a command you can copy for this computer.",
    },
    apps: {
      where: "Connected apps",
      tab: "apps",
      icon: "plug",
      what: "Press Connect, sign in on the platform's own page, and you come back here. Clipstorm never sees your passwords. Then pick which accounts each channel posts to, in that channel's Setup on the Creators page.",
    },
    ai: {
      where: "AI",
      tab: "ai",
      icon: "bolt",
      admin: true,
      what: "The service that reads a transcript and picks the moments worth posting. Logfare, OpenAI, Gemini and a local Ollama are all rows in the same list.",
    },
    storage: {
      where: "Storage",
      tab: "storage",
      icon: "folder",
      admin: true,
      what: "Where the videos and the finished clips are kept on this machine, how much room is left, and what to delete when it runs low.",
    },
    account: {
      where: "Account",
      tab: "profile",
      icon: "user",
      what: "Your name, your email, the password you sign in with, and the way out of every other browser you left signed in.",
      two: ["profile", "security"],
    },
  };

  // Settings keeps transcription for an owner account only. Say so instead of opening a tab that is not there.
  const owner = () => {
    try {
      const s = window.PeakCut.state();
      return !!(s && s.status && s.status.user && s.status.user.is_admin);
    } catch { return false; }
  };

  // The page draws the real form. An owner-only tab shows a sentence instead of a form nobody could save.
  function fill(name) {
    const d = MOVED[name];
    const box = document.getElementById("pcpg_" + name);
    if (!d || !box) return;
    if (d.admin && !owner()) {
      box.innerHTML = `<div class="card">
        <span class="pill warn">Owner only</span>
        <p class="help">${esc(d.what)}</p>
        <p class="hint">Only an owner account can change this. Ask the owner of this Clipstorm.</p>
        <div class="row"><a class="btn" href="/app/settings">${ic("cog")}Open Settings</a></div>
      </div>`;
      return;
    }
    if (typeof drawSettingTab !== "function") {
      // Older page shell: say so plainly rather than showing an empty box.
      box.innerHTML = `<div class="card"><p class="hint">This build of the page cannot draw the form here yet. It is in Settings, on the ${esc(d.where)} tab.</p>
        <div class="row"><a class="btn" href="/app/settings/${esc(d.tab)}">${ic(d.icon)}Open ${esc(d.where)}</a></div></div>`;
      return;
    }
    box.innerHTML = `<div class="set-load">Loading…</div>`;
    const keep = box;
    // Account is two tabs: the profile form, then the password and sign-out form under it.
    if (d.two) {
      const first = document.createElement("div");
      const second = document.createElement("div");
      second.style.marginTop = "26px";
      keep.innerHTML = "";
      keep.appendChild(first);
      keep.appendChild(second);
      return Promise.resolve()
        .then(() => drawSettingTab(d.two[0], first))
        .then(() => drawSettingTab(d.two[1], second))
        .catch((err) => {
          if (keep.isConnected) keep.innerHTML = `<div class="card"><p class="hint">${esc(err && err.message ? err.message : "This could not be drawn.")}</p></div>`;
        });
    }
    // Hand the promise back: the loader waits for it before running the paint hooks, so a card that decorates
    // the form (the style tiles on Brand, for one) finds the form already there.
    return Promise.resolve(drawSettingTab(d.tab, keep)).catch((err) => {
      if (keep.isConnected) keep.innerHTML = `<div class="card"><p class="hint">${esc(err && err.message ? err.message : "This could not be drawn.")}</p></div>`;
    });
  }

  window.PeakCut.add("menu-pages", {
    about: "Brand, transcription, tools, connected apps, AI, storage and account now open from the main menu.",
    tabs: ["brand", "transcribe", "tools", "apps", "ai", "storage", "account"],
  });

  window.PeakCut.page("brand", {
    nav: "Brand",
    icon: "palette",
    tip: "Colours, captions, watermark and the closing card",
    path: "brand",
    group: "Look and sound",
    order: 30,
    view() {
      return `<div class="pcpg">
        <section class="set-sec"><h1 class="pcpg-h">Brand</h1>
          <p class="help">How everything Clipstorm makes for you looks.</p></section>
        <div id="pcpg_brand"></div>
      </div>`;
    },
    load() { return fill("brand"); },
  });

  window.PeakCut.page("transcribe", {
    nav: "Transcription",
    icon: "microphone",
    tip: "Speech to text, on this machine or in the cloud",
    path: "transcribe",
    group: "Understand",
    order: 24,
    view() {
      return `<div class="pcpg">
        <section class="set-sec"><h1 class="pcpg-h">Transcription</h1>
          <p class="help">How speech becomes text, so Clipstorm can find the moments worth cutting.</p></section>
        <div id="pcpg_transcribe"></div>
      </div>`;
    },
    load() { return fill("transcribe"); },
  });

  window.PeakCut.page("tools", {
    nav: "Tools",
    icon: "wand",
    tip: "Schedule when Clipstorm runs, or copy a command for this computer",
    path: "tools",
    group: "Set up",
    order: 40,
    view() {
      return `<div class="pcpg">
        <section class="set-sec"><h1 class="pcpg-h">Tools</h1>
          <p class="help">Schedules only. Set run times or export a command for this computer.</p></section>
        <div id="pcpg_tools"></div>
      </div>`;
    },
    load() { return fill("tools"); },
  });

  window.PeakCut.page("apps", {
    nav: "Connected apps",
    icon: "plug",
    tip: "Where your clips get posted",
    path: "apps",
    group: "Set up",
    order: 44,
    view() {
      return `<div class="pcpg">
        <section class="set-sec"><h1 class="pcpg-h">Connected apps</h1>
          <p class="help">The accounts Clipstorm posts clips to.</p></section>
        <div id="pcpg_apps"></div>
      </div>`;
    },
    load() { return fill("apps"); },
  });

  window.PeakCut.page("ai", {
    nav: "AI",
    icon: "bolt",
    tip: "The service that picks the moments worth posting",
    path: "ai",
    group: "Set up",
    order: 46,
    admin: true,
    view() {
      return `<div class="pcpg">
        <section class="set-sec"><h1 class="pcpg-h">AI</h1>
          <p class="help">Which service reads the transcript and chooses the clips.</p></section>
        <div id="pcpg_ai"></div>
      </div>`;
    },
    load() { return fill("ai"); },
  });

  window.PeakCut.page("storage", {
    nav: "Storage",
    icon: "folder",
    tip: "Where the videos and clips are kept, and how much room is left",
    path: "storage",
    group: "Account",
    order: 62,
    admin: true,
    view() {
      return `<div class="pcpg">
        <section class="set-sec"><h1 class="pcpg-h">Storage</h1>
          <p class="help">Where the files live and what to do when the disk fills up.</p></section>
        <div id="pcpg_storage"></div>
      </div>`;
    },
    load() { return fill("storage"); },
  });

  window.PeakCut.page("account", {
    nav: "Account",
    icon: "user",
    tip: "Your name, email, password and signed-in browsers",
    path: "account",
    group: "Account",
    order: 60,
    view() {
      return `<div class="pcpg">
        <section class="set-sec"><h1 class="pcpg-h">Account</h1>
          <p class="help">Who you are here, and how you sign in.</p></section>
        <div id="pcpg_account"></div>
      </div>`;
    },
    load() { return fill("account"); },
  });
})();
