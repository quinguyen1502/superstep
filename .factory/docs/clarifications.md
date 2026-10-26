# Task Clarifications

Most questions do not need a dedicated UI. Agents should resolve repository-discoverable facts themselves and ask one to three simple owner questions in the current chat or CLI session, then record the answers in project artifacts.

Create a clarification artifact when a task has at least four questions, a long checklist, multiple decision groups, or conditional questions.

## Artifact

Store clarifications as `.factory-state/artifacts/CLAR-xxxx-<task>.md` using `templates/clarification-template.md`. The YAML frontmatter is the machine-readable contract; the Markdown body provides durable context.

Supported question types are `confirmation`, `single_choice`, `multi_choice`, `free_text`, and `checklist`. A question may use `depends_on` to become active only after a particular answer.

## Owner Flow

The owner answers in the current chat, or edits the `answers` map in the clarification artifact. Submitting answers does not approve a pull request or execute the selected action. The next agent reads the artifact and updates the related requirement, design, architecture, decision, or task artifacts.
