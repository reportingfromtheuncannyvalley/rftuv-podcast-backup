# RFTUV Podcast Backup — standby RSS mirror & failover

A complete, publicly hosted mirror of the three RFTUV podcasts, built
2026-10-30 as a standby failover for Rebel Audio. **Rebel stays the primary
host and its RSS remains the feed of record for the Apple/Spotify listings.**
Nothing here is submitted to any directory; no live feed pointer changes.
If Rebel stalls or dies, this system keeps the shows publishing over RSS from
infrastructure we control — see [RUNBOOK.md](RUNBOOK.md).

## The shows

| Show | Backup feed | Episodes | Rebel feed (primary) |
|---|---|---|---|
| The RFTUV Briefing | https://reportingfromtheuncannyvalley.github.io/rftuv-podcast-backup/feeds/briefing.xml | 51 | https://rss.rebelaudio.ai/rss/585a9993-4330-471e-b2ae-a328678a0637 |
| Reporting from the Uncanny Valley | https://reportingfromtheuncannyvalley.github.io/rftuv-podcast-backup/feeds/reporting.xml | 27 | https://rss.rebelaudio.ai/rss/05743ffb-60a6-4d64-b356-9cddab8286bb |
| Dead Air Valley | https://reportingfromtheuncannyvalley.github.io/rftuv-podcast-backup/feeds/dead-air-valley.xml | 26 | https://rss.rebelaudio.ai/rss/c04b9ca9-9c96-4d3e-b9aa-d65aeb5d2a51 |

Episode audio is served from this repo's GitHub Releases (one release per
show: `audio-briefing`, `audio-reporting`, `audio-dead-air-valley`; assets
named `epNNN.mp3`). Feeds, artwork, and transcripts are served from GitHub
Pages out of `docs/`. One episode (Dead Air Valley's unpublished "The
Four-Way Stop") is carried in the manifest for completeness but deliberately
excluded from the feed and from public hosting, per its unpublished status.

## Identity (why a failover doesn't break the shows)

Directories identify shows and episodes by identifiers, not URLs — the mirror
preserves all of them (full rationale in the build's DESIGN.md):

- Each show keeps Rebel's **`podcast:guid`** verbatim (the Podcast Index keys
  on it), plus identical title, author, owner, category, and explicit flag.
- Every Rebel-published episode keeps its **exact Rebel GUID, pubDate, and
  title**; never-published episodes append after them in production order
  with provisional GUIDs (see "GUID reconciliation" in RUNBOOK.md).
- Enclosure `length` and `itunes:duration` are computed from the exact files
  served here.
- Validation enforces parity: the Rebel-published subset of each backup feed
  must match the live Rebel feed's GUID set and order exactly, or the build
  fails.

## How it works

- `manifest.json` — the catalog: every episode of all three shows with title,
  description (public shownotes body), dates, durations, byte sizes, GUIDs,
  and URLs. Generated from the episode bundle masters; extended by
  `add_episode.py`.
- `generate_feeds.py` — manifest → one RSS 2.0 + iTunes + Podcasting 2.0 feed
  per show in `docs/feeds/`.
- `validate_feeds.py` — parse, GUID-uniqueness, manifest↔feed completeness,
  Rebel parity, and (with `--live`) HTTP 200 + exact content-length for every
  enclosure, artwork, and transcript URL.
- `check_drift.py` — bundles on disk vs manifest vs release assets vs feeds
  (add `--live` to include the published Pages feeds).
- `sync_backup.sh` — the single maintenance command (below).
- `add_episode.py` — extend the manifest from a finished episode bundle.
- `docs/` — the GitHub Pages root: `feeds/`, `art/` (1400×1400 JPEG episode
  and show artwork), `transcripts/`.

## Maintenance (dual — every new episode goes into Rebel AND the backup)

```bash
# 1. Publish the episode on Rebel as usual; finish its six-file bundle.
# 2. Add the bundle to the backup manifest:
python3 add_episode.py <show-slug> <bundle-folder>
#    If the episode is already live on Rebel, copy Rebel's GUID/pubDate/title
#    into the new manifest entry first (GUID reconciliation, RUNBOOK.md).
# 3. Upload audio, stage art/transcripts, regenerate, validate, push:
./sync_backup.sh
# 4. Confirm no drift:
python3 check_drift.py --live
```

## Failover

**[RUNBOOK.md](RUNBOOK.md)** — Phase 0 drift/validation checks, Phase 1
immediate-relief distribution on surfaces we control (site player, Stream On,
direct subscribers), Phase 2 the platform-listing switch with its
Rebel-mediation caveats for Apple/Spotify stated plainly, Phase 3 switching
back, and the never-do list.

## Design

The full design record — hosting evaluation (Internet Archive primary when an
account exists; GitHub Releases/Pages as the deployed no-new-account hosts),
GUID strategy, Podcasting 2.0 treatment, and source citations — is in
[DESIGN.md](DESIGN.md).

## License

MIT — see [LICENSE](LICENSE).
