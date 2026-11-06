# Worked Example: Unicode Label Normalization

## Task

“Use Unicode-aware case folding for labels and tags in the synthetic codebase.” The target's `normalize_label` and `normalize_tag` functions both used `str.lower()`. The bundled tests expect German `ß` to compare as `ss`, so the baseline has two failing assertions.

## Proposed diff

```diff
--- a/src/text_utils.py
+++ b/src/text_utils.py
@@
-    return value.strip().lower()
+    return value.strip().casefold()
@@
-    return value.strip().lower()
+    return value.strip().casefold()
```

`make_slug` is unchanged. The mock provider applies this deterministic one-file proposal to the isolated run snapshot, not to the live target.

## Checks and event history

The snapshot test command is `pytest -q tests`; result: 3 passed, exit code 0. The ordered event stream is `run_started` → `plan_generated` → `file_read` → `change_proposed` → `snapshot_created` → `command_executed` → `self_reviewed` → `run_ready_for_review` → `review_submitted`.

The file-read event contains the source text and SHA-256 snapshot hash. The command event contains its allowlisted command, exit code, captured output, and timeout state. Output is redacted before persistence.

## Reviewer decision

A rejection records the note and decision but leaves the target file byte-identical. An approval verifies that the current file still matches the snapshot hash, atomically applies the proposed text, and records `patch_applied: true`. If the source changed after the run, approval returns a conflict and does not overwrite that newer source.
