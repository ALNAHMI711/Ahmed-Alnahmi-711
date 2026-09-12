from io import BytesIO
from zipfile import ZipFile

from backend.app.services.upload_scan import inspect_upload


def test_rejects_dangerous_python():
    assert inspect_upload("bad.py", b"import subprocess\nsubprocess.run([])")["status"] == "REJECTED"


def test_scans_zip_members():
    blob = BytesIO()
    with ZipFile(blob, "w") as archive:
        archive.writestr("strategy.py", 'os.system("whoami")')
    assert inspect_upload("strategy.zip", blob.getvalue())["status"] == "REJECTED"


def test_keeps_safe_file_pending_review():
    assert inspect_upload("strategy.py", b"class Strategy: pass")["status"] == "PENDING_REVIEW"


def test_rejects_path_traversal_filename():
    assert inspect_upload("../strategy.py", b"class Strategy: pass")["status"] == "REJECTED"


def test_rejects_zip_path_traversal():
    blob = BytesIO()
    with ZipFile(blob, "w") as archive:
        archive.writestr("../escape.py", "class Strategy: pass")
    assert inspect_upload("strategy.zip", blob.getvalue())["status"] == "REJECTED"
