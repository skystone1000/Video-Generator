"""Unit tests for adapter command construction.

These tests mock the filesystem so no real model files or GPU are required.
Run with:  cd backend && pytest tests/test_adapter_commands.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.schemas import GenerationRequest


def _make_request(**overrides) -> GenerationRequest:
    defaults = dict(
        prompt="a test prompt",
        negative_prompt="",
        aspect_ratio="16:9",
        resolution="480p",
        width=854,
        height=480,
        video_length=29,
        fps=24,
        steps=12,
        seed=42,
        cfg_scale=6.0,
        flow_shift=5.0,
        use_cpu_offload=True,
        use_fp8=False,
        rewrite_prompt=False,
        preset="hunyuan-480p-fast",
        runtime="hunyuan_15",
    )
    defaults.update(overrides)
    return GenerationRequest(**defaults)


class TestHunyuan15AdapterCommand:
    """build_command() tests for Hunyuan15Adapter."""

    def _make_adapter(self, repo: str = "E:/models/HunyuanVideo-1.5", ckpts: str = "E:/models/HunyuanVideo-1.5/ckpts"):
        from app.runtime.hunyuan_15_adapter import Hunyuan15Adapter

        adapter = Hunyuan15Adapter()
        settings_mock = MagicMock()
        settings_mock.hunyuan_15_repo_path = repo
        settings_mock.hunyuan_15_model_path = ckpts
        settings_mock.hunyuan_15_torchrun_path = ".venv/Scripts/torchrun.exe"
        settings_mock.hunyuan_15_enable_sr = False
        settings_mock.hunyuan_15_use_sage_attn = False
        settings_mock.hunyuan_15_enable_cache = False
        settings_mock.resolve_path = lambda p: Path(p) if p else None
        return adapter, settings_mock

    def test_prompt_present_in_command(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(prompt="cinematic sunrise")
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert "cinematic sunrise" in cmd

    def test_seed_included(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(seed=99)
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert "--seed" in cmd
        idx = cmd.index("--seed")
        assert cmd[idx + 1] == "99"

    def test_cpu_offload_flag(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(use_cpu_offload=True)
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert "--offloading" in cmd
        idx = cmd.index("--offloading")
        assert cmd[idx + 1] == "true"

    def test_no_cpu_offload(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(use_cpu_offload=False)
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        idx = cmd.index("--offloading")
        assert cmd[idx + 1] == "false"

    def test_fp8_flag_off_by_default(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(use_fp8=False)
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert "--use_fp8_gemm" not in cmd

    def test_fp8_flag_on(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(use_fp8=True)
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert "--use_fp8_gemm" in cmd

    def test_python_exe_not_torchrun(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request()
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        # First element must be python.exe, not torchrun
        assert "torchrun" not in cmd[0].lower()
        assert "python" in cmd[0].lower()

    def test_rewrite_disabled_passes_false(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(rewrite_prompt=False)
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        idx = cmd.index("--rewrite")
        assert cmd[idx + 1] == "false"

    def test_output_path_included(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request()
        out = Path("E:/outputs/job_1")
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, out)
        assert "--output_path" in cmd
        idx = cmd.index("--output_path")
        assert cmd[idx + 1].endswith("output.mp4")

    def test_no_shell_true_in_command_list(self):
        """Command must be a list (not a string) — verifies shell=True can't be used."""
        adapter, settings_mock = self._make_adapter()
        request = _make_request()
        with patch("app.runtime.hunyuan_15_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert isinstance(cmd, list), "Command must be a list to prevent shell injection"
        for arg in cmd:
            assert isinstance(arg, str), f"All args must be strings, got {type(arg)}"


class TestHunyuanOriginalAdapterCommand:
    """build_command() tests for HunyuanOriginalAdapter."""

    def _make_adapter(self, repo: str = "E:/models/HunyuanVideo", ckpts: str = "E:/models/HunyuanVideo/ckpts"):
        from app.runtime.hunyuan_original_adapter import HunyuanOriginalAdapter

        adapter = HunyuanOriginalAdapter()
        settings_mock = MagicMock()
        settings_mock.hunyuan_original_repo_path = repo
        settings_mock.hunyuan_original_ckpt_path = ckpts
        settings_mock.resolve_path = lambda p: Path(p) if p else None
        return adapter, settings_mock

    def test_uses_sys_executable_not_python3(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(runtime="hunyuan_original")
        with patch("app.runtime.hunyuan_original_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert cmd[0] == sys.executable
        assert "python3" not in cmd[0]

    def test_prompt_in_command(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(prompt="ocean waves", runtime="hunyuan_original")
        with patch("app.runtime.hunyuan_original_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert "ocean waves" in cmd

    def test_command_is_list(self):
        adapter, settings_mock = self._make_adapter()
        request = _make_request(runtime="hunyuan_original")
        with patch("app.runtime.hunyuan_original_adapter.get_settings", return_value=settings_mock):
            cmd = adapter.build_command(request, Path("E:/outputs/job_1"))
        assert isinstance(cmd, list)


class TestProgressRegex:
    """Verify the step progress regex matches expected output patterns."""

    def test_matches_tqdm_style(self):
        import re
        from app.runtime.hunyuan_15_adapter import _STEP_RE

        line = "  50%|█████     | 15/30 [02:30<02:30,  10s/it]"
        m = _STEP_RE.search(line)
        assert m is not None
        assert m.group(1) == "15"
        assert m.group(2) == "30"

    def test_matches_step_log_style(self):
        from app.runtime.hunyuan_15_adapter import _STEP_RE

        line = "Inference step 5/30 complete"
        m = _STEP_RE.search(line)
        assert m is not None
        assert m.group(1) == "5"
        assert m.group(2) == "30"

    def test_no_match_on_plain_text(self):
        from app.runtime.hunyuan_15_adapter import _STEP_RE

        line = "Loading model weights..."
        m = _STEP_RE.search(line)
        assert m is None
