"""Break-glass admin process (TASK-0154)."""
import pytest

from app.admin_cmd import main
from app.core import security
from app.core.errors import AppError
from app.models.database import Database
from app.repositories import UserRepository
from app.services.admin_account import AdminAccountService


def _service(tmp_path):
    db = Database(f"sqlite:///{tmp_path}/admin.db")
    db.migrate()
    return db, AdminAccountService(UserRepository(db))


def test_create_inserts_an_admin_and_a_second_call_promotes(tmp_path):
    _db, svc = _service(tmp_path)
    users = svc.users
    first = svc.create("Owner@Example.com")
    assert security.password_problem(first) is None
    created = users.get_by_email("owner@example.com")
    assert created is not None and created.role == "admin" and created.active
    assert security.verify_password(first, created.password)
    before = created.password
    with pytest.raises(AppError) as exc:
        svc.create("owner@example.com", "no")
    assert exc.value.code == "AUTH_PASSWORD_TOO_SHORT"
    assert users.get_by_email("owner@example.com").password == before
    users.set_role(created.id, "editor")
    users.set_active(created.id, False)
    second = svc.create("owner@example.com", "Correct-horse-42")
    assert second == "Correct-horse-42"
    again = users.get_by_email("owner@example.com")
    assert again.id == created.id and again.role == "admin" and again.active
    assert [user.email for user, _count in users.list_all()].count("owner@example.com") == 1
    assert security.verify_password(second, again.password)
    assert not security.verify_password(first, again.password)
    assert again.password_changed


def test_reset_changes_the_hash_and_list_has_no_hash(tmp_path):
    _db, svc = _service(tmp_path)
    users = svc.users
    svc.create("owner@example.com", "Correct-horse-42")
    users.add("ed", "ed@example.com", security.hash_password("Correct-horse-42"), 1.0)
    before = users.get_by_email("ed@example.com").password
    reset = svc.reset_password("ed@example.com")
    editor = users.get_by_email("ed@example.com")
    assert editor.role == "editor" and editor.password != before
    assert security.password_problem(reset) is None
    assert security.verify_password(reset, editor.password)
    listed = svc.list_admins()
    assert listed == [("owner@example.com", "admin")]
    blob = repr(listed)
    assert "pbkdf2" not in blob and editor.password not in blob and before not in blob
    with pytest.raises(AppError) as exc:
        svc.reset_password("missing@example.com")
    assert exc.value.code == "USER_NOT_FOUND"


def test_process_prints_the_password_once_and_list_without_a_hash(tmp_path, monkeypatch, capsys):
    db = Database(f"sqlite:///{tmp_path}/proc.db")
    monkeypatch.setattr("app.admin_cmd.get_db", lambda: db)
    assert main(["create", "--email", "owner@example.com"]) == 0
    created = capsys.readouterr()
    password = created.out.strip()
    assert created.err == "" and created.out == password + "\n"
    assert security.password_problem(password) is None
    assert "pbkdf2" not in created.out
    assert main(["create", "--email", "owner@example.com", "--password", "Correct-horse-42"]) == 0
    again = capsys.readouterr()
    assert again.out == "Correct-horse-42\n" and again.err == ""
    users = UserRepository(db)
    assert [user.email for user, _count in users.list_all()].count("owner@example.com") == 1
    before = users.get_by_email("owner@example.com").password
    assert main(["reset-password", "--email", "owner@example.com"]) == 0
    reset = capsys.readouterr()
    assert reset.err == "" and "pbkdf2" not in reset.out
    assert users.get_by_email("owner@example.com").password != before
    assert main(["list"]) == 0
    listed = capsys.readouterr()
    assert listed.out == "owner@example.com\tadmin\n"
    assert "pbkdf2" not in listed.out and before not in listed.out
    assert main(["create", "--email", "other@example.com", "--password", "weak"]) == 1
    failed = capsys.readouterr()
    assert failed.out == "" and "AUTH_PASSWORD" in failed.err
    assert users.get_by_email("other@example.com") is None
