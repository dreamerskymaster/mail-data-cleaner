#!/usr/bin/env python3
"""Pull the verification link out of the newest privacy-portal email.

  confirm_link.py "<Mail account name>" [sender-like, default %onetrust%]
Prints the subject line, then the URL-encoded link (ready for a Kapture compose
`navigate?url=...` line). Only follow links on the company's own privacy domain,
OneTrust or Transcend.
"""
import email, re, sys, urllib.parse
from mdc import load, snapshot, osa, accounts

acc = load('accounts.json') or accounts()
name = sys.argv[1]; like = sys.argv[2] if len(sys.argv) > 2 else '%onetrust%'
uid = next(k for k, a in acc.items() if a['name'] == name)
db = snapshot()
r = db.execute("""select m.ROWID, s.subject, mb.url from messages m join addresses a on a.ROWID=m.sender
                  join subjects s on s.ROWID=m.subject join mailboxes mb on mb.ROWID=m.mailbox
                  where a.address like ? and mb.url like ? order by m.date_received desc limit 1""",
               (like, f'%{uid}%')).fetchone()
if not r: sys.exit('NONE')
box = urllib.parse.unquote(r[2].split('/', 3)[-1])
ok, raw = osa('''on run argv
tell application "Mail" to return source of (first message of mailbox (item 2 of argv) of account (item 1 of argv) whose id is ((item 3 of argv) as integer))
end run''', name, box, r[0], timeout=120)
m = email.message_from_string(raw)
for p in m.walk():
    if p.get_content_type() == 'text/html':
        t = p.get_payload(decode=True).decode('utf-8', 'ignore')
        for href, a in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', t, re.S):
            if re.search(r'privacyaccess|verify|confirm', href, re.I) or 'onfirm' in a:
                print(r[1]); print(urllib.parse.quote(href.replace('&amp;', '&'), safe='')); sys.exit(0)
print('NOLINK', r[1])
