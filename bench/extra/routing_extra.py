"""Extra routing items for the assay benchmark (NEW items, same shape as make_tasks.item()).

Every label is set BY CONSTRUCTION from the routing rule in bench/tasks/tasks.json: the label is the ONE
thing the customer asks us to do or fix. No model was asked. Where the rule is ambiguous the item was left out
(for example "how do I export my invoices", "pause my subscription", "does the plan include feature X",
"credit for downtime", "delete my account and my data under GDPR" all stay out).

  billing   = a charge, invoice, refund, tax detail or payment method
  technical = something in the product is broken, or how to use it
  sales     = price, quote, plan change (incl. downgrade), demo or discount
  cancel    = end the subscription or close the account
  other     = press, jobs, feedback, privacy requests, thanks, partnerships, wrong-company mail
"""
from __future__ import annotations

import random


def item(state: str, truth: str, hard: bool, kind: str) -> dict:
    return {"state": state, "truth": truth, "hard": hard, "kind": kind}


PAD_A = ("Apologies for the rambling note. We are in the middle of an audit, the office lift has been out of order "
         "since Tuesday, two of our team are off with flu, and the printer ate the only copy of the seating plan. "
         "Everything is a little chaotic here, so please bear with me. ")
PAD_B = ("I know you must get a lot of these. I have been a customer for a while, mostly from the back of a van "
         "between jobs, so I only get to write at odd hours. My phone screen is cracked, my dog chewed the charger, "
         "and my brother keeps telling me to write things down properly. So here goes. ")
PAD_C = ("Long day. The quarterly numbers came in late, the client changed the brief for the third time, and lunch "
         "was a sad sandwich at my desk. Before I forget, and in between three other calls: ")

