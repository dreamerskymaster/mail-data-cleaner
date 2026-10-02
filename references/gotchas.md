# Gotchas (each one cost real time)

## Apple Mail / AppleScript
- **Mail freezes** if you use `whose message id is …`, `whose sender …` or `all headers` on
  a message whose headers aren't local, in a big IMAP mailbox. Mail downloads headers on its
  main thread and blocks every AppleEvent (error -1712). Fix: `kill -TERM` Mail, relaunch
  with `open -g -a Mail`, and use `whose id is N` (index ROWID).
- **Mid-sync accounts** (a large Exchange or Gmail account on first sync) hang header fetches.
  Skip them, do the other accounts, and come back later.
- `osascript - -- args` passes the literal `--` as an argument. Use `osascript - arg1 arg2`.
- `item 1 of (email addresses of account X)` fails. Assign to a variable first, then index.
- `minimum of {a,b}` doesn't exist. Use `if n > 5 then set n to 5`.
- `at` is a reserved word; don't use it as a variable name.
- **Never iterate `messages of mailbox X` while moving items out of X** ("Invalid index"
  / -1728). Collect `id of every message` first, then move by id.
- `reply m without opening window` (not `opening window false`).
- macOS has no `timeout` command; use the tool's own timeout.
- A screen lock doesn't stop Mail, but browser clicks in Kapture may not register.

## Gmail via Mail
- Mail shows Gmail labels as mailboxes. The real messages live in `[Gmail]/All Mail`, and
  the `labels` table maps message → label.
- `delete` on All Mail may report success and do nothing. Use `move` to `[Gmail]/Trash`,
  or **`[Gmail]/Bin` on UK-English accounts** (check each account).
- `move` from INBOX to a user label = **add the label**; the message stays in the Inbox.
  Archive = `move` from INBOX to `[Gmail]/All Mail`.
- `duplicate` into a label mailbox = add the label. That's how labelling works without
  touching the Inbox.
- Moved messages get **new ROWIDs**. Verify by `global_message_id`.
- Emoji label names work.

## Unsubscribing
- Python urllib can fail with `CERTIFICATE_VERIFY_FAILED` behind antivirus TLS inspection.
  Use curl.
- mailto unsubscribe addresses can be 2,000+ characters. Gmail rejects them with "Syntax
  error, command line too long" and they jam the Outbox. Skip anything over 254 characters
  (local part over 64), then clean the Outbox and Drafts.
- Many job-alert platforms (e.g. jobs2web) only offer a web page. List them for the user.
- Unsubscribes can't be undone by script. If the user then says "I use X", tell them to
  re-subscribe in X.

## Privacy requests
- Addresses printed in privacy policies **bounce** (550). Check `X-Failed-Recipients` and
  look for a second official channel (Reply-To on marketing mail, the contact page).
- Some companies reply with a different ticketing domain (zendesk, freshdesk, mypurecloud,
  atlassian). Match those too.
- A contact on gmail.com makes domain matching flag every Gmail message. Match the exact address.
- OneTrust verification links expire in 48–72 h. Confirm them promptly.
- OneTrust forms reveal fields step by step; re-query after each choice. Some take one
  brand per request (submit once per brand).

## Safety
- The user's own personal threads (landlord, roommate, payments) are outside the task.
  Don't summarize, reply or flag them unless asked.
- Before publishing anything about this run, strip names, addresses, account ids and
  ticket numbers.
