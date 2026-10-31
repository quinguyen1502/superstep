"""Break-glass admin process: `python -m app.admin_cmd create|reset-password|list|attachments-*`.

Opens the database through the existing deps and calls the service. No HTTP route.
Stdout is the password, once, or one `email<TAB>role` line per admin; the attachment commands print one JSON object.
"""
import argparse
import json
import sys

from .api.deps import get_db
from .core.errors import AppError
from .repositories import UserRepository
from .services.admin_account import AdminAccountService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.admin_cmd")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--email", required=True)
    create.add_argument("--password")
    create.add_argument("--password-stdin", action="store_true")
    reset = commands.add_parser("reset-password")
    reset.add_argument("--email", required=True)
    reset.add_argument("--password")
    reset.add_argument("--password-stdin", action="store_true")
    commands.add_parser("list")
    commands.add_parser("attachments-summary")
    commands.add_parser("attachments-export")  # tar on stdout
    commands.add_parser("attachments-import")  # tar on stdin
    migrate = commands.add_parser("attachments-migrate")
    migrate.add_argument("--to", required=True)
    migrate.add_argument("--batch", type=int, default=100)
    migrate.add_argument("--limit", type=int)
    migrate.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    db = get_db()
    db.migrate()
    if args.command.startswith("attachments-"):
        return _attachments(args)
    service = AdminAccountService(UserRepository(db))
    try:
        if args.command == "list":
            for email, role in service.list_admins():
                sys.stdout.write(f"{email}\t{role}\n")
            return 0
        chosen = sys.stdin.readline().rstrip("\n") if args.password_stdin else args.password
        password = service.create(args.email, chosen) if args.command == "create" else service.reset_password(args.email, chosen)
    except AppError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1
    sys.stdout.write(password + "\n")
    return 0


def _attachments(args) -> int:
    """TASK-0194: the files per backend, or a move to another backend, as one JSON object on stdout."""
    from .api.deps import attachment_archive, attachment_migration
    from .storage import StoreError
    if args.command in ("attachments-export", "attachments-import"):
        archive = attachment_archive()
        try:
            n = archive.export(sys.stdout.buffer) if args.command == "attachments-export" else archive.restore(sys.stdin.buffer)
        except StoreError as exc:
            sys.stderr.write(json.dumps({"code": "CHAT_ATTACHMENT_STORAGE", "message": exc.reason}) + "\n")
            return 1
        sys.stderr.write(json.dumps({"files": n}) + "\n")
        return 0
    svc = attachment_migration()
    try:
        out = svc.summary() if args.command == "attachments-summary" else svc.run(args.to, args.batch, args.dry_run, args.limit)
    except AppError as exc:
        sys.stderr.write(json.dumps({"code": exc.code, "message": exc.message}) + "\n")
        return 1
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
