# Review quality planted set

20 diffs against this repo. 10 are bad. 10 are good. `run_review.py` sends each one through `review_prompt()` and the same grok argv the cloud runner uses (`grok -p`, `--cwd`, `--always-approve`, `--output-format plain`). It does not pass `--local`.

A bad diff the reviewer accepts is a false accept. A good diff the reviewer rejects is a false reject. A timeout, a rate limit, or a patch that does not apply is an error. An error is not an accept.

```text
nice -n 19 python3 eval/mvp-1031/review-quality/run_review.py --round before
nice -n 19 python3 eval/mvp-1031/review-quality/run_review.py --round after
```

Scratch for the grok cwd is `tmp/review-quality-cwd/` inside this worktree. Saved model text is redacted before it is written. `tests/test_review_quality_replay.py` replays fixture outputs, and recorded stdout when a round has been saved, through `parse_verdict` and the root-delete override.

Before and after counts are in `REPORT.md`. Baseline false accepts: 3. After the `review_prompt` sentence: 0 false accepts and 0 false rejects.
