#!/usr/bin/env python3
"""Phase 2: classify inventory into categories and build the plans the user approves.

Reads config.json keyword lists and (optionally) work/decisions.json:
  {"keep_domains": [...], "promo_keep_numbers": [3, 7], "categories": ["social","adult","promo","mixed"]}
Writes work/cats.json, work/promo_table.json, and (once decisions exist) work/trash_plan.json
and work/unsub_targets.json. Messages carrying a user-made Gmail label are never planned.
"""
import collections, datetime, json, re, urllib.parse
from mdc import cfg, load, save, snapshot, accounts, acct_for_url

C = cfg(); acc = load('accounts.json') or accounts()
inv = load('inventory.json'); dec = load('decisions.json', {})
R = lambda key: re.compile(C['patterns'][key], re.I)
SOCIAL, ADULT, SEC, KEEP, MSG = R('social_domains'), R('adult'), R('security_subject'), R('receipt_subject'), R('message_subject')
PROTECT = set(C['protected_domains']) | set(dec.get('keep_domains', []))
MIXED = set(C['mixed_domains'])
PROMO_RD, PROMO_LIST, PROMO_MIN = C.get('promo_max_read', 0.30), C.get('promo_min_list', 0.6), C.get('promo_min_count', 5)

# messages the user filed under their own Gmail labels / Exchange folders stay untouched
db = snapshot(); user_labelled = set()
JUNKISH = set(C.get('junkish_user_labels', []))
for mid, url in db.execute('select l.message_id, mb.url from labels l join mailboxes mb on mb.ROWID=l.mailbox_id'):
    a, box = acct_for_url(url, acc)
    if a and box != 'INBOX' and not box.startswith('[Gmail]/') and box not in JUNKISH:
        user_labelled.add(mid)

g = collections.defaultdict(list)
for o in inv: g[o['base']].append(o)
promo_bases = [b for b, L in g.items() if b not in PROTECT and b not in MIXED and not SOCIAL.search(b) and not ADULT.search(b)
               and len(L) >= PROMO_MIN and (sum(o['read'] for o in L) / len(L) <= PROMO_RD or sum(o['list'] for o in L) / len(L) >= PROMO_LIST)]

cats = collections.defaultdict(list)
for o in inv:
    b, s = o['base'], o['subj']
    if o['id'] in user_labelled or b in PROTECT or (o['box'] not in ('INBOX', 'Inbox', '[Gmail]/All Mail') and o['acct'] in [a['name'] for a in acc.values() if a['kind'] == 'exchange']):
        cats['protected'].append(o)
    elif ADULT.search(b) or ADULT.search(o['name']):
        cats['adult'].append(o)
    elif SOCIAL.search(b):
        cats['social_keep' if SEC.search(s) and not s.startswith(('"', '“')) else 'social'].append(o)
    elif b in MIXED:
        cats['mixed_keep' if KEEP.search(s) or MSG.search(s) else 'mixed'].append(o)
    elif b in promo_bases:
        cats['promo'].append(o)
    else:
        cats['other'].append(o)
save('cats.json', cats)
for k in ('social', 'social_keep', 'adult', 'promo', 'mixed', 'mixed_keep', 'protected', 'other'):
    print(f'{k:12} {len(cats[k]):7}')

# numbered promo table for one-by-one review
pg = collections.defaultdict(list)
for o in cats['promo']: pg[o['base']].append(o)
table = []
for i, (b, L) in enumerate(sorted(pg.items(), key=lambda t: -len(t[1])), 1):
    rd = 100 * sum(o['read'] for o in L) // len(L)
    last = datetime.date.fromtimestamp(max(o['date'] for o in L)).strftime('%b %Y')
    table.append(dict(n=i, base=b, name=collections.Counter(o['name'] for o in L).most_common(1)[0][0][:24], count=len(L), read=rd, last=last))
save('promo_table.json', table)
print('\n| # | Sender | Emails | Opened | Last |\n|---|---|---|---|---|')
for t in table: print(f"| {t['n']} | {t['name'] or t['base']} ({t['base']}) | {t['count']} | {t['read']}% | {t['last']} |")

# once the user has decided, build the action plans
if dec.get('categories'):
    keep_nums = set(dec.get('promo_keep_numbers', []))
    keep_promo = {t['base'] for t in table if t['n'] in keep_nums}
    chosen = [o for c in dec['categories'] for o in cats.get(c, []) if not (c == 'promo' and o['base'] in keep_promo)]
    chosen = [o for o in chosen if o['base'] not in set(dec.get('keep_domains', []))]
    plan = collections.defaultdict(list); best = {}
    for o in chosen:
        plan[o['acct'] + '\t' + o['box']].append(o['id'])
        k = (o['addr'], o['acct'])
        if k not in best or o['date'] > best[k]['date']: best[k] = o
    save('trash_plan.json', plan)
    save('unsub_targets.json', [dict(id=o['id'], acct=o['acct'], box=o['box'], addr=o['addr'], base=o['base'], date=o['date']) for o in best.values()])
    print(f"\nplanned: {sum(len(v) for v in plan.values())} to trash, {len(best)} unsubscribe targets")
