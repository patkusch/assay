"""Extra phishing items for the assay benchmark. Every label is set by construction, from the written
phishing rule in bench/tasks/README.md: yes = the email tries to get a credential, payment, personal data
or a risky action out of the reader by deception; no = a normal message that asks for nothing of the kind
(including mail that talks about phishing, or that says "urgent" for a real reason).

No model is asked for any answer. Hand-written items come first, then a set of templates whose label is
fixed by the template that produced them. All domains are fictional (example.com, *.example) or made-up
look-alikes on the reserved .example / .test / .invalid names.
"""
from __future__ import annotations

import random
import re

PAD1 = ("Quick note before the real point: the quarterly planning cycle is starting, the printers on level 3 are being "
        "replaced, the canteen menu changes on Monday, and the parking rota has been updated again. Please read the "
        "intranet post when you have time. ")
PAD2 = ("Thanks for a great October, everyone. The team lunch was well attended, the new starters have settled in, "
        "the office plants survived the heating being off, and the lift is finally fixed. ")


def item(state: str, truth: str, hard: bool, kind: str) -> dict:
    return {"state": state, "truth": truth, "hard": hard, "kind": kind}


# ---------------------------------------------------------------------------------------------------------
# HARD, phishing (truth yes). (kind, text)
# ---------------------------------------------------------------------------------------------------------
HARD_YES = [
    ("bec_bank_change_no_link",
     "From: accounts@brightwell-supplies.example\nSubject: Update to our remittance details\n\nHello Anna,\n\nFollowing our bank's merger, "
     "please pay all outstanding and future invoices to the new account below. Sort code 20-45-11, account 60918273. "
     "The old account will be closed at the end of the month. Please confirm once your finance team has updated its records.\n\nKind regards,\nMartin"),
    ("bec_payroll_diversion",
     "From: j.okafor@fernhill-group.example\nSubject: Direct deposit change\n\nHi HR,\n\nI have changed banks. Could you please send my next salary "
     "to the new account: sort code 30-90-22, account 41187265? I am travelling so please just reply here rather than calling. Thanks, Joy"),
    ("mfa_fatigue_notice",
     "From: it-desk@northgate-corp.test\nSubject: Authenticator test tonight\n\nHi all,\n\nIT is testing the new sign-in system this evening. You will get "
     "several approval prompts on your phone. This is expected: please tap Approve on the next one so the test can finish. No need to reply."),
    ("mfa_code_readback",
     "From: security@kestrel-cloud-help.example\nSubject: Confirming it's you\n\nWe sent a six-digit code to your phone a moment ago. To finish "
     "unlocking your workspace, reply to this email with that code. It only takes a second."),
    ("qr_parking_fine",
     "From: enforcement@city-parking-notice.example\nSubject: Unpaid parking charge\n\nA charge of $18.00 is outstanding for your vehicle. "
     "Scan the QR code in the attached image to pay by card. Charges rise after 14 days."),
    ("qr_redelivery",
     "From: noreply@marlow-couriers-help.example\nSubject: Redelivery slot\n\nWe missed you today. Scan the QR code below with your phone to choose "
     "a new slot and confirm your address and card for the small handling fee.\n\n[QR code image]"),
    ("callback_subscription_charge",
     "From: billing@securedefend-pro.example\nSubject: Your 2-year plan has renewed\n\nThank you for renewing SecureDefend Pro. $389.99 has been "
     "charged to your card. If you did not authorise this, call our refunds desk on 1-555-0173 and have your card and bank login ready."),
    ("callback_virus_warning",
     "From: alerts@pc-safe-alerts.example\nSubject: 3 viruses found on your computer\n\nOur scan detected serious threats on your device. "
     "Do not switch it off. Call a certified technician on 1-555-0188 and they will remove the threats remotely once you give them access."),
    ("polite_survey_card",
     "From: rewards@customer-voice-panel.example\nSubject: Thank you for your feedback\n\nHello,\n\nThanks for taking our short survey. As a token of "
     "appreciation we would like to send you a free hamper. There is nothing to pay; we only need your card number and expiry so we can confirm "
     "your delivery address. Warm wishes, The Panel Team"),
    ("polite_hr_login",
     "From: people-team@fernhill-benefits.example\nSubject: Annual benefits review\n\nHi there, hope you are well. No rush, but whenever you have a "
     "moment could you sign in with your work email and password at https://fernhill-benefits.example/review to confirm your selections? Many thanks."),
    ("ceo_wire_no_link",
     "From: d.whitfield@ashgrove-holdings-mail.example\nSubject: Confidential\n\nI need you to handle a confidential acquisition payment today. "
     "Please wire $48,500 to the account I will send next. Do not discuss this with anyone until it is announced. Reply as soon as you get this."),
    ("solicitor_completion_wire",
     "From: conveyancing@harlow-law-llp.example\nSubject: Completion funds - new account details\n\nDear Mr Patel,\n\nDue to a change in our "
     "client account, please transfer the completion balance of £24,300 to the account below, not the one on our earlier letter. "
     "Sort code 40-17-09, account 73025518. Please confirm by return."),
    ("lookalike_remote_tool",
     "From: it-support@acrne-corp.example\nSubject: Security patch\n\nDear user, your device needs a patch. Please download and run the attached "
     "RemoteHelp installer and give our technician the session ID it shows so we can finish the update."),
    ("macro_invoice",
     "From: ar@tradelink-invoices.example\nSubject: Statement of account\n\nHello,\n\nYour statement is attached (Statement_0921.xlsm). If the content "
     "looks blank, click Enable Editing and then Enable Content to display the figures."),
    ("calendar_invite_signin",
     "Subject: Invitation: Q4 compensation review @ Fri 14:00\nFrom: hr-calendar@fernhill-people.example\n\nYou have been invited to a meeting. "
     "Notes are secured. To open the agenda and notes, sign in with your company username and password at https://fernhill-people.example/notes."),
    ("calendar_invite_qr",
     "Subject: Invitation: All-hands, Thursday 09:30\nFrom: events@northgate-corp.test\n\nJoin the all-hands. Scan the QR code on the invite "
     "and enter your network password to receive your personal joining link."),
    ("forwarded_chain_login",
     "From: l.nguyen@brightwell-supplies.example\nSubject: Fwd: Fwd: signed agreement\n\nHi, forwarding this as promised.\n\n---------- Forwarded message ---------\n"
     "From: legal@brightwell-docs.example\nSubject: Agreement ready\n\nThe agreement is ready. Log in using your Microsoft account details at "
     "http://brightwell-docs.example/sign to view and sign."),
    ("german_konto_gesperrt",
     "Von: sicherheit@halden-bank-kunden.example\nBetreff: Ihr Konto wurde eingeschränkt\n\nSehr geehrter Kunde, wir haben ungewöhnliche Aktivitäten "
     "festgestellt. Bitte bestätigen Sie Ihr Passwort und Ihre TAN unter https://halden-bank-kunden.example/login, sonst wird Ihr Konto dauerhaft gesperrt."),
    ("spanish_banco",
     "De: seguridad@banco-pinar-clientes.example\nAsunto: Actividad sospechosa\n\nEstimado cliente, hemos bloqueado su tarjeta. Para reactivarla, "
     "introduzca el número completo de su tarjeta y el código de seguridad en https://banco-pinar-clientes.example/reactivar."),
    ("french_frais_douane",
     "De : suivi@colis-express-livraison.example\nObjet : Colis en attente\n\nBonjour, votre colis est bloqué en douane. Réglez 2,99 € de frais par carte "
     "bancaire sur https://colis-express-livraison.example/payer pour le faire livrer."),
    ("portuguese_pix",
     "De: atendimento@banco-vale-seguro.example\nAssunto: Confirmação de chave Pix\n\nOlá, para evitar o bloqueio da sua chave Pix, envie sua senha e o "
     "código que você recebeu por SMS respondendo a este e-mail."),
    ("italian_rimborso",
     "Da: rimborsi@agenzia-fisco-rimborsi.example\nOggetto: Rimborso disponibile\n\nGentile contribuente, risulta un rimborso di 312,40 euro. "
     "Per riceverlo inserisca i dati della carta e il codice fiscale su https://agenzia-fisco-rimborsi.example/rimborso."),
    ("dutch_bankhelpdesk",
     "Van: helpdesk@bank-noordzee-veilig.example\nOnderwerp: Uw pas verloopt\n\nBeste klant, uw bankpas is bijna verlopen. Geef uw pincode door aan de "
     "medewerker die u belt, dan sturen wij een nieuwe pas toe."),
    ("mixed_language_english_spanish",
     "From: soporte@tienda-sol-pagos.example\nSubject: Su pedido / Your order\n\nHello! Su pedido no se pudo cobrar. Please re-enter your card number, "
     "fecha de caducidad y CVV en https://tienda-sol-pagos.example/pago para completar la compra."),
    ("we_never_ask_but_ask",
     "From: fraud@larkspur-savings-alerts.example\nSubject: Security notice\n\nWe will never ask you for your password by email. To confirm you are "
     "the account holder, please enter your online banking password on the secure page: https://larkspur-savings-alerts.example/confirm."),
    ("fake_phishing_training",
     "From: awareness@northgate-training.example\nSubject: Mandatory security training\n\nAll staff must complete the annual phishing training. "
     "Log in with your network password at https://northgate-training.example/course to begin. Completion is tracked by your manager."),
    ("fake_security_alert",
     "From: security@kestrel-cloud-alerts.example\nSubject: We blocked a phishing attempt\n\nWe stopped a phishing attempt on your account. To finish "
     "securing it, please verify your current password and recovery phone number at https://kestrel-cloud-alerts.example/secure."),
    ("padded_yes_card_cvv",
     "From: club@lakeside-fitness-news.example\nSubject: October newsletter\n\n" + PAD2 + "This month's classes include yoga, spin and boxing, and "
     "our sauna is back. One small thing: your membership card needs re-activating, so please reply with your full card number and the three-digit CVV "
     "on the back. Otherwise the pool stays open as usual."),
    ("padded_yes_ssn",
     "From: payroll-admin@fernhill-hr.example\nSubject: Team update\n\n" + PAD1 + "One admin task for new joiners: to finish your tax set-up, reply to "
     "this message with your national insurance number and date of birth. The cafeteria will also be closed on Friday afternoon."),
    ("fake_invoice_new_bank",
     "From: billing@ironwood-freight.example\nSubject: Invoice INV-30417\n\nPlease find invoice INV-30417 for £4,180.00. Note: our banking details "
     "have changed, so use the account in the footer of the attached PDF instead of the one on file. Payment within 14 days please."),
    ("wallet_seed_validate",
     "From: support@cryptoferry-wallet.example\nSubject: Wallet validation\n\nAs part of a network upgrade every wallet must be validated. Open the app's "
     "Restore screen and enter your 12-word recovery phrase at https://cryptoferry-wallet.example/validate."),
    ("recruiter_passport_bank",
     "From: recruitment.desk.corvid@webmail-jobs.example\nSubject: Offer of employment\n\nCongratulations, we are pleased to offer you the role. To start "
     "onboarding, please send a scan of your passport, your bank account number and sort code, and your home address by reply."),
    ("html_href_mismatch",
     "From: no-reply@kestrel-cloud-notify.example\nSubject: Document shared with you\n\n<p>Jo shared a document with you.</p>\n"
     "<a href=\"http://kestrel-cloud-login.example/auth?u=1\">https://docs.kestrelcloud.example/d/Q3-plan</a>\n<p>Sign in with your email and password to view.</p>"),
    ("html_button_mismatch",
     "From: docs@fernhill-share.example\nSubject: Q3 salary review.pdf\n\n<table><tr><td><b>Review document</b></td></tr></table>\n"
     "<a href=\"http://fernhill-share.example/r/x9\" style=\"background:#0a5\">Open in SharePoint</a>\n<small>You will be asked to enter your work password.</small>"),
    ("sms_bank_decline",
     "SMS from HALDEN-BK: A payment of £900.00 to TRVL-PLUS was declined. If this was not you, confirm your card details at hldn-bank.example/c now."),
    ("voicemail_html_attachment",
     "From: voicemail@northgate-voice.example\nSubject: New voicemail (0:23)\n\nYou have a new voicemail. Open the attached VM_0923.html and sign in with "
     "your email account to listen."),
    ("polite_tax_refund",
     "From: refunds@revenue-service-portal.example\nSubject: Your refund is ready\n\nDear taxpayer, we hope this finds you well. Our records show you are due "
     "a refund of $612.30. Whenever convenient, please supply your card number and date of birth at https://revenue-service-portal.example/claim."),
    ("scholarship_processing_fee",
     "From: awards@global-scholar-fund.example\nSubject: Scholarship award notification\n\nCongratulations, you have been awarded a $5,000 scholarship. "
     "To release the funds please pay a $65 processing fee by card and send your bank details and ID number."),
    ("domain_renewal_scam",
     "From: renewals@domain-registry-notice.example\nSubject: Domain expiry notice for tamsin-studio.example\n\nYour domain will expire soon. Pay the $189.00 "
     "renewal to us at https://domain-registry-notice.example/renew to keep it. This is not from your current registrar."),
    ("shared_file_no_urgency",
     "From: noreply@fernhill-filedrop.example\nSubject: 'Q3 salaries.xlsx' shared with you\n\nHi, a colleague shared a file with you. To open it, "
     "sign in with your email and password."),
    ("lookalike_password_expiry",
     "From: it-helpdesk@northgate-corp-it.example\nSubject: Password maintenance\n\nHello, just a friendly note that your password is due for its "
     "regular maintenance. Please keep your current password by confirming it at https://northgate-corp-it.example/keep. Thank you!"),
    ("reply_yes_sms_code",
     "From: verify@kestrel-cloud-secure.example\nSubject: Quick confirmation\n\nWe will text you a code. Please reply to this email with it, so that we know "
     "the phone number is really yours."),
    ("recovery_callback",
     "From: accounts@kestrel-cloud-recovery.example\nSubject: Recovery email change requested\n\nSomeone asked to change your recovery email. If this was not you, "
     "call 1-555-0155 straight away and read the caller the verification code we send you."),
    ("bank_statement_lookalike_link",
     "From: statements@pinecrest-cu-online.example\nSubject: Your statement is ready\n\nYour October statement is available. View it here: "
     "https://pinecrest-cu-online.example/login (enter your online banking ID and password)."),
    ("supplier_registration_portal",
     "From: procurement@northgate-suppliers.example\nSubject: Supplier onboarding\n\nTo be added to our approved vendor list, please complete the registration "
     "form at https://northgate-suppliers.example/register including bank account, tax ID and a director's ID scan."),
    ("utility_overpay_refund",
     "From: billing@brightpath-energy-refunds.example\nSubject: You overpaid £48.20\n\nGood news: our records show a credit on your account. To receive "
     "your refund enter your card details at https://brightpath-energy-refunds.example/credit."),
    ("oauth_consent_mail",
     "From: apps@kestrel-cloud-apps.example\nSubject: MailSync Pro wants access\n\nTo keep your inbox in sync, click the link and grant 'MailSync Pro' full access "
     "to read, send and delete all your mail and contacts: https://kestrel-cloud-apps.example/oauth/grant"),
    ("helpdesk_ticket_reopen",
     "From: servicedesk@northgate-tickets.example\nSubject: Ticket #48213 resolved\n\nYour ticket is resolved. If you are still having trouble, reopen it by "
     "signing in with your domain password at https://northgate-tickets.example/reopen."),
    ("bec_vendor_gift_card_short",
     "From: r.holland@ashgrove-holdings-mail.example\nSubject: Quick favour\n\nAre you free? Need 4 store gift cards of $150 for a client thank-you. "
     "Buy them and photograph the codes for me. I'll repay you today."),
    ("fake_boss_number_change",
     "From: m.castellano@fernhill-group-hq.example\nSubject: New number\n\nThis is my new personal number, please save it. Before my flight I need you to "
     "pay a supplier invoice of €9,750 urgently; text me and I will send the IBAN."),
    ("fake_delivery_polite_address",
     "From: deliveries@marlow-parcel-help.example\nSubject: A small question about your parcel\n\nHello, we have your parcel but the address looks incomplete. "
     "Would you mind confirming your full name, address, date of birth and card number for the handling fee at your convenience?"),
    ("fake_password_manager",
     "From: support@vaultkey-password-help.example\nSubject: Your vault is being upgraded\n\nBefore the upgrade completes we must confirm your master password. "
     "Enter it at https://vaultkey-password-help.example/upgrade and we will migrate your vault."),
    ("fake_it_survey_credentials",
     "From: itfeedback@northgate-corp-surveys.example\nSubject: 2-minute IT satisfaction survey\n\nTell us how IT is doing. To make sure only staff take part, "
     "the survey asks you to log in with your normal username and password."),
    ("thanks_lure_invoice_html",
     "From: sales@tradelink-office.example\nSubject: Thanks for your order\n\nThank you for your order. Your invoice is attached as Invoice.htm. "
     "Open it and enter your email password to download the PDF copy."),
    ("charity_donation_bank",
     "From: appeals@childrens-hope-fund-relief.example\nSubject: Emergency appeal\n\nPlease help families affected by the floods. Send your donation by replying "
     "with your card number and CVV, and one of our volunteers will process it for you."),
    ("license_key_login",
     "From: licensing@northgate-software-keys.example\nSubject: Your license has been suspended\n\nWe could not verify your license. Please verify your "
     "administrator username and password at https://northgate-software-keys.example/verify to avoid disruption."),
]

