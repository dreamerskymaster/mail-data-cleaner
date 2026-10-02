#!/usr/bin/env python3
"""Phase 4: move planned messages to each account's trash mailbox (recoverable ~30 days).

  trash.py PLAN.json [LIMIT]            e.g. trash.py work/trash_plan.json 20   (test batch)
  trash.py --restore DOMAIN [DOMAIN...]  move those senders back out of Trash/Bin

Plan format: {"<Mail account name>\t<mailbox>": [rowid, ...]}. Log: work/<plan>_log.json.
Uses `move` (not `delete`): on Gmail, delete can silently leave mail in place.
"""
import json, os, sys, collections, urllib.parse
from mdc import load, save, osa, restart_mail, snapshot, acct_for_url, accounts

acc = load('accounts.json') or accounts()
BY_NAME = {a['name']: a for a in acc.values()}
MOVE = '''on run argv
set out to ""
with timeout of 300 seconds
tell application "Mail"
  set a to account (item 1 of argv)
  set src to mailbox (item 2 of argv) of a
  set dst to mailbox (item 3 of argv) of a
  repeat with i from 4 to count of argv
    try
      move (first message of src whose id is ((item i of argv) as integer)) to dst
      set out to out & (item i of argv) & ":ok,"
    on error
      set out to out & (item i of argv) & ":ERR,"
    end try
  end repeat
end tell
end timeout
return out
end run'''


def run(plan, logname, limit=None, dest=None):
    done = load(logname, {}); n = 0
    for key, ids in plan.items():
        name, box = key.split('\t')
        a = BY_NAME[name]; dst = dest(a) if dest else a['trash']
        todo = [i for i in ids if str(i) not in done]
        for j in range(0, len(todo), 50):
            batch = todo[j:j + 50][:(limit - n) if limit else None]
            if not batch: return
            ok, out = osa(MOVE, name, box, dst, *batch, timeout=360)
            if out == 'timeout': restart_mail()
            for p in out.strip(',').split(','):
                if ':' in p: k, v = p.split(':'); done[k] = v
            save(logname, done); n += len(batch)
            print(name, box, '->', dst, n, sum(v == 'ok' for v in done.values()), 'ok', flush=True)
            if limit and n >= limit: return


if sys.argv[1] == '--restore':
    want = set(sys.argv[2:]); db = snapshot(); plan = collections.defaultdict(list)
    for rid, url, addr in db.execute('select m.ROWID, mb.url, a.address from messages m join mailboxes mb on mb.ROWID=m.mailbox join addresses a on a.ROWID=m.sender'):
        a, box = acct_for_url(url, acc)
        if a and box == a['trash'] and any((addr or '').lower().endswith(d) for d in want):
            plan[a['name'] + '\t' + box].append(rid)
    run(plan, 'restore_log.json', dest=lambda a: a['allmail'] or a['inbox'])
else:
    plan = json.load(open(sys.argv[1]))
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run(plan, os.path.basename(sys.argv[1]).replace('.json', '_log.json'), lim)
