# Datasets

A dataset is a typed table owned by you or by a team. Workflows can look up and
write rows. An exported project can use the same rows through the Superstep API
or through its own SQLite or PostgreSQL database.

## Authoring

Open **Datasets** from the studio navigation.

![The Support tickets grid](../images/datasets-grid.png)

On a narrow screen the catalog folds under the header and the grid scrolls sideways.

![Datasets on a narrow screen](../images/datasets-narrow.png)

- **Create** asks for a name, an optional description, and a personal or team
  scope. Add columns before the first import when you already know the fields.
- Each column has a label, a stable key, and a kind: text, number, boolean,
  date, datetime, email, or select. A column can be required or unique. The
  key stays the same when you rename the label, so workflow mappings keep
  working.
- Required is chosen when you add a column. Unique can be turned on later in
  **Edit column**, for example after importing a CSV without a key. Studio
  first checks the existing rows. If some rows share a value, it shows how many
  and links to those rows so you can fix them. Unique cannot be turned off
  while a workflow uses the field to find rows for Upsert or Delete row.
- The grid edits rows. A save sends the row revision. If someone else saved
  first, Studio asks you to reload instead of overwriting that edit.
- Removing a dataset, column, or grant asks you to type the item's name.
  Deleting a row names it by its first unique field, or by its row ID when the
  row has no unique value.
- Removing a column clears its values from every row. Its key stays reserved,
  so it cannot be reused, and removed columns do not count toward the 100
  column limit.
- A required column added to a dataset that has rows needs a default. Every
  existing row gets the default, as long as no row passes the 64 KiB limit.
- **Search rows** and the **Contains** filter ignore letter case, so "webhook"
  also finds "Webhook". This includes Vietnamese letters with diacritics. Text
  sorts ignore letter case too. **Equals** and unique keys match the exact value. **Does not equal**
  also matches empty cells. Each filter condition explains its operator.

You need `resources.manage` to create a dataset or change its rows. Anyone who
can see the dataset can read rows. Without that permission the create, edit,
import, and delete controls stay visible but disabled, with a note that explains
why. A link to a dataset that was deleted, or that you cannot open, shows
"Dataset not found" with a way back to the catalog.

A personal dataset is managed by its owner. A team dataset is managed by the
member who created it and by admins. Other team members with
`resources.manage` add, edit, import, and delete rows. Only a manager edits the
dataset, changes its columns, manages access and tokens, or deletes it. Studio
shows these actions disabled, with an explanation, for other members. An
admin can move a team dataset to another team member with **Transfer
ownership** in the dataset menu.

## Access

The dataset menu **Access** grants one saved workflow read or write permission.
A workflow without that grant cannot run a Dataset node or Dataset tool against
it. Deleting rows is a separate capability: check **Allow row deletion** on the
grant. Read and write alone do not allow Delete row.

Issue a Dataset token for an exported project that calls the Superstep API.
The token is shown once. Rotating it keeps the person who issued it, so the
new secret acts with the same authority. Revoking it stops later calls. A token also needs
**Allow row deletion** before the project can delete rows. A person who cannot
see the dataset gets "not found", including for CSV download.

Where a run starts decides what the grant allows:

| Run started from | Find, Get, Insert, Upsert | Delete row |
| --- | --- | --- |
| Studio Run, a schedule, or a workflow test | With the grant | With the grant and **Allow row deletion** |
| Studio chat, public chat, or the API trigger | With the grant | Never |
| Demo mode | Never | Never |

A workflow tool follows the run that called it. An unsaved workflow cannot use a
dataset. Removing a grant also stops a run that is waiting to resume.

Write without read can insert and upsert rows but never returns cell values.
The result has only the row ID, its revision, and whether the row was inserted,
from a real run, a test or debug run, and a retried write. A Dataset node with
a write-only grant cannot choose fields to return; a saved node that still asks
for fields fails with `DATASET_GRANT_DENIED` before it writes. An Agent tool
without **Find rows** gives the model the same identifiers, even with read and
write access. Upsert still reveals whether a row with that key exists. If that
must stay hidden, use **Insert row**. An upsert that changes no value keeps the
row's revision and update time.

## CSV

**Import CSV** previews the file before it writes anything.

![Import CSV preview and column mapping](../images/datasets-csv.png)

- The file is UTF-8, at most 1 MiB and 1,000 records. A header row is required.
- Preview suggests a field key and a kind for each column. You can change the
  mapping, skip a column, and edit the schema before import.
- Values with a leading zero or `+`, such as `00123` or `+84901234567`, and
  numbers longer than 15 digits are suggested as text so nothing is lost.
  Change the column type to Number to read them as numbers.
- Import is atomic. If any row is invalid, or repeats a unique value, nothing
  is written. The preview lists up to 100 issues in line order, with a count
  for each kind of issue. Each issue names the column label and the rejected
  value, shortened when it is long.
- **Export CSV** needs read access. It includes every row. Values that a
  spreadsheet would treat as formulas are prefixed with an apostrophe. Import
  removes that apostrophe again, so exporting and importing a file gives the
  same values. The download is at most 16 MiB.

## Workflows and export

A Dataset node can find rows, get one row, insert a row, upsert a row, or
delete a row. **Delete row** targets either a row id from the state or one
unique field and its value, and returns the deleted row id. A row that is
already gone fails the step.

An Agent tool reads by default. Under **Operations the Agent can use**, you can
also allow **Insert row** and **Upsert row**, and choose the fields the Agent
can write. Upsert needs a unique key field. An Agent tool cannot delete rows.
Agent writes use the workflow's write grant. A retried model call does not
write twice. The run trace shows the operation and the row count, not the
values.

Several nodes and tools that use the same dataset share one export binding.

On the **Code** tab, **Project .zip** lists each binding. Choose Superstep API,
SQLite, or PostgreSQL. The generated graph reads that choice from the
environment, so a deployment can change it without exporting again. Set:

- `DATASET_N_BACKEND` to `superstep`, `sqlite`, or `postgresql`
- `DATASET_N_ID` to the destination id or to a stable name in your database
- `DATASET_N_API_URL` and `DATASET_N_API_TOKEN` for the Superstep API
- `DATASET_N_SQLITE_PATH` or `DATASET_N_POSTGRES_DSN` for a standalone database

Run `python agent.py --setup-datasets` or the TypeScript equivalent before the
first run. Setup is safe to repeat. It creates the project tables and keeps
rows that are already stored. Delete row and Agent writes also work in a
standalone database, and each write is recorded so a retry returns the first
result. A snapshot is off unless you check **Include
current rows** for a standalone binding. The archive then contains at most
1,000 rows in `dataset-snapshots.json`. Setup imports a snapshot row only when
its id is not already stored, and it rejects a snapshot whose schema does not
match the binding.

## Backup, upgrade, and limits

Back up a standalone SQLite file by copying it while no writer is open, or back
up PostgreSQL with `pg_dump`. The Superstep database holds Studio rows in the
`dataset_rows` tables. Keep those tables when you roll an application version
back. Schema changes are additive. Do not delete the tables to undo an upgrade.

Supported bounds:

| Limit | Value |
| --- | --- |
| Columns | 100 in use, 200 including removed columns |
| Rows in one dataset | 25,000 |
| One row | 64 KiB |
| CSV import | 1 MiB and 1,000 records |
| CSV export | 16 MiB |
| Snapshot in a project | 1,000 rows |

A Dataset write receipt keeps the row identifier and outcome for 30 days by default. An exact retry returns the same row ID and insert outcome, with current values when the caller can read the row. A retry after row deletion returns identifiers only until the receipt expires. After expiry, the write can run again.