# ---------------------------------------------------------------------------------------------------------
# HAND-WRITTEN ITEMS: (label, kind, text). kind == "easy" means hard=False.
# ---------------------------------------------------------------------------------------------------------
HAND: list[tuple[str, str, str]] = [
    # ===================================== BILLING: hard =====================================
    ("billing", "negated_cancel", "Not cancelling! I just need a receipt for the June payment so I can expense it."),
    ("billing", "refund_keep_account", "Please refund the $348 annual charge from yesterday. I renewed by accident, but I am keeping the account, I use it every day."),
    ("billing", "angry_trivial", "THIS IS UNACCEPTABLE. Your invoice PDF has my name as 'Jhon' instead of 'John'. Fix it immediately!!!"),
    ("billing", "calm_serious", "No rush at all, whenever you get a chance. It looks like we have been charged for 45 seats since January, although we only ever had 12 users. That is roughly $4,000 over the year."),
    ("billing", "thanks_with_request", "Thanks so much for the quick help last time, you are stars! One more thing: could you resend the August invoice to accounts@brightpath.example?"),
    ("billing", "forwarded_chain", "---------- Forwarded message ----------\nFrom: Olga (Finance)\nTo: Ben\nSubject: Re: Re: tools budget\n\n> Ben, please get them to take payment differently.\n> We cannot keep using the founder's personal card.\n\nHi, as per the note above: can you change our payment method from card to bank transfer?"),
    ("billing", "very_short", "wrong charge??"),
    ("billing", "very_short", "Need invoice for Q3, asap"),
    ("billing", "mixed_language", "Hola, me cobraron dos veces este mes. Please refund the extra one, gracias."),
    ("billing", "quoted_agent_reply", "Your colleague Sam wrote: \"Your plan renews on the 12th at $59.\" But my bank shows $79 taken on the 12th. Which is right, and can I have the $20 back?"),
    ("billing", "product_name_confusion", "I bought Orbit Pro (the scheduling tool, not your analytics product), but the receipt says 'Orbit Insights'. Can you reissue it with the right product name for my tax records?"),
    ("billing", "padded", PAD_A + "could you tell me which card the 14 September payment was taken from? I have three."),
    ("billing", "mentions_tech_bug", "The export was broken last week and has since started working again, thanks. What I actually need is a corrected invoice showing GST number 44 118 902 for the same period."),
    ("billing", "refund_not_cancel", "I do not want to leave, I just want my money back for the add-on I clicked by mistake ($19)."),
    ("billing", "unknown_charge_angry", "What is this $12 'SMS credits' line?!? I never bought that. Take it off my bill, now."),
    ("billing", "tax_detail", "We are a German company. Please add our USt-IdNr DE123456789 to future invoices. Nothing else needs to change."),
    ("billing", "credit_note", "Please issue a credit note for invoice 4471. We returned the extra licences within the 14 days."),
    ("billing", "payment_failed", "Payment failed: my card was declined on your side, but my bank says it is fine. Can you retry it or take a different card? The card ends 4417."),
    ("billing", "sales_words_billing_ask", "Our account manager quoted $1,200 a year and I signed, but the invoice shows $1,320. Can you correct the invoice?"),
    ("billing", "downgrade_words_refund", "I downgraded to Starter on the 5th and I am staying on it, but I was still billed at the Team rate on the 6th. Please refund the difference."),
    ("billing", "very_long_padded",
     "Hi,\n\nI hope you are well. I wanted to write properly rather than fire off a one-liner.\n"
     "We have been using the platform since 2021 for our physio clinics and on the whole it has been fine. "
     "Our office manager, Deepa, used to handle everything to do with the accounts, but she moved to the Leeds site last month.\n"
     "I have inherited the folder and I am trying to make sense of it. There are lots of PDFs, some with the old logo, some with the new.\n"
     "My own knowledge of the software is limited, I mostly just see the timetable.\n"
     "The one thing I need to get sorted is that our accountants want the tax reference 88-4410772 on every invoice from January onwards, "
     "and the ones currently issued do not show it.\n"
     "Could you add it to the account so future invoices carry it?\n\nKind regards,\nRosalind"),

    # ===================================== BILLING: easy =====================================
    ("billing", "easy", "Could you email me the receipts for the last twelve months? My accountant is asking."),
    ("billing", "easy", "My bank shows a pending $29 from your company that I do not recognise. What is it for?"),
    ("billing", "easy", "Can we switch from paying monthly by card to paying by purchase order? Our finance team prefers it."),
    ("billing", "easy", "We are VAT exempt (certificate attached). Please remove the tax from our next invoice."),
    ("billing", "easy", "please send invoice for order #88213"),
    ("billing", "easy", "I ordered 25 seats by mistake when I needed 5, and paid the same day. Nothing has been used. Could you refund the difference?"),
    ("billing", "easy", "The company name on our invoices is our old one, Halden Systems. It should read Halden Robotics."),
    ("billing", "easy", "Do you accept PayPal, or only cards? I would rather not type my card number in."),
    ("billing", "easy", "There is a $16 charge on my statement dated 2 Sept, but my invoice says $14. Which one is right?"),
    ("billing", "easy", "Invoices go to a colleague who left in June. Can you send them to accounts@tidewater.example instead?"),
    ("billing", "easy", "I'd like the $60 back for the two unused seats, please."),
    ("billing", "easy", "I got a 'payment overdue' email, but I paid by bank transfer on the 4th. Reference LK-2291-B."),
    ("billing", "easy", "Can I be billed in euros instead of dollars? My bank keeps adding a foreign transaction fee."),
    ("billing", "easy", "Please send me a statement of every payment we have made since we signed up."),
    ("billing", "easy", "You charged my card after my free trial ended, but I never entered a card. How did that happen? Please reverse it."),

    # ===================================== TECHNICAL: hard =====================================
    ("technical", "cancel_word_not_cancel", "I am not asking to cancel anything. The 'Cancel' button on the booking form is simply invisible in Safari."),
    ("technical", "invoice_ui_broken", "The 'Download invoice' button on the billing page opens a blank white page. The invoices themselves are fine, I just cannot open that page."),
    ("technical", "angry_trivial", "WORST APP EVER. The avatar upload shows a grey square until I refresh the page. I am furious."),
    ("technical", "calm_serious", "Just a heads-up, no hurry: since yesterday every project board on our team shows up empty. Nothing looks wrong on our side, but nothing loads."),
    ("technical", "thanks_with_request", "Thank you for the great product! Could you tell me how to set up a report that gets emailed to the team every Monday?"),
    ("technical", "forwarded_chain", "Fwd: Fwd: RE: cannot log in\n\n> Priya: it says 'session expired' straight after I sign in\n> Tom: same here since the update\n\nForwarding for the whole team: none of us can stay logged in."),
    ("technical", "very_short", "Login broken."),
    ("technical", "very_short", "cant log in :("),
    ("technical", "mixed_language", "Hallo, die App stürzt ab when I tap 'Neu'. iPhone 14, iOS 18."),
    ("technical", "quoted_agent_reply", "You told me: \"Clear your cache and try again.\" I did that twice and the calendar still shows last month. What else can I try?"),
    ("technical", "product_name_confusion", "I keep finding docs for 'Atlas Sync', but I use 'Atlas Sheets' and there is no 'Import' menu. How do I import a CSV file?"),
    ("technical", "padded", PAD_B + "the barcode screen in the app shows a black rectangle instead of the camera picture."),
    ("technical", "price_word_bug", "The price column in the reports table shows NaN for every row since this morning."),
    ("technical", "refund_word_bug", "The refund report in the dashboard will not generate. It just spins forever."),
    ("technical", "demo_word_bug", "The demo environment shows a 'Trial expired' banner even though the demo account was created today. The banner covers the whole screen."),
    ("technical", "reset_mail_missing", "Reset email never arrives. I have checked spam. The address on the account is jo@harbourvet.example."),
    ("technical", "plan_unchanged_regression", "After Tuesday's update my saved filters have vanished from the Orders view. Nothing about our plan or settings changed."),
    ("technical", "scheduled_job", "Our automation runs on the 1st and I noticed the scheduled job did not fire for the last two months. The cron expression is '0 9 1 * *'."),
    ("technical", "howto_direct", "How do I bulk-edit tags? I have looked under Actions and Settings and cannot find it."),
    ("technical", "seems_billing_but_bug", "The invoice total in the checkout summary shows $0.00 in the mobile app, although the website shows the right amount. The checkout screen is obviously broken."),
    ("technical", "very_long_padded",
     "Hello support,\n\nThis is a bit of a saga, so I will try to be brief and probably fail.\n"
     "We run three restaurants and use your ordering screens on the kitchen tablets. Friday night was a nightmare because the "
     "delivery driver did not turn up, the fryer tripped the fuse, and then the tablets started misbehaving.\n"
     "Chef says the screens 'went weird', and honestly I have no idea what that means because I was in the cellar.\n"
     "What I do know is this: new orders from the website appear on the kitchen tablet only after about ten minutes, "
     "and a few never appear at all until someone taps refresh.\n"
     "Before Friday they showed up instantly.\n"
     "Nothing else was changed, same wifi, same tablets.\n"
     "Can you look into why orders are arriving late?\n\nThanks,\nMarco"),

    # ===================================== TECHNICAL: easy =====================================
    ("technical", "easy", "Notifications do not arrive on my iPad, though they do on my phone."),
    ("technical", "easy", "How do I make a shared link expire after 7 days?"),
    ("technical", "easy", "Drag and drop of cards between columns stopped working in Chrome this morning."),
    ("technical", "easy", "The PDF report has all the charts blank. The data table underneath is fine."),
    ("technical", "easy", "I forgot my password and the reset link is not working. It says 'token invalid'."),
    ("technical", "easy", "How do I add a teammate to one project only and not the whole workspace?"),
    ("technical", "easy", "Zapier says 'authentication failed' for your app since Monday. Nothing changed on our end."),
    ("technical", "easy", "The barcode scanner in the app freezes after the third scan. Android 14, Pixel 7."),
    ("technical", "easy", "How do I restore a document I deleted yesterday?"),
    ("technical", "easy", "Time zones are wrong on our shared calendar: everything appears an hour late since the clocks changed."),
    ("technical", "easy", "Autosave says 'Saved', but when I reopen the file my last hour of work is gone."),
    ("technical", "easy", "I get 'invalid signature' from the API when I call /v2/orders with the new key."),
    ("technical", "easy", "The import wizard stops at 45% for any spreadsheet with more than 5,000 rows."),
    ("technical", "easy", "Where do I switch on two-factor authentication? I cannot find the setting."),
    ("technical", "easy", "Screen sharing shows a black window on my Mac, but audio works fine."),

    # ===================================== SALES: hard =====================================
    ("sales", "negated_cancel", "We are not leaving! We just need to know what it would cost to go from 10 seats to 25 in the middle of the year."),
    ("sales", "downgrade", "We would like to move from Business down to Team at the next cycle. What would we pay, and which features do we lose?"),
    ("sales", "downgrade_not_cancel", "I do not want to cancel, but $99 a month is too much for me now. Is there a cheaper plan?"),
    ("sales", "angry_price", "This is robbery. $15 per user for a to-do list? Do you give any discount to startups with 5 people?"),
    ("sales", "calm_serious", "No urgency, but our board has approved moving 2,000 staff onto the platform next quarter. Could someone send a quote for that many seats?"),
    ("sales", "thanks_with_request", "Thanks for the trial, it has been great. How much would the Pro plan be for a team of 8, billed yearly?"),
    ("sales", "forwarded_chain", "Begin forwarded message:\n> From: CEO\n> Subject: tools\n> Get a price for the full suite for the whole company.\n\nHi, as requested above: could you send us pricing for the full suite for around 120 people?"),
    ("sales", "very_short", "price for 5 users?"),
    ("sales", "very_short", "Demo please"),
    ("sales", "mixed_language", "Bonjour, nous voulons a demo pour 15 personnes la semaine prochaine, merci."),
    ("sales", "quoted_agent_reply", "Your rep wrote: \"I can offer 10% off.\" Would 15% be possible if we sign for two years?"),
    ("sales", "product_name_confusion", "Do you sell Meridian Mail on its own, or only inside the Meridian Suite? I would want a price for the standalone one."),
    ("sales", "padded", PAD_C + "we would like a quote for 35 seats of the Team plan."),
    ("sales", "price_before_buying", "Before I buy: what does annual cost for 30 users compared with monthly? I am comparing you with two other tools."),
    ("sales", "price_complaint", "Your price went up 20% at renewal and I cannot justify that to my boss. Can we negotiate a better rate?"),
    ("sales", "free_plan_limit", "I am on the free plan and have hit the 3-project limit. What is the cheapest way to get more projects?"),
    ("sales", "one_seat_addon", "Can we buy the extra storage add-on for just one team member rather than everyone? What would it cost?"),
    ("sales", "cancel_word_sales", "Our contract auto-terminates if we drop below 10 seats. We are at 12 and want to add 3 more. What would the new monthly price be?"),
    ("sales", "competitor_price", "Another vendor quoted us $8 per seat. Can you match that for 40 seats?"),
    ("sales", "refund_word_sales", "Someone told me you refund unused months when you upgrade. Rather than that, what would upgrading from Team to Business cost me per user?"),
    ("sales", "very_long_padded",
     "Dear sales team,\n\nMy name is Farid and I run IT for a mid-sized architecture practice.\n"
     "We have offices in two cities, about 90 people, and a rather ancient set of tools that nobody loves.\n"
     "Last year we tried three products, one of which ended in tears (mine).\n"
     "A colleague mentioned your platform at a conference and said the reporting module is good.\n"
     "We are not in a rush, our current licences run until March.\n"
     "The partners want a clear picture of the cost before anything else happens, and they are the sort who read every line.\n"
     "Could you send a written quote for 90 seats with the reporting module, and tell me whether you would show it to our partners on a call in January?\n\nBest,\nFarid"),

    # ===================================== SALES: easy =====================================
    ("sales", "easy", "Roughly what would it cost for 8 people on the Pro plan, billed annually?"),
    ("sales", "easy", "Could we book a 30-minute demo for our operations team on Thursday?"),
    ("sales", "easy", "Do you have a cheaper plan for a single freelancer?"),
    ("sales", "easy", "Please send a formal quote (PDF) for 60 seats over three years. Procurement needs it."),
    ("sales", "easy", "Are there student or education discounts? I teach a class of 25."),
    ("sales", "easy", "We would like to try the enterprise features for a fortnight before committing. Can that be arranged?"),
    ("sales", "easy", "I found a coupon code in your newsletter, but it says expired. Can you extend it for me?"),
    ("sales", "easy", "Our charity runs on donations. Any chance of a reduced rate for 6 users?"),
    ("sales", "easy", "We are weighing you against two other tools. Can you send your current price list?"),
    ("sales", "easy", "Can we get a walkthrough of the reporting add-on? We might buy it."),
    ("sales", "easy", "How much is one extra seat per month on the Team plan?"),
    ("sales", "easy", "Our two agencies want to buy together. Is there a bundle price for 100 licences?"),
    ("sales", "easy", "I would like to upgrade to the top tier today. What is the next step and the total?"),
    ("sales", "easy", "We are a school district with 400 teachers. Do you have volume pricing?"),
    ("sales", "easy", "Is there a discount if we pay for two years up front?"),

    # ===================================== CANCEL: hard =====================================
    ("cancel", "no_refund_no_discount", "I do not need a refund, and please do not offer me a discount. Just close the account."),
    ("cancel", "not_a_cheaper_plan", "I am not looking for a cheaper plan. I want to stop paying altogether and be done with it."),
    ("cancel", "angry_trivial", "That is it, I am done! The login page background is hideous and you never listen. Close my account."),
    ("cancel", "calm_serious", "Our team discussed it calmly and we have decided to move to another vendor. Please terminate our enterprise agreement at the end of the term, 31 December."),
    ("cancel", "thanks_with_request", "Thanks for everything over the years, it has been a pleasure. Sadly the business has closed, so I need you to close my account this week."),
    ("cancel", "forwarded_chain", "> From: Director\n> Cut the software subscriptions by Friday, including that one.\n\nBoss says to shut ours down. Please end the subscription on our side."),
    ("cancel", "very_short", "Close my account."),
    ("cancel", "very_short", "Stop renewing pls"),
    ("cancel", "mixed_language", "Bonjour, je veux résilier mon abonnement s'il vous plaît. End it from next month."),
    ("cancel", "quoted_agent_reply", "Your email says: \"We are sorry to see you go, reply to confirm.\" Confirming: yes, please go ahead and close it."),
    ("cancel", "product_name_confusion", "I have both Halo Notes and Halo Tasks. I only want to end Halo Tasks; keep Notes exactly as it is."),
    ("cancel", "padded", PAD_A + "I would like to end our subscription at the close of this month."),
    ("cancel", "no_keyword", "I'd like to terminate. Please confirm the last day I will have access."),
    ("cancel", "bug_not_reason_cancel", "The sync bug has been open for three weeks and nobody fixed it. I am out. Please close my workspace."),
    ("cancel", "refund_word_cancel", "No refund needed for this month, keep it. But please make sure I am not charged from next month, I am leaving."),
    ("cancel", "delete_account_plain", "Please delete my account and everything in it. I am done using the service."),
    ("cancel", "declines_offer", "Yes, I saw the 50% offer in your last email. No thanks, I am still leaving. Please end my plan."),
    ("cancel", "trial_end", "The trial is fine, but I will not be continuing after it. Please make sure nothing is charged and close my account when the trial ends."),
    ("cancel", "auto_renew_off", "My plan renews on Sunday. Please turn that off and let it lapse, I will not need it after."),
    ("cancel", "left_company", "I have left the company and I was the only admin. Please close the company's account, nobody will use it again."),
    ("cancel", "very_long_padded",
     "Hello,\n\nThis is the third time I have written, and I would appreciate it if this one got an answer.\n"
     "I first wrote on the 2nd and the second time on the 9th.\n"
     "Each time I got an automatic reply saying somebody would be in touch within two working days.\n"
     "Nobody has been in touch.\n"
     "I am a sole trader, I sell handmade candles, and honestly I never used more than a tenth of what your software does.\n"
     "The plan costs me every month and I have decided it is not for me.\n"
     "Please end the subscription and close the account. That is all I am asking for.\n"
     "I will not need a reply telling me what I could do differently.\n\nRegards,\nWendy"),

    # ===================================== CANCEL: easy =====================================
    ("cancel", "easy", "Please close our workspace at the end of the month. We will not need it after that."),
    ("cancel", "easy", "I'd like to terminate my membership. What is the last day I can use it?"),
    ("cancel", "easy", "Turn off auto-renew, please. I do not want to continue after this term."),
    ("cancel", "easy", "We have moved everything to another tool. Please shut down our account."),
    ("cancel", "easy", "stop my subscription"),
    ("cancel", "easy", "I no longer run the shop, so I do not need the software. Please end the plan."),
    ("cancel", "easy", "Where do I go to end my paid plan? I could not find a button anywhere."),
    ("cancel", "easy", "Please delete our account, the whole company has been wound up."),
    ("cancel", "easy", "I signed up by mistake last week and do not want the service at all. Please close my account."),
    ("cancel", "easy", "Our contract ends on 30 November. Please do not renew it."),
    ("cancel", "easy", "Ending my subscription today. Thanks for the years of service."),
    ("cancel", "easy", "Can you help me leave? I want to unsubscribe from the yearly plan and have the account removed."),
    ("cancel", "easy", "We are consolidating vendors and yours goes. Kindly terminate the agreement with effect from 1 January."),
    ("cancel", "easy", "My studies are over, so please close my student account."),
    ("cancel", "easy", "I would like to opt out of the subscription entirely. Please confirm once it is done."),

    # ===================================== OTHER: hard =====================================
    ("other", "privacy_access_request", "Under GDPR Article 15 I request a copy of all personal data you hold about me."),
    ("other", "unsubscribe_marketing_keep_account", "Please unsubscribe me from your newsletter only. I am keeping my account and my plan, I just do not want the marketing emails."),
    ("other", "press_deadline_calm", "Hi, I am with TechDaily. We would like a comment on last week's outage for an article going out Thursday. Could someone from communications reply?"),
    ("other", "jobs", "Do you have any openings for a customer success manager in Berlin?"),
    ("other", "partnership", "We are a payments start-up and think an integration partnership could help us both. Who handles partnerships on your side?"),
    ("other", "angry_feedback", "Your new navigation is TERRIBLE. Who thought hiding everything under a hamburger menu was smart? Bring back the sidebar."),
    ("other", "thanks_only", "Thanks a lot for fixing my issue yesterday, everything is working. Have a nice weekend!"),
    ("other", "calm_privacy_serious", "Calmly asking: my address appeared on a breach notification list. Could you tell me which personal data of mine you store, and who your data protection officer is?"),
    ("other", "very_short", "Thanks!"),
    ("other", "very_short", "Great product."),
    ("other", "mixed_language", "Danke für den tollen Support! Really appreciated, macht weiter so."),
    ("other", "forwarded_chain", "Fwd: Fwd: partnership?\n\n> Please pass this to your business development people.\n> We would love to explore a joint webinar series.\n\nForwarding as asked, could you point us to the right person?"),
    ("other", "quoted_agent_reply", "Your agent Lena wrote: \"Feel free to suggest features.\" So here it is: please add keyboard shortcuts for switching between workspaces."),
    ("other", "wrong_company", "Hi, I think I emailed the wrong company. I meant to contact Northwind Logistics about a missing parcel."),
    ("other", "padded", PAD_B + "I would like to apply for the sales engineer role. Where should I send my CV?"),
    ("other", "blog_logo_permission", "I am writing a blog post reviewing productivity apps. May I use your logo, and who do I ask?"),
    ("other", "negated_review", "I do not need help and I am not complaining, I am just leaving a review: the onboarding was the smoothest I have seen in years."),
    ("other", "cancel_word_sponsorship", "Our meetup was cancelled last month, so my earlier sponsorship email no longer applies. Would you like to sponsor our next event in March instead?"),
    ("other", "pricing_journalist", "I am a journalist. Please do not take this as a complaint about your bill. Could I interview your CEO about pricing trends in SaaS?"),
    ("other", "tier_suggestion", "A suggestion: a 'pay what you can' tier would be great for students. I am not asking for a discount now, just passing on the idea."),
    ("other", "dpo_due_diligence", "Which country are your servers in, and who is your data protection officer? Our legal team is doing a routine check."),
    ("other", "angry_trivial", "I am absolutely livid. Your logo changed colour and it looks awful!! Whoever approved that should be fired."),
    ("other", "legal_subpoena", "We have received a court order about one of your users. Please point me to your legal department."),
    ("other", "very_long_padded",
     "Hi there,\n\nThis is not a support request, so feel free to forward it to the right place.\n"
     "I run a small newsletter about workplace tools, roughly 12,000 readers, mostly operations managers.\n"
     "Each month I interview one founder or product lead about how their product came about, and what surprised them.\n"
     "I have used your product for two years and I think readers would enjoy the story.\n"
     "The interview would take about 30 minutes on a video call, and I would send questions in advance.\n"
     "There is no fee and no paid placement, it is purely editorial.\n"
     "Who on your team would be the right person to ask?\n\nBest wishes,\nNadia"),

    # ===================================== OTHER: easy =====================================
    ("other", "easy", "I run a podcast about small-business software and would love to have your founder as a guest."),
    ("other", "easy", "Great release this week! The new timeline view is exactly what our team wanted."),
    ("other", "easy", "Is there a careers page? I cannot find any open roles."),
    ("other", "easy", "Please tell me what personal data you store about me and how long you keep it."),
    ("other", "easy", "I am a student writing about SaaS onboarding. May I use a screenshot of your sign-up flow in my thesis?"),
    ("other", "easy", "Please add a Norwegian translation. Lots of our staff would appreciate it."),
    ("other", "easy", "We manufacture rugged tablets and think there could be a joint offering. Who should we talk to?"),
    ("other", "easy", "I would like to interview one of your engineers for a magazine feature on API design."),
    ("other", "easy", "Who is your EU representative under GDPR? We need it for our records."),
    ("other", "easy", "Just a compliment for your support team: Amara was patient and kind. Please pass it on."),
    ("other", "easy", "Do you offer internships for the summer? I am a second-year computer science student."),
    ("other", "easy", "I found a typo on your terms page: 'recieve' in section 4.2."),
    ("other", "easy", "Would you consider open-sourcing your client library? It would be a great contribution to the community."),
    ("other", "easy", "Could someone send me your media kit and a high-resolution logo? We are publishing a supplier directory."),
    ("other", "easy", "I am the organiser of a developer conference in Lisbon. Would someone from your team like to give a talk?"),
]

