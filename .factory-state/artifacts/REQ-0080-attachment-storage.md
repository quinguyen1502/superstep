# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0080
- Status: Accepted (2026-10-31, owner Thái Quí Nguyễn: "Duyệt đề xuất cả 3 backend db, fs, s3, merge #229 và lập task"). Planned into TASK-0191 to TASK-0195.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-31
- Source: owner request on 2026-10-30 ("Nghiên cứu bổ sung thêm external storage, nếu ko db sẽ phình"). Follows REQ-0077 and DEC-0072, which store chat attachment bytes in `chat_attachments.data`.
- Related Decision: DEC-0074 (Accepted)

## Summary

- Chat attachment bytes can live outside the database: in the database (today, the default), on a local folder or volume, or in S3-compatible object storage (AWS S3, Cloudflare R2, Backblaze B2, MinIO).
- The backend is chosen at deploy time with environment variables. The `superstep install` and `deploy` flows ask for it like other optional components.
- A CLI command moves existing files between backends. Backup and restore cover the files wherever they are.

## Problem Or Opportunity

- Each chat file is up to 10 MB (operator ceiling `STUDIO_CHAT_ATTACHMENT_MAX_MB`) and 5 per message. A busy published chat can add gigabytes to the database within the retention window (30 days by default).
- A large database makes backups (`superstep backup`: `pg_dump -Fc` or an SQLite online copy), restores, migrations and managed-Postgres plans slower and more expensive. Postgres stores `bytea` through TOAST, so vacuum and replication also carry the file bytes.
- Dify, Flowise, Langflow and n8n all keep uploads outside the main database by default or as an option (see DEC-0074, "Other platforms").

## Scope

### In Scope

- A storage port (`AttachmentStore`) used only by the attachment service: `put(key, stream, size, mime)`, `open(key)` (a stream), `delete(key)`, `exists(key)`, `iter_keys()`.
- Backends:
  - `db`: today's `chat_attachments.data`. Default. Needs no setup, and is right for the Render free demo, whose disk is ephemeral.
  - `fs`: a folder (`STUDIO_ATTACHMENT_FS_PATH`, default `/data/attachments`), on the same volume as the SQLite database in the all-in-one image, or a named volume shared by `api` and `worker` in the full stack.
  - `s3`: S3-compatible object storage through `boto3`, as an optional extra (`superstep-backend[s3]`) installed in the published images.
- Configuration in the existing `STUDIO_*` style:
  - `STUDIO_ATTACHMENT_STORAGE=db|fs|s3`
  - `STUDIO_ATTACHMENT_FS_PATH`
  - `STUDIO_ATTACHMENT_S3_BUCKET`, `STUDIO_ATTACHMENT_S3_ENDPOINT` (empty for AWS), `STUDIO_ATTACHMENT_S3_REGION` (`auto` for R2), `STUDIO_ATTACHMENT_S3_PREFIX`, `STUDIO_ATTACHMENT_S3_ACCESS_KEY_ID`, `STUDIO_ATTACHMENT_S3_SECRET_ACCESS_KEY` (or the default AWS credential chain when they are empty), `STUDIO_ATTACHMENT_S3_PATH_STYLE` (MinIO).
  - `superstep doctor` and `/api/health` details report the backend and whether a write, read and delete of a probe object work.
- Downloads stay owner-only, served by the backend with `Content-Disposition: attachment`, `nosniff`, `no-store` and the CSP sandbox. The backend streams the object; it does not redirect the browser to the bucket.
- A row keeps its metadata (name, kind, MIME, size, extracted text, owner, turn) in `chat_attachments`. A new column `storage` (`db`, `fs`, `s3`) and `key` say where the bytes are, so rows from several backends can be read while a migration runs.
- `superstep attachments migrate --to fs|s3|db [--dry-run] [--batch N]`: copies bytes, checks size and SHA-256, switches the row, then deletes the source. Resumable; safe to run twice.
- Retention and the unsent-file sweeper delete the object as well as the row. A periodic orphan check removes objects without a row (older than one hour).
- Backup and restore: `db` stays inside the database dump; `fs` adds the folder to the archive; `s3` records the bucket and prefix in the manifest and does not copy objects by default (`--include-attachments` downloads them into the archive). Restore refuses a manifest whose backend does not match the target's configuration unless `--force`.
- `superstep install` and `superstep deploy` ask "Where should chat attachments be stored?" (database, folder, S3-compatible) with `--attachment-storage` and the S3 flags for `--yes`; S3 secrets go to `.env` with mode 600 and are never printed.
- Handbook en and vi (Configuration, Operate: Backup, Chat: Attachments), `docs/api-errors.md` for any new error code, CHANGELOG.

