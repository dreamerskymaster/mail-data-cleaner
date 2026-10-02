---
name: mail-data-cleaner
description: Clean up and organize every email account a person has connected to Apple Mail on macOS (Gmail, Outlook/Exchange, iCloud). It inventories senders, unsubscribes, trashes junk, sends legally grounded data-deletion requests (US state privacy laws, GLBA, India IT Rules/DPDP, GDPR), handles privacy-portal web forms, watches for company replies, applies Gmail label buckets and emails a status report. Use when the user asks to clear junk email, unsubscribe in bulk, delete their data from companies, organize or label their mail, or follow up on privacy requests.
---

# Mail Data Cleaner

A phased, approval-gated playbook for cleaning a person's mail across all their
accounts through **Apple Mail + AppleScript + Mail's local SQLite index**. It needs
no Gmail API keys and works with any account Mail can sync.

> **Golden rules**
> 1. **Nothing destructive happens without the user's approval.** That covers trashing,
>    unsubscribing, sending deletion letters and submitting web forms. Show counts and
>    sender lists first.
> 2. **Trash, never delete permanently.** Move mail to the account's Trash/Bin
>    (recoverable for about 30 days). Never empty Trash.
> 3. **Never send more personal data than the email address the request comes from.**
>    No phone numbers, street addresses, ID documents or dates of birth. If a company
>    asks for any of these, stop, mark it "Needs user" and notify the user.
> 4. **Claim only legal rights the user actually has.** Pick the law from where they
>    live (see `references/legal.md`). If no law applies, write a policy-based request.
> 5. **The user's corrections win immediately.** If they say "I use X", restore X from
>    Trash and drop it from every later step.
> 6. **Do only what the user asked.** Don't comment on, reply to or rearrange personal
>    mail outside the task.

## Requirements
- macOS with Apple Mail, and every account already added under System Settings ›
  Internet Accounts.
- Terminal granted Automation access to Mail (macOS prompts the first time).
- Python 3. `sqlite3` and `curl` ship with macOS.
- Optional: the Kapture browser MCP (Chrome) for privacy web forms, the Agent tool
  for contact research, CronCreate for reply monitoring, and a Markdown or Obsidian
  vault for the tracker note.

## Setup
```bash
cp config.example.json config.json   # edit: your name, residency, keep/junk lists
python3 scripts/mdc.py accounts       # discovers accounts, UUIDs, trash mailboxes
```
Every script reads `config.json` and writes resumable JSON logs into `work/`.

## Phase map

| # | Phase | Script | User input needed? |
|---|---|---|---|
| 0 | Connect accounts | `mdc.py accounts` | **Yes:** add accounts in Internet Accounts |
| 1 | Inventory | `inventory.py` | No |
| 2 | Classify and ask | `classify.py` | **Yes:** approve categories and keep-lists |
| 3 | Unsubscribe | `fetch_headers.py` → `unsubscribe.py` | Approved in phase 2 |
| 4 | Trash | `trash.py` | Approved in phase 2 |
| 5 | Deletion letters | `send_letters.py` | **Yes:** residency, letter text, per-company exceptions |
| 6 | Web forms | Kapture (manual-assist) | **Yes:** CAPTCHA, Submit, street address |
| 7 | Reply monitoring | `replies.py`, `confirm_link.py` | Only for "Needs user" items |
| 8 | Labels / buckets | `buckets.py` → `label_run.py` | **Yes:** approve the bucket design (dry run) |
| 9 | Report | `templates/report.md` | No |

---

## Phase 0: Connect
1. `python3 scripts/mdc.py accounts` lists the Mail accounts with their UUIDs and
   trash mailbox names, and writes them to `work/accounts.json`.
2. If an account is missing, tell the user to add it under **System Settings ›
   Internet Accounts** and wait for its first sync. Gmail's first sync of a large
   account can take hours, so don't treat partial counts (often exactly 50 per
   folder) as final.
3. Work Outlook accounts may need admin approval ("Need admin approval"). That's the
   user's IT department to sort out, not something to work around.

## Phase 1: Inventory (the cheap part)
`python3 scripts/inventory.py` copies `~/Library/Mail/V10/MailData/Envelope Index*`
into `work/` and queries the copy read-only. This is **far faster and cheaper than
AppleScript**: 50k messages take about 2 seconds. It dedupes Gmail's All Mail copies,
skips Sent/Drafts/Trash/Spam, and writes `work/inventory.json` plus a sender-domain
report: count, % read, % with a List-Unsubscribe header, last date, example subject.

