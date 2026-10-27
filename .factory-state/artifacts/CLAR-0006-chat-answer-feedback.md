---
schema_version: 1
id: CLAR-0006
task_id: REQ-0075
status: open
source_artifacts:
  - .factory-state/artifacts/REQ-0075-chat-answer-feedback.md
  - .factory-state/artifacts/REQ-0074-public-chat-page.md
  - .factory-state/artifacts/REQ-0042-workflow-tests.md
  - .factory-state/artifacts/REQ-0050-langsmith-evals.md
created: 2026-10-27
updated: 2026-10-27
answered_at: null
questions:
  - id: where
    type: single_choice
    prompt: Where can people rate answers?
    required: true
    context: >-
      The public page is where outside people chat, so its ratings are the most useful. In the studio Chat tab,
      builders test their own workflow. Ratings there cost little, because both use the same chat components.
    recommendation: public-and-studio
    options:
      - value: public-and-studio
        label: On the public page, the embed and the studio Chat tab
      - value: public-only
        label: Only on the public page and the embed
  - id: comment
    type: single_choice
    prompt: Can the person add a comment?
    required: true
    context: >-
      A thumbs down tells the builder that an answer was wrong, but not what was wrong. An optional comment on a thumbs
      down is what Dify and ChatGPT ask for. A comment on a thumbs up is rarely written.
    recommendation: on-down
    options:
      - value: on-down
        label: An optional comment with a thumbs down
      - value: on-both
        label: An optional comment with either rating
      - value: none
        label: No comment, only the thumbs
  - id: builder-view
    type: single_choice
    prompt: What do builders see?
    required: true
    context: >-
      Marks on the answers and a "thumbs down" filter in the Visitors list are enough to find the bad answers. Totals
      (up, down and the share of down over the last 7 or 30 days) in the Chat tab's header show the trend. A page
      across all workflows would be new navigation.
    recommendation: marks-filter-totals
    options:
      - value: marks-filter-totals
        label: Marks on the answers, a "thumbs down" filter and totals for the workflow in the Chat tab
      - value: marks-filter
        label: Marks on the answers and the filter, with no totals
  - id: langsmith
    type: single_choice
    prompt: Is a rating sent to LangSmith when LangSmith is configured?
    required: true
    context: >-
      Runs already go to LangSmith as traces, and test runs already send feedback (REQ-0050). A rating would show on
      the run's trace as the feedback key "user_rating" (1 or 0, with the comment). The ratings stay in the studio
      either way.
    recommendation: send
    options:
      - value: send
        label: Yes, in the background, when LangSmith is configured
      - value: keep-local
        label: No, the ratings stay in the studio
  - id: to-test
    type: single_choice
    prompt: Can a builder turn a rated answer into a test case?
    required: true
    context: >-
      "Save as test case" already makes a draft test case from a run (REQ-0042). Offering it on a rated answer turns a
      reported problem into a check the workflow must pass. It reuses the existing draft, so the cost is small.
    recommendation: save
    options:
      - value: save
        label: Yes, "Save as test case" on rated answers
      - value: later
        label: Not now
  - id: channels
    type: single_choice
    prompt: Do Slack and Telegram chats get ratings too?
    required: true
    context: >-
      Slack reactions and Telegram's inline buttons could carry a rating, but each channel needs its own event and
      callback handling, plus mapping a message back to its turn. Keeping them for later keeps this requirement small.
    recommendation: later
    options:
      - value: later
        label: Not now, only the web chat
      - value: include
        label: Yes, Slack reactions and Telegram buttons as well
answers: {}
---
# Clarification

Owner questions for REQ-0075, which adds a thumbs up or down to the answers in a chat. Each question has a
recommended option. The owner can answer in chat (for example, "trả lời CLAR-0006 theo đề xuất"), or by editing the
`answers` map.

The owner may answer it with:

```text
factory clarify CLAR-0006 -C <project-dir>
```
