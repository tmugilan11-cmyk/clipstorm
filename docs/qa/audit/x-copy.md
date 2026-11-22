# x-copy — cross-cutting copy audit (beginner five-second test)

Auditor: agent-160 (cross-cutting copy). Wave: audit (no fixes). Skill loaded: frontend-design.

## Files owned

Cross-cutting brief: user-facing strings over the whole web app, no single page owned.

- `web/index.html` (shell + all inline pages/dialogs, read fully, 3504 lines)
- `web/feat/*.js` (76 feature files, swept by grep for hint/help/toast/placeholder/label strings; context read around every candidate)

## Checks run

1. Full read of `web/index.html` (all 3504 lines, three passes with ops_inspect_local_file).
2. `ops_grep web/feat` for `class="hint"` — 37 hits reviewed.
3. `ops_grep web/feat` for `toast(` — 68 hits reviewed.
4. `ops_grep web/feat` for `alert(|confirm(|prompt(` — 1 hit (day.js confirm), reviewed.
5. `ops_grep web/feat` for `placeholder=` — 17 hits reviewed.
6. `ops_grep web/index.html` and `web/feat` for the jargon terms that surfaced: hook, arm, face, tunnel, relay, route, DankMachine, punch, score badge — every hit read in context.
7. Context reads: `web/feat/streamer-mode.js` (258–312), `web/feat/sounds.js` (283–307), `web/feat/learn-arms.js` (31–42, 115–159, 176–183, 200, 295), `web/feat/creators.js` (200–217), `web/feat/audio-page.js` (195–234), `web/feat/icons-extra.js` (140–169).
8. Every line number below re-verified by a final targeted grep (line numbers are from the current working tree).

No dsh_browser tools were used (contract rule 2). No HTTP checks were needed: no finding here rests on a route or a response code.

## Verdict in one line

The app's copy is unusually good — most strings already pass the five-second test — but three hints in Streamer Mode speak pure backend jargon, one empty state names Python source files, and the experiment card says "Arm" as if everyone knows A/B testing vocabulary.

## Findings

