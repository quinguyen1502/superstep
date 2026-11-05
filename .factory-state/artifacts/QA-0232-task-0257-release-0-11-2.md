# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0232
- Task ID: TASK-0257
- QA Owner: Codex
- Created/Updated: 2026-11-05
- Outcome: source handoff passes local checks; exact-head CI/publication gates remain

## Scope And Acceptance Coverage

- Factory ready passed with approved todo before source edits.
- Shared versions: backend/Python SDK/CLI/frontend/installer 0.11.2; React package/pin/lock 0.1.2; TS SDK remains 0.2.0. Node assertion audit passes. Only the intended three lock entries change; no dependency selection changed.
- Runtime/workflow/migration/UI/SDK TS trees are byte-identical to approved TASK-0256 e1caf171 (`git diff --exit-code`); its full 8/8 finish rerun and reviewed-head CI apply to unchanged behaviour. A release-source full Factory rerun is additionally running; its outcome and exact-head remote checks gate merges, not merely this report.
- Current release metadata: root npm build/lint/test pass; unit counts 157 frontend + 21 React + 102 TS SDK. Python SDK/CLI/release-installer suite: 229 passed / 8 skipped in 10.04s.
- React npm pack dry-run passes at 0.1.2 (102 files, 94.2 kB); Python build from sdist produces superstep-0.11.2 wheel/tarball in /private/tmp/superstep-0257-python-dist. Wheel version confirmed 0.11.2. Logs are /private/tmp/superstep-0257-{build,lint,units,python-sdk,react-pack,python-build}.log; no evidence binaries committed.
- Changelog/sample release scope agrees with the approved implementation and preserves native/device/display-snapshot caveats. No migration or new package.
- Factory structure/ID/diff checks pass with inherited install-receipt/no-todo warnings; recheck immediately before publication. Source task done denotes validated handoff under explicit owner release approval, not external delivery.

## External Publication Checklist

1. Merge #305 only with final e1caf171 checks green. Release branch must have one release-only commit relative to integrated develop; rebase if new changes require it (an identical-tree integration merge needs no source rewrite).
2. Require release-source and develop→main PR CI, then integrate main. Bind new immutable v0.11.2 and sdk-react-v0.1.2 tags to that checked main SHA.
3. Verify configured PyPI superstep 0.11.2, npm @superstep/react 0.1.2 and GHCR superstep, superstep-api, superstep-web, superstep-sandbox 0.11.2 tags/digests/revision labels. Never republish unchanged SDK TS tags.
4. Keep GitHub Release Draft until actual tag workflows and registry checks succeed. Record exact main/tag SHA and workflow/registry receipts on the release. A launched workflow is not proof of publication.

## Residual Risk And Decision

Native OS drag image and physical phone keyboard remain inherited manual follow-ups. The public-deployment-specific diagnosis from 0.11.1 is not newly claimed fixed. Conditionally passed for source handoff under the explicit full release instruction; remote/tag/registry gates above remain mandatory. No hosted production/provider/bot cutover is authorised.
