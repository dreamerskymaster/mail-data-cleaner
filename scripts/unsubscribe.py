#!/usr/bin/env python3
"""Phase 3b: unsubscribe using the collected headers.

Order: RFC 8058 one-click POST (curl) -> RFC 2369 mailto (sent via Mail from the receiving
account) -> link-only (listed for the user). Resumable log: work/unsub_log.json.
  unsubscribe.py [id ...]     # optional subset (use for a 3-4 message test batch first)
"""
import json, re, subprocess, sys, time, urllib.parse
from mdc import load, save, osa

H = load('unsub_hdrs.json', {}); T = {str(t['id']): t for t in load('unsub_targets.json', [])}
acc = load('accounts.json', {}); NAME2ADDR = {a['name']: (a['emails'] or [''])[0] for a in acc.values()}
log = load('unsub_log.json', {}); ONLY = set(sys.argv[1:])

SEND = '''on run argv
set {fromAddr, toAddr, subj, bod} to {item 1 of argv, item 2 of argv, item 3 of argv, item 4 of argv}
with timeout of 90 seconds
tell application "Mail"
  set msg to make new outgoing message with properties {subject:subj, content:bod, sender:fromAddr, visible:false}
  tell msg to make new to recipient at end of to recipients with properties {address:toAddr}
  send msg
end tell
end timeout
return fromAddr
end run'''


def field(v, name):
    m = re.search(rf'^{name}:(.*?)(?=^\S|\Z)', v, re.I | re.M | re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''


def mailto(t, uri):
    p = urllib.parse.urlparse(uri); q = urllib.parse.parse_qs(p.query)
    to = urllib.parse.unquote(p.path)
    if len(to) > 254 or len(to.split('@')[0]) > 64:     # Gmail rejects these; they jam the Outbox
        return 'mailto-SKIPPED address too long (RFC 5321)'
    ok, out = osa(SEND, NAME2ADDR.get(t['acct'], ''), to, q.get('subject', ['unsubscribe'])[0], q.get('body', ['unsubscribe'])[0], timeout=150)
    return ('mailto-sent from ' + out) if ok else 'mailto-ERR ' + out[-120:]


for k, v in H.items():
    if ONLY and k not in ONLY: continue
    if k in log and 'ERR' not in log[k]: continue
    t = T.get(k)
    if not t: continue
    uris = re.findall(r'<([^>]+)>', field(v, 'List-Unsubscribe'))
    https = [u for u in uris if u.lower().startswith('https://')]
    mt = [u for u in uris if u.lower().startswith('mailto:')]
    res = 'no-header'
    if https and re.search('One-Click', field(v, 'List-Unsubscribe-Post'), re.I):
        r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '-X', 'POST', '-H',
                            'Content-Type: application/x-www-form-urlencoded', '-d', 'List-Unsubscribe=One-Click',
                            '--max-time', '30', https[0]], capture_output=True, text=True, timeout=60)
        code = r.stdout.strip()
        res = f'oneclick {code}' if code[:1] in '23' else f'oneclick-ERR http {code}' + (' | ' + mailto(t, mt[0]) if mt else '')
    elif mt:
        res = mailto(t, mt[0])
    elif https:
        res = 'link-only ' + https[0]
    log[k] = res; save('unsub_log.json', log)
    print(t['base'], t['addr'], '->', res[:110], flush=True); time.sleep(0.5)

ok, n = osa('tell application "Mail" to get count of messages of outbox', timeout=60)
print('Outbox now holds', n, 'message(s). If >0, inspect for long addresses and delete them.')