# ---------------------------------------------------------------------------------------------------------
# HARD, legitimate (truth no). (kind, text)
# ---------------------------------------------------------------------------------------------------------
HARD_NO = [
    ("training_quote_bec",
     "From: security@fernhill-group.example\nSubject: Awareness bulletin: fake CEO emails\n\nA typical scam looks like this: \"I'm in a meeting, buy 5 gift cards "
     "and send me the codes.\" Our CEO will never ask for that. If you see something like it, do not reply; report it with the Report button."),
    ("training_quote_password",
     "From: awareness@northgate-corp.test\nSubject: Spot the phish (part 2)\n\nExample from last month, shared with permission: \"Your mailbox is full, "
     "reply with your password to increase the quota.\" Red flags: a generic greeting, a request for your password, and a look-alike sender. "
     "Nobody at Northgate will ever ask for your password. Forward suspicious mail to phish@northgate-corp.test."),
    ("phishing_sim_results",
     "From: secops@fernhill-group.example\nSubject: Phishing simulation results\n\nIn last week's test, 14% of staff clicked the fake sign-in link and 61% reported it. "
     "No one needs to do anything now. A short refresher video is on the intranet if you want it."),
    ("colleague_forwards_suspicious",
     "From: tom.brady@fernhill-group.example\nSubject: Fwd: is this real?\n\nHi security team, this landed in my inbox and looks off. It says my account is locked and I must "
     "verify my password on a link. I haven't clicked anything. Can you take a look?\n\n> Your account is locked. Verify your password now at http://acc0unt-check.example"),
    ("urgent_ops_outage",
     "From: sre-oncall@fernhill-group.example\nSubject: URGENT: payments API degraded\n\nURGENT: the payments API is returning errors since 09:12. The incident channel is #inc-4471 "
     "and the status page is at https://status.fernhill-group.example. Engineers on call only: join the bridge. Everyone else: no action."),
    ("urgent_cfo_meeting",
     "From: cfo.office@fernhill-group.example\nSubject: Urgent: board call moved to 15:00\n\nThe board call has been moved to 15:00 today because of a flight delay. "
     "Dial-in details are unchanged from the invite. Please make sure your slides are on the shared drive by 14:00."),
    ("urgent_payroll_cutoff",
     "From: payroll@fernhill-group.example\nSubject: Urgent: timesheet cut-off tomorrow\n\nPayroll closes tomorrow at noon. Please submit your timesheet in the "
     "usual system on the intranet by then. Late entries are paid next month."),
    ("password_reset_requested",
     "From: no-reply@kestrelcloud.example\nSubject: Reset your password\n\nWe received a request to reset your password. Use code 305871 in the app within 15 minutes. "
     "If you did not ask for this, you can ignore the email and your password will stay the same."),
    ("mfa_code_delivered",
     "From: no-reply@haldenbank.example\nSubject: Your one-time code\n\nYour code is 774209. It expires in 5 minutes. Never share this code with anyone, "
     "including our staff. We will not call to ask for it."),
    ("bank_safety_notice",
     "From: security@pinecrest-cu.example\nSubject: How we contact you\n\nWe will never email you asking for your PIN, your password or a one-time code, and we "
     "will never ask you to move money to a 'safe account'. If a caller says otherwise, hang up and call the number on the back of your card."),
    ("invoice_details_on_file",
     "From: ar@brightwell-supplies.example\nSubject: Invoice 5528 - November\n\nDear Anna,\n\nInvoice 5528 for November is attached, against PO 8814. Payment terms are 30 days "
     "to the account we have always used. Our bank details are unchanged; if you ever get an email saying otherwise, please call us first."),
    ("invoice_paid_receipt",
     "From: billing@ironwood-freight.example\nSubject: Payment received, thank you\n\nWe have received your payment of £4,180.00 for invoice INV-30417. "
     "A receipt is attached. There is nothing further to do."),
    ("shipping_notice_no_action",
     "From: orders@tamarind-books.example\nSubject: Your order has shipped\n\nGood news! Your order #TB-77102 is on its way and should arrive on Thursday. "
     "You can track it in your account. No action needed."),
    ("shipping_delay_notice",
     "From: support@marlow-couriers.example\nSubject: Delivery update\n\nYour parcel will arrive a day late because of the weather. You do not need to be home; "
     "the driver will leave it in your safe place. There is no fee to pay."),
    ("newsletter_verify_word",
     "From: digest@devweekly.example\nSubject: Verify before you merge (issue 212)\n\nThis week: why you should verify signatures on release artifacts, a guide to "
     "reproducible builds, and how one team cut CI time by half. Read online: https://devweekly.example/212. Unsubscribe at the bottom."),
    ("calendar_invite_real",
     "Subject: Invitation: Design review @ Tue 11:00-11:45\nFrom: priya.nair@fernhill-group.example\n\nDesign review for the onboarding flow. Room: Birch (3rd floor). "
     "Video link: https://meet.fernhill-group.example/design-review. Agenda in the invite description."),
    ("calendar_invite_password_word",
     "Subject: Updated invitation: Password policy workshop @ Wed 14:00\nFrom: it-training@northgate-corp.test\n\nWe have moved the password policy workshop to Wednesday "
     "14:00 in the training room. Bring a laptop; no preparation is needed."),
    ("forwarded_fyi_chain",
     "From: dana.li@fernhill-group.example\nSubject: Fwd: Fwd: supplier meeting notes\n\nFYI, see the thread below. I'll take the follow-up on the pricing question.\n\n"
     "---------- Forwarded message ---------\nFrom: sales@brightwell-supplies.example\nSubject: Meeting notes\n\nThanks for meeting today. Notes are attached; we will send the revised quote by Friday."),
    ("it_policy_change_no_ask",
     "From: it-notices@fernhill-group.example\nSubject: Password policy from 1 December\n\nFrom 1 December, new passwords need at least 14 characters. You do not need to change your "
     "current password now; you will be prompted at the next scheduled expiry when you log in to your laptop."),
    ("password_changed_notice",
     "From: no-reply@kestrelcloud.example\nSubject: Your password was changed\n\nThe password for your account was changed today at 08:41. If this was you, there is nothing to do. "
     "If it was not, open the app and choose Security, or use the recovery steps on our website."),
    ("payment_processed_notice",
     "From: subscriptions@tamarind-books.example\nSubject: Your renewal\n\nYour annual membership renewed today and $39.00 was charged to your saved card. "
     "This is your receipt. You can turn off auto-renewal any time in Settings."),
    ("german_rechnung_legit",
     "Von: buchhaltung@lindenhof-gmbh.example\nBetreff: Rechnung 2024-118\n\nGuten Tag, anbei die Rechnung 2024-118 für die Beratung im Oktober. Die Zahlung erfolgt wie vereinbart "
     "innerhalb von 30 Tagen auf unser bekanntes Konto. Bei Fragen rufen Sie uns bitte an."),
    ("spanish_recibo_legit",
     "De: pedidos@tienda-olivar.example\nAsunto: Confirmación de pedido\n\nHola, hemos recibido su pedido nº 5531 y ya lo estamos preparando. Recibirá un aviso cuando salga del almacén. "
     "No necesita hacer nada más."),
    ("french_reunion_legit",
     "De : nadia.benali@fernhill-group.example\nObjet : Réunion de jeudi\n\nBonjour à tous, la réunion de jeudi est déplacée à 10 h, salle Chêne. "
     "L'ordre du jour est sur l'intranet. À jeudi !"),
    ("portuguese_aviso_legit",
     "De: no-reply@banco-vale.example\nAssunto: Aviso de segurança\n\nOlá. Lembramos que o Banco Vale nunca pede a sua senha nem códigos por e-mail, SMS ou telefone. "
     "Se receber uma mensagem assim, ignore-a e avise-nos pela aplicação."),
    ("italian_riunione_legit",
     "Da: marco.bianchi@fernhill-group.example\nOggetto: Cena di squadra\n\nCiao a tutti, la cena di squadra sarà venerdì alle 20:00 al ristorante vicino all'ufficio. "
     "Fatemi sapere se avete allergie."),
    ("dutch_nieuwsbrief_legit",
     "Van: nieuws@fietsclub-noord.example\nOnderwerp: Ritten van november\n\nBeste leden, dit zijn de ritten van november. Start telkens om 9:00 bij de molen. "
     "U hoeft zich niet aan te melden; kom gewoon langs."),
    ("mixed_language_legit",
     "From: anke.vogel@fernhill-group.example\nSubject: Termin / Appointment\n\nHi Tom, der Termin mit dem Kunden ist am Donnerstag um 10 Uhr, so we can meet in the lobby at 9:45. "
     "Bring die Angebote bitte ausgedruckt."),
    ("negation_not_asking_password",
     "From: kofi.mensah@fernhill-group.example\nSubject: Shared drive access\n\nHi Ines, just to be clear, I am not asking for your password and you should never share it. "
     "If you need access to the finance folder, ask your manager to approve it in the access request tool."),
    ("negation_no_link_no_ask",
     "From: help@tamarind-telecom.example\nSubject: About your bill\n\nThis email does not contain any links and we are not asking for any payment or details. "
     "Your new bill is ready in the app. If you have questions, chat to us there."),
    ("pentest_notice_authorised",
     "From: ciso@fernhill-group.example\nSubject: Planned penetration test, 4-6 November\n\nAn authorised external firm will test our network between 4 and 6 November. You may see "
     "unusual login prompts on the guest Wi-Fi. Staff do not need to do anything, and please do not enter credentials anywhere unexpected. Questions to secops@fernhill-group.example."),
    ("intranet_signin_genuine",
     "From: hr@fernhill-group.example\nSubject: New holiday policy\n\nThe new holiday policy is on the intranet: https://intranet.fernhill-group.example/hr/holidays. "
     "You will need to be on the office network or VPN, as usual. Nothing to send back."),
    ("real_supplier_not_changed",
     "From: finance@northgate-corp.test\nSubject: Warning: fake bank-change emails\n\nSome suppliers have received emails claiming to be from us that ask them to pay a new account. "
     "Our bank details have not changed. Please ignore any such message and tell us."),
    ("bec_awareness_training",
     "From: audit@fernhill-group.example\nSubject: Finance control reminder\n\nTeam, any request to change a supplier's bank details must be confirmed by phone using the number in our "
     "vendor system, never the number in the email. This applies even if the request appears to come from the CEO."),
    ("team_gift_collection",
     "From: ines.costa@fernhill-group.example\nSubject: Leaving gift for Marcus\n\nMarcus leaves on Friday. I am collecting for a gift card; if you would like to chip in, "
     "leave a few pounds in the envelope on my desk or tell me and I will note it down. No pressure at all."),
    ("attendance_verify_sheet",
     "From: events@fernhill-group.example\nSubject: Please verify your attendance\n\nTo help with fire safety, please verify your name on the sign-in sheet at reception when you arrive at Thursday's event. "
     "There is nothing to fill in online."),
    ("kyc_branch_notice",
     "From: notices@larkspur-savings.example\nSubject: Identity checks at our branches\n\nNew rules mean we must verify the identity of some customers. If you are chosen, "
     "we will write to you and you will be asked to bring your ID to a branch. We will never ask you to send documents by email."),
    ("landlord_rent_same",
     "From: lettings@ashgrove-property.example\nSubject: Rent reminder\n\nHi both, rent for December is due on the 1st as usual, to the same account as before. There are no changes to our "
     "details. Merry Christmas!"),
    ("webinar_on_phishing",
     "From: events@northgate-corp.test\nSubject: Invite: How attackers steal passwords (webinar)\n\nJoin our free 30-minute webinar next Wednesday to see how password-stealing "
     "emails work and how to report them. Register with your work email at https://events.northgate-corp.test/phish-webinar."),
    ("product_recall_urgent",
     "From: safety@tamarind-kitchens.example\nSubject: URGENT product safety recall\n\nURGENT: we are recalling the 2-litre kettle (model K200, batch B7) because the lid can loosen. "
     "Stop using it and see our website for a free replacement. You do not need to send us any personal details."),
    ("appointment_reminder",
     "From: reception@elmwood-dental.example\nSubject: Appointment reminder\n\nThis is a reminder of your check-up on Tuesday at 09:20. Reply YES to confirm or call us to move it. "
     "We look forward to seeing you."),
    ("school_notice",
     "From: office@riverside-primary.example\nSubject: Sports day\n\nDear parents, sports day is on Friday afternoon if the weather holds. Children should wear their PE kit and bring a water bottle. "
     "Parents are welcome from 1:30 pm."),
    ("signin_alert_was_you",
     "From: no-reply@kestrelcloud.example\nSubject: New sign-in to your account\n\nWe noticed a sign-in from a new laptop in Leeds today. If this was you, no action is needed. "
     "If not, change your password from the app's Security page. We will never ask for your password in an email."),
    ("padded_no_never_send_password",
     "From: office-manager@fernhill-group.example\nSubject: Office news\n\n" + PAD1 + "One reminder from IT: please do not send passwords by email or chat. Use the password manager and "
     "share vault items instead. Also the bike shed is now locked at night."),
    ("padded_no_invoice_fyi",
     "From: pm@brightwell-supplies.example\nSubject: Project Halifax weekly\n\n" + PAD2 + "Project status is green. The invoice for stage 2 will come from accounts next week to the "
     "usual account; you do not need to action anything now. Next update on Friday."),
    ("password_manager_vendor_news",
     "From: news@vaultkey.example\nSubject: What's new in VaultKey 5.2\n\nVersion 5.2 adds passkey support and a faster import tool. We will never ask for your master password by email or phone, "
     "and we cannot see it. Full release notes: https://vaultkey.example/releases/5.2."),
    ("support_reply_order_number",
     "From: support@tamarind-books.example\nSubject: RE: Missing book\n\nHi Priya, sorry your book has not arrived. Could you send us the order number from your confirmation email? "
     "That is all we need. We will trace it today."),
    ("refund_issued_notice",
     "From: refunds@tamarind-books.example\nSubject: Your refund has been issued\n\nWe have refunded $24.99 to your original payment method. It can take 3-5 working days to show. "
     "You do not need to do anything."),
    ("urgent_it_maintenance",
     "From: it-notices@northgate-corp.test\nSubject: URGENT: mail server maintenance tonight\n\nURGENT: mail will be offline from 22:00 to 23:30 tonight for an emergency patch. "
     "Save drafts before then. You do not need to do anything else."),
    ("urgent_hr_verify_holiday",
     "From: hr@fernhill-group.example\nSubject: Urgent - please verify your leave dates by Friday\n\nPlease open the HR system on the intranet (the usual link in your bookmarks) "
     "and verify the leave dates already recorded for December. Payroll uses them for the rota. This needs doing by Friday."),
    ("github_style_notification",
     "From: notifications@codehost.example\nSubject: [acme/api] Pull request #418 approved\n\nAlicia approved this pull request. All checks have passed. You can merge when ready: "
     "https://codehost.example/acme/api/pull/418"),
    ("unsubscribe_confirm",
     "From: newsletter@devweekly.example\nSubject: You have been unsubscribed\n\nYou will no longer receive our weekly digest. If this was a mistake, you can re-subscribe on our website any time. "
     "We will not ask for your password."),
    ("html_matching_link_no_ask",
     "From: news@tamarind-books.example\nSubject: Autumn reads\n\n<h2>Autumn reads</h2>\n<p>Our staff picks are in.</p>\n<a href=\"https://tamarind-books.example/autumn\">https://tamarind-books.example/autumn</a>\n"
     "<p><small>You can manage email preferences in your account.</small></p>"),
    ("plain_two_line_legit",
     "From: jonas@fernhill-group.example\nSubject: Re: lunch\n\nThursday works. See you at 12:30 by the lifts."),
    ("mfa_bulletin_reminder",
     "From: secops@northgate-corp.test\nSubject: Reminder: MFA prompts you did not start\n\nIf your phone shows a sign-in approval you did not start, tap Deny and tell us. "
     "IT will never ask you to approve a prompt for a 'test'. We are not running any tests this week."),
    ("qr_legit_conference",
     "From: registration@devsummit.example\nSubject: Your ticket for DevSummit\n\nYour ticket is attached as a PDF with a QR code. Show it at the entrance on Thursday. "
     "Nothing else is required; you have already paid. See you there!"),
    ("job_offer_hr_portal_genuine",
     "From: talent@fernhill-group.example\nSubject: Welcome to Fernhill\n\nWe are looking forward to you joining on 3 March. Your manager Dana will meet you at reception at 9:00. "
     "Bring your ID on day one; HR will collect any forms in person. There is nothing to send in advance."),
]