# ---------------------------------------------------------------------------------------------------------
# TEMPLATED ITEMS: label fixed by the template (each template asks for exactly one thing).
# ---------------------------------------------------------------------------------------------------------
PRODUCTS = ["ClinicPlan", "Tallyo", "Shelfwise", "Crewboard", "Lexdesk", "Pixelforge", "Ledgerly", "Rentable",
            "Kitchenpass", "Learnloop", "Fleetly", "Menuly", "Farmhand", "Spanwise", "Quotebird", "Stagehand"]
INDUSTRIES = ["dental practice", "law firm", "landscaping company", "online course", "bakery chain", "haulage firm",
              "film studio", "estate agency", "yoga studio", "accounting practice", "vet clinic", "print shop",
              "recruitment agency", "brewery", "charity", "design agency"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
OPEN = ["Hi,", "Hello,", "Good afternoon,", "Hi there,", "", "", "Dear support,", "Morning,"]
CLOSE = ["Thanks", "Best", "Many thanks", "", "Cheers", "Regards", "Thank you"]
SIGN = ["Ana", "Ibrahim", "Colm", "Sofia", "Lars", "Nkechi", "Owen", "Hana", "Tariq", "Elise", "Mateo", "Ruth"]


def wrap(core: str, rng: random.Random) -> str:
    parts = [rng.choice(OPEN), core]
    tail = rng.choice(CLOSE)
    if tail:
        tail += ("\n" + rng.choice(SIGN)) if rng.random() < 0.6 else ""
        parts.append(tail)
    return "\n".join(p for p in parts if p)


def _billing(rng):
    P, I = PRODUCTS, INDUSTRIES
    return [
        lambda: f"{rng.choice(P)}: my statement shows ${rng.choice([39, 79, 129, 249])}.00 on {rng.randint(2, 27)} {rng.choice(MONTHS)}, "
                f"but I expected ${rng.choice([29, 59, 99, 199])}.00. Please explain the difference.",
        lambda: f"Please reissue invoice INV-{rng.randint(1000, 9999)} with our purchase order number PO-{rng.randint(100, 999)} on it. "
                f"We are a {rng.choice(I)} and cannot pay without it.",
        lambda: f"Our {rng.choice(['finance', 'operations', 'admin'])} team now pays by {rng.choice(['company credit card', 'SEPA direct debit', 'purchase order', 'bank transfer'])}. "
                f"Could you change how {rng.choice(P)} is paid for?",
        lambda: f"Please return ${rng.choice([15, 45, 90, 120, 210])} for the duplicate charge on {rng.randint(2, 27)} {rng.choice(MONTHS)}.",
        lambda: f"Can you email a receipt for the {rng.choice(MONTHS)} payment to {rng.choice(SIGN).lower()}@{rng.choice(['northfield', 'kestrel', 'plumtree', 'oakhurst'])}.example?",
        lambda: f"For our {rng.choice(I)}, please add tax number {rng.choice(['GB', 'NL', 'FR', 'IE'])}{rng.randint(10000000, 99999999)} to every future invoice.",
    ], [4, 4, 4, 4, 3, 3]


def _technical(rng):
    P = PRODUCTS
    return [
        lambda: f"{rng.choice(P)} keeps showing '{rng.choice(['Something went wrong', 'Error 500', 'Request timed out', 'Unexpected token'])}' when I "
                f"{rng.choice(['open the calendar', 'save a report', 'upload a photo', 'run a search', 'print a label'])}. It started {rng.choice(['this morning', 'on Monday', 'after the update', 'yesterday afternoon'])}.",
        lambda: f"How do I {rng.choice(['merge two customer records', 'change the default view', 'set up a recurring task', 'share a dashboard read-only', 'move a project to another folder'])} in {rng.choice(P)}?",
        lambda: f"Since {rng.choice(['Tuesday', 'last week', 'the weekend', 'the latest release'])} the {rng.choice(['timeline', 'inbox', 'report builder', 'map view', 'template gallery'])} in {rng.choice(P)} "
                f"{rng.choice(['loads blank', 'freezes for a minute', 'shows old data', 'cuts off the last column'])}.",
        lambda: f"I cannot sign in on {rng.choice(['my work laptop', 'a new phone', 'the office tablet'])}. The {rng.choice(['verification code', 'magic link', 'confirmation email'])} never arrives.",
        lambda: f"Our {rng.choice(['Slack', 'Google Calendar', 'Salesforce', 'QuickBooks', 'Teams'])} integration stopped syncing on {rng.choice(['Monday', 'the 3rd', 'Friday'])}. "
                f"The last item that came across was from {rng.choice(['9am', 'last week', 'two days ago'])}.",
        lambda: f"The app on my {rng.choice(['Galaxy S23', 'iPad Air', 'Pixel 8', 'iPhone 13'])} closes by itself when I {rng.choice(['tap the camera icon', 'open a large project', 'switch to landscape', 'start a sync'])}.",
    ], [4, 4, 4, 4, 3, 3]


def _sales(rng):
    P, I = PRODUCTS, INDUSTRIES
    return [
        lambda: f"We are a {rng.choice(I)} with {rng.choice([7, 14, 22, 55, 130])} people. Could you quote us for that many seats on the {rng.choice(['Team', 'Business', 'Pro'])} plan?",
        lambda: f"Can someone walk our {rng.choice(['sales', 'finance', 'support', 'operations'])} team through {rng.choice(P)} on a call around {rng.choice(['next Tuesday', 'the 15th', 'early next month'])}? We are shortlisting tools.",
        lambda: f"Is there a discount for {rng.choice(['universities', 'charities', 'annual prepayment', 'early-stage start-ups', 'agencies buying in bulk'])}? We would need {rng.choice([10, 25, 60, 150])} licences.",
        lambda: f"What is the price difference between {rng.choice(['Starter', 'Team'])} and {rng.choice(['Business', 'Enterprise'])} for {rng.choice([12, 30, 45, 80])} users?",
        lambda: f"We want to move from {rng.choice(['Starter', 'Team'])} to {rng.choice(['Business', 'Enterprise'])} from {rng.choice(MONTHS)}. What would we pay after that?",
        lambda: f"Please send pricing for adding the {rng.choice(['analytics', 'automation', 'audit log', 'white-label'])} add-on to our {rng.choice(I)}'s account.",
    ], [4, 4, 4, 4, 3, 3]


def _cancel(rng):
    P = PRODUCTS
    reasons = ["the clinic is closing", "we merged with a company that uses another tool", "there is a budget freeze",
               "I retired last week", "we went back to spreadsheets", "the project has been shelved",
               "the season is over and so is the business", "our contract with the client ended"]
    return [
        lambda: f"Please end our {rng.choice(P)} subscription on {rng.randint(2, 28)} {rng.choice(MONTHS)}. {rng.choice(reasons).capitalize()}.",
        lambda: f"I am leaving {rng.choice(P)}. Turn off the renewal and close my account, {rng.choice(reasons)}.",
        lambda: f"Kindly terminate our contract for {rng.choice(P)} as of {rng.choice(MONTHS)} {rng.randint(1, 28)}.",
        lambda: f"How do I close my {rng.choice(P)} account? {rng.choice(reasons).capitalize()}.",
        lambda: f"{rng.choice(P)} has been fine, but we will not need it after {rng.choice(MONTHS)}. Please stop the plan at that point.",
        lambda: f"Please wind down the {rng.choice(INDUSTRIES)} workspace. We are done at the end of {rng.choice(MONTHS)}.",
    ], [4, 4, 4, 4, 3, 3]


def _other(rng):
    return [
        lambda: f"I am a reporter at {rng.choice(['the Ledger', 'Metro Business', 'Wired Weekly', 'a regional radio station'])} covering {rng.choice(['remote work', 'AI in the office', 'small-business software', 'data security'])}. "
                f"Could someone in communications call me before {rng.choice(['Friday', 'the 20th', 'next Wednesday'])}?",
        lambda: f"Is the {rng.choice(['data engineer', 'account executive', 'technical writer', 'support lead', 'product designer'])} position still open? I would like to apply.",
        lambda: f"Thank you to {rng.choice(SIGN)} in your team for helping me with {rng.choice(['my move to the new office', 'the onboarding', 'a tricky import'])} yesterday. Lovely service!",
        lambda: f"Suggestion: please add {rng.choice(['a dark theme for reports', 'a way to pin favourite projects', 'Japanese language support', 'a weekly digest email', 'colour-blind friendly charts'])}. "
                f"It would make life easier for {rng.choice(['our night shift', 'the whole team', 'my colleagues in Tokyo', 'people like me'])}.",
        lambda: f"Please send me a copy of the personal data you hold about me, under {rng.choice(['GDPR', 'UK GDPR', 'the CCPA', 'the LGPD'])}.",
        lambda: f"We are {rng.choice(['a training provider', 'a consultancy', 'a hardware maker', 'a marketplace'])} and would like to discuss {rng.choice(['a co-branded guide', 'a referral arrangement', 'a joint case study', 'an integration listing'])} with your team.",
        lambda: f"Would someone from your team speak at {rng.choice(['DevDay Oslo', 'the Small Business Summit', 'SaaSCon Lisbon', 'our regional meetup'])} in {rng.choice(MONTHS)}?",
    ], [4, 3, 3, 3, 3, 3, 3]


def _templated(rng, label, maker) -> list[dict]:
    templates, counts = maker(rng)
    out, seen = [], set()
    for tpl, n in zip(templates, counts):
        made = 0
        while made < n:
            text = wrap(tpl(), rng)
            if text in seen:
                continue
            seen.add(text)
            out.append(item(text, label, False, "template"))
            made += 1
    return out


def items(rng: random.Random) -> list[dict]:
    out = [item(text, label, kind != "easy", kind) for label, kind, text in HAND]
    for label, maker in (("billing", _billing), ("technical", _technical), ("sales", _sales),
                         ("cancel", _cancel), ("other", _other)):
        out.extend(_templated(rng, label, maker))
    return out


if __name__ == "__main__":
    import collections
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import make_tasks as mt
    its = items(random.Random(1))
    print("count", len(its))
    print("by label", dict(collections.Counter(i["truth"] for i in its)))
    hard = sum(i["hard"] for i in its)
    print("hard", hard, f"{hard / len(its):.1%}")
    print("hand", len(HAND), "templated", len(its) - len(HAND))
    print("hard by label", dict(collections.Counter(i["truth"] for i in its if i["hard"])))
    texts = [i["state"] for i in its]
    assert len(set(texts)) == len(texts), "duplicate texts"
    old = {mt.wrap(c, random.Random(0)) for cs in mt.ROUTING_CORES.values() for c in cs}
    olds = [c for cs in mt.ROUTING_CORES.values() for c in cs] + [t for _, _, t in mt.ROUTING_HARD]
    assert not any(o in t for o in olds for t in texts), "overlap with existing items"
    assert all(i["truth"] in {"billing", "technical", "sales", "cancel", "other"} for i in its)
    assert items(random.Random(1)) == its, "not deterministic"
    print("kinds", len({i["kind"] for i in its if i["hard"]}))
    print("OK")