| severity | where | what | evidence | fix |
| --- | --- | --- | --- | --- |
| important | web/feat/streamer-mode.js:303-305 | Hint under "Prefer moments with a police chase, a crash or a wanted level" is pure mechanism: "A note, not a filter. The job route has no field for it, so it is not sent, and PeakCut picks moments from what it hears the same way for every video." A beginner cannot parse "job route" or "not sent", and cannot tell what the tick actually does. | File line: `303 | <p class="hint">A note, not a filter. The job route has no field for it, so it is not sent, and PeakCut` | Rewrite in result terms: "This is a preference note, not a hard filter. PeakCut still picks moments by what it hears; after a clip is made it can use the note to label it a chase or a crash." |
| important | web/feat/streamer-mode.js:269-270 | The select "How loud chat must get" is changeable but does nothing, and the hint says so in mechanism language: "PeakCut does not read this for a job. A spike is decided by the Chat settings and by the creator's own 'only check on a spike' setting, so this box is not sent and changes nothing yet." A beginner sees a live-looking control and cannot tell why it exists. | File line: `269 | <p class="hint">PeakCut does not read this for a job. A spike is decided by the Chat settings and by the` | Lead with the result: "This box does nothing yet. Whether a chat spike counts is decided by the Chat settings and the creator's 'only check on a spike' setting." Better: disable the select (or hide it) until it is wired to the job. |
| important | web/feat/streamer-mode.js:274-277 | Same pattern under "Keep recording for at most, minutes": changeable number box that is never sent, plus a garbled label (the comma splits "at most" from its unit): "Keep recording for at most, minutes". Hint: "PeakCut does not read this for a job... so this box is not sent." | File lines: `274 | <label for="str_minutes">Keep recording for at most, minutes</label>` and `276 | <p class="hint">PeakCut does not read this for a job. How much of a stream a recording keeps is the` | Rename the label "Keep recording for at most (minutes)" and rewrite the hint: "This box does nothing yet. How much of a stream a recording keeps is set on that creator's Setup page." |
| important | web/feat/sounds.js:296-297 | Empty-catalogue state names Python source files to the end user: "The server answered, and the list of moods was empty, so there is nothing to show yet." + "That list is written by studio/meme.py and studio/music.py. If it stays empty, the server log names the one that failed." A beginner does not know what a .py file is or where a server log lives. | File line: `297 | <p class="hint">That list is written by studio/meme.py and studio/music.py. If it stays empty, the server log names the one that failed.</p>` | "These sounds come with PeakCut and are built on first start. If the list stays empty, the build failed — press Build sounds again; the app's log file, in PeakCut's own folder, names what went wrong." |
| minor | web/feat/sounds.js:290-291 | Error state says "the server log says why" with no pointer to where that is. | File line: `291 | <p class="hint">This list comes from the server. Reload the page; if it stays empty, the server log says why.</p>` | "Reload the page. If it stays empty, the app's log file — in PeakCut's own folder — says why." |
| minor | web/feat/learn-arms.js:170-171, 168, 200, 295 | The Improve page's trial card speaks A/B-testing jargon: heading "Two arm trial" (line 200), "Both arms have run." (168), "Arm a is running now: ... Arm b is ..." (170-171), toast "The trial is written down. Arm a runs first." (295). "Arm" means nothing to a beginner. | File lines: `170 | parts.push(`<p class="armline">Arm ${esc(arm)} is running now: ...` and `295 | P.toast("The trial is written down. Arm a runs first.", "ok");` | Replace arm a/b with "the first setting"/"the second setting" everywhere the card speaks; rename the heading "Try one setting, then another" or "Two-setting trial". |
| minor | web/feat/learn-arms.js:178-179 | Edge state explains itself with mechanism: "Both arms have run. PeakCut has not sent the sentence that compares them yet, so there is nothing to quote here." ("has not sent" = a server field is missing). | File line: `178 | parts.push(`<p class="sub" style="margin:11px 0 0">Both arms have run. PeakCut has not sent the sentence` | "Both settings have been measured. The sentence comparing them is not written yet — it appears here once PeakCut has finished." |
| minor | web/index.html:2494 | Font-picker empty state uses typographer jargon: "This server sent no font list, so only the style's own face is offered." The rest of the app says "font". | File line: `2494 | grid.innerHTML = `<p class="hint">This server sent no font list, so only the style's own face is offered.</p>`;` | "...so only each style's own font is offered." |
| minor | web/index.html:2549 | The AI Address field's hint names neither result nor action: "Where the service answers." A beginner cannot tell what to type or whether to leave it blank. | File line: `2549 | <label class="f" id="ai_basewrap">Address<input id="ai_base" ...><span class="hint" id="ai_basehint">Where the service answers.</span></label>` | "Leave blank unless your key comes with its own web address." |
| minor | web/index.html:2439 | Watermark hint mixes one explained term with file-system jargon: "A handle like @yourname, a PNG logo path, or blank for none." | File line: `2439 | <label class="f">Watermark<input id="br_watermark" ...><span class="hint">A handle like @yourname, a PNG logo path, or blank for none.</span></label>` | "A handle like @yourname, the location of a PNG logo on this computer, or blank for none." |
| minor | web/index.html:2459 | Editing jargon twice in one control: toggle label "Flash on the punch-in", hint "A short white flash when the clip punches in." A beginner does not know "punch-in". | File line: `2459 | ${toggle("br_flash", "Flash on the punch-in", "A short white flash when the clip punches in.", b.flash)}` | Label "Flash when the clip zooms in"; hint "A short white flash at the moment the picture zooms in quickly." |
| minor | web/index.html:2098 | Empty-chart text is doubly temporal and reads oddly: "No clips in the last 14 days yet". | File line: `2098 | <text class="none" ...>No clips in the last 14 days yet</text>` | "No clips in the last 14 days". |
| minor | web/index.html:2741 | The clip dialog's score badge uses two different formats for the same slot and shows no scale: "Words 7 · Reaction 4", "Score 7", or "Clipped by hand". A beginner cannot tell what 7 is out of. | File line: `2741 | <span class="badge ...>${c.judges ? "Words " + c.judges.words + ... : c.score ? "Score " + c.score : "Clipped by hand"}</span>` | Pick one format with a scale: "Score 7/10" or "Words 7/10 · Reaction 4/10". |
| minor | web/index.html:2431 + 2755 | The same setting has two names in two places: the Brand page section is titled "Hook" ("Hook title colour", "Hook position") while the clip editor calls the same field "Big text". A beginner will not connect them. | File lines: `2431 | <h3>Hook</h3>` and `2755 | <label class="f">Big text<input data-f="hook" ...>` | Add a hint under the Brand section heading: "The hook is the big text at the top of the clip — the editor calls it Big text." Or rename the Brand section "Big text". |
| minor | web/feat/audio-page.js:215 | The catalogue's name is used but never introduced: placeholder "Search all of DankMachine"; the rights note at 222 explains what DankMachine marks, never what it is. | File line: `215 | '<input type="search" id="alb_search" placeholder="Search all of DankMachine" ...>'` | Introduce it once at the first mention: "Search all of DankMachine — the sound catalogue" or "Search the whole catalogue". |
| minor | web/feat/icons-extra.js:154-158 | The Icons Tools card is written for the maintainer, not the user: "Three icon names the page uses but never drew", "Press this after editing the file", "It re-reads the page's icon map". Every signed-in user sees this card. | File line: `158 | <p class="hint">Press this after editing the file. It re-reads the page's icon map and marks each icon as drawn or missing.</p>` | Either move the card behind a maintainer flag, or rewrite: "Three missing icons, now filled in. Press Check again after updating PeakCut." |
| minor | web/feat/autopilot.js:253, 292 + web/feat/schedule.js:254 | A schedule "installed" and "off this machine": "The schedule is installed." (253), "The schedule is off this machine." (292), "The schedule was installed." (schedule.js:254). "Off this machine" reads as "disabled"; "installed" is odd English for a schedule. | File line: `292 | PeakCut.toast("The schedule is off this machine.", "ok");` | "The schedule is set." / "The schedule was removed." — keep the same verb pair in both files. |

