# Clipstorm

Clipstorm turns long videos and live streams into short vertical clips. You give it a video link (or a live
stream), it writes down what is said, picks the moments people are most likely to watch and share, and renders
each one as a 9:16 clip with captions, a heading and sound. You review the clips, change what you want in the
clip editor, and post them when you are ready. It runs on your own PC and opens in your web browser.

(The code and its settings still use the old name, PeakCut: settings start with `PEAKCUT_`.)

## Install on Windows

What the PC needs:

- Windows 10 or 11
- 8 GB of memory or more (less works, but rendering is slow)
- 15 GB of free disk space (a long live recording needs room)
- An internet connection

Steps:

1. Put the Clipstorm folder at a short path, such as `C:\clipstorm`. Either download it and unzip it there, or run
   `git clone <this repository> C:\clipstorm`. Do not leave it in a long or temporary folder: Windows cannot open
   files whose full path is over 260 characters, and the speech library then fails to load.
2. Double-click `setup.bat`. It checks the PC and installs what is missing:
   - Python 3.12 and ffmpeg, through winget, if they are not already there
   - a private Python folder (`.venv`) inside the Clipstorm folder, so nothing else on the PC is changed
   - the libraries Clipstorm uses (`requirements.txt`), and the newest video downloader
   - a `.env` file copied from `.env.example`
   It is safe to run again; it only adds what is missing.
3. Double-click `start.bat`. After a few seconds your browser opens `http://127.0.0.1:8765/app`. Keep the black
   window open while you use Clipstorm; closing it stops the app.

The first start downloads the speech model (about 480 MB) by itself.

When setup says something could not be installed:

- **"winget is not available"**: install the named program (Python 3.12 or ffmpeg) by hand, then run `setup.bat`
  again.
- **"ffmpeg was installed but this window cannot see it yet"**: close the window and run `setup.bat` once more.
- **"Could not install: sherpa-onnx"**: Clipstorm still runs, but it cannot turn speech into text on this PC.
  Choose a speech service under Settings > Transcription instead.
- **"The app did not load"**: copy the lines above that message and send them to whoever set Clipstorm up.

## First run

All keys are entered inside the app, not in files:

- **Settings > Transcription**: the speech-to-text service and its model (or "on this PC").
- **Settings > AI**: any OpenAI-compatible provider: its address, your key and the model name.
- **Connected apps**: the accounts clips are posted to.

Keys are saved in the `data` folder on your PC. That folder is never published.

## The menu

- **Start**: Home, Projects, Review clips
- **Record live**: Live recording, Streamer mode, Creators
- **Look and sound**: Caption styles, Brand template, Asset library, Audio
- **Grow**: Analytics, This week, Improve, Calendar
- **Settings**

## Make clips from a video

1. Open **Start > Home** and paste a video link (YouTube, Twitch, Kick and other sites the downloader supports).
2. Wait while it downloads, writes down the words and picks moments. Progress shows under **Projects**.
3. Open **Review clips**. Keep the good ones, reject the rest; a rejected clip is never posted.
4. Open a clip to change it in the clip editor, then post it from the Post tab.

## Record a live stream

1. Add the streamer under **Record live > Creators**. In the creator's Setup you can fill in "What should it look
   for?" in your own words.
2. Open **Live recording** and start a recording of the stream. If the stream is already running, Clipstorm goes
   back to its first minute and catches up.
3. Clips appear while it records, and go to **Review clips** like any other.
4. Press **Stop** when you are done, or let it end with the stream. Review the clips as usual.

## How clips are picked

Every stretch of talk gets six AI reads:

- **Reader**: works out who is talking, who "he" and "they" are, and what is being referred to; it can look things
  up on the web and see the streamer's most-watched clips.
- **Scout 1**: follows the talk.
- **Scout 2**: starts from the reactions (loud moments, chat bursts, pauses) and works backwards.
- **Scout 3**: hunts for the line people will quote.
- **Critic 1, an editor**: marks hook, payoff, emotion, share and stands-alone, may move the cut, says post or skip.
- **Critic 2, a fast-swiping viewer**: does the same without seeing the editor's answer.

The two critics' marks are averaged into the clip's score, out of 100. 80 or more is a strong clip worth posting;
90 or more means people will share it. A clip a critic said to skip can never score that high. A video makes fewer
clips rather than weak ones.

The "What should it look for?" box in a creator's Setup is passed to the judge in your own words.

For a finished YouTube video, Clipstorm also uses YouTube's most-replayed graph and comments that name a moment.

## The clip editor

- **Cut**: move the start and end of the clip.
- **Captions**: fix the words and choose the caption look.
- **Look**: layout, the big heading text, pictures on the clip, and the clip type (Moment, Wait for it, Reveal;
  Reveal needs a webcam in the video).
- **Sound**: meme noises and music; **Edit audio** opens the full sound editor for this clip.
- **Post**: the title and description, and where and when it is posted.

The heading and the post text show a preview frame while you type, so you do not need a render to check them.

## Good to know

- Clip types that join several moments (Callback, Compilation, Escalation, Then vs now) are not available yet.
- The judge reads the words, the loudness and chat; it does not look at the picture.
- Instagram is not used as a data source; it shows nothing without a sign-in.
- A live recording keeps running until you press Stop or the stream ends.
- Nothing is posted unless you turn posting on.
- Downloads go up to 1080p.

## Where your things are kept

Videos, clips, keys and settings are in the `data` folder inside the Clipstorm folder, unless `storage.json`
points somewhere else. When you move or update Clipstorm, copy `.env`, `storage.json` and `data` across, and
check the clips are there before deleting the old folder.

## For developers

- Run: `python -m studio.server` (settings from `.env`; see `.env.example`). Needs Python 3.10 to 3.13 and ffmpeg.
- Tests: `PYTHONPATH=. python tests/test_<name>.py` for one file, or `python tests/run.py` for all of them. The
  tests start a throwaway copy with an empty data folder and need no keys.
- Try a change without touching real data: `PEAKCUT_DATA=<temp folder> PEAKCUT_PORT=8766 python -m studio.server`.
- `AGENTS.md` is the map: which file does what, and the rules worth knowing.
- New pieces of the page go in `web/feat/<name>.js`, registered through `web/plugins.js`; copy `web/feat/heard.js`.
- Never write a key, a real address or a personal path into a tracked file.
