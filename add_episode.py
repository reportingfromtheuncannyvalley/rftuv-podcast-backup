#!/usr/bin/env python3
"""
add_episode.py — add one finished episode bundle to the backup manifest.

Usage:
    python3 add_episode.py <show-slug> <bundle-folder>

The bundle folder must contain the standard six files (audio.mp3, cover.jpg,
script.md, transcript.txt, shownotes.md, metadata.json). The episode gets a
provisional UUIDv5 GUID (same scheme as the initial build: UUIDv5 over
"rftuv-backup|<show>|ep<production-number>|<normalized title>" in the show's
podcast:guid namespace). If the episode is later published on Rebel with a
different GUID, reconcile per RUNBOOK.md ("GUID reconciliation") BEFORE any
failover — directories key episode identity on GUID.

After running this, use ./sync_backup.sh to upload audio, stage artwork and
transcript, regenerate feeds, validate, and push.
"""
import json, os, re, subprocess, sys, uuid
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

HERE = os.path.dirname(os.path.abspath(__file__))

INTERNAL_MARKERS = re.compile(
    r'^\s*[-*]\s+(Show|Episode|Status|Host|Show ID|Drive|Drive Folder|Rebel|YouTube|Cover|Script|Bundle|Audio|Voice|Edition|Date|Publish|Internal)\s*[:\-]', re.I)
INTERNAL_HEADING = re.compile(r'^\s*#{1,6}\s+.*(internal|production record)', re.I)
FURNITURE_LINE = re.compile(
    r'^\s*(Title|Date|Narrator|Status|Duration|Artwork|Audio|Transcript|Contents|Rebel episode page|Host|Voice|Show|Episode ID|Bundle|Script file|Cover file|Drive|YouTube ID)\s*:', re.I)
EPISODE_RECORD_LINE = re.compile(r'^\s*Episode \d+\b.*(Produced|Published|Duration)', re.I)
REBEL_RECORD_LINE = re.compile(r'(Published|Produced).{0,60}on Rebel', re.I)
HARD_SIGNALS = re.compile(
    r'(avocado_v2|metadata\.json|RSS verified|drive\.google\.com|Graphic Designer chat|TTS render|urn:aaid|Episode ID [0-9a-f-]{30,}|ffprobe of audio)', re.I)

def norm_title(t):
    t = (t or '').lower()
    t = re.sub(r'^(the rftuv briefing|reporting from the uncanny valley|dead air valley)\s*[:,–—-]?\s*', '', t)
    t = t.strip().strip('"').strip()
    t = re.sub(r'[^a-z0-9]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def shownotes_public_body(path):
    if not path or not os.path.exists(path):
        return ''
    out = []
    for ln in open(path, encoding='utf-8', errors='replace').read().splitlines():
        if INTERNAL_MARKERS.match(ln) or INTERNAL_HEADING.match(ln):
            break
        if FURNITURE_LINE.match(ln) or EPISODE_RECORD_LINE.match(ln) or REBEL_RECORD_LINE.search(ln):
            continue
        out.append(ln)
    text = '\n'.join(out)
    text = re.sub(r'^\s*# .*\n', '', text, count=1)
    text = re.sub(r'^Episode summary:\s*', '', text, flags=re.M)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = text.replace('**', '').replace('__', '')
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if HARD_SIGNALS.search(text):
        return ''
    return text if len(text) >= 40 else ''

def ffprobe_duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'csv=p=0', path], capture_output=True, text=True)
    return int(round(float(out.stdout.strip())))

def fmt_duration(secs):
    secs = int(secs)
    return f'{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}'

def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    slug, folder = sys.argv[1], os.path.abspath(sys.argv[2])
    manifest_path = os.path.join(HERE, 'manifest.json')
    man = json.load(open(manifest_path))
    show = next((s for s in man['shows'] if s['slug'] == slug), None)
    if show is None:
        sys.exit(f'unknown show slug: {slug}')
    if any(e['bundle_folder'] == folder for e in show['episodes']):
        sys.exit('bundle already in manifest — nothing to do')
    meta = json.load(open(os.path.join(folder, 'metadata.json')))
    audio = os.path.join(folder, meta.get('audio_file') or 'audio.mp3')
    title = (meta.get('title') or '').strip()
    if not title or not os.path.exists(audio):
        sys.exit('bundle missing title or audio file')
    prod_num = meta.get('episode_number')
    if prod_num is None:
        m = re.search(r'-ep(\d+)$', os.path.basename(folder))
        prod_num = int(m.group(1)) if m else max(
            (e['production_episode_number'] or 0 for e in show['episodes']), default=0) + 1
    date = None
    for v in (meta.get('date'), meta.get('publish_date')):
        if v:
            dm = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(v))
            if dm:
                date = dm.group(0)
                break
    if date is None:
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    dur = meta.get('duration_seconds') or meta.get('duration_secs') or ffprobe_duration(audio)
    desc = shownotes_public_body(os.path.join(folder, meta.get('shownotes_file') or 'shownotes.md'))
    if not desc and meta.get('description'):
        desc = str(meta['description']).strip()
    if not desc:
        sys.exit('no public description could be extracted — fix shownotes.md first')
    guid = str(uuid.uuid5(uuid.UUID(show['podcast_guid']),
                          f'rftuv-backup|{slug}|ep{prod_num}|{norm_title(title)}'))
    pages_base = show['feed_url'].rsplit('/feeds/', 1)[0]
    release_base = show['episodes'][0]['enclosure_url'].rsplit('/', 2)[0] if show['episodes'] else ''
    same_day = sum(1 for e in show['episodes'] if e.get('pubDate_derived') and e['date'] == date)
    dt = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(hours=12, minutes=same_day * 10)
    e = {
        'episode_number': prod_num, 'production_episode_number': prod_num,
        'title': title, 'bundle_title': title, 'source': 'network-bundle',
        'bundle_folder': folder, 'audio_local_path': audio,
        'audio_bytes': os.path.getsize(audio),
        'duration_seconds': int(dur), 'duration': fmt_duration(dur),
        'duration_source': 'bundle-metadata' if (meta.get('duration_seconds') or meta.get('duration_secs')) else 'ffprobe',
        'date': date, 'feed_match': False, 'status_raw': str(meta.get('status') or ''),
        'description': desc, 'description_source': 'shownotes',
        'guid': guid, 'guid_source': 'provisional',
        'pubDate': format_datetime(dt), 'pubDate_derived': True,
        'include_in_feed': 'UNPUBLISHED' not in str(meta.get('status') or '').upper(),
        'asset_name': f'ep{prod_num:03d}.mp3',
        'enclosure_url': f"{release_base}/{show['release_tag']}/ep{prod_num:03d}.mp3",
        'artwork_url': f'{pages_base}/art/{slug}/ep{prod_num:03d}.jpg',
        'transcript_url': f'{pages_base}/transcripts/{slug}/ep{prod_num:03d}.txt',
    }
    show['episodes'].append(e)
    man['generated'] = datetime.now(timezone.utc).isoformat()
    json.dump(man, open(manifest_path, 'w'), indent=1)
    print(f"added {slug} ep{prod_num}: {title[:70]}")
    print(f"  guid (provisional): {guid}")
    print('  next: ./sync_backup.sh')

if __name__ == '__main__':
    main()
