#!/usr/bin/env python3
"""
generate_feeds.py — read manifest.json and emit one RSS 2.0 + iTunes +
Podcasting 2.0 feed per show into docs/feeds/<show>.xml.

Identity rules (see DESIGN.md): Rebel item GUIDs and pubDates are reused
verbatim for Rebel-published episodes; each show keeps Rebel's podcast:guid;
the backup never emits itunes:new-feed-url. Episodes never on Rebel carry
provisional UUIDv5 GUIDs minted by build_manifest.py / add_episode.py.
"""
import json, os, sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ITUNES = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
PODCAST = 'https://podcastindex.org/namespace/1.0'
ATOM = 'http://www.w3.org/2005/Atom'
ET.register_namespace('itunes', ITUNES)
ET.register_namespace('podcast', PODCAST)
ET.register_namespace('atom', ATOM)

def q(ns, tag):
    return f'{{{ns}}}{tag}'

def sub(parent, ns, tag, text=None, **attrs):
    el = ET.SubElement(parent, q(ns, tag) if ns else tag, attrs)
    if text is not None:
        el.text = str(text)
    return el

def build_feed(show):
    rss = ET.Element('rss', {'version': '2.0'})
    ch = ET.SubElement(rss, 'channel')
    sub(ch, None, 'title', show['title'])
    sub(ch, None, 'link', show['link'])
    sub(ch, None, 'description', show['description'])
    sub(ch, None, 'language', show['language'])
    sub(ch, None, 'lastBuildDate', format_datetime(datetime.now(timezone.utc)))
    sub(ch, None, 'generator', 'RFTUV Backup Feed Generator')
    sub(ch, ATOM, 'link', None, href=show['feed_url'], rel='self', type='application/rss+xml')
    sub(ch, ITUNES, 'author', show['author'])
    ET.SubElement(ch, q(ITUNES, 'category'), {'text': show['category']})
    sub(ch, ITUNES, 'image', None, href=show['artwork_url'])
    owner = sub(ch, ITUNES, 'owner')
    sub(owner, ITUNES, 'name', show['owner_name'])
    sub(owner, ITUNES, 'email', show['owner_email'])
    sub(ch, ITUNES, 'explicit', 'false' if not show['explicit'] else 'true')
    sub(ch, ITUNES, 'type', show['type'])
    sub(ch, PODCAST, 'guid', show['podcast_guid'])
    sub(ch, PODCAST, 'locked', show['podcast_locked'], owner=show['owner_email'])
    sub(ch, PODCAST, 'medium', show['podcast_medium'])
    if show.get('podcast_location'):
        sub(ch, PODCAST, 'location', show['podcast_location'])

    items = [e for e in show['episodes'] if e['include_in_feed']]
    # feed order: newest first (manifest order is Rebel order then production order;
    # reverse by pubDate sort, stable)
    from email.utils import parsedate_to_datetime
    items.sort(key=lambda e: parsedate_to_datetime(e['pubDate']), reverse=True)
    for e in items:
        it = ET.SubElement(ch, 'item')
        sub(it, None, 'title', e['title'])
        sub(it, None, 'description', e['description'])
        sub(it, None, 'pubDate', e['pubDate'])
        sub(it, None, 'guid', e['guid'], isPermaLink='false')
        ET.SubElement(it, 'enclosure', {
            'url': e['enclosure_url'], 'length': str(e['audio_bytes']), 'type': 'audio/mpeg'})
        sub(it, ITUNES, 'duration', e['duration'])
        sub(it, ITUNES, 'episode', e['episode_number'])
        sub(it, ITUNES, 'season', show['season'])
        sub(it, ITUNES, 'episodeType', 'full')
        sub(it, ITUNES, 'image', None, href=e['artwork_url'])
        if e.get('transcript_url'):
            sub(it, PODCAST, 'transcript', None, url=e['transcript_url'], type='text/plain')
    return ET.ElementTree(rss)

def main():
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    outdir = os.path.join(HERE, 'docs', 'feeds')
    os.makedirs(outdir, exist_ok=True)
    for show in man['shows']:
        tree = build_feed(show)
        ET.indent(tree, space='  ')
        path = os.path.join(outdir, f"{show['slug']}.xml")
        tree.write(path, encoding='utf-8', xml_declaration=True)
        n = sum(1 for e in show['episodes'] if e['include_in_feed'])
        print(f"{show['slug']}: {n} items -> {path}")

if __name__ == '__main__':
    main()
