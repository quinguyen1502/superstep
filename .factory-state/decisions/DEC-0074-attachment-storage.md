# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0074
- Status: Accepted (2026-10-31, owner Thái Quí Nguyễn). Not implemented yet; planned into TASK-0191 to TASK-0195.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-31
- Related Requirements: REQ-0080 (Accepted), REQ-0077
- Related Tasks: TASK-0191, TASK-0192, TASK-0193, TASK-0194, TASK-0195
- Related Architecture: DEC-0072 (chat attachments), DEC-0009 (layers), DEC-0068 and DEC-0071 (CLI)

## Context

- DEC-0072 stores each chat file in `chat_attachments.data` (LargeBinary: `bytea` on Postgres, BLOB on SQLite). Limits: 10 MB per file, 5 per message, operator ceilings `STUDIO_CHAT_ATTACHMENT_MAX_MB` and `_MAX_FILES`; retention 30 days by default; unsent files deleted after an hour.
- The owner worries that the database will grow too large.
- Deployments: the all-in-one image with SQLite on `/data` (a volume), the full stack (Postgres, Redis, `api`, `worker`, `web`), and the Render free demo (`superstep-demo`), whose filesystem is ephemeral and which refuses uploads in demo mode.

## Other platforms (official documentation, read on 2026-10-30)

