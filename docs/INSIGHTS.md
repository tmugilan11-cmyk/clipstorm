# Insights

Insights is the menu row under **Understand**. It opens at `/app/analytics` and answers one question: how are
the videos doing. Nothing here changes a clip, post or setting.

It has five tabs: Overview, Content, Audience, Trends, Traffic.

## Where the numbers come from

Every answer carries a source. `youtube` means YouTube's own Analytics numbers. `peakcut` means PeakCut's own
records, or an empty answer plus a sentence naming what is missing. A number that did not arrive is drawn as a
dash with a sentence, never as a zero.

## Date ranges

| Choice | What it covers |
| --- | --- |
| Last 7 days | the seven days ending today |
| Last 28 days | the default, the twenty eight days ending today |
| Last 90 days | the ninety days ending today |
| Last 365 days | the year ending today |
| Lifetime | from 1 January 2005 |

The header says the window in words, for example "Last 28 days, ending 20 Nov 2026". Tick **Compare** to add
the window of the same length immediately before it, and the header then reads ", compared with the 28 days
before". Compare is off and disabled while Lifetime is chosen.

Answers are cached two minutes. Past 120 calls a minute the server answers 429 with a sentence.

## Overview

Six key numbers from `GET /api/analytics/summary`. With a channel it reads these YouTube Analytics metric ids:
`views`, `estimatedMinutesWatched`, `averageViewDuration`, `averageViewPercentage`, `subscribersGained`,
`subscribersLost`, `likes`, `comments`, `shares`. Watch time is `estimatedMinutesWatched` divided by 60.
Subscribers gained is `subscribersGained` minus `subscribersLost`, so it is a net figure. Likes and comments
are `likes` plus `comments`.

Impressions and click-through rate draw a dash: this route does not ask YouTube for either metric. Each card
carries a question mark explaining what the number would mean.

Two charts, views and watch time, draw one point per day from `/api/analytics/timeseries` on dimension `day`.
The earlier window is the thinner dashed line.

**Right now** shows the views on the newest day returned, refreshed once a minute. **Revenue** reads the same
summary and, without revenue, RPM or CPM keys, shows one sentence and no figures.

## Content

One row per video from `/api/analytics/videos`: dimension `video`, sorted by views, a hundred rows by default
and at most two hundred. The columns read `views`, `estimatedMinutesWatched`, `averageViewDuration`,
`averageViewPercentage`, `likes`, `comments`, `shares` and `subscribersGained`. Headers sort, and a search box
filters titles.

The Impressions and Click-through columns stay dashed because the route does not ask for those metrics.

Below the table, **How far people watched** draws a retention curve for the video you pick from
`/api/analytics/retention`: dimension `elapsedVideoTimeRatio`, metrics `audienceWatchRatio` and
`relativeRetentionPerformance`, filtered to that video. A Shorts block keeps the rows of 60 seconds or less and
says what their numbers mean.

## Audience

From `/api/analytics/audience`: countries on dimension `country`, the top ten with their shares, and hours on
dimension `day,hour`, one cell for each hour of the week, with the busiest slot named. Hours are in your
channel's own time zone. The returning versus new block says the server sends no split yet rather than
inventing one.

## Trends

Top searches use dimension `insightTrafficSourceDetail`, filtered to `insightTrafficSourceType==YT_SEARCH`,
with an interest word worked out from each term's share of the search views. Breakout videos are this channel's
own videos by views. They are not YouTube's public trending chart, which needs a Data API key PeakCut does not
keep. Saved searches live in your own folder, up to fifty.

## Traffic

From `/api/analytics/traffic`: dimension `insightTrafficSourceType`, metrics `views` and
`estimatedMinutesWatched`, biggest first, each row with views, minutes and its share. Enum values become words,
so `YT_SEARCH` reads "YouTube search" and `SHORTS_FEED` reads "Shorts feed".

## What needs a connected channel

Needs YouTube: watch time, average view duration, average percentage viewed, subscribers, likes, comments,
shares, retention, countries, hours of the week, search terms, traffic sources.

PeakCut alone: clips made, posts sent, views PeakCut tracked, waiting to go out, failed posts, creators set up.

The server sends those six counters when no channel is connected, but the key number row only draws YouTube's
six, so without a channel every card is a dash plus a sentence saying why. The Content table still lists your
own posts, dashed where YouTube's numbers would go.

## Connecting a channel

1. Save a Google app client id and secret under **Connected apps** at `/app/apps`. PeakCut cannot
   start the handshake without them.
2. Press Connect beside YouTube. That goes to `/oauth/youtube/start`.
3. Google asks for three permissions: `youtube.upload`, `youtube.readonly` and `yt-analytics.readonly`. The
   analytics tabs stay empty without the third.
4. Come back to Insights. The header shows the channel name.

If the channel was connected before the analytics permission was added, disconnect it on Connected apps and
connect it again. A Google account with no YouTube channel is refused at the end of the handshake.

## Limits of this build

- The routes accept at most 3650 days. Choosing Lifetime sends 3650 and not the real span, so the key numbers
  and the Audience tab cover the last ten years rather than every year the channel has existed.
- The Content table sends dates. That route reads a day count instead, so the table answers a 28 day window
  while its sentence names the dates you picked. The Traffic tab sends dates too, but its pill now shows the
  window the answer covers, so the two numbers on that tab agree.
- Export writes a CSV from what is already on the screen, without a request. It has no button on a tab that
  holds no rows: Trends, and Audience and Traffic, which draw no table.
