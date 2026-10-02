#!/usr/bin/env python3
"""Phase 7: find replies to the deletion letters (from a fresh index copy).

  replies.py           list all replies grouped by company -> work/replies.json
  replies.py --new     only replies not seen before (then marks them seen)

Matches by sender domain, EXCEPT when the contact address is on a free-mail domain
(gmail/outlook/yahoo): then it matches the exact address, otherwise every Gmail message
would look like a reply.
"""
import datetime, re, sys
from mdc import load, save, snapshot

S = load('sendlist.json', []); sent_at = load('letters_log.json', {})
FREE = ('gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com', 'icloud.com')
doms, exact = {}, {}
for s in S:
    d = s['to'].split('@')[1].lower()
    (exact.__setitem__(s['to'].lower(), s['company']) if d in FREE else doms.__setitem__(d, s['company']))
for d in ('onetrust.com', 'transcend.io', 'zendesk.com', 'freshdesk.com', 'mypurecloud.com'):
    doms.setdefault(d, f'({d.split(".")[0]} portal)')
first = min((v.split(' ')[1] + ' ' + v.split(' ')[2] for v in sent_at.values() if v.startswith('sent ')), default='2000-01-01 00:00')
since = int(datetime.datetime.strptime(first, '%Y-%m-%d %H:%M').timestamp())
KW = re.compile(r'privacy|request|deletion|delete|erasure|grievance|dsar|ticket|case|verif|confirm|opt.?out|personal (data|information)|Re:', re.I)
db = snapshot()
out, seen = {}, set()
for rid, addr, subj, dr, url in db.execute("""select m.ROWID, a.address, s.subject, m.date_received, mb.url from messages m
        join addresses a on a.ROWID=m.sender join subjects s on s.ROWID=m.subject join mailboxes mb on mb.ROWID=m.mailbox
        where m.date_received >= ?""", (since,)):
    addr = (addr or '').lower(); d = addr.split('@')[-1]
    comp = exact.get(addr) or next((c for k, c in doms.items() if d == k or d.endswith('.' + k)), None)
    if not comp or not KW.search(subj or '') or (addr, subj) in seen: continue
    seen.add((addr, subj))
    out.setdefault(comp, []).append(dict(id=rid, frm=addr, subj=subj, url=url,
                                         date=datetime.datetime.fromtimestamp(dr).isoformat(timespec='minutes')))
save('replies.json', out)
old = load('replies_seen.json', {}); oldkeys = {(x['frm'], x['subj']) for L in old.values() for x in L}
for c, L in sorted(out.items()):
    for r in L:
        if '--new' in sys.argv and (r['frm'], r['subj']) in oldkeys: continue
        print(f"{r['id']} | {r['date']} | {c} | {r['frm']} | {r['subj'][:80]}")
if '--new' in sys.argv: save('replies_seen.json', out)
print('companies replied:', len(out))
