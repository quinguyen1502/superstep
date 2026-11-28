# Task

## Metadata

- Project: superstep
- Task ID: TASK-0374
- Title: Match Dataset Formula behavior in runtime and project exports
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-28
- Updated: 2026-11-28
- Requirement IDs: REQ-0102
- Design IDs: DES-0008
- Architecture IDs: ARCH-0004

## Objective

Let Formula-enabled datasets participate in workflow and Agent exports with the same typed results, diagnostics, and write restrictions in Studio, Connected and standalone deployments.

## Dependencies

- Formula database persistence and Studio preview merged in TASK-0365 and TASK-0366. Connected v1 already accepts Formula definitions.
- Use the existing bounded Formula compiler and evaluator contract, grants, projections and transaction boundaries.

## Scope

- Include Formula versions and expressions in deployment bindings. Reject Formula write mappings and incompatible destination definitions.
- Calculate stored Formula results and diagnostics in both standalone writers, including optimistic updates, operation retries, and opt-in snapshot restoration. Preserve current read projections and write-only responses.
- Keep Formula schema configuration under the existing preview flag for this slice. Relation storage, picker and exports are separate work items.

## Acceptance Criteria

- Python and TypeScript exports work with Formula bindings in both connected and standalone mode. Changed formula definitions fail binding validation.
- Dataset nodes and Agent tools can project and query typed computed values with an authorized read grant. Write-only execution returns identifiers and excludes values and diagnostics.
- Standalone writers calculate Formula values in the write transaction, including auto-number dependencies and null/error propagation. Snapshot setup derives values from inputs. Repeated setup and receipt replay preserve stored rows.
- Project schemas and rows created before Formula support can still be used after an additive, idempotent standalone setup upgrade. Document the upgrade and rollback behavior.
- Common conformance cases run against the compiler and generated evaluators. Exercise SQLite and PostgreSQL with connected and standalone writes, reads, snapshot setup, and binding mismatch tests.

## Validation Plan

Run the Formula conformance, Connected API, Dataset workflow/Agent, generated Python and TypeScript, snapshot, and backend layer tests. Check OpenAPI drift, TypeScript compilation in the generated project, Factory hygiene, and run full PR CI.

## Related Artifacts

- [Plan](../../artifacts/PLAN-0020-dataset-formulas-and-relations.md)
- [Requirement](../../artifacts/REQ-0102-dataset-formulas-and-relations.md)
- [Design](../../artifacts/DES-0008-dataset-formulas-and-relations.md)
- [Architecture](../../artifacts/ARCH-0004-dataset-formulas-and-relations.md)
- [Storage decision](../../decisions/DEC-0102-dataset-formula-relation-storage.md)

## Activity Log

- 2026-11-28: The owner requested implementation of the next approved Dataset milestone. Preserve the preview flag until Formula rollout is reviewed.

- 2026-11-28: Enabled Formula bindings in both generated runtimes, added projected diagnostics and standalone setup upgrades, and verified Connected and runtime behavior. Local acceptance passed. See [REV-0363](../../artifacts/REV-0363-TASK-0374-dataset-formula-runtime-export.md) and [QA-0363](../../artifacts/QA-0363-TASK-0374-dataset-formula-runtime-export.md).

- 2026-11-28: The owner approved merging [PR #435](https://github.com/quinguyen1502/superstep/pull/435) into develop. Reviewed head `84d9a65b` passed all 24 CI checks. The PR skipped container publication. Require CI on the final state-only commit before integration.
