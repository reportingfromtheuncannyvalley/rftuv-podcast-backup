#!/usr/bin/env bash
# sync_backup.sh — the evergreen maintenance command for the RFTUV podcast backup.
#
# Run after add_episode.py has extended manifest.json (or after any manifest
# change). It performs, in order:
#   1. upload any missing episode audio to the show's GitHub Release
#   2. stage episode artwork (1400x1400) + transcripts into docs/
#   3. regenerate the three feeds from the manifest
#   4. run the local validation suite (validate_feeds.py)
#   5. commit and push (GitHub Pages republishes from docs/)
#
# Safe to re-run: uploads are skipped for assets that already exist with the
# right size, and git commits only when something changed.
set -euo pipefail
cd "$(dirname "$0")"

python3 - <<'PYEOF'
import json, os, subprocess, sys
HERE = os.getcwd()
man = json.load(open('manifest.json'))
REPO = 'reportingfromtheuncannyvalley/rftuv-podcast-backup'

def assets(tag):
    out = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO, '--json', 'assets'],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return {}
    return {a['name']: a['size'] for a in json.loads(out.stdout)['assets']}

for show in man['shows']:
    tag = show['release_tag']
    existing = assets(tag)
    for e in show['episodes']:
        if not e['include_in_feed'] or not e['asset_name']:
            continue
        if existing.get(e['asset_name']) == e['audio_bytes']:
            continue
        print(f"uploading {tag}/{e['asset_name']} ({e['audio_bytes']} bytes)")
        import shutil, tempfile
        tmp = os.path.join(tempfile.mkdtemp(), e['asset_name'])
        shutil.copy(e['audio_local_path'], tmp)
        r = subprocess.run(['gh', 'release', 'upload', tag, tmp, '--repo', REPO, '--clobber'],
                           capture_output=True, text=True)
        os.unlink(tmp)
        if r.returncode != 0:
            sys.exit(f"upload failed for {tag}/{e['asset_name']}: {r.stderr.strip()}")
print('audio uploads complete')
PYEOF

# stage artwork + transcripts for any episode missing them
python3 - <<'PYEOF'
import json, os, shutil
from PIL import Image
man = json.load(open('manifest.json'))
for show in man['shows']:
    slug = show['slug']
    cover = os.path.join('docs', 'art', slug, 'cover.jpg')
    for e in show['episodes']:
        if not e['include_in_feed']:
            continue
        n = e['episode_number']
        dst = os.path.join('docs', 'art', slug, f'ep{n:03d}.jpg')
        if not os.path.exists(dst):
            srcs = [os.path.join(e['bundle_folder'], f) for f in os.listdir(e['bundle_folder'])
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')) and ('cover' in f.lower() or 'art' in f.lower())]
            srcs.sort(key=lambda p: (0 if os.path.basename(p) == 'cover.jpg' else 1, len(p)))
            if srcs:
                im = Image.open(srcs[0]).convert('RGB')
                im.thumbnail((1400, 1400), Image.LANCZOS)
                im.save(dst, 'JPEG', quality=88)
            else:
                shutil.copy(cover, dst)
            print('staged art', dst)
        tsrc = os.path.join(e['bundle_folder'], 'transcript.txt')
        tdst = os.path.join('docs', 'transcripts', slug, f'ep{n:03d}.txt')
        if os.path.exists(tsrc) and not os.path.exists(tdst):
            shutil.copy(tsrc, tdst)
            print('staged transcript', tdst)
PYEOF

python3 generate_feeds.py
python3 validate_feeds.py

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "Sync backup mirror: $(date -u +%Y-%m-%dT%H:%MZ)"
  git push origin main
  echo "pushed — GitHub Pages will republish docs/ within a few minutes"
else
  echo "no changes to push"
fi