# ---------------------------------------------------------------------------------------------------------
# EASY, hand-written. (text)
# ---------------------------------------------------------------------------------------------------------
EASY_YES = [
    "From: security@halden-bank-verify.example\nSubject: Verify now\n\nYour Halden Bank account is locked. Verify your password at https://halden-bank-verify.example/unlock within 24 hours.",
    "Your parcel is held. Pay £1.45 at http://parcel-release-fee.example to get it delivered.",
    "From: prizes@mega-draw-winners.example\nSubject: WINNER\n\nYou won 250,000 dollars! Send your full name, address and bank details to claim.",
    "Dear customer, your email password expires today. Click http://mail-keep-password.example and type your password to keep it.",
    "From: admin@north-gate-it.example\nSubject: Account disabled\n\nYour account will be disabled. Send us your username and password to keep it active.",
    "URGENT: your tax rebate of $780 is waiting. Enter your card number and SSN at http://rebate-desk.example/claim.",
    "From: ceo@ashgrove-holdings-mail.example\nSubject: Urgent task\n\nBuy 3 gift cards worth $200 each and email me the codes right away. I am in a meeting.",
    "Hi, this is Sam from your bank's fraud team. To stop the fraud, please read me the code we just texted you.",
    "From: no-reply@kestrel-cloud-login.example\nSubject: Sign in required\n\nYour session expired. Sign in again with your email and password: http://kestrel-cloud-login.example",
    "From: winners@sunshine-cruise-promo.example\nSubject: Free cruise!\n\nYou have been chosen for a free cruise. Pay $99 port tax by card at http://sunshine-cruise-promo.example to book.",
    "Your Wi-Fi bill is overdue. Pay now with your card at http://telco-bill-pay.example or lose service tonight.",
    "From: support@vaultkey-support.example\nSubject: Master password check\n\nPlease reply with your master password so we can fix your vault.",
    "Hello, I am a prince and need help moving funds. Send a $500 fee and your bank login and I will pay you 10%.",
    "From: hr@fernhill-benefit-portal.example\nSubject: Bonus payment\n\nYour bonus is ready. Enter your bank account number and login at http://fernhill-benefit-portal.example/bonus.",
    "Attention: your antivirus expired. Download the attached update.exe now to stay protected.",
    "From: legal@court-notice-summons.example\nSubject: Court summons\n\nYou are summoned. Open the attached file to see details, or a warrant will be issued.",
    "From: sweepstakes@lucky-stars-lotto.example\nSubject: Claim\n\nTo release your prize send a copy of your passport and pay the $45 courier fee by card.",
    "From: deliveries@fastship-parcels.example\nSubject: Address failed\n\nWe could not deliver. Confirm your address and card number at http://fastship-parcels.example/redeliver.",
    "From: crypto-alerts@coinbridge-secure.example\nSubject: Withdrawal on hold\n\nTo release your withdrawal, verify your wallet by entering your seed phrase.",
    "From: payroll@ashgrove-hr-desk.example\nSubject: Verify direct deposit\n\nPlease verify your direct deposit by logging in with your employee ID and password at http://ashgrove-hr-desk.example.",
]

