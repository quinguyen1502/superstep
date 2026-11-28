# Design

## Metadata

- Project: superstep
- Design ID: DES-0009
- Status: Proposed for implementation review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Related Requirements: REQ-0103
- Related Architecture: ARCH-0005

## SDK And API Experience

From Dataset Access, a permitted manager creates a Dataset API token. An integration developer configures the official SDK with the server URL, Dataset ID, scoped token and explicit binding. Handbook examples show a paged find, an insert with an operation ID, and handling denied operations and schema drift. The SDK reports server codes and keeps the same operation identity across a retry.

## Studio Realtime

The open Rows tab refreshes its data in place. Preserve filter, sort, grouping, summary settings, column layout, focused cell and scroll position when the refreshed view permits it. Avoid a full loading overlay for background updates. Show a concise status only when updates are delayed or access is lost. An active editor keeps focus and draft text. If its row was changed elsewhere, the existing save conflict flow remains the recovery path.

## Share Flow

1. A permitted manager opens **Access**, then **Share links**. Select at least one column and optionally a fixed filter. The preview renders the same projection as the public page.
2. Create the link and copy it from the result. The system displays the secret URL at creation or rotation. Access lists share names and configuration afterward. Rotate to issue a fresh URL and invalidate the previous URL. Use the shared exact-name confirmation flow to revoke.
3. A logged-out visitor opens the link and sees the published name, approved columns and matching rows. Offer paging and search over published searchable columns. Show a loading state, no matches, a recoverable request error, or an unavailable link state as appropriate.
4. The public page has a Rows view. Configuration, editing actions, CSV, and access management stay in Studio. Formula values may appear only when the manager selects their columns. Relation fields stay unavailable in v1.

## Accessibility And Responsive Behavior

- Use shadcn components, theme tokens, and paired EN/VI labels and feedback. Keep share dialogs keyboard usable, restore focus on close, and announce copied, revoked and error status once.
- Keep the existing grid focus ring and scroll behavior. The visitor page works with narrow touch viewports, keyboard paging, and both themes.
- Preview and anonymous Playwright sessions must display identical approved columns and row results for the same query. Capture light and dark screenshots during QA.

## Related Artifacts

- [Requirement](REQ-0103-dataset-integrations-and-live-sharing.md)
- [Architecture](ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Dataset design baseline](DES-0007-datasets.md)
- [UI conventions](../../docs/ui-conventions.md)
