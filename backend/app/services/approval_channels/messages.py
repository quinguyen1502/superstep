"""Chat texts of approval requests, outcomes and identity codes in English and Vietnamese (TASK-0022 follow-up).

The request and the edited message follow the run owner's language (users.lang, set by the studio's language
switcher); a private answer to the person who pressed a button follows theirs. Unknown / unset: English.
"""
from typing import Optional

LANGS = ("en", "vi")
TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Approval needed", "workflow": "Workflow: {v}", "step": "Step: {v}", "question": "Question: {v}", "run": "Run: {v}",
        "expires": "Expires: {v}", "open": "Open in Superstep", "approve": "Approve", "reject": "Reject",
        "approved_by": "✅ Approved by {who}", "rejected_by": "❌ Rejected by {who}", "at": "{text} at {when}",
        "answered": "Answered in Superstep", "cancelled": "The run was cancelled", "expired": "The request expired",
        "finished": "The run went on without this request",
        "reminded": "⏰ Reminder sent in a new message", "escalated": "⏰ No answer in time: handed to other approvers",
        "deadline_approved": "⏰ No answer in time: approved by the deadline", "deadline_rejected": "⏰ No answer in time: rejected by the deadline",
        "auto_approved": "🤖 Approved by AI review", "auto_rejected": "🤖 Rejected by an AI review rule",
        "ai_opinion": "AI review: {decision} ({confidence}). {reason}", "ai_approve": "approve", "ai_reject": "reject", "ai_escalate": "ask a person",
        "code": "Superstep verification code: {code}\nIt expires in {minutes} min. If you did not ask for it, ignore this message.",
        "APPROVAL_TOKEN_INVALID": "Invalid approval button", "APPROVAL_TOKEN_EXPIRED": "This approval request has expired",
        "APPROVAL_ALREADY_DECIDED": "This request was already answered",
        "APPROVAL_IDENTITY_UNKNOWN": "Link and verify your {kind} account in Superstep (Settings → My accounts) to approve",
        "APPROVAL_FORBIDDEN": "You are not allowed to approve this run",
        # chat triggers (TASK-0075)
        "chat_started": "▶️ Started {workflow} (run {run})", "chat_finished": "✅ {workflow} finished: {value}",
        "chat_waiting": "⏸ {workflow} is waiting for approval at {node}", "chat_failed": "❌ {workflow} failed: {error}",
        "chat_ended": "⏹ {workflow} stopped ({status})", "chat_empty": "(no value)", "chat_open": "Open the run: {link}",
        "CHAT_IDENTITY_UNKNOWN": "Link your {kind} account in Superstep (Settings → My accounts) to run workflows from the chat",
        "CHAT_IDENTITY_UNVERIFIED": "Verify your {kind} account in Superstep (Settings → My accounts) with the code the bot sent you",
        "CHAT_FORBIDDEN": "You are not allowed to run this workflow", "CHAT_TRIGGER_OFF": "This chat trigger is off",
        "RATE_LIMITED": "Too many runs from you with this command. Try again in a minute",
        "RUN_INPUT_TOO_LARGE": "The message is too long", "WORKFLOW_NOT_FOUND": "This workflow no longer exists",
    },
    "vi": {
        "title": "Cần phê duyệt", "workflow": "Workflow: {v}", "step": "Bước: {v}", "question": "Câu hỏi: {v}", "run": "Lượt chạy: {v}",
        "expires": "Hết hạn: {v}", "open": "Mở trong Superstep", "approve": "Duyệt", "reject": "Từ chối",
        "approved_by": "✅ {who} đã duyệt", "rejected_by": "❌ {who} đã từ chối", "at": "{text} lúc {when}",
        "answered": "Đã trả lời trong Superstep", "cancelled": "Lượt chạy đã bị huỷ", "expired": "Yêu cầu đã hết hạn",
        "finished": "Lượt chạy đã tiếp tục mà không cần yêu cầu này",
        "reminded": "⏰ Đã nhắc lại trong một tin nhắn mới", "escalated": "⏰ Hết hạn chờ: đã chuyển cho người duyệt khác",
        "deadline_approved": "⏰ Hết hạn chờ: tự động duyệt theo hạn", "deadline_rejected": "⏰ Hết hạn chờ: tự động từ chối theo hạn",
        "auto_approved": "🤖 AI đã tự duyệt", "auto_rejected": "🤖 Bị từ chối theo quy tắc AI duyệt",
        "ai_opinion": "AI duyệt: {decision} ({confidence}). {reason}", "ai_approve": "duyệt", "ai_reject": "từ chối", "ai_escalate": "cần người duyệt",
        "code": "Mã xác minh Superstep: {code}\nMã hết hạn sau {minutes} phút. Nếu bạn không yêu cầu, hãy bỏ qua tin nhắn này.",
        "APPROVAL_TOKEN_INVALID": "Nút phê duyệt không hợp lệ", "APPROVAL_TOKEN_EXPIRED": "Yêu cầu phê duyệt này đã hết hạn",
        "APPROVAL_ALREADY_DECIDED": "Yêu cầu này đã được trả lời",
        "APPROVAL_IDENTITY_UNKNOWN": "Hãy liên kết và xác minh tài khoản {kind} trong Superstep (Cài đặt → Tài khoản của tôi) để phê duyệt",
        "APPROVAL_FORBIDDEN": "Bạn không có quyền phê duyệt lượt chạy này",
        "chat_started": "▶️ Đã chạy {workflow} (lượt chạy {run})", "chat_finished": "✅ {workflow} đã xong: {value}",
        "chat_waiting": "⏸ {workflow} đang chờ phê duyệt ở {node}", "chat_failed": "❌ {workflow} bị lỗi: {error}",
        "chat_ended": "⏹ {workflow} đã dừng ({status})", "chat_empty": "(không có giá trị)", "chat_open": "Mở lượt chạy: {link}",
        "CHAT_IDENTITY_UNKNOWN": "Hãy liên kết tài khoản {kind} trong Superstep (Cài đặt → Tài khoản của tôi) để chạy workflow từ chat",
        "CHAT_IDENTITY_UNVERIFIED": "Hãy xác minh tài khoản {kind} trong Superstep (Cài đặt → Tài khoản của tôi) bằng mã bot đã gửi cho bạn",
        "CHAT_FORBIDDEN": "Bạn không có quyền chạy workflow này", "CHAT_TRIGGER_OFF": "Chat trigger này đang tắt",
        "RATE_LIMITED": "Bạn đã chạy lệnh này quá nhiều lần. Hãy thử lại sau một phút",
        "RUN_INPUT_TOO_LARGE": "Tin nhắn quá dài", "WORKFLOW_NOT_FOUND": "Workflow này không còn tồn tại",
    },
}


def lang_of(user) -> str:
    """A user's chat language (None / unknown -> en)."""
    v = getattr(user, "lang", None)
    return v if v in LANGS else "en"


def text(lang: Optional[str], key: str, **kw) -> str:
    t = TEXTS.get(lang or "en", TEXTS["en"]).get(key) or TEXTS["en"].get(key) or key
    return t.format(**kw) if kw else t


def opinion_text(lang: Optional[str], r: Optional[dict]) -> Optional[str]:
    """The AI review's opinion as one line of an approval message (TASK-0187), or None without one."""
    if not r or r.get("decision") not in ("approve", "reject", "escalate"): return None
    c = r.get("confidence")
    return text(lang, "ai_opinion", decision=text(lang, f"ai_{r['decision']}"), confidence="-" if c is None else f"{c:.2f}", reason=r.get("reason") or "").strip()
