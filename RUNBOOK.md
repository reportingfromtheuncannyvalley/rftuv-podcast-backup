# FAILOVER RUNBOOK — RFTUV Podcast Backup RSS

**Purpose:** if Rebel Audio stalls (metering, outage) or dies, keep the three
RFTUV shows publishing over RSS from infrastructure we control, and — only if
Noel decides to move the directory listings — execute the feed change without
breaking the shows' identity in any directory.

**Standing model (Noel, 2026-10-30):** Rebel is the primary host and its RSS is
the feed of record for the Apple/Spotify listings. This backup is a **complete
mirror** of all three shows — everything Rebel has published plus everything
produced since — and is maintained **dually**: every new episode goes into both
Rebel and the backup (see "Maintenance" in README.md). The backup's first job
is carrying the episodes the Oct 22, 2026 meter stall kept out of Rebel, so
they exist in proper RSS form immediately.

**What the backup can and cannot reach — plainly.** A platform listing pulls
exactly **one** feed. While Rebel's feed is the listed feed, the backup
**cannot** add episodes to the existing Apple/Spotify listings — no feed trick
changes that, and submitting the backup as a second listing would create a
duplicate listing (see "Never do"). What the backup reaches **immediately,
with no platform's permission**: the rftuv.ai site player, Stream On, Podcast
Index–aware apps, and anyone subscribed to a backup feed URL directly. The
backlog reaches Apple/Spotify only when (a) Rebel publishes it (the Nov 1
plan), or (b) a feed change is executed (Phase 2 below).

---

## Phase 0 — Confirm the backup is current (always first)

```bash
cd rftuv-podcast-backup
python3 check_drift.py --live     # bundles vs manifest vs release assets vs live feeds
python3 validate_feeds.py --live  # parses, GUID sets, every enclosure 200 + exact length
```

Both must pass before anything else in this runbook. If drift is reported,
run `./sync_backup.sh` and re-check. Do not start a failover on a stale mirror.

## Phase 1 — Immediate-relief distribution (no platform permission needed)

Do these the moment Rebel stalls; none of them touches a directory listing.

1. **rftuv.ai site player** — point the site's podcast player embed at the
   backup feeds:
   - Briefing: `https://reportingfromtheuncannyvalley.github.io/rftuv-podcast-backup/feeds/briefing.xml`
   - Reporting: `https://reportingfromtheuncannyvalley.github.io/rftuv-podcast-backup/feeds/reporting.xml`
   - Dead Air Valley: `https://reportingfromtheuncannyvalley.github.io/rftuv-podcast-backup/feeds/dead-air-valley.xml`
2. **Stream On** — update the three shows' feed URLs to the same backup URLs
   (Stream On resolves shows through the Podcast Index; the shows' Podcast
   Index entries key on `podcast:guid`, which the backup preserves verbatim,
   so Index-aware surfaces keep resolving the same shows).
3. **Direct subscribers / social** — the backup feed URLs above are public and
   permanent; share them wherever episode links are posted.
4. **YouTube** — unaffected by Rebel; the desk's direct-upload pattern
   continues as normal.

Phase 1 is fully reversible: point the same surfaces back at Rebel's feeds
when Rebel recovers. No directory state changes, so nothing can duplicate.

## Phase 2 — Platform-listing switch (ONLY on Noel's explicit word)

This is the highest-risk move in podcasting. It is also **partially out of our
hands today**, and the runbook says so plainly:

### What Rebel's Terms say (Rebel Terms of Service v2026-10-22-v2, §8)

- **Spotify:** distribution runs through **Rebel's own Spotify account** with a
  **90/10 revenue split**; because Rebel holds that relationship, we cannot set
  up or change Spotify monetization for these shows ourselves.
- **Apple:** distribution is **release-on-request** through Rebel; our Apple
  Podcasts Connect presence currently sits inside Rebel's.

### Apple Podcasts

1. The documented feed-move mechanism is `<itunes:new-feed-url>` in the **old**
   feed plus a 301 redirect from the old feed URL (Apple Podcasts
   requirements/support; desk memo `apple-podcasts.md`, `rss-standards.md` §5).
   **We cannot place either on Rebel's feed** — the old feed is Rebel's. A
   clean Apple switch therefore requires Rebel's cooperation (Rebel sets the
   redirect/new-feed-url or releases the show), or a fresh submission under our
   own Apple Podcasts Connect account, which risks a duplicate listing while
   Rebel's listing lives (Apple guideline 1.9 territory). **Escalate to Noel;
   do not improvise.**
2. With Rebel's cooperation: Rebel adds the 301 + `itunes:new-feed-url`
   pointing at the backup feed; Apple follows on its refresh cycle
   (**up to 24 hours** documented planning figure). Verify on the public Apple
   show page: episode list, artwork, and that playback streams the backup
   enclosures (byte lengths match the manifest).

### Spotify

1. The listing sits inside Rebel's distribution account (Terms §8 above).
2. Spotify for Creators documents a **claim** flow for externally hosted shows
   (creators.spotify.com → Find an existing show → enter RSS feed URL →
   8-digit verification code sent to the email in the feed). **Whether a
   Rebel-distributed show can be claimed by us is UNSETTLED** from the official
   pages read (desk memo `spotify.md` §4), and Rebel's Terms bar us from
   touching its monetization regardless. **Do not attempt a claim without
   Noel's word and a Rebel support answer first** (support@rebelaudio.ai).
3. Spotify's own feed-polling interval is **UNSETTLED** (no official page read
   states it); plan on hours-to-days for changes to already-published content
   and verify on the public show page rather than assuming.
