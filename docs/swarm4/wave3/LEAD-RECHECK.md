# Lead re-check list (written while wave 3 runs)

I edited `web/feat/learn.js` by hand while the wave 3 agent `learn-ui-polish` also owns it.
If that agent overwrote the file, these two changes must be re-applied after the wave ends:

1. **The preview button must never be disabled.** `data-act="lrndry"` had `${can ? "" : "disabled"}` on it. A preview changes nothing, so the six hour wait does not apply, and a disabled button on a fresh install made the feature look broken. The line must read: `<button class="btn sm" data-act="lrndry">What would it change?</button>`

2. **"Nothing was changed." must not appear twice in one round card.** The `.pill` already says "nothing changed", and the `.did` line repeated it. The `.did` line now renders only when it has something to add: `const said = did.length ? "Changed " + esc(names.join(", ")) : (r.saying && (r.facts || []).indexOf(r.saying) < 0 ? esc(r.saying) : "");` then `${said ? ... : ""}`.

Both are checked by `node --check web/feat/learn.js` and `python tests/test_feat_files.py`.
