#!/usr/bin/env python3
"""Phase 3a: collect From/Subject/List-Unsubscribe headers for each unsubscribe target.

Disk-first (.emlx files Mail already downloaded), AppleScript fallback with a short timeout.
Restarts Mail after two consecutive hangs. Resumable: work/unsub_hdrs.json.
  fetch_headers.py [--skip "Account Name"]...
"""
import email, glob, json, os, subprocess, sys
from mdc import load, save, osa, restart_mail

skip = {sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--skip'}
T = load('unsub_targets.json', []); H = load('unsub_hdrs.json', {})
inv = load('inventory.json', [])
disk = {}
for p in glob.glob(os.path.expanduser('~/Library/Mail/V10/**/*.emlx'), recursive=True):
    n = os.path.basename(p).split('.')[0]
    if n.isdigit(): disk[int(n)] = p
pool = {}
for o in inv: pool.setdefault((o['addr'], o['acct']), []).append(o)

HDR = '''on run argv
with timeout of 30 seconds
tell application "Mail"
  set m to first message of mailbox (item 2 of argv) of account (item 1 of argv) whose id is ((item 3 of argv) as integer)
  return all headers of m
end tell
end timeout
end run'''
WANT = ('from:', 'subject:', 'list-unsubscribe:', 'list-unsubscribe-post:')


def from_disk(path):
    raw = open(path, 'rb').read(); nl = raw.index(b'\n'); n = int(raw[:nl])
    m = email.message_from_bytes(raw[nl + 1:nl + 1 + n])
    return ''.join(f"{k}: {' '.join(str(m[k]).split())}\n" for k in ('From', 'Subject', 'List-Unsubscribe', 'List-Unsubscribe-Post') if m[k])


def from_headers(text):
    keep, out = False, []
    for l in text.splitlines():
        if l.lower().startswith(WANT): keep = True; out.append(l)
        elif keep and l[:1] in (' ', '\t'): out[-1] += ' ' + l.strip()
        else: keep = False
    return '\n'.join(out) + '\n'


fails = 0
for i, t in enumerate(T):
    k = str(t['id'])
    if k in H or t['acct'] in skip: continue
    cands = sorted(pool.get((t['addr'], t['acct']), [t]), key=lambda o: -o['date'])
    hit = next((o for o in cands if o['id'] in disk), None)
    if hit:
        H[k] = from_disk(disk[hit['id']])
    else:
        ok, out = osa(HDR, t['acct'], t['box'], t['id'], timeout=40)
        if ok: H[k] = from_headers(out); fails = 0
        else:
            fails += 1
            if fails >= 2: restart_mail(); fails = 0
            continue
    if i % 10 == 0: save('unsub_hdrs.json', H); print(i, len(T), flush=True)
save('unsub_hdrs.json', H)
print('DONE', len(H), 'of', len(T))
