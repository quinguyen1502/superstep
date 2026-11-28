# Review

## Metadata

- Project: superstep
- Review ID: REV-0363
- Task ID: TASK-0374
- Reviewer: Codex
- Created: 2026-11-28
- Updated: 2026-11-28
- Outcome: approved for QA

## Scope

Reviewed the Dataset binding contract, generated Python and TypeScript evaluators, standalone row and snapshot storage, Connected aggregate revision checks, and runtime and export coverage. The Formula preview setting remains the rollout boundary for configuration in Studio.

## References

- [Delivery plan](PLAN-0020-dataset-formulas-and-relations.md)
- [Requirement](REQ-0102-dataset-formulas-and-relations.md)
- [Architecture](ARCH-0004-dataset-formulas-and-relations.md)
- [Task and acceptance criteria](../tasks/done/TASK-0374-dataset-formula-runtime-export.md)

## Findings

### Blocking

- No blocking findings.

### Non-Blocking

- Upgraded standalone projects initialize a nullable diagnostic column when the operator reruns setup. This extends the existing setup contract for standalone migrations and is documented in the generated README and export guide.
- The TypeScript exporter compiles expression syntax with the server's bounded compiler. The runtime checks definitions against the exported program and interprets typed operations. Python embeds the existing evaluator.
- Write-only responses and receipts exclude Formula diagnostics. Read responses include errors only for projected fields.

## Validation Review

- The generated-project matrix verifies Formula writes, receipts, aggregate and Agent projections, schema mismatch, snapshot recomputation, and compatibility with both database engines.
- Python and TypeScript use the same conformance inputs. The test suite exercises high safe integers and Unicode in standalone rows. See [QA-0363](QA-0363-TASK-0374-dataset-formula-runtime-export.md).

## Review Decision

Approved for QA. Owner approval and CI gate merge.