## Checked and found good (no finding)

- `web/feat/creators.js:206-211` — creators error state is a model error state: plain cause ("The page asked and did not get an answer"), reassurance ("Nothing has been lost: the creators are still on the server"), and one clear action ("Try again").
- The AI and Transcription help paragraphs (`web/index.html:2544`, `2560`) — plain service names, who pays, what happens without a key.
- Storage tab copy (`web/index.html:2600-2611`) — "Use this folder", "Move everything that is in the current folder there too", and the reason the change waits for a restart.
- Caption-colour labels (`web/index.html:2425-2429`) — "Words not said yet", "The word being said", "Outline behind every word" — mechanism translated into sight.
- Connected-apps copy (`web/index.html:2677`) — "press Connect, sign in on the platform's own page, and you're back here. PeakCut never sees your passwords."
- Keyboard shortcut legends (`web/index.html:2194`) — "A says yes to the next clip, X says no, S skips ahead."
- Analytics hints (`web/feat/analytics-*.js`) — every control has a one-line why.
- "dead air" (`web/index.html:2769`) — jargon, but the hint explains it ("Drops 'um' and 'uh' and shortens long pauses"), so it passes.
- day.js confirm — plain two-sentence confirm, no jargon.

## Summary

Copy is a strength of this app; the failures are concentrated in three Streamer Mode hints and one Sounds empty state that name the mechanism instead of the result, plus "Arm" jargon on the Improve page — 4 important, 13 minor, every finding carrying a file line as evidence.
