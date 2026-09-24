# Benchmark tasks: how the labels were made, and what they cannot tell you

There are four tasks with 60 items each (240 in total). Each line of a `.jsonl` file is
`{"id", "state", "truth", "split", "hard", "kind"}`. `tasks.json` holds the question asked for each task.

| Task | Question type | Answers | Hard items |
|---|---|---|---|
| `phishing` | yes/no (`noul`) | yes = phishing, no = legitimate | 18 of 60 |
| `command_safety` | choice | safe, risky, destructive | 18 of 60 |
| `routing` | choice | billing, technical, sales, cancel, other | 20 of 60 |
| `urgency` | score 1 to 5 | 1 (a wish) to 5 (outage or leak) | 20 of 60 |

## Exactly how the labels were made

**No label comes from a model.** Every label is set by construction: it was fixed by the person who built the item, using a written rule
(below). `make_tasks.py` in the folder above is the whole recipe: run it and you get the same files back
(fixed random seed). Two kinds of item exist:

1. **Easy items (about 70%).** Either hand-written one-liners, one per label pattern, wrapped in a random
   greeting and sign-off; or templates (for phishing emails and shell commands) whose answer is decided by the
   template that produced them. A "phishing" template always asks for a password, payment or personal data
   through a look-alike address; a "legitimate" template never asks for anything of the kind.
2. **Hard items (about 30%).** Written by hand, one at a time, to be the cases a lazy keyword rule gets wrong:
   negations ("I am not cancelling"), quoted text (a phishing example inside a training email, a manager's
   alarming quote), near-misses (`git push --dry-run --force`, `curl ... -o file` without running it),
   mixed signals (an angry tone about a trivial problem, a calm tone about a data leak), and padding (an
   irrelevant paragraph in front of the one sentence that matters). Each hard item carries a `kind` name that
   says what the trap is.

### The rules that define each label

- **phishing:** yes if the email tries to get a credential, payment, personal data or a risky action out of
  the reader by deception. No if it is a normal message that asks for nothing of the kind, including messages
  that talk about phishing, or that say "urgent" for a real reason.
- **command_safety:** *destructive* = permanently deletes or overwrites data that cannot be regenerated or
  restored from version control, or wipes a disk, database, volume or system directory. *risky* = runs code
  nobody has read, rewrites shared history, changes permissions broadly, installs system-wide software, or
  deletes something that can be regenerated or recovered. *safe* = read-only, a dry run, or writes only a new
  harmless file in the project. Where the surrounding facts matter (a clean tree, a production volume), they are
  written into the item.
- **routing:** the label is the one thing the customer asks us to do or fix. *billing* = a charge, invoice,
  refund, tax detail or payment method. *technical* = something in the product is broken, or how to use it.
  *sales* = a price, quote, plan change, demo or discount. *cancel* = end the subscription or close the account.
  *other* = press, jobs, feedback, privacy requests, thanks.
- **urgency:** decided by facts in the ticket, never by tone. 1 = question or wish; 2 = small annoyance with an
  easy workaround; 3 = one person affected, work continues, can wait a day; 4 = a person or team is blocked or
  has a deadline within about a day; 5 = outage, data loss, security exposure, or many customers stopped now.

### Dev and test split

Each task is split 30 / 30 into `dev` and `test`, stratified so both halves have the same mix of labels and of
easy and hard items. The id says which half an item is in (`routing-dev-07`, `routing-test-07`) and so does the
`split` field. Calibration is fitted on `dev` only. Every headline number is reported on `test` only.

## Limits: read these before trusting any number

- **Synthetic.** These are not real emails, commands or tickets. Real traffic is messier, longer and
  differently distributed.
- **Small.** 30 test items per task (120 overall). A gap of a few percentage points in accuracy or calibration
  error can be noise. Nothing here has confidence intervals.
- **Author-labelled.** One person wrote the rules and the items. Someone else might draw the borderline cases
  (is `rm -rf ./build` risky or safe? is a 3 really a 3?) differently. I tried to avoid ambiguous items, but some
  disagreement is unavoidable, and a rule that is written down is still one person's judgement.
- **Templates repeat.** The easy items reuse a small number of phrasings. A model that has learned those wins
  easily; the hard items exist to check for that but are few.
- **Not a neutral set.** The author also built the engine that is being tested. The labels never touch a model,
  but the choice of hard cases was made by someone who wanted them to be informative. Treat this as a first
  honest check, not a final verdict.