- **Dify**: `STORAGE_TYPE` selects `opendal` (default, `OPENDAL_SCHEME=fs` with `OPENDAL_FS_ROOT=storage`), `s3` (`S3_ENDPOINT`, `S3_BUCKET_NAME`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_ADDRESS_STYLE`), Azure, GCS and others; local mode needs the same volume on `api` and `worker`. Migration commands: `flask upload-local-files-to-cloud-storage`. https://docs.dify.ai/en/self-host/deploy/configuration/environments and https://docs.dify.ai/en/self-host/deploy/troubleshooting/storage-and-migration
- **Flowise**: `STORAGE_TYPE=local|s3|gcs|azure`, default `local` under `BLOB_STORAGE_PATH` (`~/.flowise/storage`); chat image and audio uploads use it; S3 has `S3_ENDPOINT_URL` and `S3_FORCE_PATH_STYLE` for compatible services. https://docs.flowiseai.com/configuration/environment-variables
- **Langflow**: `LANGFLOW_STORAGE_TYPE=local|s3`; local files under `LANGFLOW_CONFIG_DIR` (lost with the container unless that is a mounted volume); S3 through boto3 with `LANGFLOW_OBJECT_STORAGE_BUCKET_NAME` and `_PREFIX`; a `relocate-files` command moves existing files. https://docs.langflow.org/concepts-file-management and https://docs.langflow.org/deployment-docker
- **n8n**: `N8N_DEFAULT_BINARY_DATA_MODE` = memory (default), `filesystem`, `database` (needed in queue mode, max 512 MiB per file by default) or `s3`/`azure` (Business and Enterprise licences only); S3-compatible services such as R2 and B2 work but are not officially supported; S3 pruning is delegated to a bucket lifecycle rule. https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/handle-binary-data and https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/use-external-storage

Common pattern: a storage abstraction with a local-folder default and an S3-compatible option chosen by environment variables, plus a one-off migration command. None of the four keeps uploads in the main database by default except n8n's `database` mode, which exists for multi-instance setups without shared disks.

## Options

| Option | Setup | DB size | Multi-instance (api + worker) | Backup | Cost and ops |
|---|---|---|---|---|---|
| A. Database only (today) | none | grows with files | works | one dump has everything, but it is large and slow | managed Postgres storage is the most expensive per GB; vacuum, replication and `pg_dump` carry the bytes |
| B. Local folder or volume (`fs`) | a path on a persistent volume | metadata only | needs a shared volume (all-in-one: same container, fine; full stack: a named volume mounted on `api` and `worker`) | archive the folder next to the dump | cheapest; lost on ephemeral disks (Render free) |
| C. S3-compatible (`s3`) | bucket, keys, endpoint | metadata only | works anywhere | objects stay in the bucket (versioning or the provider's replication); the CLI can copy them on request | pay per GB and request; R2 has no egress fees; B2 is low-cost; MinIO self-hosted; one more credential to protect |

## Decision

1. **A storage port with three backends**, `db` (default), `fs` and `s3`, selected by `STUDIO_ATTACHMENT_STORAGE`, with the S3 settings in REQ-0080. The attachment service depends on the port; repositories keep metadata only. `boto3` is an optional extra included in the published images.
2. **Rows say where their bytes are** (`storage`, `key`), so a change of backend needs no downtime and old rows stay readable until migrated.
3. **Streaming through the backend, not presigned URLs.** Downloads keep the DEC-0072 guarantees: owner check on every request, `attachment` disposition, `nosniff`, `no-store`, CSP sandbox, and no bucket URL in the page. Uploads keep the size check before reading (Content-Length, then a capped read) and stream to the backend in chunks. Presigned URLs would leak a bearer link valid for its lifetime, bypass the owner check after issue, need bucket CORS, and let the provider choose the response headers; at 10 MB per file the bandwidth through the API is acceptable. Revisit if limits grow past about 100 MB.
4. **Migration** with `superstep attachments migrate --to <backend>` (a CLI command calling an admin API endpoint or `docker exec` into the api container, like other CLI admin commands): copy, verify size and SHA-256, switch the row, delete the source; resumable in batches.
5. **Deletion** stays in the service: retention, the unsent sweeper and session delete remove the object after the row (an orphan sweep catches crashes). Lifecycle rules on the bucket are optional extra safety, not the mechanism.
6. **Backup**: `db` unchanged; `fs` adds `attachments/` to the archive; `s3` writes bucket and prefix to the manifest, with `--include-attachments` to copy objects.
7. **CLI install and deploy** ask for the backend; the Render demo keeps `db` (ephemeral disk, uploads refused in demo mode anyway).

## Recommendation

- Build the port and `fs` + `s3` together (one REQ, about five tasks: port and `db` backend refactor; `fs` backend; `s3` backend with a MinIO-based CI test; migrate command and backup/restore; CLI prompts, doctor and handbook).
- Default: `db` when nothing is configured (zero-config, Render demo). `superstep install` proposes `fs` on the instance volume for single-host installs and `s3` for the full stack or when the operator already has a bucket. Recommend Cloudflare R2 or Backblaze B2 for low-cost hosted storage, MinIO for on-premise.
- Until this ships, operators can cap growth with the existing settings: lower `STUDIO_CHAT_ATTACHMENT_MAX_MB` and the chat's retention days.

## Alternatives Considered

- Only `fs`: simplest, but fails on multi-instance deployments without a shared volume and on ephemeral hosts.
- Only `s3`: forces every self-hoster to run or rent a bucket.
- A general library (Apache OpenDAL, as Dify does, or fsspec): many backends for free, but a larger dependency and less control over streaming and errors; three small backends are enough now.
- Presigned URLs: see decision 3.

## Risks

- Two places to keep consistent (row and object): handled by write order and the orphan sweep.
- S3 credentials are one more secret: stored like other secrets in `.env`, never logged, `doctor` shows only whether they work.
- `fs` on the full stack without a shared volume: `doctor` and the health probe from the worker detect it.

## Approval

- Accepted by the owner, Thái Quí Nguyễn, on 2026-10-31: "Duyệt đề xuất cả 3 backend db, fs, s3, merge #229 và lập task". All three backends and the recommendations above are accepted as proposed: `db` default; install offers `fs` (single host) and `s3` (full stack); streaming downloads, no presigned URLs; `attachments migrate` with SHA-256 checks and resumable batches; deletion in the service with an orphan sweep; backup as in decision 6 with `--include-attachments`; the Render demo stays on `db`; `boto3` optional extra included in the images.

## Review Or Revisit Trigger

- The owner's answer to REQ-0080's open questions; file limits above 100 MB; other binary data (logos, knowledge documents) moving to the port.
