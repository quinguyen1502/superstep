"""Break-glass admin process: `python -m app.admin_cmd create|reset-password|list`.

Opens the database through the existing deps and calls the service. No HTTP route.
Stdout is the password, once, or one `email<TAB>role` line per admin.
"""
import argparse
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
    reset = commands.add_parser("reset-password")
    reset.add_argument("--email", required=True)
    reset.add_argument("--password")
    commands.add_parser("list")
    args = parser.parse_args(argv)
    db = get_db()
    db.migrate()
    service = AdminAccountService(UserRepository(db))
    try:
        if args.command == "list":
            for email, role in service.list_admins():
                sys.stdout.write(f"{email}\t{role}\n")
            return 0
        password = service.create(args.email, args.password) if args.command == "create" else service.reset_password(args.email, args.password)
    except AppError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1
    sys.stdout.write(password + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
