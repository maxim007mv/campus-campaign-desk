# Demo video script (about 3 minutes)

Record the screen with Switch Console and the Mattermost room side by side.

1. **Show the setup (20 s).** In Switch Console, open Templates and show
   `campus-campaign-desk.template.yaml` loaded; deploy it with `team` = `desk`.
   Show the two new agents (`desk-triager`, `desk-ops`) and the room
   `desk-campaign-desk` in Mattermost.
2. **Kickoff (15 s).** Let the kickoff run: both agents introduce themselves.
3. **GO case (60 s).** Paste the text of `01-online-ctf.md`. Expected:
   triager restates it, fills the card (online, certificate: yes, deadline
   12 March 2027 10:00 UTC), classifies GO and hands off to `@desk-ops`.
   desk-ops replies in the thread with a checklist ending in "collect the
   certificate" and a team message draft.
4. **CHECK case (45 s).** Paste `02-hybrid-hackathon.md`. Expected: format
   hybrid with in-person kickoff and finals flagged, certificate "not stated",
   classified CHECK; desk-ops drafts a question to organisers about fully
   online participation and certificates.
5. **Human in the loop (20 s).** Reply in the room as a person:
   "Registered for the CTF, mark it." Expected: desk-ops updates the
   running status only after this confirmation.
6. **SKIP case (20 s).** Paste `03-past-deadline-contest.md`. Expected: SKIP
   (registration closed, on-site final, certificates only for finalists),
   no handoff.
7. **Wrap up (10 s).** Show desk-ops' `plan.md` in its working directory and
   say: without Switch there is no shared room, no handoff between agents and
   no human confirmation step.
