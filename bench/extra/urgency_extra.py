"""Extra URGENCY items for the assay benchmark (kept apart from make_tasks.py, which is not edited).

Every label is set BY CONSTRUCTION by the author from the written urgency scale in bench/tasks/tasks.json:
  1 = question or wish, no problem      2 = small annoyance with an easy workaround
  3 = one person affected, work continues, can wait a day
  4 = a person or team is blocked, or a deadline within about a day
  5 = outage, data loss, security exposure, or many customers stopped now
The facts that decide the level (how many people, deadline, workaround, data at risk) are written INTO each
ticket. No model was asked. `truth` is the string "1".."5", exactly like make_tasks.item().

    from bench.extra.urgency_extra import items
    rows = items(random.Random(1))
"""
from __future__ import annotations

import random

NAMES = ["Priya", "Tom", "Alicia", "Marcus", "Dana", "Yusuf", "Ines", "Kofi", "Helen", "Raj", "Mei", "Jonas"]
OPENERS = ["Hi team,", "Hello,", "Hey,", "Good morning,", "", "Hi support,", "Hello there,", "Hi,"]
CLOSERS = ["Thanks!", "Cheers", "Thank you.", "", "Regards", "Many thanks,", "Thanks in advance."]

# Irrelevant text placed in front of the one sentence that decides the level (four different paddings).
PADS = [
    "Apologies for the essay. Our team has just gone through a reorganisation, three people have new managers, the "
    "canteen changed its menu, and I have been sitting in workshops about 'ways of working' all week. My inbox is a "
    "mess and I forgot to send this yesterday. Right, ",
    "Not sure if this is the right place, I was passed around a bit. I have been with the company for eleven years, "
    "started in the old building, and I remember when we used paper forms for everything. Things were simpler then. "
    "Also the lift is broken again. Anyway, ",
    "Long day, so bear with me. The parking situation is terrible, the heating is either off or on full, and our "
    "quarterly meeting overran by an hour and a half. I also need to book a dentist appointment. Moving on, ",
    "Hope you are well. I have been meaning to write for a while but the summer holidays got in the way, the kids "
    "were off school, and then I had a cold for a week. Looking back at my notes from last month, ",
]


def _wrap(core: str, rng: random.Random) -> str:
    op, cl = rng.choice(OPENERS), rng.choice(CLOSERS)
    sign = f"\n{rng.choice(NAMES)}" if rng.random() < 0.5 else ""
    return "\n".join(x for x in (op, core, cl + sign) if x).strip()


def _item(state: str, truth: str, hard: bool, kind: str) -> dict:
    return {"state": state, "truth": truth, "hard": hard, "kind": kind}


