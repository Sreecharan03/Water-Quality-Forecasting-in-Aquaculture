# Pond Water Forecast: runbook

For whoever runs or demonstrates the app. Plain steps; nothing here needs machine-learning knowledge.

## 1. Run it on your own computer
```
pip install -r requirements-app.txt
modal volume get aquatic-xai-artifacts models/final_v1 ./bundle     # one-time download of the model bundle (needs the Modal profile)
set AQUATIC_BUNDLE=bundle
uvicorn app.main:app --port 8000
```
Open http://127.0.0.1:8000 . Click **Try an example** then **Get my forecast** to see how it works with made-up numbers.

## 2. Put it on the internet (only with approval)
`modal serve -m modal_jobs.serve` gives a temporary link while the command runs. `modal deploy -m modal_jobs.serve` gives a permanent public link: anyone with the link can use it, so do this only after the supervisor agrees and after the sealed final test (Phase 11). The page stores nothing: readings are processed in memory and are not saved or logged.

## 3. What the page does when something is wrong
| What you see | What it means | What to do |
|---|---|---|
| "We need at least 25 hours of readings" | Too little history to see the daily pattern | Send more readings, ending with the latest |
| "...sensor looks stuck" | The last 2 hours of oxygen (or pH) are exactly the same number | Check the sensor; the app will not forecast that variable |
| "Less than half of the last 24 hours ... are available" | Too many gaps | Check sensor connection |
| "...is far outside what this computer learned from" | The pond is unlike the ones the models were trained on (for example much colder water) | Do not rely on the app for that variable |
| "at the edge of what this computer learned from" | Reading is unusual but still inside the learned range | Use the forecast with extra care |
| A reading shown as "ignored" | Exact zeros, impossible values, non-numbers, or conflicting duplicate times | Fix the source if it happens often |
| "We cannot forecast this" | The app refuses instead of guessing | This is by design |

## 4. Rollback and versions
The model bundle lives at `models/final_v1` on the Modal artifact volume, with a manifest that records the code commit, data and split versions, and a SHA-256 hash of every file. `verify_bundle` checks the hashes. To roll back, point `AQUATIC_BUNDLE` (or `modal_jobs/serve.py`) at the previous bundle folder. Never edit a bundle in place: build a new folder (`final_v2`) and switch.

## 5. Checks before anyone relies on a new bundle
`modal run -m modal_jobs.phase10::verify` must print `all_pass: true`. It checks: file hashes; that the app's numbers equal the research pipeline's for the same moment (train/serve parity); the example forecast; that an out-of-range pond is refused; and that the answer arrives in under one second.

## 6. Monitoring (what to watch)
Per request the service logs only errors and never readings. For a real deployment, add a daily job that compares incoming readings with the training range stored in the manifest (`training_range`), counts refusals by reason, and, once true outcomes arrive, tracks forecast error and range coverage. Alert the operator if refusals exceed 20% of requests or coverage falls outside 85% to 95%. These thresholds are proposals, not yet exercised on live traffic.

## 7. Limits (also shown in the app)
Research demonstration; tested on one farm region in a cool season; the low-oxygen chance is experimental; explanations describe the model, not the pond. It never replaces sensors or alarms.
