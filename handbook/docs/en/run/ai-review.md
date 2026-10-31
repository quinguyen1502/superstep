# AI review of approvals

A model can look at an approval request before people do. It works on a
**Human** node and on an **Agent** node's tool approval. People stay in charge:
the model never rejects on its own, and anything it is unsure about goes to
people as usual.

## Modes

Set the mode in the node's **AI review** section, under the approval settings.

| Mode | What happens |
| --- | --- |
| Off | People answer every request (the default). |
| Suggest | The model gives its opinion (approve, reject or not sure, a confidence and a reason). People still answer. The opinion shows on the **Approvals** page and in channel messages. |
| Answer automatically | The model approves requests it is sure about. Everything else goes to people. |

Anyone who can edit the workflow can choose **Suggest**. Only the workflow
owner or an admin can choose **Answer automatically**, or save a change to a
node that uses it. Others get `AUTO_APPROVAL_FORBIDDEN`.

Start with **Suggest**. The section shows how often people agreed with the
model over the last 30 days. Turn on automatic answers when that rate is high.

## Settings

| Setting | Meaning |
| --- | --- |
| Judge credential | Any chat credential. The review is a separate model call. |
| Model | The model of that credential to use. |
| Instructions | What the judge should know, for example "Refunds up to 50 USD for existing customers are fine." |
| Minimum confidence | 0 to 1, default 0.8. Below it, the request goes to people. |
| Automatic answers per day | Per workflow, default 50, at most 10000. Days are counted in UTC. After the cap, requests go to people. |
| Notify | Tell the run owner when a request was answered automatically. Only the run owner is notified. |
| Rules | Checked before the model, see below. |

## Rules

A rule looks at a field of the request and, when it matches, sends the request
to people or rejects it. A rule never approves.

- Fields: `tool` and `args.<name>` (an Agent tool call), `prompt` and
  `state.<field>` (a Human node).
- Operators: equals, does not equal, contains, does not contain, matches (a
  regular expression), greater than, less than, is empty.
- When several rules match, reject wins over ask people.
- Up to 20 rules per node.

Example: `args.amount` greater than `100`, then **Ask people**.

In suggest mode a rule's reject is only a suggestion.

## When people are asked anyway

The request goes to people, as if AI review were off, when:

- AI review is paused (see below) or turned off on the server;
- the daily cap is reached;
- the judge credential is missing, or the studio runs in demo mode;
- the request is longer than 12,000 characters, so the model could not see all
  of it;
- the model call fails, times out (30 seconds) or returns something that is not
  a valid answer;
- the server restarted while the model was being asked;
- the model suspects the request tries to instruct it (prompt injection);
- the model would reject, or is not sure, or its confidence is below the
  minimum.

## Pause

- On the **Approvals** page, the **AI review** panel lists your workflows that
  use AI review, with the last 30 days' counts and the agreement rate. The
  workflow owner or an admin can pause one workflow there.
- Admins can pause AI review for every workflow in the same panel.
- The operator can turn automatic answers off with `STUDIO_AUTO_APPROVAL=off`.

Pausing does not change the workflow and does not make a new version.

## Audit

Every review is in the approval audit: the outcome, confidence, model, reason,
the rules that matched and a hash of the policy. A person's later answer
records whether they agreed with the model.

## Risks

- **Overconfidence.** A model can be sure and wrong. Keep the minimum
  confidence high, use rules for what must always reach people, and watch the
  agreement rate.
- **Prompt injection.** The request can carry text written by someone else.
  The judge treats the request as data only, and a suspected injection goes to
  people. Rules run before the model and cannot be talked out of.
- **Cost.** Each review is a model call on the judge credential. Its tokens
  and cost count in the run's usage: the run history, the trace summary and
  the Human node's row in the trace (its tooltip has an "AI review" line).
  A judge answer that is not the expected JSON still counts; a call that
  failed without an answer does not.

## Exports

Python, TypeScript and LangGraph project exports keep the graph only: there,
people answer every request. A note in the code says so. Workflow export and
templates keep the AI review settings without the judge credential.

See also [Human approval](human-approval.md) and the [Agent node](../guide/agent.md).
