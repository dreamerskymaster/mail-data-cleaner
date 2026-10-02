#!/usr/bin/env python3
"""Phase 8b: apply Gmail labels from work/bucket_plan.json (run in the background).

`duplicate` into a label mailbox == "add label" in Gmail; nothing leaves the Inbox.
Smallest buckets first, 50 per AppleScript call, resumable log work/label_log.json,
restarts Mail on a hang. Watch with: tail -f work/label_run.log
"""
from mdc import load, save, osa, restart_mail

P = load('bucket_plan.json'); done = load('label_log.json', {})
MK = '''on run argv
tell application "Mail"
  set a to account (item 1 of argv)
  try
    set mb to mailbox (item 2 of argv) of a
  on error
    make new mailbox with properties {name:(item 2 of argv)} at a
  end try
end tell
end run'''
DUP = '''on run argv
set out to ""
with timeout of 300 seconds
tell application "Mail"
  set a to account (item 1 of argv)
  set src to mailbox "[Gmail]/All Mail" of a
  set dst to mailbox (item 2 of argv) of a
  repeat with i from 3 to count of argv
    try
      duplicate (first message of src whose id is ((item i of argv) as integer)) to dst
      set out to out & (item i of argv) & ","
    end try
  end repeat
end tell
end timeout
return out
end run'''
for key, ids in sorted(P.items(), key=lambda kv: len(kv[1])):
    acct, lab = key.split('\t')
    osa(MK, acct, lab, timeout=150)
    todo = [i for i in ids if str(i) not in done]
    for j in range(0, len(todo), 50):
        ok, out = osa(DUP, acct, lab, *todo[j:j + 50], timeout=360)
        if out == 'timeout': restart_mail(); continue
        for x in out.strip(',').split(','):
            if x: done[x] = lab
        save('label_log.json', done); print(acct, lab, len(done), flush=True)
print('DONE', len(done))
