# RFTUV Podcast Backup RSS — Design

**Status:** Built 2026-10-30 under Noel Brown's direct order (sole exception to the
2026-10-30 STOP-AND-STUDY production halt). Rebel Audio remains the primary host.
This system is a standby failover: **nothing here is submitted to Apple, Spotify, or
any directory, and no live feed pointer changes.** It exists so that if Rebel stalls
(meter exhaustion, outage) or dies, finished episodes can keep going out over RSS
within hours, from infrastructure we control.

## 0. Operating model (confirmed by Noel, 2026-10-30 11:35)

- **Complete mirror.** The backup carries *every* episode of all three shows —
  everything published on Rebel plus everything produced since (the post-stall
  backlog) — generated from the local bundle masters.
- **Rebel stays the feed of record.** The Apple/Spotify listings keep pointing at
  Rebel's RSS. The backup is never submitted as a second listing anywhere
  (duplicate-listing trap).
- **Dual maintenance from Nov 1.** Every new episode goes into *both* Rebel and
  the backup as part of the normal release flow, so the mirror never drifts.
- **Catch-up role.** The backup's first job is carrying the episodes the Oct 22
  meter stall kept out of Rebel, so they exist in proper RSS form immediately.
- **What the backup reaches — and what it cannot.** A platform listing pulls
  exactly one feed. While Rebel's feed is the listed feed, the backup **cannot**
  add episodes to the existing Apple/Spotify listings. What it *does* reach
  immediately, with no platform permission: the rftuv.ai site player, Stream On,
  Podcast Index–aware apps, and anyone subscribed to the backup feed URL
  directly. Reaching Apple/Spotify with the backlog requires either Rebel
  publishing them (the Nov 1 plan) or an executed feed change (the runbook's
  switch procedure). Anything beyond the platform help docs on propagation
  behaviour is marked UNSETTLED in the runbook rather than assumed.

### Why a future feed change would not break the shows (no-breakage rationale)

Noel's explicit worry: a bulk move causing stalls, errors, or duplicates. The
mirror is built so platforms read it as the *same* shows and the *same*
episodes, because identity in podcast directories is carried by identifiers,
not URLs:

1. **Show identity:** the backup reuses each show's `podcast:guid` verbatim —
   the URL-independent identifier the Podcast Index keys on — plus identical
   title, author, owner email, language, category, and explicit flag.
2. **Episode identity:** every Rebel-published episode keeps its exact Rebel
   item GUID, pubDate, and title. A directory that has already ingested the
   Rebel feed matches backup items to episodes it already has by GUID; nothing
   re-posts as new, nothing duplicates.
3. **New episodes append, never interleave:** episodes that were never on Rebel
   appear in the backup only *after* the Rebel-published subset, in production
   order, so the published catalog's ordering is untouched.
4. **Byte-accurate metadata:** enclosure `length` and `itunes:duration` are
   computed from the exact files the backup serves, so clients see consistent
   metadata for the GUIDs they know.
5. **Validation enforces it:** the build's validation step compares, per show,
   the backup feed's Rebel-published subset against the live Rebel feed —
   episode count, GUID set, and ordering must match exactly — and fails the
   build if they don't.

## 1. What the backup must preserve (the identity layer)

Parsed live from the three Rebel feeds on 2026-10-30
(`https://rss.rebelaudio.ai/rss/<show-id>`):

| Show | Feed items | podcast:guid (Podcast Index identity) | Category | Owner |
|---|---|---|---|---|
| The RFTUV Briefing | 35 (S1 Ep1–36; **Ep6 absent from the Rebel feed**) | `dd1b915a-98c8-59c0-a2ce-b5f61f5255a9` | Technology | willowbrookandmonarch@gmail.com |
| Reporting from the Uncanny Valley | 19 (S1 Ep1–19) | `a4622d9f-67b3-5a1e-a88d-9938ac89ba24` | Technology | willowbrookandmonarch@gmail.com |
| Dead Air Valley | 18 (S1 Ep1–18) | `2cc053a0-fe92-53ea-8d06-dbf69c1e94f2` | History | willowbrookandmonarch@gmail.com |

Per-episode identity carried over verbatim for every episode live on Rebel:
item GUID (UUID), pubDate (exact GMT string), title, itunes:episode / season /
episodeType, explicit=false. Enclosure `length` and `itunes:duration` in the backup
are recomputed from the **local master files** (the backup serves the local files,
so its metadata must describe them; where the Oct 19–21 remediation re-renders made
local files differ from what Rebel serves, the GUID is unchanged and the difference
is recorded in the manifest).

