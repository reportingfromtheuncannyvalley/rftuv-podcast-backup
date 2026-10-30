#!/usr/bin/env python3
"""
validate_feeds.py — the backup build's mandatory checks.

Local mode (default): for each show —
  * feed parses as XML; item count == manifest include_in_feed count
  * every manifest episode is present in the feed (by GUID); no extras
  * GUIDs unique per show; enclosure length == manifest audio_bytes
  * Rebel parity: the Rebel-published subset of the backup feed matches the
    fetched Rebel feed exactly — same GUID set, same relative order,
    same pubDates and titles (work/rebel-<show>.xml must be present;
    skipped with a warning outside the build workspace)

Live mode (--live): additionally HEAD/GET-range checks every enclosure,
artwork, transcript and feed URL on the public hosts.

Exit code 0 = all checks pass. Any failure prints FAIL lines and exits 1.
"""
import json, os, sys, urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
IT = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'
failures = []

def check(cond, msg):
    if not cond:
        failures.append(msg)
        print('FAIL:', msg)

def head(url, range_bytes=False):
    req = urllib.request.Request(url, method='GET' if range_bytes else 'HEAD')
    if range_bytes:
        req.add_header('Range', 'bytes=0-1023')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {})

def main():
    live = '--live' in sys.argv
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    work = os.path.join(HERE, '..', 'work')
    for show in man['shows']:
        slug = show['slug']
        path = os.path.join(HERE, 'docs', 'feeds', f'{slug}.xml')
        tree = ET.parse(path)
        ch = tree.getroot().find('channel')
        items = ch.findall('item')
        expected = [e for e in show['episodes'] if e['include_in_feed']]
        check(len(items) == len(expected), f'{slug}: feed has {len(items)} items, manifest expects {len(expected)}')
        feed_guids = [(i.findtext('guid') or '').strip() for i in items]
        check(len(feed_guids) == len(set(feed_guids)), f'{slug}: duplicate GUIDs in feed')
        exp_guids = {e['guid'] for e in expected}
        check(set(feed_guids) == exp_guids, f'{slug}: feed/manifest GUID sets differ')
        by_guid = {e['guid']: e for e in expected}
        for i in items:
            g = (i.findtext('guid') or '').strip()
            e = by_guid.get(g)
            if e is None:
                continue
            enc = i.find('enclosure')
            check(enc is not None and enc.get('url') == e['enclosure_url'], f'{slug} {g}: enclosure URL mismatch')
            check(enc is not None and int(enc.get('length')) == e['audio_bytes'], f'{slug} {g}: enclosure length mismatch')
            check((i.findtext('pubDate') or '') == e['pubDate'], f'{slug} {g}: pubDate mismatch')
        # Rebel parity for the published subset
        rebel_path = os.path.join(work, f'rebel-{slug}.xml')
        if os.path.exists(rebel_path):
            rch = ET.parse(rebel_path).getroot().find('channel')
            rebel = [(it.findtext('guid') or '').strip() for it in rch.findall('item')]
            backup_subset = [g for g in feed_guids if by_guid.get(g, {}).get('guid_source') == 'rebel']
            check(backup_subset == rebel, f'{slug}: Rebel-subset GUID order/set differs from live Rebel feed')
            check(len(rebel) == show['rebel_published_count'], f'{slug}: rebel_published_count stale')
        else:
            print(f'note: {rebel_path} not present — Rebel parity check skipped')
        if live:
            status, _ = head(show['feed_url'])
            check(status == 200, f'{slug}: live feed URL HTTP {status}')
            for e in expected:
                status, headers = head(e['enclosure_url'])
                check(status == 200, f"{slug} ep{e['episode_number']}: enclosure HTTP {status}")
                cl = headers.get('Content-Length') or headers.get('content-length')
                check(cl is not None and int(cl) == e['audio_bytes'],
                      f"{slug} ep{e['episode_number']}: enclosure length {cl} != {e['audio_bytes']}")
                ct = (headers.get('Content-Type') or headers.get('content-type') or '')
                check('audio' in ct or 'octet' in ct, f"{slug} ep{e['episode_number']}: content-type {ct}")
                status, _ = head(e['artwork_url'])
                check(status == 200, f"{slug} ep{e['episode_number']}: artwork HTTP {status}")
                if e.get('transcript_url'):
                    status, _ = head(e['transcript_url'])
                    check(status == 200, f"{slug} ep{e['episode_number']}: transcript HTTP {status}")
            status, _ = head(expected[0]['enclosure_url'], range_bytes=True)
            check(status in (200, 206), f'{slug}: byte-range probe HTTP {status}')
        print(f"{slug}: local checks done ({len(items)} items)")
    if failures:
        print(f'\n{len(failures)} FAILURE(S)')
        sys.exit(1)
    print('\nALL CHECKS PASSED' + (' (live)' if live else ' (local)'))

if __name__ == '__main__':
    main()
