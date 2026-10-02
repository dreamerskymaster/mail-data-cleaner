#!/usr/bin/env python3
"""Shared helpers for Mail Data Cleaner.

CLI:
  mdc.py accounts            discover Mail accounts -> work/accounts.json
  mdc.py snapshot            copy Mail's Envelope Index into work/
  mdc.py verify LOG.json     check where logged message ids ended up (by global id)
"""
import glob, json, os, re, shutil, sqlite3, subprocess, sys, time, urllib.parse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, 'work')
INDEX_GLOB = os.path.expanduser('~/Library/Mail/V10/MailData/Envelope Index*')
os.makedirs(WORK, exist_ok=True)


def cfg():
    p = os.path.join(ROOT, 'config.json')
    if not os.path.exists(p):
        sys.exit('config.json missing: cp config.example.json config.json and edit it')
    return json.load(open(p))


def load(name, default=None):
    p = os.path.join(WORK, name)
    return json.load(open(p)) if os.path.exists(p) else default


def save(name, obj):
    json.dump(obj, open(os.path.join(WORK, name), 'w'), indent=1, ensure_ascii=False)


def snapshot(sub='snap'):
    """Copy the live index (plus -wal/-shm) and open the copy read-only. Never touch the live file."""
    d = os.path.join(WORK, sub); os.makedirs(d, exist_ok=True)
    for f in glob.glob(INDEX_GLOB):
        shutil.copy(f, d)
    return sqlite3.connect(os.path.join(d, 'Envelope Index'))


def base(dom):
    """Registrable domain, good enough for grouping senders (handles co.in, ac.uk ...)."""
    p = (dom or '').lower().split('.')
    if len(p) >= 3 and p[-2] in ('co', 'com', 'ac', 'org', 'net', 'gov', 'edu') and len(p[-1]) == 2:
        return '.'.join(p[-3:])
    return '.'.join(p[-2:])


def osa(script, *args, timeout=180):
    """Run AppleScript with argv. Returns (ok, stdout_or_err)."""
    try:
        r = subprocess.run(['osascript', '-', *map(str, args)], input=script,
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, 'timeout'


def restart_mail():
    subprocess.run(['pkill', '-TERM', '-x', 'Mail']); time.sleep(8)
    subprocess.run(['pkill', '-9', '-x', 'Mail']); time.sleep(2)
    subprocess.run(['open', '-g', '-a', 'Mail']); time.sleep(25)


def accounts():
    """Map Envelope-Index UUID -> {name, trash, kind, emails}."""
    ok, out = osa('''tell application "Mail"
set r to ""
set AppleScript's text item delimiters to "||"
repeat with a in every account
  set r to r & (id of a) & "\t" & (name of a) & "\t" & ((email addresses of a) as string) & linefeed
end repeat
return r
end tell''', timeout=120)
    if not ok:
        sys.exit('Could not talk to Mail: ' + out)
    # full mailbox paths (incl. nested [Gmail]/Bin) come from the index, not AppleScript
    paths = collections.defaultdict(list)
    for (url,) in snapshot().execute('select url from mailboxes'):
        m = re.match(r'\w+://([0-9A-F-]{36})/(.*)', url or '')
        if m: paths[m.group(1)].append(urllib.parse.unquote(m.group(2)))
    acc = {}
    for line in out.splitlines():
        uid, name, emails = (line.split('\t') + ['', '', ''])[:3]
        mbs = paths.get(uid, [])
        trash = next((m for m in mbs if m in ('[Gmail]/Trash', '[Gmail]/Bin', 'Deleted Items', 'Deleted Messages', 'Trash')), None)
        kind = 'gmail' if any(m.startswith('[Gmail]') for m in mbs) else ('exchange' if 'Deleted Items' in mbs else 'imap')
        acc[uid] = dict(name=name, emails=[e.strip() for e in emails.split('||') if e.strip()], trash=trash, kind=kind,
                        inbox='INBOX' if 'INBOX' in mbs else 'Inbox', allmail='[Gmail]/All Mail' if kind == 'gmail' else None)
    save('accounts.json', acc)
    return acc


def acct_for_url(url, acc):
    """Envelope-Index mailbox URL -> (account dict, mailbox path)."""
    m = re.match(r'\w+://([0-9A-F-]{36})/(.*)', url or '')
    if not m:
        return None, None
    return acc.get(m.group(1)), urllib.parse.unquote(m.group(2))


def own_addresses(acc):
    return {e.lower() for a in acc.values() for e in a['emails']} | {e.lower() for e in cfg().get('own_addresses', [])}


SKIP_BOXES = ('Sent', 'Drafts', 'Trash', 'Bin', 'Deleted', 'Spam', 'Junk', 'Outbox', '[Gmail]/Important')


def verify(logname):
    """For ids in a trash/label log, report which mailbox each message now lives in."""
    log = json.load(open(logname))
    ids = [int(k) for k, v in log.items() if v == 'ok']
    old = sqlite3.connect(os.path.join(WORK, 'snap', 'Envelope Index'))
    new = snapshot('snap_verify')
    c = collections.Counter()
    for i in range(0, len(ids), 900):
        chunk = ids[i:i + 900]
        gids = [r[0] for r in old.execute(f"select global_message_id from messages where ROWID in ({','.join(map(str, chunk))})")]
        for g in gids:
            locs = sorted({u.split('/', 3)[-1] for (u,) in new.execute(
                'select mb.url from messages m join mailboxes mb on mb.ROWID=m.mailbox where m.global_message_id=?', (g,))})
            c[' + '.join(urllib.parse.unquote(l) for l in locs) or 'GONE'] += 1
    for k, v in c.most_common():
        print(f'{v:6}  {k}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'accounts'
    if cmd == 'accounts':
        for uid, a in accounts().items():
            print(f"{a['name']:40} {a['kind']:8} trash={a['trash']}  {', '.join(a['emails'])}")
    elif cmd == 'snapshot':
        snapshot(); print('copied to', os.path.join(WORK, 'snap'))
    elif cmd == 'verify':
        verify(sys.argv[2])