EASY_NO = [
    "From: orders@tamarind-books.example\nSubject: Order confirmation\n\nThanks for your order #5521. It will ship tomorrow. No action needed.",
    "From: priya@fernhill-group.example\nSubject: Coffee?\n\nCoffee at 3? The good machine on the second floor is working again.",
    "Reminder: the office closes at 1 pm on Friday for the holiday. Enjoy the long weekend.",
    "From: no-reply@codehost.example\nSubject: Build passed\n\nThe build for main passed in 4m 12s. Nothing to do.",
    "From: dana@fernhill-group.example\nSubject: Slides\n\nHi Tom, the slides for Monday are on the shared drive in the Q4 folder. Shout if anything is missing.",
    "From: newsletter@gardenclub.example\nSubject: Autumn planting\n\nThis month: bulbs to plant now, a talk on composting, and a plant swap on the 12th. Unsubscribe below.",
    "From: billing@tamarind-telecom.example\nSubject: Your bill is ready\n\nYour November bill of £32.00 is ready in the app and will be taken by direct debit on the 15th, as usual.",
    "Thanks for the call, Helen. I'll send the notes by end of day.",
    "From: reception@elmwood-dental.example\nSubject: Appointment\n\nYour appointment is on Tuesday at 09:20. Please arrive 10 minutes early.",
    "From: it-notices@northgate-corp.test\nSubject: Planned downtime\n\nThe wiki will be offline on Saturday from 06:00 to 08:00 for an upgrade. Nothing for you to do.",
    "From: library@city-library.example\nSubject: Hold ready\n\nYour reserved book is ready to collect at the front desk until Friday.",
    "From: events@devsummit.example\nSubject: Schedule published\n\nThe schedule for DevSummit is now live at https://devsummit.example/schedule. See you in March.",
    "From: yusuf@fernhill-group.example\nSubject: Holiday cover\n\nI am off 10 to 14 March. Ines will cover my tickets. Back on the 17th.",
    "From: no-reply@kestrelcloud.example\nSubject: Storage report\n\nYou used 41% of your storage this month. You can see details on your dashboard. No action needed.",
    "From: hr@fernhill-group.example\nSubject: Welcome, Mei\n\nPlease welcome Mei Tanaka, who joins the design team on Monday. Say hello if you see her in the kitchen.",
    "From: ops@northgate-corp.test\nSubject: URGENT: office evacuation drill\n\nURGENT: evacuation drill at 10:30 today. Leave by the nearest stairs and meet at the car park.",
    "From: accounts@ironwood-freight.example\nSubject: Statement\n\nYour monthly statement is attached for your records. No payment is due this month.",
    "From: coach@lakeside-fitness.example\nSubject: Class moved\n\nThursday's spin class moves from 18:00 to 18:30. Bikes are the same. See you there!",
    "From: no-reply@haldenbank.example\nSubject: Your monthly statement\n\nYour statement is ready in the app. We never ask for your password or PIN by email.",
    "From: katrin.weber@lindenhof-gmbh.example\nSubject: Termin\n\nHallo Tom, der Termin am Dienstag um 14 Uhr passt gut. Ich bringe die Unterlagen mit.",
]