### Out Of Scope

- Moving other binary data (chat logos, knowledge base documents, run payloads) in this requirement; the port is designed so they can use it later.
- Browser uploads straight to the bucket (presigned PUT) and presigned GET downloads (see DEC-0074, decision 3).
- Azure Blob and Google Cloud Storage native APIs (GCS has an S3-compatible XML API; Azure can come later as another backend).
- Encryption at rest managed by superstep; buckets use their provider's server-side encryption.

## Desired Behavior

1. A fresh install with no new settings stores files in the database, as today.
2. An operator sets `STUDIO_ATTACHMENT_STORAGE=s3` and the bucket settings, restarts, and new uploads go to the bucket. Old files still download from the database.
3. `superstep attachments migrate --to s3` moves the old files; the database shrinks after the next vacuum.
4. A visitor downloads their file exactly as before; another visitor still gets 404, and the bucket is never exposed.
5. Retention deletes a chat and its objects.

## Business Rules

- The bytes never enter run state or checkpoints (DEC-0072 stays).
- A file is either fully stored and linked, or not visible: the row is written after the object, and a failed row write deletes the object.
- Keys are random (`<workflow>/<session>/<attachment id>`), never the file name.

## Constraints

- No change to exports, templates or the public API shapes.
- `boto3` only in an optional extra; the `db` and `fs` backends need no new dependency.
- The public demo keeps refusing uploads.

## Acceptance Criteria

- The three backends pass one shared contract test suite (`fs` on a temp folder, `s3` against a local MinIO or `moto` stub in CI).
- Upload, download, delete, retention and the sweeper work on each backend; owner-only downloads and headers are unchanged.
- `attachments migrate` moves rows both ways, is resumable, and checks checksums.
- Backup and restore round-trip for `db` and `fs`; for `s3` the manifest records the bucket and restore warns as specified.
- `superstep install --yes --attachment-storage s3 ...` writes the settings; `doctor` reports a failing bucket clearly.

## Open Questions

None open. The owner accepted DEC-0074's recommendations on 2026-10-31:

1. Default for new installs: `db` stays the default when nothing is configured. `superstep install` offers `fs` on the instance volume for single-host installs and `s3` for the full stack (or when the operator has a bucket).
2. `superstep backup` does not copy S3 objects by default: the manifest records bucket and prefix; `--include-attachments` copies the objects.
3. Logos and knowledge documents: not in this requirement (see Out Of Scope). The port is designed so they can use it later; moving them needs a new requirement.

## Owner Decisions (2026-10-31)

- Three backends, `db` (default), `fs` and `s3`.
- The install offers `fs` for single-host installs and `s3` for the full stack.
- Downloads stream through the backend; no presigned URLs.
- `superstep attachments migrate --to <backend>` with SHA-256 checks and resumable batches.
- Deletion stays in the service (retention, sweeper, session delete), with an orphan sweep.
- Backup: `fs` adds the folder to the archive; `s3` writes bucket and prefix to the manifest, with `--include-attachments`.
- The Render demo stays on `db`.
- `boto3` is an optional extra, included in the published images.

## Planned Tasks

| Task | Scope | Depends on |
|---|---|---|
| TASK-0191 | Storage port, `storage`/`key` columns, `db` backend refactor, write order, orphan sweep, contract suite | none |
| TASK-0192 | `fs` backend, health probe, shared volume in Docker | TASK-0191 |
| TASK-0193 | `s3` backend (`boto3` extra), streaming, health probe, MinIO CI job | TASK-0191 |
| TASK-0194 | `superstep attachments migrate` and backup/restore | TASK-0192, TASK-0193 |
| TASK-0195 | Install/deploy prompts, `doctor`, handbook en and vi, e2e | TASK-0194 |

## Related Artifacts

- `.factory-state/artifacts/REQ-0077-chat-attachments.md`, `.factory-state/decisions/DEC-0072-chat-attachments.md`
- `.factory-state/decisions/DEC-0074-attachment-storage.md` (Accepted)
- `.factory-state/artifacts/REQ-0079-superstep-cli.md`