# ==================================================================================================
# HAND-WRITTEN ITEMS. (level, kind, text). kind "easy" = plain item, wrapped in a greeting/sign-off.
# Everything else is a hard item (a trap) and is used exactly as written.
# ==================================================================================================
HAND: list[tuple[str, str, str]] = [
    # ---------------------------------------------------------------- level 1: question or wish
    ("1", "shouting_wish", "HELP!!! CRITICAL!!! MAKE THE LOGO IN THE TOP LEFT CORNER BIGGER!!! URGENT!!! (Everything works, this is just what I would like.)"),
    ("1", "urgent_subject_feature", "Subject: URGENT - action required\n\nWe would love a dark mode for the admin panel. It is not needed for any deadline; it is just a feature request from our design team."),
    ("1", "urgent_subject_feature", "Subject: !!! CRITICAL !!!\n\nCould you add a Slack integration for the weekly digest email? We do not use anything like it today and nothing is wrong, it is only an idea."),
    ("1", "urgent_subject_feature", "Subject: ASAP\n\nHi, could you add an export to Markdown one day? It would be a nice extra for our documentation team, who copy and paste today without any trouble."),
    ("1", "padded_question", PADS[0] + "I was wondering whether the timeline view could have a zoom slider some day. That is the whole request, nothing is broken."),
    ("1", "quoted_alarm", "The site manager pinned a note that reads \"CRITICAL: FIND OUT ABOUT THE OLD ARCHIVE!!\" and it turns out all he wants to know is how long you keep archived tickets. A number is enough, please."),
    ("1", "deadline_weeks_away", "We launch our new online store in seven weeks. Will your platform support gift wrapping options by then? A yes or no is enough, there is no problem today."),
    ("1", "deadline_weeks_away", "Our external audit is in March, months from now. Is there a way to get an overview of who logged in over the last year? Asking early so we can plan, nothing is wrong."),
    ("1", "mixed_language", "Hallo, kurze Frage: gibt es einen Dunkelmodus fuer das Dashboard? Kein Problem, nur ein Wunsch. Thanks!"),
    ("1", "mixed_language", "Hola, quisiera saber si planean anadir una integracion con Notion. Sin prisa, just curious about the roadmap."),
    ("1", "very_short", "Is there a dark mode?"),
    ("1", "very_short", "Any API docs in Portuguese?"),
    ("1", "already_resolved", "Please ignore my earlier ticket about the missing invoice, I found it in the archive folder and everything is fine. One question: could that folder be renamed 'Old invoices' at some point? Only a thought."),
    ("1", "already_resolved", "My login trouble from yesterday fixed itself after a restart, so nothing is needed from you. Out of interest, will single sign-on come to the small plan?"),
    ("1", "shouting_wish", "I AM FURIOUS!!! WHY DOES NOBODY OFFER EMOJI REACTIONS ON COMMENTS??? Everything works fine, I just want them."),
    ("1", "billing_question_calm", "Do you offer annual invoicing in euros? We are planning next year's budget. Nothing is wrong with the current invoices."),
    ("1", "staging_wish", "A small wish for the staging site: a banner saying 'STAGING' so we do not confuse it with production. Nothing is wrong right now."),
    ("1", "security_wish", "General question about security: do you plan to support hardware security keys someday? We use authenticator apps today and have had no incidents."),
    ("1", "multi_wish", "Two ideas: could the export button be on the left, and could the app remember my last used filter? Neither blocks anything."),
    ("1", "big_words_wish", "Dear Sir or Madam, I wish to formally register a request of the gravest importance: may the tables one day offer a compact density option? That is all."),
    ("1", "padded_question", PADS[2] + "does the platform have a way to print labels in A6 format? I am only asking for future planning."),
    ("1", "healthcare_wish", "Question from the clinic manager: could the appointment list be sorted by clinician? We manage fine without it, so only if it is easy to add."),
    # level 1, plain
    ("1", "easy", "How do I change the language of the interface? I could not find the option, but I am not in a hurry."),
    ("1", "easy", "Can you tell me in which countries your servers are located? It is for our internal records."),
    ("1", "easy", "Could the CI dashboard show build durations as a graph? It would be a nice extra."),
    ("1", "easy", "Is the free plan limited to a number of projects? I am curious before I recommend it to a friend."),
    ("1", "easy", "The pharmacy portal manual mentions a mobile version. Is that on the roadmap?"),
    ("1", "easy", "Our warehouse team asked whether the scanner app could offer a left-handed layout. Just an idea."),
    ("1", "easy", "How long do you keep deleted items in the recycle bin? Curious only, nothing has been deleted."),
    ("1", "easy", "Which time zone do the daily digest emails use? Just for my own understanding."),
    ("1", "easy", "Would it be possible to get a printed user guide for new staff? Nice to have, no rush."),
    ("1", "easy", "Do you have a partner programme for small agencies? I would like to read about it when you have a minute."),

    # ---------------------------------------------------------------- level 2: small annoyance, easy workaround
    ("2", "workaround_exists", "The scheduled report email no longer includes the attachment, but I can download the same report from the Reports page in two clicks. Only a nuisance."),
    ("2", "angry_tone_small", "THIS IS UNACCEPTABLE!!! The country dropdown still lists Swaziland instead of Eswatini. Everything else works. Fix it when you can."),
    ("2", "shouting_cosmetic", "CRITICAL BUG!!! The 'Cancel' button in the settings dialog is grey instead of red. It still works exactly as it should, it is just irritating."),
    ("2", "negated_outage", "This is not an outage and nothing is down. The search box in the mobile app ignores capital letters, so 'Berlin' finds nothing, but 'berlin' works, so I type lowercase."),
    ("2", "padded_workaround", PADS[1] + "the date picker opens on the wrong month, but I click the arrow to move it and carry on."),
    ("2", "staging_cosmetic", "On the staging site the logo does not load on the login page. Production is fine and we are not releasing anything this week. Just so you know."),
    ("2", "test_data", "The sample order we created for staff training shows a wrong invoice total. It is demo data only, real customers are not affected, and the trainer just says 'ignore that one'."),
    ("2", "security_low", "Very low severity, I think: the login page says 'no such user' for unknown emails and 'wrong password' for known ones. I have seen no abuse and this can go into the normal backlog."),
    ("2", "security_scanner_low", "Our security scanner flags a missing X-Frame-Options header on your public marketing pages, which have no login. It is rated 'low' and we accept the risk for now, so no rush."),
    ("2", "billing_label", "The invoice says 'VAT 19%' on one line and 'Sales tax' on another. The amounts are correct; my accountant would just prefer consistent wording. Next release is fine."),
    ("2", "billing_tiny", "We were charged one cent too much on this month's bill because of rounding. I am not worried, I am just letting you know."),
    ("2", "already_resolved_residual", "The sync error from this morning cleared up on its own and all data arrived. The only leftover is that the red error banner stays until I refresh the page. Irritating but harmless."),
    ("2", "mixed_language", "Guten Tag, die Schaltflaeche 'Export' hat einen Tippfehler ('Exprot'). Es funktioniert aber alles. Not urgent."),
    ("2", "mixed_language", "Bonjour, le tri par nom ignore les accents, so 'Emile' ends up at the bottom of the list. I just scroll down to find him."),
    ("2", "very_short", "Typo on pricing page: 'recieve'."),
    ("2", "very_short", "Print preview cuts off the last column. Landscape works."),
    ("2", "multi_small", "Three small things: the avatar upload preview is squashed, the help link opens in the same tab, and the date format is US instead of UK. All livable; I change the date by hand each time."),
    ("2", "quoted_alarm", "A colleague called this 'a total disaster', but honestly the only issue is that the phone keyboard covers the send button in landscape mode. Portrait mode works, so I use that."),
    ("2", "padded_workaround", PADS[3] + "the CSV export uses semicolons instead of commas. My spreadsheet copes if I choose the delimiter on import."),
    ("2", "devtools_small", "Our CI job logs are missing timestamps on the first two lines. Builds pass, deploys work, and everything else is normal."),
    ("2", "deadline_weeks_minor", "Page numbers in the PDF report start at 0. We need clean reports for a conference in five weeks. Until then I renumber the pages by hand in two minutes."),
    ("2", "urgent_subject_minor", "Subject: URGENT!!!\n\nOne label on the Team page is dark grey on black in dark mode. I can read it if I select the text. Not sure it matters much."),
    # level 2, plain
    ("2", "easy", "The confirmation email says 'Thank you for you order'. Small typo, orders themselves work fine."),
    ("2", "easy", "The calendar starts the week on Sunday and I would prefer Monday. I just count the columns myself, it is a small irritation."),
    ("2", "easy", "Address autocomplete suggests the wrong postcode first, but I can pick the right one from the list."),
    ("2", "easy", "The report footer shows last year in the copyright line. Only cosmetic."),
    ("2", "easy", "When I resize the window the toolbar icons overlap slightly. Maximising the window fixes it."),
    ("2", "easy", "The guest Wi-Fi portal needs one extra page reload before it shows the terms page. After that it works."),
    ("2", "easy", "The notification sound plays twice for each message. I muted the sound and have no other issue."),
    ("2", "easy", "The ticket list loses my scroll position after I open a ticket. I scroll down again, it is just irritating."),
    ("2", "easy", "The header row of the patient list is not frozen, so I scroll back up to see the column names. Everything else works."),
    ("2", "easy", "The barcode scanner beeps a second late but every scan is recorded correctly. A small annoyance."),

    # ---------------------------------------------------------------- level 3: one person, work continues, can wait a day
    ("3", "one_user_loud", "MY ACCOUNT IS BROKEN!!! I cannot change my notification settings, only mine. Everyone else on my team can. I am still doing my job, so replying tomorrow is fine."),
    ("3", "one_user_calm", "I have not been able to reset my password from the emailed link since this morning. I am still logged in on my desktop and can keep working. Could someone look at it in the next day or so?"),
    ("3", "one_vs_many", "Only my account shows a 'Payment failed' banner, although my card is fine and billing says paid. Nobody else on the team sees it. I keep working. A reply tomorrow is fine."),
    ("3", "deadline_weeks_away", "I cannot open the yearly report template. Our filing is due in three weeks, so there is no rush, but I wanted it on your list."),
    ("3", "deadline_weeks_away", "The VPN client crashes on start on my laptop, so I work from the office network for now. I travel in three weeks and need it working by then."),
    ("3", "billing_single", "I was charged $39 twice this month for my personal subscription. I am in no hurry, but I would like the refund this week."),
    ("3", "billing_small_gap", "Our March invoice shows 12 seats but we have 10, a difference of about $60. We pay by bank transfer in two weeks, so there is no rush."),
    ("3", "security_hypothetical", "I noticed the password reset link stays valid for a few hours after it has been used. I only tested it on my own account and have seen no abuse. Please have a look this week."),
    ("3", "security_scanner_moderate", "Our scanner shows that TLS 1.0 is still enabled on your API host. I do not know whether anyone uses it and we have no sign of abuse. Please review it within the week."),
    ("3", "staging_one_dev", "The staging environment does not deploy for me since this morning. I am the only developer testing right now and the next release is in two weeks."),
    ("3", "test_data_class", "Someone deleted the shared test project in our sandbox, including the demo customers. No real data was involved, but our trainer needs it restored by the end of the week for a class."),
    ("3", "already_resolved_residual", "The outage this morning is over and we are back up, thank you. One thing remains: my personal dashboard has been empty since then, though everyone else's is fine. It can wait until tomorrow."),
    ("3", "mixed_language", "Hallo, seit dem Update kann ich meine gespeicherten Ansichten nicht mehr oeffnen. Meine Kollegen koennen es. I can still work with the default view, tomorrow is OK."),
    ("3", "mixed_language", "Buenos dias, no puedo enviar informes desde el portal, solo me pasa a mi. Mis companeros si pueden. Puedo esperar hasta manana, I am still busy with other work."),
    ("3", "very_short", "My calendar sync stopped, only mine. Tomorrow is fine."),
    ("3", "very_short", "Can't open my inbox on the phone. Laptop works, no rush."),
    ("3", "multi_issue", "Two things: the sidebar icon looks blurry, and I can no longer see my team's holiday calendar. Only I am affected and I need it to plan leave, but not before next week."),
    ("3", "padded_one_user", PADS[0] + "I cannot attach files larger than 5 MB to my tickets since Monday, while others can. I send big files by email in the meantime, so a day's wait is fine."),
    ("3", "quoted_alarm", "My manager said 'this is blocking everything', but what actually happens is that she cannot see the weekly chart on her own account. She uses my screen instead. She is the only one affected and it can wait until tomorrow."),
    ("3", "healthcare_one_user", "One nurse cannot open the medication chart module on her workstation and gets 'profile not found'. Her colleagues are fine and she is using a shared workstation for the shift. Please fix it before tomorrow's shift."),
    ("3", "devtools_one_user", "Installing one package from your registry fails on my machine with a checksum error. Colleagues install it fine and I can use a cached copy. No deadline this week."),
    ("3", "ecommerce_one_customer", "One of our customers cannot see her order history in her account, but her orders are fine and she got the emails. She wrote today and can wait until tomorrow."),
    ("3", "big_words_one_person", "Absolute catastrophe on my end: the calendar invite button does nothing for me. Colleagues can still send invites for me, so I am working normally and can wait a day."),
    # level 3, plain
    ("3", "easy", "Since this morning my account cannot create new projects (error 403). Other team members can. I am working on existing ones, so tomorrow is fine."),
    ("3", "easy", "The mobile app crashes for me whenever I open the scanner screen. I use the web version at my desk. Please look at it in the next day or so."),
    ("3", "easy", "My email signature templates are gone from my profile, while my colleagues' are fine. I will rewrite them, but restoring them by tomorrow would save me time."),
    ("3", "easy", "My timesheet will not submit for this week. The deadline is next Friday, so it can wait until tomorrow or the day after."),
    ("3", "easy", "I do not receive any password-reset emails on my address, although other people do. I am still logged in, so it is not urgent."),
    ("3", "easy", "My saved queries in the analytics tool are all gone from my account. Other users still have theirs. I will manage this week without them."),
    ("3", "easy", "My account was moved to the wrong team after the reorganisation, so I lost access to two project folders. I still have the rest. Please correct it tomorrow."),
    ("3", "easy", "My board shows only half of my assigned issues since yesterday; the rest appear when I search by my name. Only my board is affected."),
    ("3", "easy", "The bill-of-materials import fails for my file (error on row 214). Other imports work. I need the data by next week, so tomorrow is fine."),
    ("3", "easy", "I lost the 'approve' button, but I am not the only approver, so my colleague approves for me. Please fix it within a day or two."),

    # ---------------------------------------------------------------- level 4: person/team blocked or deadline within about a day
    ("4", "calm_deadline", "Not a big deal, but I present the quarterly numbers to the board at 8:30 tomorrow and the revenue chart is empty. Could you look at it today?"),
    ("4", "blocked_team", "Our five-person accounts payable team gets 'permission denied' on the invoice queue since the update. We cannot process the supplier payments that go out this afternoon."),
    ("4", "quoted_deadline", "Our client wrote: 'If the migration files are not in by noon, the contract is void.' The upload to your portal has been failing for me since 9."),
    ("4", "padded_blocked", PADS[2] + "I cannot open the customs declaration form and the container is held at the port until we file by 6pm today."),
    ("4", "staging_blocks_release", "Staging is down and we cannot test the hotfix that has to go to production tonight. Production itself is fine, but two engineers are stuck."),
    ("4", "billing_blocks_work", "Our card was charged twice ($7,800 instead of $3,900) and the corporate limit is now reached, so we cannot pay the supplier invoice that is due tomorrow morning. Please reverse it today."),
    ("4", "one_user_hard_deadline", "Only I am affected, but I must submit a tender document by 9am tomorrow and the editor refuses to save. I have not been able to save for two hours."),
    ("4", "one_user_hard_deadline", "I know it is just me, but my licence key is rejected and I cannot run the compiler for the release build I must hand to the client in five hours."),
    ("4", "multi_issue", "Two problems: the footer link colour is wrong, and I cannot open the shipping manifest form. The truck must be loaded by 4pm today and the manifest is missing."),
    ("4", "already_resolved_but_blocked", "The login issue I raised is fixed, thanks. But the fix broke the approval step, which our team of eight needs in order to release tomorrow's shipment. Everyone on the team is blocked."),
    ("4", "security_lockout", "Your rate limiter locked us out after a script misconfiguration. All three IT admins are blocked from the console and we must onboard 30 new starters at 9am tomorrow."),
    ("4", "mixed_language", "Hallo, wir koennen seit heute Morgen keine Lieferscheine drucken, und der LKW muss bis 16 Uhr beladen sein. Nur unser Lager ist betroffen."),
    ("4", "mixed_language", "Hola, no puedo entrar a la plataforma de nominas y tengo que enviar las nominas de mi equipo antes de las 5pm hoy. It only affects my team of four."),
    ("4", "very_short", "Locked out. Board meeting in one hour."),
    ("4", "very_short", "Cannot submit tax filing, due midnight tonight."),
    ("4", "healthcare_team_blocked", "The theatre scheduling module will not let our team of three add tomorrow's operations to the list, and the list must be published by 4pm today. Other modules work."),
    ("4", "devtools_deadline", "Our release pipeline is stuck on the code-signing step and the app store submission deadline is tomorrow at 10am. Two engineers are blocked; production is not affected."),
    ("4", "ecommerce_team_blocked", "The discount codes for tomorrow's flash sale, which starts at 9am, cannot be created because the form errors on save. Our marketing team of four is blocked."),
    ("4", "deadline_tomorrow", "The report export fails. Our regulator deadline is tomorrow at noon, not the end of the month as I first thought, so I need it working today."),
    ("4", "caps_but_real", "PLEASE HELP ASAP!!! I cannot reset my password and my manager needs the signed forms from me by 5pm today."),
    ("4", "padded_blocked", PADS[3] + "our team of six cannot log into the shared timetable, and the exam schedule has to be published tomorrow morning."),
    ("4", "helpdesk_single_blocked", "My laptop does not boot after the update. I run a client workshop at 9am tomorrow and my slides are on it. I have no other device."),
    # level 4, plain
    ("4", "easy", "The e-signature service rejects our contract PDFs and the signing deadline is tomorrow morning. Two people in legal are stuck."),
    ("4", "easy", "I cannot access the shared drive with the tender documents, and the tender closes tomorrow at noon."),
    ("4", "easy", "Our meeting room has no audio and we have a customer demo in two hours. The whole sales team of four uses this room."),
    ("4", "easy", "The VPN does not connect for anyone in the finance team of six, and they must close the books today."),
    ("4", "easy", "I have been locked out of the payroll tool and payments need my approval by 3pm today."),
    ("4", "easy", "Our label printer server is stuck. The warehouse crew of twelve cannot print shipping labels and the courier collects at 4pm."),
    ("4", "easy", "I cannot upload the exam papers to the portal and they must be available to students at 8am tomorrow."),
    ("4", "easy", "My git token was revoked and I cannot push the fix that has to be deployed before tomorrow's 9am launch."),
    ("4", "easy", "The pharmacy label printer is broken, and a stack of prescriptions has to leave with the courier at 5pm today."),
    ("4", "easy", "I cannot open the grant application file that has to be submitted by noon tomorrow; the app says it is corrupted."),

    # ---------------------------------------------------------------- level 5: outage, data loss, security exposure, many customers stopped
    ("5", "calm_data_leak", "Just a heads-up, no rush: a web search for our company shows a link to a shared folder holding customer contracts with names and addresses. Anyone can open it without logging in."),
    ("5", "casual_outage", "Hi, small thing, the checkout has been giving an error to every shopper for about 20 minutes. We normally take around 50 orders an hour and none are coming in. Thanks!"),
    ("5", "negated_small", "This is not a cosmetic issue. Since the last deploy, every user can read every other user's private messages."),
    ("5", "padded_security", PADS[1] + "our security team says someone is downloading our customer database through your API with a stolen token right now, and it is still going."),
    ("5", "test_vs_real", "We thought the file in the public storage bucket was test data, but it is a full export of real patient records from last week. It is reachable by anyone with the link."),
    ("5", "staging_is_prod", "We just realised the 'staging' database we exposed is actually a live copy of production, with real customer emails and password hashes, reachable from the internet."),
    ("5", "security_real", "Our admin credentials for your platform were posted in a public code repository an hour ago. We have not rotated them yet and they give full access to our customers' data."),
    ("5", "billing_many", "A bug in your billing run charged 12,000 of our customers ten times their monthly fee, about $1.2 million in total. The batch is still running."),
    ("5", "multi_issue", "Two things: there is a typo on the About page, and all our clinics' appointment booking has been down since 8am, so no patient can book. Please prioritise as you see fit."),
    ("5", "resolved_but_new_outage", "The ticket about the login banner colour can be closed, it is resolved. Separately, every card terminal in our stores is now declining all payments, about 300 stores."),
    ("5", "mixed_language", "Hallo, alle unsere Kunden sehen seit zehn Minuten nur eine Fehlerseite, die gesamte Plattform ist nicht erreichbar."),
    ("5", "mixed_language", "Hola, un empleado externo descargo toda nuestra base de clientes con una cuenta que debia estar desactivada, and it is still happening now."),
    ("5", "very_short", "Prod database gone. Backups empty."),
    ("5", "very_short", "All patients can see each other's records."),
    ("5", "healthcare_safety", "Since the update the ward system shows every patient's allergy list as empty. Nurses on all four wards are giving medication with no allergy warnings right now."),
    ("5", "devtools_secret_leak", "The package we published to your public registry contains our production secrets and it has already been downloaded. Please take it down and help us rotate the keys."),
    ("5", "ecommerce_price_bug", "Our storefront shows every item at $0.00 and orders are being placed. About 300 orders came in over the last 10 minutes."),
    ("5", "helpdesk_ransomware", "There is a ransomware note on our file server and files are being encrypted across the company right now. All 250 staff are unable to work."),
    ("5", "calm_data_loss", "Not sure if this is known, but the folder with all our client documents has been empty for all of us since last night's migration. Sixty people use it."),
    ("5", "quoted_dismissal", "My CTO wrote 'no big deal, it will come back'. It has not: the production database was dropped and the last backup we can find is from last month."),
    ("5", "caps_but_real", "HELP!!! ALL OUR CUSTOMERS ARE LOCKED OUT OF THEIR ACCOUNTS. LOGIN RETURNS AN ERROR FOR EVERYONE SINCE 14:05."),
    ("5", "many_vs_one", "It is not only me: 30 of our customers report seeing other companies' names and figures in their dashboards."),
    ("5", "big_words_but_real", "Please forgive the understatement, but a minor hiccup: our patients' lab results are being emailed to the wrong recipients, several hundred so far today."),
    # level 5, plain
    ("5", "easy", "The API has returned 500 for every request for 20 minutes. Our 2,000 users cannot use our app."),
    ("5", "easy", "Logs show someone downloaded our full customer table using a stolen support token. The token is still active."),
    ("5", "easy", "All the data uploaded to your storage service over the last month has vanished. Nothing comes back from the trash."),
    ("5", "easy", "Our website has been unreachable for everyone since the DNS change. The online shop is completely down."),
    ("5", "easy", "Video visits on our telehealth platform drop after 10 seconds for every doctor. About 200 appointments are affected right now."),
    ("5", "easy", "Someone changed the bank details of our supplier payment run through your admin panel and payments are going out to the new account. Please stop it now."),
    ("5", "easy", "The deploy pipeline deleted the live cluster and all customer services are offline."),
    ("5", "easy", "Email delivery is failing for every message across all 900 of our mailboxes. Nothing has been delivered in the last hour."),
    ("5", "easy", "Shoppers are being shown other people's saved credit cards at checkout. We saw it three times in the last ten minutes."),
    ("5", "easy", "Our emergency-call dispatch software shows a blank screen at every station right now."),
]


