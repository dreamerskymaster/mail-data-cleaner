# Mail Data Cleaner

A [Claude Code](https://claude.com/claude-code) **skill** that cleans and organizes every
email account you've connected to **Apple Mail on macOS** (Gmail, Outlook/Exchange, iCloud),
with no API keys or OAuth apps.

What it does, with your approval at every destructive step:

- 📊 **Inventories** every sender in seconds, from a read-only copy of Mail's local SQLite index
- 🗂️ **Classifies** social, adult/dating, pure promo, and mixed senders (receipts kept)
- 🔕 **Unsubscribes** with RFC 8058 one-click, mailto, or a list of link-only pages
- 🗑️ **Moves junk to Trash** (recoverable about 30 days, never permanently deleted), with a restore command
- 🛡️ **Sends data-deletion letters** grounded in the law that actually applies: US state
  privacy acts (e.g. CTDPA/CCPA), GLBA-aware letters for financial firms, India IT Rules / DPDP, GDPR
- 🌐 **Assists with privacy web forms** (OneTrust, Clarip, Zendesk) via the Kapture Chrome MCP.
  You do the CAPTCHA and Submit; it confirms the verification email
- 👀 **Watches for replies** and handles them: records tickets, marks Done, and flags any
  request for ID, phone or address for you. It never sends those itself
- 🏷️ **Applies Gmail label buckets** (Finance, Shopping, Travel, Jobs, …) without moving
  anything out of your Inbox
- 📨 **Emails you an ADHD-friendly report** (your to-dos first, with checkboxes and time
  estimates), replying on the same thread for each update

## Install

```bash
git clone https://github.com/dreamerskymaster/mail-data-cleaner ~/.claude/skills/mail-data-cleaner
cd ~/.claude/skills/mail-data-cleaner && cp config.example.json config.json   # then edit it
```

Then ask Claude Code something like *"clean up my email"* or *"unsubscribe me from junk
and ask companies to delete my data"*. The skill's `SKILL.md` drives the workflow.

## Requirements
- macOS with Apple Mail and your accounts added (System Settings › Internet Accounts)
- Automation permission for your terminal to control Mail (macOS prompts once)
- Python 3. `sqlite3` and `curl` ship with macOS
- Optional: the [Kapture](https://github.com/williamkapke/kapture) browser MCP for web forms

## Layout
```
SKILL.md                 the playbook Claude follows (phases, approval gates, rules)
config.example.json      your name/state, keep-lists, regexes, Gmail bucket rules
scripts/                 inventory, classify, headers, unsubscribe, trash, letters,
                         replies, confirm_link, buckets, label_run, readmsg.sh
templates/letters.md     deletion letters A (US state) · B (GLBA) · C (India) · D (GDPR)
templates/report.md      ADHD-friendly status email
references/              legal.md · token-saving.md · gotchas.md · research-brief.md
work/                    created at runtime (git-ignored): index copy, plans, logs
```

## Safety model
- Nothing is trashed, unsubscribed, sent or submitted without your approval.
- Mail goes to Trash and is never permanently deleted.
- Deletion letters identify you **only by the sending email address**.
- Requests for phone numbers, addresses, user IDs or ID documents are passed to you.
- `work/` holds a copy of your mail index and stays on your machine. It's in `.gitignore`.

## Disclaimer
Not legal advice. Privacy laws change. The skill tells Claude to check the current status
(`references/legal.md`) and to claim only the rights you actually have.

MIT License.
