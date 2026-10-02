# Subagent brief: privacy-contact research

Paste this into the Agent tool (general-purpose, background):

> Read-only web research. Do NOT submit forms or send anything.
> For each company below, find the OFFICIAL channel for a consumer personal-data deletion
> request in the company's current privacy policy, on official domains only. The requester
> is a {STATE} resident for US companies, an Indian data principal for companies marked IN,
> and an EU/UK data subject for companies marked EU.
> Companies: {Company [sending domain]; …}
> For each one, record: company, privacy_policy_url, deletion_email (only if the policy
> lists it, else null), webform_url, email_accepted (true/false/null), grievance_officer
> (IN only), notes (GLBA/insurance exemption, parent company handles it, CA-only form,
> etc.), confidence.
> Never guess an address like privacy@domain. If no channel exists, say so.
> Work in parallel. Write a JSON array to work/privacy_contacts.json and return a compact
> table (company | email | webform | email_accepted) plus the companies with no channel.

Tips:
- Policies sometimes hide addresses behind Cloudflare email protection. The agent can decode them.
- Watch for typos in mailto links (e.g. `.como`). Write the address by hand.
- "Contact form only" or "California only" means a web form or no right for this user.
