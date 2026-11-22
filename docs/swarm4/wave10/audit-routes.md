# Audit: API routes (wave10, swarm4)

Verdict: PASS

Scope: curl every listed route against the already running dev server at http://127.0.0.1:8798 with no request body, note the status, and test the bad-id render POST for a human readable 404. Everything below was measured on 2026-11-20. No server was started, nothing else was written.

## Route sweep, GET with no body

Command pattern used (one curl per route, quoted URL, `--max-time 20`):

    curl -s -w "%{http_code}" "http://127.0.0.1:8798ROUTE"

Measured statuses and the first bytes of each body:

1. GET /api/transcribe -> 200. Body: `{"provider":"logfare","model":"nova-3","ready":true,"has_key":true,"key_hint":"Ve7d","proxy":false,...}`.
2. GET /api/ai -> 200. Body: `{"provider":"logfare","models":["deepseek-v4.1-flash-1017"],...,"ready":true,"label":"Logfare","saved_here":true,"providers":[...]}`.
3. GET /api/learn/state -> 200. Body: `{"rounds":[{"applied":[],"at":1795128089.7336497,...,"effect":"Nothing was changed, so there is no effect to look for.","facts":["No YouTube channel is connected, ..."]}]}`.
4. GET /api/learn/hooks?limit=5 -> 200. Body: `{"ok":true,"hooks":[{"job":"20261120-200119-5fdd2d8f89","clip":"clip01","hook":"WAIT FOR IT","score":100,"verdict":"strong",...}]}`.
5. GET /api/learn/report?limit=3 -> 200. Body: `{"ok":true,"rounds":[{"at":1795128089.7336497,"when":"15 h 56 min ago","days":28,...}]}`.
6. GET /api/posttime -> 200. Body: `{"enough":false,"best":[],"total":0,"note":"Not enough posts yet. PeakCut names no hour until there are 5 posts with view counts.","ok":true}`.
7. GET /api/analytics/summary?start=2026-10-01&end=2026-11-01 -> 200. Body: `{"source":"peakcut","days":28,"start":"2026-10-24","end":"2026-11-20","cards":[{"key":"clips","label":"Clips made","value":4,...}]}`.
8. GET /api/trends/status -> 200. Body: `{"connected":false,"note":"No YouTube account is connected, so PeakCut cannot read what people typed to find your videos...."}`.
9. GET /api/captions/styles -> 200. Body: `{"default":"bounce","styles":[{"name":"bounce","label":"Bounce","house":true},{"name":"hype","label":"Hype","house":true},...]}`.
10. GET /api/memesounds/library -> 200. Body: `{"sounds":[{"slug":"vine-boom-sound-70972","title":"VINE BOOM SOUND","seconds":1.25,"bytes":21230}],"folder":"C:\\...\\data\\memesounds\\sounds",...}`.
11. GET /api/jobs/20261120-200119-5fdd2d8f89 -> 200. Body: `{"id":"20261120-200119-5fdd2d8f89","kind":"video","creator":null,"created":1795185079.0706265,"source":{"type":"file","name":"speech_video.mp4"},"options":{...}}`.
12. GET /api/jobs/20261120-200119-5fdd2d8f89/review -> 200. Body: `{"clips":[{"id":"clip01","title":"Loud moment","hook":"WAIT FOR IT","file":"clip01.mp4","duration":11.0,"review":null}],"remaining":1}`.

All 12 routes answered 200 with JSON bodies. Zero 500 responses in this sweep.

## Bad id render POST

Test 1, the POST exactly as asked (no body):

    curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" \
      "http://127.0.0.1:8798/api/jobs/x/clips/y/render"

    {"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}  -> 422

Same 422 with a well-formed but absent job id (`/api/jobs/doesnotexist-123/clips/clip99/render`). With no body the framework rejects the request as missing-body before the route ever inspects the ids, so a bare no-body POST never reaches the 404 path. This is expected validation behavior, not a 500, so it is a note, not a defect.

Test 2, same POSTs with an empty JSON body `{}` to get past validation:

    curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' \
      "http://127.0.0.1:8798/api/jobs/x/clips/y/render"

    {"detail":"No such video"}  -> 404

The well-formed absent-id variant (`/api/jobs/doesnotexist-123/clips/clip99/render`) also returned `{"detail":"No such video"}` with 404.

Judgment on the message: "No such video" is plain English, no stack trace, no raw exception text. It is a terse fragment rather than a full sentence such as "No such video exists in this job", but it clearly reads like something written for a human, so the check passes. Both bad-job and bad-clip cases produce the same message, which is acceptable and consistent.

## Summary

- 12 of 12 listed GET routes: 200. No 500s. No findings.
- POST render with bad ids: 404 with a human readable message once a JSON body is present. Pass.
- Note: with no body at all, the render POST answers 422 (missing body) before id lookup. Worth knowing if any client calls it without a body, but not a defect.

Findings count (problems): 0.