# ---------------------------------------------------------------------------------------------------------
# TEMPLATES. The label is fixed by the template that builds the text. Each template makes 5 items, drawing
# from slot pools, and none of them is a copy of another. Phishing templates always try to obtain a credential,
# payment, personal data or a risky action by deception; legitimate templates never do.
# ---------------------------------------------------------------------------------------------------------
BANKS = ["Halden Bank", "Pinecrest Credit Union", "Larkspur Savings", "Ironwood Bank", "Wexley Bank", "Corvid Trust", "Ashgrove Building Society", "Tamsin Bank"]
BANK_SLUG = ["halden", "pinecrest", "larkspur", "ironwood", "wexley", "corvid", "ashgrove", "tamsin"]
TLDS = [".example", ".test", ".invalid"]
FIRST = ["Priya", "Tom", "Alicia", "Marcus", "Dana", "Yusuf", "Ines", "Kofi", "Helen", "Raj", "Mei", "Jonas", "Sofia", "Liam", "Nadia", "Oskar"]
COURIERS = ["Marlow Couriers", "Swiftpath Parcels", "Redwood Express", "Bluefin Delivery", "Kite Logistics", "Northline Freight"]
COURIER_SLUG = ["marlow", "swiftpath", "redwood", "bluefin", "kite", "northline"]
SHOPS = ["Tamarind Books", "Elmwood Outfitters", "Sunfield Garden", "Quill & Ink", "Harbour Coffee", "Birchwood Toys", "Pebble Electronics"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
ROOMS = ["Birch", "Oak", "Cedar", "Aspen", "Willow", "Maple"]


def _key(text: str) -> str:
    """Text with digits and first names blanked, so two items that differ only by a number or a name count as the same."""
    return re.sub(r"\d+", "#", re.sub("|".join(FIRST), "N", text))


def _five(fn) -> list[str]:
    seen: list[str] = []
    keys: set[str] = set()
    guard = 0
    while len(seen) < 5 and guard < 500:
        guard += 1
        s = fn()
        if _key(s) not in keys:
            keys.add(_key(s))
            seen.append(s)
    return seen


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _slug(name: str) -> str:
    return name.lower().replace("&", "").split()[0]


def template_yes(rng: random.Random) -> list[dict]:
    c = rng.choice

    def bank():
        i = rng.randrange(len(BANKS))
        return BANKS[i], BANK_SLUG[i]

    def t1():
        b, s = bank(); d = f"{s}-secure{c(TLDS)}"
        return (f"From: alerts@{d}\nSubject: {c(['Action needed on your account', 'Your access has been limited', 'Security review'])}\n\n"
                f"Dear customer, we have limited your {b} online access after unusual activity. "
                f"{c(['Verify your password', 'Confirm your login details', 'Re-enter your password and card number'])} at https://{d}/{c(['review', 'restore', 'unlock'])} "
                f"within {c([12, 24, 48, 72])} hours or the limit becomes permanent.")

    def t2():
        cr = rng.randrange(len(COURIERS)); d = f"{COURIER_SLUG[cr]}-parcel-fee{c(TLDS)}"
        return (f"From: tracking@{d}\nSubject: Parcel {c(['on hold', 'not delivered', 'awaiting payment'])}\n\n{COURIERS[cr]} could not deliver your parcel "
                f"(ref {rng.randint(100000, 999999)}). Pay the {c(['£1.85', '$2.40', '€2.10', '£3.20'])} redelivery fee by card at https://{d}/pay to reschedule.")

    def t3():
        b, s = bank(); d = f"{s}-refunds{c(TLDS)}"
        return (f"From: refunds@{d}\nSubject: {c(['Refund waiting', 'You are owed money', 'Overpayment credit'])}\n\nOur records show you were overcharged "
                f"{c(['£34.10', '$58.75', '€41.00', '£120.60'])}. To receive it, submit your card number, expiry date and CVV at https://{d}/claim.")

    def t4():
        co = c(['northgate', 'fernhill', 'brightwell', 'ashgrove']); d = f"{co}-mail-admin{c(TLDS)}"
        return (f"From: postmaster@{d}\nSubject: {c(['Mailbox quota exceeded', 'Storage warning', 'Mailbox full'])}\n\nYour mailbox is {rng.randint(93, 99)}% full and new mail "
                f"may bounce. To increase your quota reply with your email address and current password and our system will apply it.")

    def t5():
        d = f"{c(['tradelink', 'ironwood', 'brightwell', 'quillco'])}-accounts{c(TLDS)}"
        return (f"From: ar@{d}\nSubject: {c(['Overdue invoice', 'Remittance copy', 'Final reminder'])} #{rng.randint(1000, 9999)}\n\nDear customer, "
                f"invoice #{rng.randint(20000, 29999)} is unpaid. See the attached {c(['Invoice.xlsm', 'Statement.docm', 'Payment_details.zip'])}; "
                f"{c(['click Enable Content', 'enable macros', 'extract and open the file'])} to view the amount due.")

    def t6():
        co = c(['northgate', 'fernhill', 'brightwell', 'ashgrove']); d = f"{co}-mfa-setup{c(TLDS)}"
        return (f"From: security@{d}\nSubject: {c(['Authenticator migration', 'Re-enrol your MFA', 'New sign-in method'])}\n\nOur authenticator app is being replaced. "
                f"Scan the attached QR code with your phone, then type the six-digit code your old app shows into the reply box to complete the move.")

    def t7():
        n = c(FIRST); amt = c([100, 150, 200, 250]); k = c([3, 4, 5, 6])
        return (f"From: {n.lower()}.{c(['mgr', 'director', 'boss'])}@{c(['ashgrove', 'fernhill', 'northgate'])}-exec-mail{c(TLDS)}\nSubject: {c(['Are you available?', 'Small favour', 'Need your help'])}\n\n"
                f"It's {n}. I'm stuck in a meeting and can't call. Please buy {k} gift cards worth ${amt} each for a client and send me photos of the codes. "
                f"I'll reimburse you {c(['this afternoon', 'tomorrow', 'on Monday'])}.")

    def t8():
        d = f"{c(['fernhill', 'northgate', 'brightwell'])}-payroll-portal{c(TLDS)}"
        return (f"From: payroll@{d}\nSubject: {c(['Pay slip available', 'Salary review', 'Pay adjustment'])}\n\nYour {c(['October', 'November', 'December', 'March', 'April'])} pay adjustment cannot be "
                f"processed until you re-confirm your bank account number and sort code. Do it at https://{d}/pay {c(['today', 'this week', 'before Friday'])}.")

    def t9():
        d = f"{c(['coinferry', 'tidewallet', 'ledgerlark', 'satoshi-nest'])}-support{c(TLDS)}"
        return (f"From: help@{d}\nSubject: {c(['Wallet sync issue', 'Action needed: wallet', 'Airdrop eligibility'])}\n\nYour wallet is out of sync after the last upgrade. "
                f"Enter your {c(['12-word', '24-word'])} recovery phrase at https://{d}/sync to restore your balance.")

    def t10():
        prod = c(['SafeGuard Antivirus', 'CloudBackup Plus', 'PCShield Pro', 'StreamMax'])
        return (f"From: billing@{prod.lower().replace(' ', '')}-orders{c(TLDS)}\nSubject: Receipt for your order\n\nThank you. ${rng.randint(199, 499)}.99 has been debited for {prod}. "
                f"If you did not order this, call 1-555-01{rng.randint(10, 99)} at once, and have your online banking ready so the agent can cancel it.")

    def t11():
        n = c(FIRST); d = f"{c(['docshare', 'fileloop', 'sharedrive'])}-secure{c(TLDS)}"
        return (f"From: {n.lower()}@{d}\nSubject: {n} shared '{c(['Budget 2025', 'Team salaries', 'Contract draft', 'Board pack'])}' with you\n\n"
                f"Open the file: https://{d}/f/{rng.randint(1000, 9999)}\nYou will need to sign in with your work email and password to view it.")

    def t12():
        d = f"{c(['corvid', 'quillco', 'harlow', 'pebble'])}-careers-mail{c(TLDS)}"
        return (f"From: hiring@{d}\nSubject: {c(['Your job offer', 'Onboarding documents', 'Welcome aboard'])}\n\nWe are delighted to confirm your offer. Please email a scan of your "
                f"{c(['passport', 'driving licence', 'national ID'])}, your date of birth and your bank account details today so we can create your payroll record.")

    def t13():
        n = c(FIRST); co = c(['Brightwell Supplies', 'Ironwood Freight', 'Quill & Co', 'Harlow Print'])
        return (f"From: {n.lower()}@{_slug(co)}-billing-team{c(TLDS)}\nSubject: {c(['Bank details update', 'Our new account', 'Please note new account'])}\n\nHi, "
                f"{co} has moved banks. From now on pay invoices to sort code {rng.randint(10, 89)}-{rng.randint(10, 89)}-{rng.randint(10, 89)}, account {rng.randint(10000000, 99999999)}. "
                f"Please {c(['update your records', 'confirm by reply', 'let me know when done'])}.")

    def t14():
        b, s = bank()
        return (f"SMS from {s.upper()}: {c(['Your card is blocked', 'Payment of $' + str(rng.randint(80, 900)) + ' needs approval', 'New device added'])}. "
                f"To fix it, log in at {s}-mobile{c(TLDS)}/{c(['a', 'b', 'x'])}{rng.randint(10, 99)} and enter your PIN.")

    def t15():
        app = c(['MailSync Pro', 'CalPlus', 'DocuFlow', 'InboxZero'])
        d = f"{c(['kestrel', 'tidewell', 'ashgrove'])}-apps{c(TLDS)}"
        return (f"From: apps@{d}\nSubject: {app} needs permission\n\nTo keep {app} working, approve full access to your mailbox, files and contacts at https://{d}/grant. "
                f"{c(['Approve the sign-in prompt on your phone when it appears.', 'Then accept every prompt that follows.'])}")

    out = []
    for f in (t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15):
        out += [item(s, "yes", False, "easy") for s in _five(f)]
    return out


def template_no(rng: random.Random) -> list[dict]:
    c = rng.choice

    def t1():
        shop = c(SHOPS); cr = c(COURIERS)
        return (f"From: orders@{_slug(shop)}.example\nSubject: {c(['Your order has shipped', 'On its way', 'Dispatched'])}\n\nYour order #{rng.randint(10000, 99999)} "
                f"from {shop} left our warehouse today with {cr}. Expected delivery: {c(DAYS)}. Track it in your account. No action needed.")

    def t2():
        n = c(FIRST)
        return (f"From: {n.lower()}@fernhill-group.example\nSubject: {c(['Team sync', 'Weekly catch-up', 'Planning'])}\n\nReminder: our {c(['team sync', 'planning session', 'retro'])} is on "
                f"{c(DAYS)} at {c(['09:30', '11:00', '14:00', '15:30'])} in {c(ROOMS)}. Agenda: https://intranet.fernhill-group.example/agenda/{rng.randint(10, 99)}. Bring your laptop.")

    def t3():
        shop = c(SHOPS)
        return (f"From: receipts@{_slug(shop)}.example\nSubject: Your receipt\n\nThank you for shopping at {shop}. ${rng.randint(5, 180)}.{c(['00', '50', '99'])} was "
                f"charged to the card ending {rng.randint(1000, 9999)}. Returns are accepted within {c([14, 28, 30])} days; details are on our website.")

    def t4():
        svc = c(['Kestrel Cloud', 'Tidewell Mail', 'Pebble Photos', 'Harbour Notes'])
        return (f"From: no-reply@{svc.lower().replace(' ', '')}.example\nSubject: {c(['Your reset code', 'Password reset', 'Security code'])}\n\nYou asked to reset your password for {svc}. "
                f"Your code is {rng.randint(100000, 999999)}. It expires in {c([10, 15, 30])} minutes. If it was not you, ignore this email; your password stays as it is.")

    def t5():
        return (f"From: awareness@{c(['fernhill-group', 'northgate-corp', 'brightwell-supplies'])}.example\nSubject: {c(['Security tip of the week', 'Stay safe online', 'Phishing reminder'])}\n\n"
                f"This week's tip: {c(['hover over links before you click', 'check the sender address carefully', 'be wary of unexpected attachments', 'use a different password for every site'])}. "
                f"Remember that we will never ask you for your password by email. Report anything odd with the Report button.")

    def t6():
        n = c(FIRST); repo = c(['api', 'web', 'mobile', 'billing', 'docs'])
        return (f"From: notifications@codehost.example\nSubject: [acme/{repo}] Issue #{rng.randint(100, 999)} assigned to you\n\n{n} assigned you to '{c(['Fix flaky test', 'Update README', 'Add retry on timeout', 'Bump dependency'])}'. "
                f"View it: https://codehost.example/acme/{repo}/issues/{rng.randint(100, 999)}")

    def t7():
        return (f"From: hr@{c(['fernhill-group', 'northgate-corp', 'ashgrove-holdings'])}.example\nSubject: {c(['Benefits update', 'New parental leave policy', 'Holiday calendar', 'Wellbeing week'])}\n\n"
                f"We have updated the {c(['benefits guide', 'leave policy', 'holiday calendar', 'wellbeing programme'])}. Read it on the intranet; it takes about five minutes. "
                f"You do not need to reply or send anything.")

    def t8():
        n = c(FIRST)
        return (f"Subject: Invitation: {c(['Product review', 'Customer call', 'Hiring sync', 'Roadmap'])} @ {c(DAYS)} {c(['10:00', '13:00', '16:00'])}\nFrom: {n.lower()}@brightwell-supplies.example\n\n"
                f"{n} invited you to a meeting. Join by video: https://meet.brightwell-supplies.example/{rng.randint(1000, 9999)}. Dial-in numbers are in the invite.")

    def t9():
        sys_ = c(['the payments API', 'the login service', 'the reports dashboard', 'the file server', 'the VPN'])
        return (f"From: sre@{c(['fernhill-group', 'northgate-corp'])}.example\nSubject: URGENT: {sys_} is down\n\nURGENT: {sys_} has been down since {c(['08:05', '10:40', '13:15'])}. "
                f"Engineers are working on it and updates are on the status page. You do not need to do anything unless you are on call.")

    def t10():
        util = c(['Brightpath Energy', 'Clearwater Utilities', 'Tamarind Telecom', 'Hillside Broadband'])
        return (f"From: no-reply@{_slug(util)}.example\nSubject: Your bill is ready\n\nYour latest {util} bill of £{rng.randint(20, 140)}.{c(['00', '35', '80'])} is in the app. "
                f"It will be taken by direct debit on the {_ord(c([3, 10, 15, 22, 28]))} as usual. You do not need to do anything.")

    def t11():
        svc = c(['Kestrel Cloud', 'Tidewell Mail', 'Pebble Photos', 'Harbour Notes'])
        return (f"From: security@{svc.lower().replace(' ', '')}.example\nSubject: New sign-in from {c(['Leeds', 'Porto', 'Gdansk', 'Denver', 'Osaka'])}\n\nYour {svc} account was signed in on a new "
                f"{c(['phone', 'laptop', 'tablet'])}. If that was you, ignore this message. If not, open the app and review your devices. We will never ask for your password by email.")

    def t12():
        n = c(FIRST); shop = c(SHOPS)
        return (f"From: support@{_slug(shop)}.example\nSubject: RE: {c(['Wrong size', 'Late delivery', 'Broken item'])}\n\nHi {c(FIRST)}, thanks for getting in touch. I'm sorry about the problem. "
                f"I have arranged a {c(['replacement', 'refund', 'free return label'])} and it will be with you within {rng.randint(3, 7)} working days. Kind regards, {n}, {shop} support")

    def t13():
        co = c(['Brightwell Supplies', 'Ironwood Freight', 'Quill & Co', 'Harlow Print']); inv = rng.randint(1000, 9999)
        return (f"From: accounts@{_slug(co)}.example\nSubject: Invoice {inv}\n\nInvoice {inv} for the {c(['September', 'October', 'November'])} work is attached, "
                f"against PO {rng.randint(5000, 9999)}. Payment terms are {c([14, 30, 45])} days to the account already on file. Bank details are unchanged.")

    def t14():
        n = c(FIRST)
        return (f"From: {n.lower()}@fernhill-group.example\nSubject: {c(['Friday drinks', 'Pizza on Thursday', 'Team quiz', 'Bake sale'])}\n\nWe are doing {c(['drinks', 'pizza', 'a quiz', 'a bake sale'])} on "
                f"{c(DAYS)} after work. Everyone is welcome; tell me if you have dietary needs. It's optional and nothing to bring.")

    def t15():
        cl = c(['Elmwood Dental', 'Riverside Clinic', 'Northside Vets', 'Greenleaf Physio'])
        return (f"From: reception@{_slug(cl)}.example\nSubject: Appointment reminder\n\nThis is a reminder of your appointment on {c(DAYS)} at {c(['09:20', '11:40', '14:10', '16:30'])}. "
                f"Please call us if you need to move it. We look forward to seeing you at {cl}.")

    out = []
    for f in (t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15):
        out += [item(s, "no", False, "easy") for s in _five(f)]
    return out


def items(rng: random.Random) -> list[dict]:
    out: list[dict] = []
    out += [item(s, "yes", True, k) for k, s in HARD_YES]
    out += [item(s, "no", True, k) for k, s in HARD_NO]
    out += [item(s, "yes", False, "easy") for s in EASY_YES]
    out += [item(s, "no", False, "easy") for s in EASY_NO]
    out += template_yes(rng)
    out += template_no(rng)
    return out
