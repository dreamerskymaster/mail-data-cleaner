#!/usr/bin/env python3
"""Phase 8a: dry-run bucket classification of every Gmail All Mail message.

Buckets and their domain/subject regexes come from config.json "buckets" (first match
wins, order matters). Prints counts + example domains; writes work/bucket_plan.json:
{"<Mail account name>\t<label>": [rowid, ...]}. Iterate on config until "Other" < ~15%.
"""
import collections, re
from mdc import cfg, load, save, snapshot, acct_for_url, accounts, own_addresses

C = cfg(); acc = load('accounts.json') or accounts(); OWN = own_addresses(acc)
B = [(b['label'], re.compile(b['domains'], re.I), re.compile(b['subject'], re.I) if b.get('subject') else None) for b in C['buckets']]
PRIV = re.compile(C['patterns']['privacy_subject'], re.I)
FREE = re.compile(r'@(gmail|yahoo|hotmail|outlook|icloud|live|rediffmail|proton)\.', re.I)
db = snapshot()
plan = collections.defaultdict(list); cnt = collections.Counter(); ex = collections.defaultdict(collections.Counter)
for rid, url, addr, subj, lh, ut in db.execute("""select m.ROWID, mb.url, a.address, s.subject, m.list_id_hash, m.unsubscribe_type
        from messages m join mailboxes mb on mb.ROWID=m.mailbox join addresses a on a.ROWID=m.sender join subjects s on s.ROWID=m.subject
        where mb.url like 'imap://%/%5BGmail%5D/All%20Mail'"""):
    a, _ = acct_for_url(url, acc)
    if not a: continue
    addr = (addr or '').lower(); dom = addr.split('@')[-1]; subj = subj or ''
    if PRIV.search(subj): continue                      # keep in the existing Privacy Requests label
    if addr in OWN: lab = C.get('own_label', '🤖 My Automations & Notes')
    else:
        lab = next((l for l, d, s in B if d.search(dom)), None)
        lab = lab or next((l for l, d, s in B if s and s.search(subj)), None)
        lab = lab or ('👤 People' if FREE.search(addr) else ('📰 Newsletters & Promos' if (lh or ut) else '📦 Other'))
    plan[a['name'] + '\t' + lab].append(rid); cnt[lab] += 1; ex[lab][dom] += 1
save('bucket_plan.json', plan)
tot = sum(cnt.values())
for k, v in cnt.most_common():
    print(f"{v:7} {100*v/tot:5.1f}%  {k:32} e.g. {', '.join(d for d, _ in ex[k].most_common(6))}")
print('total', tot)
