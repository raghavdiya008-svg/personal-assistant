"""
Tests for Semantic Desktop Capability Engine in Project JARVIS v2.
"""

import pytest
from pathlib import Path
from core.desktop import SemanticDesktopEngine
from core.config import settings


@pytest.fixture
def desktop(tmp_path):
    return SemanticDesktopEngine(workspace_root=settings.DATA_DIR)


@pytest.mark.asyncio
async def test_create_folder_and_move_file(desktop):
    subfolder = settings.DATA_DIR / "test_folder_v2"
    result = await desktop.create_folder(str(subfolder))
    assert result.content["status"] == "CREATED"
    assert subfolder.exists()

    # Create dummy file
    test_src = settings.DATA_DIR / "dummy_file.txt"
    test_src.write_text("sample content", encoding="utf-8")

    test_dst = subfolder / "moved_file.txt"
    move_result = await desktop.move_file(str(test_src), str(test_dst))
    assert move_result.content["status"] == "MOVED"
    assert test_dst.exists()
    assert not test_src.exists()


@pytest.mark.asyncio
async def test_path_escape_blocked(desktop):
    with pytest.raises(PermissionError) as exc_info:
        await desktop.create_folder("C:\\Windows\\System32\\unauthorized_folder")
    assert "outside authorized workspace" in str(exc_info.value)


@pytest.mark.asyncio
async def test_take_screenshot(desktop):
    result = await desktop.take_screenshot("test_screen.png")
    assert "path" in result.content
    assert Path(result.content["path"]).exists()