## Phase 2: Classify and ask
`python3 scripts/classify.py` sorts each message into `social`, `social_keep`
(security/login emails), `adult`, `promo`, `mixed`, `mixed_keep` (receipts, orders,
statements, messages) or `protected`. The keyword lists live in `config.json`. The
script prints totals and a **numbered promo table**.

Ask with **AskUserQuestion**, one question per category, with a recommended option first:
- Social: delete everything except security/login emails? Or everything? Or only named platforms?
- Adult/dating: which platforms?
- Pure promo: delete everything on a reviewed list, only never-opened senders, or review one by one?
- Mixed senders: promos only (keep receipts and orders), leave alone, or delete all?

For a one-by-one review, print the numbered table and ask the user to "reply with the
numbers to KEEP". Point out likely keeps yourself (vehicle reports, utility bills,
newsletters they open often).

Ask before going further:
- **Where do you live?** This decides the deletion law; see `references/legal.md`.
- **Accounts holding money or devices** (exchanges, wallets, cards, routers, phones):
  deletion can lose balances or lock the user out of hardware. Ask company by company.
- **Spam networks:** unsubscribing confirms the address is live. Unsubscribe, or just trash?
- **Apps they still use:** unsubscribe and trash only, with no deletion letter.

Write the approved choices to `work/decisions.json`; later steps read it.

## Phase 3: Unsubscribe
1. `fetch_headers.py` picks the newest message per (sender address, account) and reads
   its `List-Unsubscribe` header. It reads the `.emlx` file on disk first and falls back
   to AppleScript (`whose id is N`, 30 s timeout). If Mail hangs twice in a row, it
   restarts Mail. It skips accounts that are still syncing (`--skip ACCOUNT`) and
   retries them later.
2. `unsubscribe.py`, in order of preference:
   - **RFC 8058 one-click**: `curl -X POST -d List-Unsubscribe=One-Click <https url>`.
     Use curl, not Python urllib, because antivirus/TLS-inspection setups break
     Python's certificate check.
   - **mailto**: an outgoing message sent through Mail from the account that received
     the mail. **Skip addresses longer than 254 characters (or a local part over 64).**
     Some senders use 2,000-character addresses that make Gmail bounce with "command
     line too long" and leave messages stuck in the Outbox.
   - **link-only** (a web page): list it for the user, or open it with Kapture and
     confirm visually.
3. Afterwards, check that the Outbox is empty, and delete leftover drafts the script
   created (Mail sometimes autosaves outgoing messages as drafts).

## Phase 4: Trash
`trash.py work/trash_plan.json` moves messages in batches of 50 by local id, from the
mailbox where the copy lives to that account's trash mailbox. On Gmail that's
`[Gmail]/All Mail` → `[Gmail]/Trash`, or `[Gmail]/Bin` on UK-locale accounts.
- **Use `move` to the trash mailbox, not `delete`.** On Gmail, `delete` sometimes
  reports success and leaves the message where it was.
- **Test with 20 messages first** (`trash.py plan.json 20`). Then run
  `mdc.py verify work/trash_log.json`, which matches by `global_message_id` because
  moved messages get new ROWIDs, and confirm they're in Trash/Bin.
- `classify.py` excludes anything with a user-made Gmail label or in a user-made
  Exchange folder. Those exist because the user filed them on purpose.
- **To restore**, run `trash.py --restore <domains>`. It moves messages back from
  Trash to All Mail / Inbox.

## Phase 5: Deletion letters
1. **Research contacts with a subagent** (Agent tool, general-purpose). Use the brief
   in `references/research-brief.md`. Ask for official privacy-policy sources only, no
   guessed `privacy@` addresses, and JSON with email, webform, grievance officer and
   exemption notes. This keeps dozens of page fetches out of your own context.
2. Choose the letter from `templates/letters.md` (see `references/legal.md`):
   **A** US state privacy law · **B** GLBA-exempt financial firm (policy-based) ·
   **C** India (IT Rules r.5(7), continuing under DPDP s.12) · **D** GDPR/UK GDPR Art. 17.
3. Show the user the letter text once and get approval. Then `send_letters.py` sends
   one letter per (company, address that company holds), from that address,
   identifying the user only by that address.
4. Handle bounces (`mailer-daemon` with `X-Failed-Recipients`). Look for another
   official address, such as the Reply-To on their marketing mail or the contact page.
   Don't guess.

## Phase 6: Web forms (Kapture / Chrome MCP)
These are privacy portals with no email channel: OneTrust, Clarip, Zendesk and
custom forms.
- Fill only the minimum: name, email, state, request type ("Delete"), "Myself". Use
  the ZIP only if the form requires it and the user has given it.