# ==================================================================================================
# TEMPLATED ITEMS (28 per level). The level is fixed by the family that produced the ticket.
# The facts that decide the level are part of every template sentence.
# ==================================================================================================
def _pick(rng: random.Random, seq):
    return rng.choice(seq)


def _templates(rng: random.Random) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    # ---------------------------------------------------------------- level 1
    l1_questions = [
        ("export a filtered list to a spreadsheet", "the CRM"),
        ("add a second email address to my profile", "the customer portal"),
        ("see who last edited a page", "the wiki"),
        ("connect a barcode scanner", "the stock app"),
        ("turn off the weekly summary email", "the analytics dashboard"),
        ("change the date format on invoices", "the billing tool"),
        ("share a read-only link to a board", "the project tool"),
        ("book a recurring appointment", "the clinic scheduler"),
        ("mute a channel for a month", "the team chat"),
        ("print a pick list in A5", "the warehouse system"),
        ("change the default branch name", "the code hosting service"),
        ("find the audit log", "the HR system"),
        ("set my working hours", "the helpdesk"),
        ("switch the storefront to a second currency", "the shop admin"),
    ]
    l1_tails = ["No hurry.", "Just curious.", "Nothing is broken, I only want to know.", "Whenever you have a minute.",
                "I am only exploring at the moment.", "It is not urgent at all."]
    for task, prod in rng.sample(l1_questions, 14):
        out.append(("1", f"How would I {task} in {prod}? {_pick(rng, l1_tails)}"))
    l1_wishes = [
        ("saved views that sync between my phone and laptop", "the field service app"),
        ("a keyboard shortcut for archiving", "the mail client"),
        ("an option to hide completed tasks by default", "the to-do tool"),
        ("a bulk rename function", "the file manager"),
        ("a weekly digest per team instead of per person", "the reporting module"),
        ("a colour-blind friendly chart palette", "the dashboard"),
        ("a way to pin favourite patients to the top", "the ward overview"),
        ("a compare view for two releases", "the changelog page"),
        ("a gift message field on orders", "the checkout"),
        ("an option to show week numbers", "the shift planner"),
        ("a dry-run mode for imports", "the data loader"),
        ("support for scanning QR codes with the webcam", "the asset register"),
        ("a shortcut to duplicate a pipeline", "the CI tool"),
        ("an option to sort tickets by customer name", "the service desk"),
    ]
    l1_tail2 = ["Feature idea only.", "No problem on our side at the moment.", "Something for the wish list, no deadline.",
                "Everything works well as it is, this would just be a bonus.", "Only a suggestion.", "Please add it to the ideas list."]
    for wish, prod in rng.sample(l1_wishes, 14):
        out.append(("1", f"Would it be possible to get {wish} in {prod}? {_pick(rng, l1_tail2)}"))

    # ---------------------------------------------------------------- level 2
    l2_pairs = [
        ("the tooltip on the invoice screen is cut off on my small monitor", "hovering slowly shows it fully"),
        ("the app shows a stale unread count until I open the inbox", "opening the inbox refreshes it"),
        ("the print layout puts the page number on the wrong side", "I flip the pages manually"),
        ("the search field loses focus after each result", "I click it again"),
        ("the profile photo appears with a white border on the dark theme", "it does not stop me from doing anything"),
        ("exported filenames have spaces replaced by underscores", "I rename them in a batch tool"),
        ("the time zone label on the meeting invite says GMT even though the time itself is right", "everyone reads the time correctly"),
        ("the 'undo' toast disappears after two seconds instead of five", "I use the history page when I miss it"),
        ("the receipt PDF is missing our second address line", "the customer's first line is enough for delivery"),
        ("the label printer prints a faint line at the edge", "the labels still scan fine"),
        ("the sort order on the contacts list ignores middle names", "the search finds everyone anyway"),
        ("the help page link in the footer leads to the German version", "there is a language switch at the top"),
        ("the onboarding checklist keeps reminding me of a step I already finished", "I dismiss it each time"),
        ("the drag handle for reordering columns is very small", "the arrows in the menu do the same thing"),
    ]
    l2_frames = [
        "Minor thing: {g}. It is only an annoyance because {w}.",
        "For the backlog: {g}. Livable, since {w}.",
        "Small bug report: {g}, but {w}, so nothing is blocked.",
        "Not urgent. {G}, and {w}.",
    ]
    for g, w in rng.sample(l2_pairs, 14):
        fr = _pick(rng, l2_frames)
        out.append(("2", fr.format(g=g, G=g[0].upper() + g[1:], w=w)))
    l2_systems = [
        ("the payslip page", "shows the month name in lower case", "The figures are right."),
        ("the mobile checkout", "puts the promo code box below the pay button", "Customers still find it and can pay."),
        ("the dashboard", "flickers for a second on load", "It settles and works after that."),
        ("the intranet search", "returns results in random order for very short words", "Adding a second word fixes it."),
        ("the chat client", "does not show typing indicators in group threads", "Messages arrive normally."),
        ("the shift planner", "prints the weekend in grey", "Everything is still legible."),
        ("the ward list", "shows bed numbers with a leading zero on one floor", "Staff know what it means."),
        ("the admin console", "keeps the sidebar scrolled to the top on each page", "I scroll back down in a second."),
        ("the API docs", "have a broken anchor link in the pagination section", "Scrolling down finds the section."),
        ("the invoice PDF", "uses a slightly different font than the website", "It is fully readable."),
        ("the ticket form", "does not remember the last chosen category", "Picking it again takes a few seconds."),
        ("the file uploader", "shows 'Uploading...' for a moment after it has finished", "The file is always there."),
        ("the build status badge", "is one shade lighter in dark mode", "It is still readable."),
        ("the loyalty page", "shows points with no thousands separator", "The number is correct."),
    ]
    for sysname, glitch, note in rng.sample(l2_systems, 14):
        out.append(("2", f"{sysname[0].upper() + sysname[1:]} {glitch}. {note} Purely a small annoyance, not blocking anyone."))

    # ---------------------------------------------------------------- level 3
    roles = ["I", "One of our accountants", "Our new intern", "My colleague Sam", "A single user in our Leeds office", "Our part-time bookkeeper"]
    when = ["since yesterday afternoon", "since the update on Monday", "since this morning", "since last Thursday", "since the password change"]
    keep = ["Everyone else on the team can, and work continues.", "The rest of the tool works, so work goes on.",
            "It affects only this one person, and other tasks are not held up.", "Nobody else is affected and nothing is stuck."]
    waits = ["A reply tomorrow is fine.", "It can wait a day.", "Anytime in the next day or two is fine.", "No need to drop everything."]
    l3_actions = [
        ("open the shared budget spreadsheet in comments mode", "the finance workspace"),
        ("see the 'Team' tab", "the project tool"),
        ("download last month's statements", "the customer portal"),
        ("sign in with a security key", "the admin console"),
        ("attach a photo to a work order", "the field service app"),
        ("export reports as Excel", "the analytics tool"),
        ("book meeting rooms on the 3rd floor", "the room booking system"),
        ("edit the product descriptions", "the shop admin"),
        ("view lab results older than a year", "the clinical records system"),
        ("merge branches from the web page", "the code hosting site"),
        ("see the leave balance", "the HR portal"),
        ("save drafts of replies", "the helpdesk"),
        ("create new labels", "the warehouse system"),
        ("sync contacts to the phone", "the CRM"),
    ]
    for act, prod in rng.sample(l3_actions, 14):
        out.append(("3", f"{_pick(rng, roles)} cannot {act} in {prod} {_pick(rng, when)}. {_pick(rng, keep)} {_pick(rng, waits)}"))
    l3_billing = [
        ("On my invoice a monthly plan charge came out twice ($29).", "Payment of the rest is not due for two weeks; I would like it corrected this week."),
        ("A refund we were promised ($45) has not arrived.", "It concerns one small account and can wait a day or two."),
        ("One seat was billed without the discount we agreed ($12 per month).", "No deadline is attached; please put it right this week."),
        ("A late fee of $18 was added to an invoice that was paid on time.", "Only my own account is affected and everything else is fine."),
        ("One add-on we cancelled last month was billed again ($15).", "I am in no rush, tomorrow or the day after is fine."),
        ("A currency conversion looks wrong on one invoice line (about $22).", "It is a single account and there is no payment deadline this week."),
        ("Our card was charged the annual price for one user ($120) instead of monthly ($10).", "Not urgent, but I would like the difference back within the week."),
        ("The invoice for my single licence shows the wrong company name.", "I need the corrected copy for the end of the month, so a day's wait is fine."),
        ("I was billed for a seat of a colleague who left in June ($25).", "Just one account, nothing blocked, a reply within a day or two is fine."),
        ("My receipt shows two lines for the same $9 subscription, though the bank shows one charge.", "Just my own account, and it can wait until tomorrow."),
        ("A promotional credit of $30 is missing from my account balance.", "I can still use the service, and a fix this week is fine."),
        ("My invoice was sent to my old email address ($60 for the quarter).", "I have found it via the portal, and the due date is in three weeks."),
        ("The tax ID on my last invoice has a digit wrong.", "I need the corrected copy before our next accounting close in ten days."),
        ("I was charged $15 for a trial I cancelled within the free period.", "One small account, no deadline; this week is fine."),
    ]
    for head, tail in l3_billing:
        out.append(("3", f"{head} {tail}"))

    # ---------------------------------------------------------------- level 4
    teams = ["Our team of {n}", "The {n} of us in accounts", "All {n} people in our support desk", "Our {n} engineers"]
    l4_rows = [
        ("open the tender folder", "the tender closes at noon tomorrow"),
        ("approve purchase orders", "the supplier cut-off is 4pm today"),
        ("generate the payroll file", "salaries must be released tomorrow morning"),
        ("log in to the trading desk reports", "the client review starts at 9am tomorrow"),
        ("print delivery notes", "the trucks leave at 3pm today"),
        ("publish the timetable", "students see it at 8am tomorrow"),
        ("send the quotation PDFs", "the offer expires at 5pm today"),
        ("close the month-end ledger", "the auditors arrive tomorrow at 9"),
        ("create prescriptions in the pharmacy system", "the courier collects at 4pm"),
        ("deploy to production", "the launch is scheduled for 7am tomorrow"),
        ("access the customer contracts", "renewals must be signed by end of day today"),
        ("submit the customs paperwork", "the ship sails tonight"),
        ("upload the campaign assets", "the campaign goes live at 8am tomorrow"),
        ("run the stock count report", "the stocktake is tomorrow morning"),
    ]
    l4_tail = ["Please treat this as a priority today.", "Everything else in the tool works, but this is holding us up.",
               "Other departments are unaffected.", "We need it fixed today.", "This is blocking our work right now."]
    for act, why in rng.sample(l4_rows, 14):
        team = _pick(rng, teams).format(n=rng.choice([3, 4, 5, 6, 7, 9]))
        out.append(("4", f"{team} cannot {act}, and {why}. {_pick(rng, l4_tail)}"))
    l4_solo = [
        ("I am locked out of my mailbox and I have to send the signed offer", "by 11am tomorrow"),
        ("my licence for the design software expired unexpectedly and I must deliver the artwork", "to the printer by 9am tomorrow"),
        ("my laptop will not start after a firmware update and my thesis defence slides are on it", "for the defence tomorrow at 10"),
        ("I cannot access the case file system and I must file a court document", "before 4pm today"),
        ("the shop admin refuses my login and I must change tomorrow's price list", "before the sale starts at 8am"),
        ("my badge is disabled so I cannot enter the lab where the sample run must be started", "by 2pm today"),
        ("my ssh key stopped working and I must ship the security patch", "before tomorrow's 9am freeze"),
        ("the presentation tool will not open my file and I speak at the conference", "at 9am tomorrow"),
        ("the tax portal rejects my certificate and I must file for a client", "before midnight tonight"),
        ("my account is suspended and I need to approve the shipment", "before the truck leaves at 5pm today"),
        ("the video call tool crashes on my machine and I host a customer workshop", "in three hours"),
        ("my calendar is corrupted and I cannot see the interview slots for candidates arriving", "tomorrow morning"),
        ("the accounting app freezes when I post the year-end journal that is due", "to the bank by tomorrow noon"),
        ("I cannot download the certificate of insurance my client needs", "before the site visit tomorrow at 8"),
    ]
    for prob, dl in rng.sample(l4_solo, 14):
        out.append(("4", f"Only I am affected, but {prob} {dl}. {_pick(rng, l4_tail[3:])}"))

    # ---------------------------------------------------------------- level 5
    l5_out = [
        ("The online shop", "returning error pages", "all of our customers", "No orders are coming in."),
        ("The mobile app", "unable to sign anyone in", "every one of our 40,000 users", "Nobody can use it."),
        ("The patient portal", "down", "all patients", "Nobody can book or see results."),
        ("The payment gateway", "declining every card", "all stores", "No sales can be completed."),
        ("The CI and deployment service", "offline", "all customer environments", "Production deployments of every client are frozen and their sites are erroring."),
        ("The ticketing API", "returning 500 errors", "every customer integration", "Our customers' own products are failing because of it."),
        ("The video conferencing service", "dropping every call", "all customers", "Nobody can hold a meeting."),
        ("The warehouse system", "not responding", "all six depots", "No orders can be picked or shipped."),
        ("The identity provider", "rejecting all logins", "all of our 10,000 staff and customers", "Everything behind login is unreachable."),
        ("The booking engine", "timing out", "every airline partner", "No tickets can be sold."),
        ("The email service", "not delivering anything", "all customers", "Nothing has been delivered since the incident began."),
        ("The dispatch system", "frozen", "all ambulance stations", "Crews cannot see their calls."),
    ]
    l5_when = ["for the last {m} minutes", "since {m} minutes ago", "for about {m} minutes now"]
    for sysname, fail, scope, impact in l5_out:
        m = rng.choice([10, 15, 20, 30, 45])
        out.append(("5", f"{sysname} has been {fail} for {scope} {_pick(rng, l5_when).format(m=m)}. {impact} This is a full outage."))
    l5_leak = [
        ("a customer table with names, addresses and phone numbers", "a public link that needs no login"),
        ("all patient discharge letters", "an unprotected storage folder indexed by search engines"),
        ("employees' payslips and bank details", "a shared link that anyone can open"),
        ("full card numbers of shoppers", "a debug page that is open to the internet"),
        ("customers' passwords in plain text", "a log file accessible without authentication"),
        ("the private keys for our production servers", "a public code repository"),
        ("support chats containing ID card scans", "an open API endpoint"),
        ("our whole client database", "a stolen admin token that is still active"),
        ("private messages between users", "a bug that shows one user's inbox to others"),
        ("exam results of 3,000 students", "a public spreadsheet link"),
    ]
    for what, how in l5_leak:
        who = rng.choice(["We just found", "Our security team found", "A customer reported and we confirmed", "We have confirmed"])
        out.append(("5", f"{who} {what} exposed through {how}. It is live right now and we have not been able to close it."))
    l5_loss = [
        ("the whole production database", "a failed migration", "no usable backup exists"),
        ("all customer files stored in the last month", "a storage bug", "the recycle bin is empty too"),
        ("every appointment booked for the next three weeks", "a scheduled clean-up job", "the nightly backup ran after the deletion"),
        ("the whole ledger of last quarter", "a bad script", "restoring from backup has failed twice"),
        ("all uploaded medical images", "a disk failure", "the replica was corrupted as well"),
        ("the complete order history of 200,000 customers", "an accidental drop", "the newest backup is 11 days old"),
    ]
    for what, cause, extra in l5_loss:
        out.append(("5", f"We lost {what} because of {cause}, and {extra}. This affects all of our customers."))

    return out


# ==================================================================================================
def items(rng: random.Random) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    def add(state: str, truth: str, hard: bool, kind: str) -> None:
        key = " ".join(state.lower().split())
        if key in seen:
            return
        seen.add(key)
        out.append(_item(state, truth, hard, kind))

    for lvl, kind, text in HAND:
        if kind == "easy":
            add(_wrap(text, rng), lvl, False, "easy")
        else:
            add(text, lvl, True, kind)
    for lvl, text in _templates(rng):
        add(_wrap(text, rng), lvl, False, "easy_template")
    return out
