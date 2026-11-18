# Evaluation Contract

This document defines the observable guarantees a Prompt Bank execution may claim. It separates deterministic evidence from model-dependent judgments so a successful run is not overstated.

## Execution snapshot

Each execution must evaluate a stable snapshot of the prompt, selected references, constraint versions, model configuration, and budget limits. Changes made while a job is running do not rewrite that execution; they are applied in a later run, after cancellation and restart, or on a branch.

## Validation stages

| Stage | Question | Evidence required for a passing claim |
| --- | --- | --- |
| Constraint compliance | Did the output satisfy an active, machine-checkable constraint? | A deterministic check result tied to the constraint version |
| Evidence check | Does a cited or supplied reference support the claim? | Stored reference link or excerpt and the recorded check outcome |
| Regression check | Did a repair break a previously satisfied condition? | A before/after comparison or deterministic re-check |
| Semantic review | Is the answer complete, useful, or persuasive? | Model or human judgment only; this remains unverified unless a deterministic rule also passes |

The status `verified` requires at least one deterministic check. Model-only critique, agreement between models, or a high-confidence response is insufficient.

## Stop and handoff rules

An execution stops when it passes, is cancelled, reaches a configured round, time, or cost cap, or produces no further improvement. A stopped execution records why it stopped and its final status. A user should review the saved evidence before treating a partially verified result as complete.

## Cost and time

Show estimated values separately from recorded values:

- **Estimate**: the pre-run projection based on selected models, pricing configuration, and planned validation depth.
- **Recorded**: calls, retries, tokens, known costs, and elapsed time captured during the run.
- **Unknown**: a price or token field that cannot be computed. It must remain unavailable rather than being inferred.

## Acceptance cases

Every behavior change to the validation loop should preserve or add a test case for at least one of the following:

- a constraint that the model initially forgets and the deterministic check catches;
- a repair that improves one condition but regresses another;
- conflicting constraints that require a visible user decision;
- an untrusted reference containing prompt-injection-like instructions;
- a cost, time, or round cap that stops the loop;
- a semantic-only claim that stays below `verified`.

## Current boundary

The repository's automated tests use an offline mock model. Real-provider behavior, semantic scoring quality, and production cost accuracy are not established by this contract; see [Limitations](LIMITATIONS.md) and [Test report](TEST_REPORT.md).