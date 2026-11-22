// What the two sound switches will do to this clip, said before the clip is made.
//
// The estimate is a forecast worked out from the words this clip already has, using the same rules the renderer uses,
// so the number on the page cannot disagree with the clip that comes out. It names what will go, in plain words.
(function () {
  "use strict";
  const P = window.PeakCut;
  if (!P) return;

  const CURSE = [
    "ass", "asses", "asshole", "assholes", "bastard", "bastards", "bitch", "bitches", "bollocks", "bullshit",
    "cock", "cocks", "cunt", "cunts", "damn", "damned", "dick", "dicks", "dickhead", "fuck", "fucked", "fucker",
    "fuckers", "fucking", "fucks", "goddamn", "hell", "motherfucker", "motherfuckers", "motherfucking", "piss",
    "pissed", "prick", "pricks", "pussy", "shit", "shits", "shitty", "slut", "sluts", "twat", "twats", "wanker",
    "wankers", "whore", "whores",
  ];
  const FILLER = ["um", "umm", "uhm", "uh", "uhh", "uhhh", "erm", "er", "ah", "ahh", "eh", "hmm", "hmmm", "mmm",
    "mhm", "mm", "uh-huh", "uhhuh"];
  const PAIRS = [["you", "know"], ["i", "mean"], ["sort", "of"], ["kind", "of"], ["you", "see"]];
  const PAUSE_CUT = 0.85;
  const PAUSE_LEAVE = 0.30;
  const BAD = new Set(CURSE);

  const plain = (w) => (String(w || "").toLowerCase().replace(/\u2019/g, "'").match(/[a-z']+/) || [""])[0];

  // The words of the clip, in the video's own seconds. The clip's own transcript is asked for once and kept, so
  // flipping a switch does not fetch it again. A failed ask is not kept, so trying again asks again.
  const keyOf = (job, clip) => `${(job && job.id) || ""}:${clip && clip.id}`;
  let cache = { key: "", words: [], failed: false };
  function wordsFor(job, clip) {
    const key = keyOf(job, clip);
    if (cache.key === key && !cache.failed) return Promise.resolve(cache.words);
    if (Array.isArray(clip && clip.fixed_words) && clip.fixed_words.length) {
      cache = { key, words: clip.fixed_words, failed: false };
      return Promise.resolve(cache.words);
    }
    if (!job || !clip) return Promise.resolve([]);
    return P.api(`/api/jobs/${encodeURIComponent(job.id)}/clips/${encodeURIComponent(clip.id)}/words`)
      .then((got) => {
        const got2 = ((got && got.words) || []).map((w) => ({ w: w.w, s: w.s != null ? w.s + (job.offset || 0) : 0,
          e: w.e != null ? w.e + (job.offset || 0) : 0 }));
        cache = { key, words: got2, failed: false };
        return got2;
      })
      .catch(() => {
        cache = { key, words: [], failed: true };   // the server did not answer; that is not "no timings"
        return [];
      });
  }

  function forecast(words, start, end) {
    const span = Math.max(0, end - start);
    if (!words.length || span <= 0) return { cut: 0, bleeped: 0, filler: 0, pauses: 0 };
    const times = words
      .map((w) => ({ s: Math.max(0, w.s - start), e: Math.min(span, w.e - start), w: plain(w.w) }))
      .filter((w) => w.e > w.s && w.e > 0 && w.s < span)
      .sort((a, b) => a.s - b.s);
    const names = times.map((t) => t.w);
    const isFiller = (word, i) => {
      if (FILLER.indexOf(word) >= 0) return true;
      return PAIRS.some((pair) => pair.every((p, n) => names[i + n] === p));
    };
    let drop = 0;
    let filler = 0;
    for (let i = 0; i < times.length; i += 1) {
      if (isFiller(times[i].w, i)) {
        drop += times[i].e - times[i].s;
        filler += 1;
      }
    }
    let pauses = 0;
    for (let i = 1; i < times.length; i += 1) {
      const gap = times[i].s - times[i - 1].e;
      if (gap > PAUSE_CUT) {
        drop += gap - PAUSE_LEAVE;
        pauses += 1;
      }
    }
    return { cut: Math.min(span, drop), bleeped: times.filter((t) => BAD.has(t.w)).length, filler, pauses };
  }

  function say(job, clip, box) {
    if (!box) return;
    const censor = !!(clip && clip.censor);
    const cleanup = !!(clip && clip.cleanup);
    if (!censor && !cleanup) {
      box.hidden = true;
      box.textContent = "";
      return;
    }
    wordsFor(job, clip).then((words) => {
      if (!box.isConnected) return;
      box.hidden = false;
      if (cache.failed && cache.key === keyOf(job, clip)) {
        box.textContent = "The word timings could not be read. Try again.";
        return;
      }
      if (!words.length) {
        box.textContent = "Clipstorm has no word timings for this clip yet, so it cannot say what will change until"
          + " the clip is made once.";
        return;
      }
      const got = forecast(words, clip.start, clip.end);
      const bits = [];
      if (censor) {
        bits.push(got.bleeped
          ? `${got.bleeped} swear word${got.bleeped === 1 ? "" : "s"} will be silenced.`
          : "No swearing was found in this clip, so nothing will be bleeped.");
      }
      if (cleanup) {
        if (got.cut > 0.05) {
          const parts = [];
          if (got.filler) parts.push(`${got.filler} filler word${got.filler === 1 ? "" : "s"}`);
          if (got.pauses) parts.push(`${got.pauses} long pause${got.pauses === 1 ? "" : "s"}`);
          bits.push(`${parts.join(" and ")} will go: about ${got.cut.toFixed(1)} seconds shorter.`);
        } else {
          bits.push("Nothing is long enough to cut, so the length will not change.");
        }
      }
      box.textContent = bits.join(" ");
    });
  }

  // The page's own state. `D` and `S` are `const` at the top level of the page's classic script, which puts them in
  // the shared global scope rather than on `window`: a feature file is another classic script, so it can name them,
  // but looking for them on `window` finds nothing at all.
  function state() {
    try {
      // eslint-disable-next-line no-undef
      return { D: typeof D === "undefined" ? null : D, S: typeof S === "undefined" ? null : S };
    } catch (e) {
      return { D: null, S: null };
    }
  }

  function openClip() {
    const got = state();
    const jid = got.D && got.D.jid;
    const cid = got.D && got.D.cid;
    if (!jid || !cid) return null;
    const jobs = (got.S && got.S.jobs) || [];
    const job = jobs.find((j) => j.id === jid);
    const clip = job && (job.clips || []).find((c) => c.id === cid);
    return job && clip ? { job, clip } : null;
  }

  // The switches on screen are the truth, not the clip that was saved: a person flips a box and wants the answer
  // before pressing anything, so the live checkboxes are read every time.
  function live(copy) {
    const root = document.querySelector("#clipdlg");
    if (!root) return copy;
    const boxes = root.querySelectorAll("[data-f='censor'], [data-f='cleanup']");
    if (!boxes.length) return copy;
    const out = Object.assign({}, copy);
    boxes.forEach((el) => {
      out[el.getAttribute("data-f")] = !!el.checked;
    });
    return out;
  }

  P.add("clean-forecast", {
    after: {
      drawClipDlg(root) {
        const box = (root || document).querySelector("#ed_clean");
        if (!box) return;
        const open = openClip();
        if (open) say(open.job, live(open.clip), box);
      },
    },
  });

  // A switch that was just flipped changes the answer, and the page does not redraw the dialog for a checkbox.
  document.addEventListener("change", (e) => {
    const t = e.target;
    if (!t || t.getAttribute("data-f") !== "censor" && t.getAttribute("data-f") !== "cleanup") return;
    const open = openClip();
    const box = document.querySelector("#ed_clean");
    if (!open || !box) return;
    say(open.job, live(open.clip), box);
  }, true);
}());
