import shutil

import pytest

from app.runtime.mock_adapter import MockVideoAdapter
from app.schemas import GenerationRequest


def test_mock_adapter_reports_missing_video_tooling(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = MockVideoAdapter()
    monkeypatch.setattr("app.runtime.mock_adapter.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="Mock runtime needs ffmpeg"):
        adapter.validate()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_mock_adapter_generates_mp4(tmp_path) -> None:
    adapter = MockVideoAdapter()
    request = GenerationRequest(
        prompt="color bars",
        width=320,
        height=180,
        video_length=12,
        fps=12,
        steps=4,
    )
    adapter.validate()
    result = adapter.generate(request, tmp_path, lambda *_: None)

    assert result.video_path.exists()
    assert result.video_path.suffix == ".mp4"
