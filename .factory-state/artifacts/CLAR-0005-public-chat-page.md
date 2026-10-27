---
schema_version: 1
id: CLAR-0005
task_id: REQ-0074
status: open
source_artifacts:
  - .factory-state/artifacts/REQ-0074-public-chat-page.md
  - .factory-state/artifacts/REQ-0048-agent-chat.md
  - .factory-state/decisions/DEC-0052-web-chat-model.md
  - .factory-state/decisions/DEC-0053-chat-access-and-steps.md
  - .factory-state/decisions/DEC-0054-human-answered-by.md
created: 2026-10-27
updated: 2026-10-27
questions:
  - id: access
    type: single_choice
    prompt: Which access values does the public page offer in 0.9.0?
    required: true
    context: >-
      DEC-0053 reserved two values. With anonymous, anyone who has the link can chat. With signed_in, any account of
      this studio can chat, including one without the run right on the workflow, and it uses the studio sign-in. Both
      use the same page and the same API; signed_in only adds the sign-in redirect and ties sessions to the account.
      Offering only one of them saves little work.
    recommendation: both
    options:
      - value: both
        label: Both anonymous and signed_in
      - value: anonymous
        label: Only anonymous; signed_in stays reserved
      - value: signed_in
        label: Only signed_in; anonymous stays reserved
    depends_on: null
  - id: visitor-identity
    type: single_choice
    prompt: How does the page remember an anonymous visitor?
    required: true
    context: >-
      The visitor needs an id to see their earlier chats and to keep other visitors out of them. An HttpOnly cookie,
      set by the server for that chat page only, cannot be read by scripts on the page and expires after the
      retention period. An id in localStorage is simpler but can be read by any script on the page. With no id, each
      visit starts empty, there is no list of earlier chats, and a chat is lost on reload.
    recommendation: cookie
    options:
      - value: cookie
        label: An HttpOnly cookie for that chat page, set by the server
      - value: local-storage
        label: An id in the browser's localStorage
      - value: none
        label: No id; each visit starts a new chat and there is no list of earlier chats
    depends_on: null
  - id: limits
    type: single_choice
    prompt: Which limits protect a published chat from abuse and cost?
    required: true
    context: >-
      Every message is a run that uses the owner's model keys. The studio already has fixed-window limiters, shared
      through Redis. The recommended defaults are 10 messages per minute per visitor, 30 per minute per IP, and a cap of
      500 per workflow per day that the builder can change in Chat settings. The operator can change all three
      through STUDIO_ environment variables, and 0 turns a limit off. A CAPTCHA (Cloudflare Turnstile) stops bots
      better, but it needs an outside account, sends visitor data to that service, and a site key for every
      deployment.
    recommendation: limits
    options:
      - value: limits
        label: Limits per visitor, per IP and per workflow per day, with no CAPTCHA
      - value: limits-and-captcha
        label: The same limits, plus an optional Cloudflare Turnstile CAPTCHA when the operator sets a key
      - value: ip-only
        label: Only a limit per IP
    depends_on: null
  - id: visitor-answers
    type: single_choice
    prompt: On the public page, who answers a Human node whose "answered by" is visitor?
    required: true
    context: >-
      In the studio (DEC-0054), the person chatting answers it inline, and a reviewer answers when the node says
      reviewer. An Agent node's tool approvals always go to a reviewer. Keeping the same rule means a workflow behaves
      the same in the Chat tab and on the page; a builder who does not trust outside visitors sets the node to
      reviewer. The alternative is that every Human node on the public page goes to a reviewer, which is safer but
      makes visitor questions (a choice, a form) impossible.
    recommendation: same-as-studio
    options:
      - value: same-as-studio
        label: The same as in the studio; the node's "answered by" setting decides
      - value: always-reviewer
        label: Always a reviewer on the public page
    depends_on: null
  - id: embed
    type: single_choice
    prompt: Does 0.9.0 also let the page be embedded in another site?
    required: true
    context: >-
      An iframe embed of the same page needs a list of allowed sites (frame-ancestors), a compact layout and a copy
      button for the snippet. The third option is a script widget with a floating chat bubble, which is more work again.
      Leaving the embed out keeps 0.9.0 smaller; DEC-0052 already reserved the embed channel for it.
    recommendation: later
    options:
      - value: later
        label: Later; 0.9.0 has only the page
      - value: iframe
        label: An iframe embed with a list of allowed sites
      - value: widget
        label: A script widget with a floating chat bubble
    depends_on: null
  - id: page-content
    type: single_choice
    prompt: What can the builder set for the page's look?
    required: true
    context: >-
      The page uses the studio's theme (light and dark) and the shadcn chat components. The recommended option adds
      the text a visitor sees first: a title, a short intro in Markdown, and up to four suggested messages. A logo
      and an accent colour need image upload and colour tokens that come from the builder, which the UI rules keep to
      the theme.
    recommendation: text
    options:
      - value: text
        label: A title, an intro and up to four suggested messages
      - value: title-only
        label: A title only
      - value: branded
        label: Also a logo and an accent colour
    depends_on: null
  - id: builder-review
    type: single_choice
    prompt: Can builders read visitor chats?
    required: true
    context: >-
      The runs already show in the run history, but a whole conversation is easier to read as a chat. The
      recommended option is a "Visitors" list in the Chat tab that shows each visitor chat read-only, to people with
      the run right, until retention deletes it. The handbook would tell builders to say on the page that chats are
      kept. The alternative is the run history only.
    recommendation: read-only
    options:
      - value: read-only
        label: A read-only "Visitors" list in the Chat tab
      - value: runs-only
        label: The run history only
    depends_on: null
  - id: version
    type: single_choice
    prompt: Which version of the workflow does the public page run?
    required: true
    context: >-
      The studio Chat tab, Slack, Telegram and the API trigger all run the latest saved version, so a save goes live
      at once. Versions exist (REQ-0005), so the page could instead run a version the builder pins when publishing.
      The builder then has to publish again after each change, and the setting needs a version picker. Pinning is safer
      for a public page, and both can be offered later.
    recommendation: latest
    options:
      - value: latest
        label: The latest saved version, as for the other triggers
      - value: pinned
        label: A version the builder picks when publishing
    depends_on: null
answers: {}
---
# Clarification

Owner questions for REQ-0074, the public chat page (phase 2 of REQ-0048, to ship in 0.9.0). Each question has a
recommended option. The answers go into REQ-0074 and a new DEC that replaces the "reserved" part of DEC-0053.

The owner may answer it with:

```text
factory clarify CLAR-0005 -C <project-dir>
```

or in chat, for example "theo đề xuất" to pick every recommended option.
