# Reducing token usage

A full run touched about 46k messages, 55 companies and 8 accounts. Most of the token cost
comes from *reading*, not doing. Each rule below cut cost a lot in practice.

1. **Index copy, not AppleScript, for anything bulk.** `Envelope Index` holds sender,
   subject, date, read flag, list-unsubscribe flag, mailbox and Gmail labels. One sqlite
   query replaces thousands of AppleScript round-trips and returns in seconds.
2. **Aggregate before printing.** Group by sender domain and print one line per domain:
   the top 80 plus a total. Never print per-message rows except a small sample.
3. **Write to files, read slices.** Keep inventories, plans, header caches and logs as JSON
   in `work/`. Pipe tool output through `cut -c1-120` / `head`.
4. **Background + Monitor.** Header fetch, trash and labelling take minutes to hours. Run
   them with `run_in_background` or `nohup`, and use `Monitor` with a grep that matches only
   milestones (`DONE|timeout|Traceback| [0-9]*000$`). Don't poll with sleep loops.
5. **Subagents for research.** Privacy-contact lookup reads 2–4 pages per company. Give it
   to a general-purpose Agent that writes JSON and returns a compact table. Your context
   only receives the table.
6. **Disk-first headers.** `.emlx` files already on disk give headers with no Mail call. Use
   AppleScript only for the rest, with a 30–40 s timeout.
7. **Read bodies selectively.** Only new replies, and only the first ~500 characters. Strip
   quoted text (`awk '/^On .*wrote:|^From: /{exit}'`).
8. **Kapture economics.** Use `elements` with tight selectors, not `dom` on the whole page.
   Take screenshots at `scale=0.4–0.5`. Batch actions with `compose`. Skip screenshots
   after deterministic steps.
9. **Dry runs.** Show counts first (classify, buckets) so the user corrects the design
   once, not after a long run.
10. **Resumable logs** make retries free: every script skips ids it has already logged.
11. **Large tool outputs.** If a result is huge, pass it to a compression tool (e.g.
    headroom) or re-run with a narrower query instead of reading it all.
