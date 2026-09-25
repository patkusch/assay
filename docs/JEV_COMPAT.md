# How assay lines up with Jev

assay copies the shape of Jev's request so a request written for one can be tried on the other. It does not copy the model, and it does not claim to match Jev's accuracy.

## What matches

| | Jev | assay |
|---|---|---|
| Endpoint | `POST /v1/systemone` | `POST /v1/systemone` |
| Input | `state` (text, JSON or a list) and a `questions` map | the same |
| Question types | choice, score, noul (yes/no) | the same three |
| Questions | answered independently, in parallel | answered independently, one after another |
| Output | `answers` with the value, `probabilities` and `confidence` for each question | the same, plus the fields below |

## What assay adds to each answer

- `stability`: how often the top pick survived the options being shown in a different order. 1.0 means order made no difference.
- `prediction_set`: every option that cannot be ruled out once the answer is calibrated.
- `abstain`: true when more than one option is left. A calibrated system saying "not sure" is the clearest win in our measurements.
- `calibrated`: whether a fitted calibrator was applied to this answer.

## What differs, on purpose or by limit

| | Jev | assay |
|---|---|---|
| Weights and hosting | closed, hosted, waitlist | open code, runs on your machine through a local model |
| How answers are produced | a non-chat model trained for decisions (details not published) | reads a small chat model's odds for each option in one step; no text is generated |
| Options per choice question | up to 255 | up to 36 with the Ollama backend |
| Context | 64K tokens | whatever the local model allows |
| Speed | 70 to 500 ms claimed | about 200 ms with one ordering and 600 ms with three, for gemma3 4B on an Apple M5 |
| How it is graded | against the answers of two other models, on tests its own team wrote | against answers written by construction, with blind audit and raw receipts |

## Not the same model

Numbers from one system say nothing about the other. If you switch, re-measure on your own data: the calibration you fitted for one will not carry over to the other.
