#!/bin/zsh
# Print a message body. usage: readmsg.sh "<Mail account name>" "<mailbox>" <local id> [--source]
# Uses `whose id is N` (the Envelope Index ROWID): fast. Never use `whose message id` on big mailboxes.
prop=content; [[ "$4" == "--source" ]] && prop=source
osascript - "$1" "$2" "$3" "$prop" <<'AS'
on run argv
with timeout of 90 seconds
tell application "Mail"
  set m to first message of mailbox (item 2 of argv) of account (item 1 of argv) whose id is ((item 3 of argv) as integer)
  if (item 4 of argv) is "source" then return source of m
  return content of m
end tell
end timeout
end run
AS
