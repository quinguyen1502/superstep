"""Opt-in browser fixture: only Google Drive HTTP is replaced; never a production entry point."""
import os

if os.environ.get("STUDIO_E2E_DRIVE_FIXTURE") != "1":
    raise RuntimeError("Drive preview requires the explicit isolated E2E flag")

from app.main import app
from app.services.managed_tools import drive
from tests.fixtures.drive_provider import DriveProvider

provider = DriveProvider()
provider.shared = False
drive.request = provider.request


@app.get("/api/_drive-fixture")
def recorded_files():
    return {"uploads": provider.uploads, "files": [drive.DriveTools._metadata(entry["metadata"]) for entry in provider.files.values()]}


@app.post("/api/_drive-fixture/lose-ack")
def lose_ack():
    provider.write_mode = "timeout"
    return {"armed": True}


@app.post("/api/_drive-fixture/restore")
def restore_ack():
    provider.write_mode = "ok"
    return {"armed": False}
