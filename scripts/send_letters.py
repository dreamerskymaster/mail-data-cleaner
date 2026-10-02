#!/usr/bin/env python3
"""Phase 5: send data-deletion letters from templates/letters.md.

work/sendlist.json: [{"company": "Acme", "to": "privacy@acme.com", "letter": "A",
                      "from": "me@example.com", "subject_prefix": null}, ...]
Each row is sent once (resumable log work/letters_log.json). Run with N to send only N (test).
"""
import os, re, sys, time
from mdc import ROOT, cfg, load, save, osa

C = cfg(); S = load('sendlist.json', []); log = load('letters_log.json', {})
md = open(os.path.join(ROOT, 'templates', 'letters.md')).read()
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else None
SEND = '''on run argv
set {fromAddr, toAddr, subj, bod} to {item 1 of argv, item 2 of argv, item 3 of argv, item 4 of argv}
with timeout of 90 seconds
tell application "Mail"
  set msg to make new outgoing message with properties {subject:subj, content:bod, sender:fromAddr, visible:false}
  tell msg to make new to recipient at end of to recipients with properties {address:toAddr}
  send msg
end tell
end timeout
return "sent"
end run'''


def template(letter):
    blk = md.split(f'## {letter}.', 1)[1].split('\n## ', 1)[0].split('\n', 1)[1].strip()
    subj = re.match(r'Subject:\s*(.*)', blk).group(1)
    return subj, blk.split('\n', 1)[1].strip()


n = 0
for s in S:
    key = f"{s['company']}|{s['from']}"
    if log.get(key, '').startswith('sent'): continue
    subj, body = template(s['letter'])
    body = (body.replace('{Company}', s['company']).replace('{address}', s['from'])
                .replace('{name}', C['name']).replace('{state}', C.get('state', '')).replace('{law}', C.get('state_law', '')))
    if s.get('subject_prefix'): subj = s['subject_prefix'] + ' - ' + subj
    ok, out = osa(SEND, s['from'], s['to'], subj, body, timeout=150)
    log[key] = ('sent ' + time.strftime('%Y-%m-%d %H:%M') + ' to ' + s['to']) if ok else 'ERR ' + out[-120:]
    save('letters_log.json', log); print(key, '->', log[key], flush=True)
    n += 1
    if LIMIT and n >= LIMIT: break
    time.sleep(3)
