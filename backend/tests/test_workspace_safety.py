import os

import pytest
from fastapi import HTTPException

from xoai.workspace.router import _ensure_not_workspace_root, _resolve_or_403, _safe_upload_filename
from xoai.workspace.service import resolve_safe_path


def test_safe_upload_filename_strips_path_segments():
    assert _safe_upload_filename("../../secrets.txt") == "secrets.txt"
    assert _safe_upload_filename("nested/report.md") == "report.md"


def test_safe_upload_filename_rejects_empty_names():
    with pytest.raises(HTTPException) as exc:
        _safe_upload_filename("")
    assert exc.value.status_code == 400


def test_resolve_or_403_blocks_workspace_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(HTTPException) as exc:
        _resolve_or_403("u1", "../outside.txt", str(workspace))

    assert exc.value.status_code == 403


def test_resolve_safe_path_blocks_commonprefix_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    escaped = "../workspace-other/secrets.txt"

    with pytest.raises(PermissionError):
        resolve_safe_path("u1", escaped, str(workspace))


def test_delete_guard_blocks_workspace_root(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(HTTPException) as exc:
        _ensure_not_workspace_root(os.path.join(workspace, "."), str(workspace), "delete")

    assert exc.value.status_code == 400
