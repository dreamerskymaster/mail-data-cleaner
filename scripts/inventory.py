#!/usr/bin/env python3
"""Phase 1: build a deduplicated inventory of every message from a COPY of Mail's index.

Writes work/inventory.json (one row per unique message per account) and prints the
top sender domains. Read-only; no AppleScript.
"""
import collections, datetime, sys
from mdc import snapshot, accounts, acct_for_url, base, save, load, SKIP_BOXES

acc = load('accounts.json') or accounts()
db = snapshot()
rows = db.execute("""select m.ROWID, m.global_message_id, mb.url, a.address, a.comment, s.subject,
                            m.date_received, m.read, m.list_id_hash, m.unsubscribe_type
                     from messages m join mailboxes mb on mb.ROWID=m.mailbox
                     left join addresses a on a.ROWID=m.sender left join subjects s on s.ROWID=m.subject""")
seen, out = set(), []
for rid, gid, url, addr, name, subj, dr, rd, lh, ut in rows:
    a, box = acct_for_url(url, acc)
    if not a or any(k in box for k in SKIP_BOXES):
        continue
    key = (a['name'], gid)
    if key in seen:                # Gmail stores one copy per label; keep one
        continue
    seen.add(key)
    addr = (addr or '').lower()
    dom = addr.split('@')[-1] if '@' in addr else addr
    out.append(dict(id=rid, gid=gid, acct=a['name'], box=box, addr=addr, name=name or '', dom=dom,
                    base=base(dom), subj=subj or '', date=dr or 0, read=rd, list=bool(lh) or bool(ut)))
save('inventory.json', out)

g = collections.defaultdict(lambda: dict(n=0, read=0, lst=0, last=0, subj=collections.Counter(), accts=collections.Counter()))
for o in out:
    x = g[o['base']]; x['n'] += 1; x['read'] += o['read']; x['lst'] += o['list']; x['last'] = max(x['last'], o['date'])
    x['subj'][o['subj'][:55]] += 1; x['accts'][o['acct']] += 1
print(f"{len(out)} unique messages across {len({o['acct'] for o in out})} accounts")
print(dict(collections.Counter(o['acct'] for o in out)))
top = int(sys.argv[1]) if len(sys.argv) > 1 else 80
for b, x in sorted(g.items(), key=lambda t: -t[1]['n'])[:top]:
    last = datetime.date.fromtimestamp(x['last']).isoformat() if x['last'] else '?'
    print(f"{x['n']:6} rd{100*x['read']//x['n']:3}% list{100*x['lst']//x['n']:3}% {last} {b:28} | {x['subj'].most_common(1)[0][0]}")