- **Stop at the CAPTCHA and the Submit button.** The user ticks the CAPTCHA and makes
  the "under penalty of law" declaration themselves.
- **Stop if a street address or phone number is required.** Hand the form to the user.
- After the user submits, `confirm_link.py <account> <sender-like>` pulls the
  verification link from the newest matching email. Open it with Kapture and
  screenshot the "request confirmed" page. Links expire in 48–72 h.
- Kapture tips: call `show` before clicking, because clicks in hidden tabs are
  dropped. Use `elements` with selectors rather than full DOM dumps. Take screenshots
  at scale 0.4–0.5. Accept `beforeunload` dialogs with the `dialog` tool. OneTrust
  forms reveal fields step by step, so re-query `elements` after each choice.
- If the harness permission classifier blocks a form action, stop and give the user
  the list. Don't look for a way around it.

## Phase 7: Reply monitoring
Schedule `CronCreate` every ~6 hours (session-only, ends after 7 days) with this prompt:
> Run `python3 scripts/replies.py --new`. For each new reply, read its body
> (`scripts/readmsg.sh`), then: (a) acknowledgement or ticket → record the ticket number;
> (b) "deleted" / "completed" / "no account found" → mark Done; (c) verification link
> from the company's privacy domain, OneTrust or Transcend → open it with Kapture;
> (d) a request for ID, phone or address, or a denial → send nothing, mark "Needs user"
> and PushNotification; (e) refusal citing an exemption → record the reason. Update the
> tracker.

"Use our form instead" replies: answer that the law allows any request method the
policy lists, that the 45-day clock started on the original email date, and ask them
to process it.

## Phase 8: Labels / buckets (Gmail)
1. `buckets.py` runs a **dry run**. It assigns every All Mail message to one bucket
   (Finance, Shopping & Orders, Travel, Jobs, Education, Government, Tech, Security,
   Home, Work, People, My Automations, Newsletters, Other) and prints counts with
   example domains. Show it to the user and refine `config.json` until "Other" is
   under ~15%.
2. `label_run.py` creates the labels and **duplicates** each message into its label,
   resumably, smallest buckets first. In Gmail, duplicating adds a label and removes
   nothing.
3. **Gmail quirks:** `move` from INBOX to a label mailbox only adds the label; the
   message stays in the Inbox. To archive, move it from INBOX to `[Gmail]/All Mail`.
   Leave Exchange/Outlook folders alone, because moving there takes mail out of the Inbox.

## Phase 9: Report
Fill in `templates/report.md` (ADHD-friendly: a summary, then the user's to-dos as
checkboxes with time estimates and exact paths, then Done, Waiting and Where things
are). Send it from one account to all the user's addresses. For later updates,
**reply on the same thread** so the history stays together. Log the same content to
the user's notes vault.

---

## Where the user must act (prompt them clearly)
- Adding accounts, and granting Automation / Full Disk Access.
- Every approval gate in phase 2, plus residency, the letter text and money/device accounts.
- CAPTCHAs, Submit buttons and "penalty of law" declarations.
- Any request for phone, street address, user ID or ID documents.
- In-app-only account deletion (some companies offer nothing else).
- Re-subscribing to anything unsubscribed before a correction arrived.

## Token-saving rules (see `references/token-saving.md`)
1. Query a **copy of the SQLite index**, not AppleScript, for anything you read in bulk.
2. Aggregate in Python and **print only summaries**: counts, the top N and samples.
3. Write big outputs to `work/` files and read slices back.
4. Run long jobs (headers, trash, labels) in the **background with resumable logs**,
   and watch them with `Monitor` on a filtered log line.
5. Send research (privacy contacts, legal status) to a **subagent**.
6. Never put `whose message id is` or `whose sender` on a big IMAP mailbox. It downloads
   every header on Mail's main thread and freezes Mail. Use `whose id is N`, which is
   the index ROWID.
7. Never loop over `messages of mailbox X` while moving them. Collect ids first.
8. For Kapture, take small screenshots and use `elements` with tight selectors.

## Other skills and tools this playbook uses
- **AskUserQuestion**: every approval gate.
- **Agent (general-purpose)**: privacy-contact research and legal-status checks.
- **WebSearch / WebFetch**: current law status (US state laws, India DPDP phases).
- **Kapture MCP (Chrome)**: privacy web forms, verification links, link-only unsubscribes.
- **CronCreate / Monitor / PushNotification**: reply monitoring and background progress.
- **Memory**: per-machine quirks, such as which accounts use `[Gmail]/Bin`.
- A **Markdown / Obsidian vault** for the tracker note.

Read `references/gotchas.md` before running anything for the first time.