4. The Spotify **Podcast Delivery Specification v1.10** (codec/bitrate/
   file-size/cover-art specs) lives only in a provider-support PDF and is
   **not required for this standby system** — the backup delivers nothing to
   Spotify directly. It becomes required reading only if a future direct
   Spotify delivery path is ever built.

### Podcast Index

- Reporting = feed ID **8057966**; The RFTUV Briefing = **8057967**;
  **Dead Air Valley's Index status is UNSETTLED** (site search needs JS/API
  auth; no listing was found in the 2026-10-30 build pass — its feed carries a
  `podcast:guid`, which is the identifier the Index keys on).
- The Index keys show identity on `podcast:guid`; the backup reuses Rebel's
  values verbatim, so a feed-URL change does not create a new show identity.
- To register a changed URL: `GET /api/1.0/add/byfeedurl?url=<backup feed URL>`
  — requires a **read-write** Podcast Index API key (desk holds none today;
  obtaining one is a Noel-approved step). Exact merge/propagation behaviour
  when a known `podcast:guid` arrives at a new URL is **UNSETTLED** from the
  docs read; after submitting, verify at podcastindex.org that the existing
  feed IDs show the backup URL and the full episode list.

### After any Phase 2 switch

- Keep Rebel's feed alive and untouched for at least one full refresh cycle
  of every directory before considering it retired (never retire it while a
  directory still points at it).
- Re-run Phase 0 checks against the backup, then verify each directory's
  public show page: same show, same episode GUIDs, no duplicates, backlog
  episodes present.

## Phase 3 — Switching BACK to Rebel

1. Confirm Rebel is healthy and its feed again carries every episode
   (including anything published only to the backup during the outage — those
   must be published into Rebel first, or the listings will lose them when the
   pointer moves back).
2. Reverse Phase 1 surface changes (site player, Stream On) — instant.
3. If Phase 2 was executed, reverse it with the same belt-and-braces
   procedure (301 + `itunes:new-feed-url`, this time placed in the backup
   feed pointing back at Rebel — that side we control), with the same
   platform-cooperation caveats for Apple/Spotify, and the same verification.
4. Announce nothing publicly until every switched surface verifies.

## GUID reconciliation (read before Phase 2)

Episodes that were never on Rebel carry **provisional** GUIDs
(`guid_source: "provisional"` in manifest.json). If Rebel later publishes one
of those episodes, Rebel assigns its own GUID. Before any failover, reconcile:
update the manifest entry to Rebel's GUID (`guid_source: "rebel"`, Rebel's
pubDate/title), regenerate, re-validate. The GUID directories have already
seen is the one that must survive a feed change — a changed GUID reads as a
brand-new episode (duplicates, lost history). Dual maintenance normally
prevents this: publish to Rebel first, then add to the backup with Rebel's
GUID from the live feed (`add_episode.py` handles the not-yet-on-Rebel case;
when the episode IS on Rebel, copy its GUID/pubDate into the manifest entry
before syncing).

## Never do

- **Never submit a backup feed as a new/second listing** on Apple, Spotify, or
  any directory while the Rebel listing is live — duplicate-listing trap.
- **Never copy Rebel's `itunes:new-feed-url`** (it points at
  feeds.rebelaudio.ai) into a backup feed.
- **Never regenerate GUIDs** during a migration — carry them (see above).
- **Never swap a file at an unchanged enclosure URL** and expect platforms to
  notice — Apple and Spotify both key pickup on URL; corrected audio goes out
  at a new URL with the same GUID.
- **Never attempt a Spotify claim or an Apple submission** without Noel's
  explicit word (see Phase 2 caveats).
- **Never pay Rebel more or migrate the primary host** — the account is comped
  by Rebel (Noel, 2026-10-30); both are off the table without new facts.

## Sources

- Rebel Audio Terms of Service v2026-10-22-v2, §8 (desk memo:
  `~/workspace/tool-guides/rebel-audio.md`).
- Apple Podcasts requirements & support — podcasters.apple.com/support/823-podcast-requirements
  (desk memo: `~/workspace/tool-guides/apple-podcasts.md`).
- Spotify for Creators support — claiming & feed articles
  (desk memo: `~/workspace/tool-guides/spotify.md`; claim path UNSETTLED as noted).
- Podcasting 2.0 namespace spec — github.com/Podcastindex-org/podcast-namespace
  (guid/locked/transcript tag docs; desk memo: `~/workspace/tool-guides/rss-standards.md`).
- Podcast Index API docs — api.podcastindex.org/developer_docs
  (desk memo: `~/workspace/tool-guides/podcast-index-and-podcasting-2.md`).
- Adam Curry, hyperlocal podcasting notes — http://hyperlocal.noagendanotes.com/
  ("Your RSS feed is your direct connection to your listeners" — the reason
  this failover exists and must stay rehearsed, not improvised.)

---

## Addendum — 2026-11-03 (GUID preservation; agreed with Codex cross-check)

The 51 backlog episodes' provisional GUIDs are no longer internal: they are live in the backup feeds, held by direct subscribers and the Podcast Index. The reconciliation step above (rewrite a manifest GUID to Rebel's when Rebel publishes the episode) therefore carries a backup-side cost Codex flagged and the desk accepts: changing a GUID that listeners already hold forks that episode's identity on the backup side too. **Rule until Noel approves an explicit identity plan: provisional GUIDs are PRESERVED as-is. Do not reconcile them to Rebel GUIDs after any capacity relief, and do not regenerate them, unless Rebel confirms it can accept/assign the existing GUIDs or Noel rules otherwise.** New episodes under a restored Rebel-first flow are unaffected (they take Rebel's GUID from birth, as dual maintenance intends).
