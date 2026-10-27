---
schema_version: 1
id: CLAR-0008
task_id: REQ-0077
status: answered
source_artifacts:
  - .factory-state/artifacts/REQ-0077-chat-attachments.md
  - .factory-state/artifacts/REQ-0074-public-chat-page.md
  - .factory-state/decisions/DEC-0052-web-chat-model.md
created: 2026-10-27
updated: 2026-10-27
answered_at: '2026-10-27'
questions:
  - id: kinds
    type: single_choice
    prompt: Which kinds of file can be attached in the first version?
    required: true
    context: >-
      Documents (.txt, .md, .pdf, .csv) reuse the knowledge bases' text extraction, and every model can read them as
      text. Images (PNG, JPEG, WebP) are what people most often want to send, for example a screenshot or a photo of an
      invoice, but they need image parts in each provider's messages and a model that can see. Office files would need
      a new dependency.
    recommendation: documents-and-images
    options:
      - value: documents-and-images
        label: Documents (.txt, .md, .pdf, .csv) and images (PNG, JPEG, WebP)
      - value: documents
        label: Documents only; images later
      - value: documents-images-office
        label: Documents, images and Office files (.docx, .xlsx), with a new dependency
  - id: workflow-view
    type: single_choice
    prompt: How does the workflow see the files, and what happens to an image sent to a model that cannot see?
    required: true
    context: >-
      A list field of file records (name, type, size, extracted text) lets any node use the files: a Condition can
      check for them, a Tool can read the text. LLM and Agent nodes add them to the prompt only when "Include
      attachments" is on. For an image sent to a text-only model, failing is explicit, but a chat that sometimes gets
      images would then fail. Skipping the image with a note that the model reads ("an image was attached but this
      model cannot see images") keeps the chat going.
    recommendation: field-skip-note
    options:
      - value: field-skip-note
        label: A list field; nodes include files on request; a text-only model gets a note instead of the image
      - value: field-fail
        label: A list field; nodes include files on request; a text-only model fails with an error code
      - value: text-in-message
        label: No field; the documents' text is appended to the message, and images are not supported
  - id: storage
    type: single_choice
    prompt: Where are the files stored?
    required: true
    context: >-
      The database is how the chat logo is stored. It needs no new volume, is in the backups, and works the same on
      SQLite and Postgres. With the limits below it stays small. A directory on a volume scales better, but it is a new
      thing for operators to mount and back up. S3-compatible storage suits large deployments, but it adds a
      dependency and settings.
    recommendation: database
    options:
      - value: database
        label: In the database, like the chat logo
      - value: volume
        label: In a directory on a volume (STUDIO_FILES_DIR)
      - value: s3
        label: S3-compatible object storage, with the database as a fallback
  - id: limits
    type: single_choice
    prompt: What are the default limits?
    required: true
    context: >-
      10 MB per file and 5 files per message cover documents and phone photos. The builder can lower them per chat, and
      the operator can lower the ceiling with an environment variable. Larger limits make the database grow fast when
      files are stored there.
    recommendation: ten-mb-five
    options:
      - value: ten-mb-five
        label: 10 MB per file and 5 files per message; lower per chat; ceiling set by the operator
      - value: five-mb-three
        label: 5 MB per file and 3 files per message
      - value: twenty-five-mb-ten
        label: 25 MB per file and 10 files per message
  - id: channels
    type: single_choice
    prompt: Do Slack and Telegram chats pass files to the workflow too?
    required: true
    context: >-
      Both channels can send files, and a chat trigger could download them into the same field. Each channel needs its
      own download, size check and token handling, so leaving them out keeps this requirement to the web chat.
    recommendation: later
    options:
      - value: later
        label: Not now, only the web chat
      - value: include
        label: Yes, Slack and Telegram files go to the same field
  - id: scanning
    type: single_choice
    prompt: How are files checked for harmful content?
    required: true
    context: >-
      Checking each file's bytes against the allowed kinds, and always serving files as downloads with nosniff, stops a
      file from running in the studio's pages. A virus scanner (ClamAV) would be a new service to run. The workflow
      itself only reads text and image parts, never runs a file.
    recommendation: type-check
    options:
      - value: type-check
        label: Check the type from the bytes and serve files only as downloads; no virus scanner
      - value: clamav
        label: Also scan with ClamAV when the operator sets one up
answers:
  kinds: documents-and-images
  workflow-view: field-skip-note
  storage: database
  limits: ten-mb-five
  channels: later
  scanning: type-check
---
# Clarification

Owner questions for REQ-0077, which adds file attachments to the chat. The owner answered in chat on 2026-10-27 ("Trả lời CLAR-0006 đến
CLAR-0009 theo đề xuất, rồi merge #200") and picked the recommended option for every question. The answers are written
into REQ-0077 under Owner Decisions.