**Deliberately NOT copied:** Rebel's `<itunes:new-feed-url>` (it points at Rebel's
own feeds.rebelaudio.ai URL; copying it into the backup feed would tell clients to
leave the backup), Rebel's per-item `podcast:transcript`/`podcast:chapters` URLs
(they point at Rebel's CDN), and Rebel's tracking-laden episode `link` URLs
(backup items link to rftuv.ai instead).

**Podcast Index status (checked 2026-10-30):** Reporting is feed ID **8057966**
and The RFTUV Briefing is **8057967** on podcastindex.org (both page titles
verified). Dead Air Valley's index status is **UNSETTLED**: the Index site search
requires JavaScript/API auth, adjacent IDs (8057965, 8057968) are not Dead Air
Valley, and a web search surfaced no listing. The backup feed carries Dead Air
Valley's existing `podcast:guid`, which is the identifier the Index keys on; the
runbook includes verifying/claiming it at failover time.

## 2. Podcasting 2.0 treatment (free, identity-preserving only)

Implemented per the Podcast Index namespace spec
(https://github.com/Podcastindex-org/podcast-namespace) and
https://podcastindex.org:

- `<podcast:guid>` per show — **the Rebel values, reused verbatim.** The GUID is
  independent of feed URL by design; it is the failover identity anchor. Keeping
  the same GUIDs means the Podcast Index and supporting apps recognise the backup
  feed as the same shows.
- `<podcast:locked owner="willowbrookandmonarch@gmail.com">yes</podcast:locked>` —
  same as the Rebel feeds; tells aggregators not to import the feed to a new host
  without the owner's consent. (The owner executes failover personally via
  Podcasts Connect / Spotify dashboards, which is not blocked by this tag.)
- `<podcast:medium>podcast</podcast:medium>` — same as Rebel.
- `<podcast:transcript>` per episode, pointing at the episode's transcript.txt
  hosted with the backup (type text/plain, language en) — replaces Rebel's
  Rebel-CDN SRT links with files we control.
- `<podcast:location>` — Reporting and Dead Air Valley: `Hudson Valley, New York,
  USA` (both shows' own published descriptions place them in New York's Hudson
  Valley). Omitted for the Briefing (its published description makes no location
  claim) and geo/OSM attributes are **UNSETTLED** (no verified coordinates on
  record), so they are omitted.
- `<podcast:funding>` — **UNSETTLED**: no funding URL exists in our records.
  Omitted rather than invented.
- Episode-level GUIDs use the plain RSS `<guid isPermaLink="false">` exactly as
  Rebel does.

## 3. Guidance folded in from Adam Curry's hyperlocal notes

Source: Adam Curry (Podcasting 2.0 / Podcast Index co-founder), "How to Start a
Hyper Local Podcast", http://hyperlocal.noagendanotes.com/ — sent to Noel by email
2024-11-29 ("Re: Local Podcast - Starter Kit") and read in full 2026-10-30.

- **"Your RSS feed is your direct connection to your listeners, wherever they get
  their podcasts"** — uploading to platforms surrenders ownership of the audience.
  This is the design principle behind this build: feed identity (GUIDs, episode
  GUIDs) is held in files we own, and every layer (feed XML, audio, artwork,
  transcripts) has a copy on infrastructure we control.
- **Consistency is a golden rule** — publish on schedule or listeners replace the
  slot. A meter stall that silences the shows for weeks is exactly the failure
  this backup removes: failover must be fast and rehearsed, not improvised.
- **Curry advises paid hosting (~$20/mo) over free options, for the support.**
  Noted honestly: Rebel (comped, primary) is outside that advice's scope, and
  this backup deliberately uses no-cost infrastructure because its job is
  standby, not primary service. If the backup ever becomes primary for an
  extended period, this trade-off should be revisited.
- **The email list is "your podcast's most valuable asset"** — distribution we own
  outright; outside this build's scope but consistent with the rftuv.ai player /
  owned-channel leg of the failover runbook.

## 4. Hosting evaluation (from official docs, 2026-10-30)

### Audio (enclosures)

| Candidate | Facts (source) | Verdict |
|---|---|---|
| **Internet Archive** | S3-compatible API at s3.us.archive.org; upload requires a free archive.org account + IA-S3 keys issued at https://archive.org/account/s3.php (IA S3 docs, https://archive.org/services/docs/api/ and the IA S3 manual). Files serve world-readable at predictable `https://archive.org/download/<identifier>/<file>` URLs; designed for permanent preservation; podcast clients hot-link IA enclosures routinely. | **PRIMARY (intended)** — best permanence and URL stability. **BLOCKED today:** no archive.org account exists in our records, and creating one means setting a password, which is Noel's step. |
| **GitHub Releases** | Up to 1,000 assets per release, each file < 2 GiB, **no limit on total release size or bandwidth** (https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases). Download URLs are predictable (`https://github.com/<owner>/<repo>/releases/download/<tag>/<file>`) and redirect to GitHub's CDN. GitHub account already connected (gh CLI, repo scope). | **DEPLOYED NOW as the working host** — zero new accounts, limits are orders of magnitude above our ~640 MB / 106 files. Caveat: GitHub is a code platform, not a podcast CDN; if the backup becomes long-term primary, migrate enclosures to IA per §6. |
| **Cloudflare R2** | Free tier: 10 GB-month storage, 1M Class A / 10M Class B ops, free egress (https://developers.cloudflare.com/r2/pricing/). But the `r2.dev` public URL is rate-limited and documented as non-production (custom domain on a Cloudflare zone is the production path), and enabling R2 requires a Cloudflare account with a payment method. | **Runner-up, not deployed** — no Cloudflare account exists; r2.dev-only access is explicitly dev-grade. Revisit if a Cloudflare account is ever created for other reasons. |
| GitHub Pages for audio | Published site ≤ 1 GB total, soft 100 GB/mo bandwidth (https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). Our audio alone is ~640 MB and growing daily; Pages is also not intended as a file-distribution service. | Rejected for audio. Fine for feeds/art (below). |

### Feed XML + artwork + transcripts

**GitHub Pages** from the same repo. Feeds are a few hundred KB; even with
1400×1400 episode artwork (~106 images) and plain-text transcripts the published
site stays far under the 1 GB cap. URLs:
`https://reportingfromtheuncannyvalley.github.io/rftuv-podcast-backup/feeds/<show>.xml`.
A custom domain (e.g. feeds.rftuv.ai) can be layered on later without changing
any GUID — only enclosure/feed URLs, via one manifest edit + regeneration.

## 5. Repository and layout

Repo: **github.com/reportingfromtheuncannyvalley/rftuv-podcast-backup** (public —
required for Pages on the free plan; contains no secrets and no unpublished
audio beyond what the feeds themselves serve).

```
manifest.json            single source of truth (shows, episodes, GUIDs, URLs)
generate_feeds.py        manifest -> docs/feeds/*.xml (+ validation report)
add_episode.py           bundle folder -> manifest entry + artwork/transcript staging
sync_backup.sh           add_episode + upload audio + regenerate + validate + push
check_drift.py           bundles vs manifest vs live release assets vs live feeds
docs/                    GitHub Pages root: feeds/, art/, transcripts/, index.html
RUNBOOK.md               failover procedure (also at ~/workspace/podcast-network/backup-rss/RUNBOOK.md)
```

Naming: audio asset `epNNN.mp3` per show release (`audio-briefing`,
`audio-reporting`, `audio-dead-air-valley`); unnumbered-in-Rebel episodes use
their series production number. Artwork `docs/art/<show>/epNNN.jpg`,
show cover `docs/art/<show>/cover.jpg` (1400×1400, from the bundle cover art /
Rebel channel art).

## 6. GUID strategy

- Episode live on Rebel → Rebel's item GUID, verbatim, `guid_source: "rebel"`.
- Episode never on Rebel (post-stall slate, Briefing Ep6 which is absent from
  Rebel's current feed) → deterministic **UUIDv5** over
  `rftuv-backup|<show-slug>|<episode-key>` in the show's podcast:guid namespace,
  `guid_source: "provisional"`. Stable across regenerations; if the episode later
  publishes on Rebel and Rebel assigns a different GUID, the Nov 1 backfill
  procedure must reconcile (the runbook covers this: prefer keeping the backup
  GUID by *not* re-minting — the backup GUID was first published, so if Rebel
  lets us set GUIDs we use ours; where Rebel assigns its own, record Rebel's in
  the manifest and switch the backup item to it before any failover, since the
  Rebel-listed GUID is the one the directories already know).
- Show GUID → the `podcast:guid` values in §1, verbatim.

## 7. Update flow (evergreen)

Every new episode bundle: `sync_backup.sh <bundle-folder>` → manifest extended,
audio uploaded to the show's release, artwork/transcript staged, feeds
regenerated, validated (parse + enclosure HEAD checks + GUID uniqueness +
manifest↔feed completeness), committed and pushed, Pages redeploys. A weekly
`check_drift.py` run (or manual, per runbook) catches anything missed.
