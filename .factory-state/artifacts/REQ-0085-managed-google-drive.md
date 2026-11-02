# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0085
- Status: Implemented — owner accepted implementation and approved merge on 2026-11-02
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-02
- Source: Owner chat: add Google Drive managed adapter

## Summary And Scope

Add Google Drive to the managed MCP registry, using existing MCP nodes/Agent slots. Initial operations: list/search direct child files, inspect metadata, read bounded UTF-8 text or export a Google Doc as text, and create a bounded plain-text file in one configured folder.

Support encrypted Google service-account JSON and pre-provisioned OAuth authorised-user refresh-token JSON. OAuth supports personal My Drive; service accounts can read explicitly shared folders and create only inside Shared Drives. No interactive OAuth consent UI, delegated-user impersonation, recursive traversal, binary/large-file transfer, delete/move/share/update operations, deployment or live account setup.

## Business Rules

- The connection fixes a non-root folder ID; runtime file IDs must refer to its non-trashed direct children. Do not follow shortcuts or arbitrary download URLs. Shared Drive metadata is checked and its ID determines query corpus.
- Service accounts cannot own files; create refuses a My Drive destination before any upload. OAuth uses only Google's fixed token endpoint and granted permissions; it does not request a broader consent grant.
- Reuse encrypted secrets, MCP owner/org policy, pinned HTTP transport, offline dry runs and durable operation handling. No secret values in metadata/errors/results.
- Creation stores a stable hashed operation marker and content checksum as app-private file properties. Lost responses/crashes may reconcile through a read-only marker lookup, never a second upload. Missing/duplicate/incomplete results remain unknown. Confirm only a scoped matching blob file with its checksum.
- Bound list pages and text/body sizes. Provider errors are sanitised. File text is untrusted data, not instructions or executable content.

## Acceptance Criteria

- Configure/discover/use all four operations from current MCP/Agent interfaces; no new canvas node, migration or dependency.
- Correct fixed-endpoint OAuth refresh/service-account signing, Shared Drive parameters, direct-folder access checks, escaped search and bounded text/Google Docs export verified with fake HTTP.
- Confirmed creation replay does not upload again; accepted/lost response and crash reconcile read-only; unresolved/duplicate/mismatched results never falsely confirm. My Drive service-account create is refused.
- Wrong owner/org policy, malformed credentials/IDs, unsupported content, oversized responses and token/provider failure are safe; mock runs do no network work.
- Sheets authentication remains compatible after shared helper extraction. UI labels/help/docs are en/vi, screenshots both themes/locales; full Factory/layer/envelope/frontend/handbook/review/QA checks pass.

## Assumptions And References

Owner requested the adapter, authorising implementation/tests; real credentials/consent remain operator setup. Use the existing service-account mechanism and additionally accept manually provisioned refresh credentials; never ask for secrets in chat.

- DES-0003, DEC-0083, PLAN-0005, TASK-0237; existing REQ-0083/0084 and DEC-0081/0082.
- https://developers.google.com/workspace/drive/api/guides/about-shareddrives
- https://developers.google.com/workspace/drive/api/guides/enable-shareddrives
- https://developers.google.com/workspace/drive/api/guides/manage-uploads
- https://developers.google.com/workspace/drive/api/guides/properties
- https://developers.google.com/identity/protocols/oauth2/web-server

## Delivery Approval

Owner explicitly approved the implementation and merging the delivery PRs into develop on 2026-11-02. Related tasks: TASK-0237. Review/QA results are recorded in those tasks. Final rebased one-commit PR checks must pass before the merge. Evidence screenshots are intentionally removed at the owner's request; handbook illustrations and textual verification records remain.
