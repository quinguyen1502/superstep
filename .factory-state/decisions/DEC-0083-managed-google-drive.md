# Decision

- Decision ID: DEC-0083
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0085
- Created/Updated: 2026-11-02
- Related: REQ-0085, DES-0003, PLAN-0005; DEC-0081/0082

Add DriveTools at the managed adapter boundary. Store only folder ID in public settings; encrypt `google_credentials`, accepting service-account or authorised-user JSON. Extract shared Google service-account validation/token exchange from Sheets while preserving its request injection and scope. OAuth refresh uses fixed Google token URL; supplied token URLs, delegation subjects and extra auth endpoints are ignored. Reuse existing PyJWT/cryptography/httpx without dependencies or schema changes.

Every operation verifies the folder and direct-child scope, with Shared Drive corpus derived from the folder metadata. File content endpoints are built from checked IDs, never provider-supplied URLs; shortcuts and recursive access are excluded. Return only bounded metadata/UTF-8 text, with configured auth values/access tokens redacted using a shared helper. Four tools: list_files, get_file, read_text_file, create_text_file. Text limit 64 KiB; list page at most 100. Google Docs export is plain text only.

Create uses a multipart plain-text blob in the fixed folder and appProperties containing SHA-256(operation key) plus content SHA-256. Successful response must match the scoped parent/marker/content hash and Drive's blob MD5 checksum. Initial lookup and retry/manual reconciliation use a bounded read-only query for that marker and verify the actual bounded file bytes against its recorded hash. No/multiple/incomplete/mismatched matches stay unknown and never upload. Marker app privacy depends on the same Google app/account; changing credentials to another app can prevent reconciliation and must not authorise a resend. External file edits/moves are not locked by Studio.

Service accounts have no personal storage quota; refuse create outside Shared Drives. Manually provisioned authorised-user OAuth permits My Drive within its grant. Interactive consent, binary/resumable transfers and mutating existing files are separate concrete future needs. This keeps the initial adapter usable for personal and Workspace accounts without guessing ownership or broadening a grant.
