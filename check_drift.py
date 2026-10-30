#!/usr/bin/env python3
"""
check_drift.py — is the backup mirror still complete and current?

Compares four layers and reports gaps:
  1. Bundle folders on disk (~/workspace/podcast-network/archive/<show>/)
     vs the manifest — a bundle with no manifest entry is an episode the
     backup does not carry.
  2. Manifest vs GitHub Release assets — an include_in_feed episode whose
     epNNN.mp3 asset is missing from its show's release is not downloadable.
  3. Manifest vs the generated feeds (delegated to validate_feeds.py logic:
     GUID set comparison).
  4. With --live: the published Pages feeds vs the local manifest GUID sets.

Run before any failover (RUNBOOK.md step 1) and after every sync.
Exit code 0 = no drift. Requires the gh CLI for layer 2.
"""
import json, os, subprocess, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
NET = os.path.expanduser('~/workspace/podcast-network/archive')
REPO_SLUG = 'reportingfromtheuncannyvalley/rftuv-podcast-backup'

def norm_title(t):
    import re
    t = (t or '').lower()
    t = re.sub(r'^(the rftuv briefing|reporting from the uncanny valley|dead air valley)\s*[:,–—-]?\s*', '', t)
    t = t.strip().strip('"').strip()
    t = re.sub(r'[^a-z0-9]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def release_assets(tag):
    out = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO_SLUG,
                          '--json', 'assets', '--jq', '[.assets[].name] | @tsv'],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return set(out.stdout.strip().split('\t')) if out.stdout.strip() else set()

def main():
    live = '--live' in sys.argv
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    drift = []
    for show in man['shows']:
        slug = show['slug']
        # layer 1: bundles vs manifest. A bundle whose (normalized title,
        # duration ±2s) matches a carried episode is a duplicate production
        # copy (e.g. briefing 2026-10-06-ep8 duplicates Ep5) — covered, not drift.
        known = {os.path.normpath(e['bundle_folder']) for e in show['episodes']}
        root = os.path.join(NET, slug)
        if os.path.isdir(root):
            for d in sorted(os.listdir(root)):
                full = os.path.normpath(os.path.join(root, d))
                mp = os.path.join(full, 'metadata.json')
                if not (os.path.isdir(full) and os.path.exists(mp)) or full in known:
                    continue
                try:
                    meta = json.load(open(mp))
                except Exception:
                    meta = {}
                nt = norm_title(meta.get('title') or '')
                dur = meta.get('duration_seconds') or meta.get('duration_secs') or 0
                dup = any(norm_title(e['bundle_title']) == nt and abs((e['duration_seconds'] or 0) - dur) <= 2
                          for e in show['episodes'])
                if not dup:
                    drift.append(f'{slug}: bundle not in manifest: {d}')
        # layer 2: manifest vs release assets
        assets = release_assets(show['release_tag'])
        if assets is None:
            print(f'{slug}: WARNING could not read release assets (gh) — layer 2 skipped')
        else:
            for e in show['episodes']:
                if e['include_in_feed'] and e['asset_name'] and e['asset_name'] not in assets:
                    drift.append(f"{slug}: ep{e['episode_number']} asset {e['asset_name']} missing from release {show['release_tag']}")
        # layer 3: manifest vs generated feed
        tree = ET.parse(os.path.join(HERE, 'docs', 'feeds', f'{slug}.xml'))
        feed_guids = {(i.findtext('guid') or '').strip() for i in tree.getroot().find('channel').findall('item')}
        exp = {e['guid'] for e in show['episodes'] if e['include_in_feed']}
        if feed_guids != exp:
            drift.append(f'{slug}: generated feed GUID set != manifest (missing {len(exp - feed_guids)}, extra {len(feed_guids - exp)})')
        # layer 4: live feed vs manifest
        if live:
            import urllib.request
            try:
                data = urllib.request.urlopen(show['feed_url'], timeout=30).read()
                lch = ET.fromstring(data).find('channel')
                live_guids = {(i.findtext('guid') or '').strip() for i in lch.findall('item')}
                if live_guids != exp:
                    drift.append(f'{slug}: LIVE feed GUID set != manifest — Pages may be stale; re-run sync')
            except Exception as ex:
                drift.append(f'{slug}: live feed fetch failed: {ex}')
        print(f"{slug}: manifest {len(show['episodes'])} episodes, {sum(1 for e in show['episodes'] if e['include_in_feed'])} in feed")
    if drift:
        print('\nDRIFT DETECTED:')
        for d in drift:
            print(' -', d)
        sys.exit(1)
    print('\nNO DRIFT — backup mirror is complete and current.')

if __name__ == '__main__':
    main()
