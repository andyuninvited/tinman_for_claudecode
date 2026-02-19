"""Tests for the HeartbeatRunner - mocks claude CLI to avoid real API calls."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tinman.config import TinManConfig
from tinman.heartbeat import HeartbeatRunner, DEFAULT_HEARTBEAT_MD


@pytest.fixture
def cfg(tmp_path):
    return TinManConfig(
        heartbeat_md=str(tmp_path / "HEARTBEAT.md"),
        log_file=str(tmp_path / "heartbeat.log"),
        notify_stdout=False,   # silence output during tests
        notify_c3poh=False,
    )


@pytest.fixture
def runner(cfg):
    return HeartbeatRunner(cfg)


class TestEnsureHeartbeatMd:
    def test_creates_default_if_missing(self, runner, tmp_path):
        md = runner.ensure_heartbeat_md()
        assert md.exists()
        assert "HEARTBEAT_OK" in md.read_text()

    def test_does_not_overwrite_existing(self, runner, tmp_path):
        md_path = tmp_path / "HEARTBEAT.md"
        md_path.write_text("# Custom checklist\nDo stuff.")
        result = runner.ensure_heartbeat_md()
        assert result.read_text() == "# Custom checklist\nDo stuff."


class TestRunBeat:
    def _mock_claude_ok(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "HEARTBEAT_OK"
        mock.stderr = ""
        return mock

    def _mock_claude_alert(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "- Disk space low (2.1 GB free)\n- 3 uncommitted files"
        mock.stderr = ""
        return mock

    def _mock_claude_error(self):
        mock = MagicMock()
        mock.returncode = 1
        mock.stdout = ""
        mock.stderr = "Authentication failed"
        return mock

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_ok_status(self, mock_which, mock_run, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        mock_run.return_value = self._mock_claude_ok()
        result = runner.run_beat()
        assert result["status"] == "ok"
        assert result["output"] == "HEARTBEAT_OK"

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_alert_status(self, mock_which, mock_run, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        mock_run.return_value = self._mock_claude_alert()
        result = runner.run_beat()
        assert result["status"] == "alert"

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_error_status_when_stderr_only(self, mock_which, mock_run, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        mock_run.return_value = self._mock_claude_error()
        result = runner.run_beat()
        assert result["status"] == "error"

    @patch("shutil.which", return_value=None)
    def test_missing_claude_returns_error(self, mock_which, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        result = runner.run_beat()
        assert result["status"] == "error"
        assert "claude CLI not found" in result["error"]

    def test_empty_heartbeat_md_skips(self, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text("   \n  ")
        result = runner.run_beat()
        assert result["status"] == "skipped_empty"

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_result_is_logged(self, mock_which, mock_run, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        mock_run.return_value = self._mock_claude_ok()
        runner.run_beat()
        log = tmp_path / "heartbeat.log"
        assert log.exists()
        entry = json.loads(log.read_text().strip())
        assert entry["status"] == "ok"

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_result_has_timestamp(self, mock_which, mock_run, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        mock_run.return_value = self._mock_claude_ok()
        result = runner.run_beat()
        assert "timestamp" in result
        assert result["timestamp"].endswith("Z")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_result_has_duration(self, mock_which, mock_run, runner, tmp_path):
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        mock_run.return_value = self._mock_claude_ok()
        result = runner.run_beat()
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 0


class TestSafetyPrefix:
    def test_notify_only_in_prefix(self, tmp_path):
        cfg = TinManConfig(notify_only=True, notify_stdout=False)
        runner = HeartbeatRunner(cfg)
        prefix = runner._safety_prefix()
        assert "NOTIFY-ONLY" in prefix

    def test_no_prefix_for_chaos_mode(self, tmp_path):
        cfg = TinManConfig(
            notify_only=False,
            max_actions_per_run=10,
            require_confirmation=False,
            notify_stdout=False,
        )
        runner = HeartbeatRunner(cfg)
        prefix = runner._safety_prefix()
        assert prefix == ""


class TestC3PohNotify:
    @patch("urllib.request.urlopen")
    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_c3poh_notify_called(self, mock_which, mock_run, mock_urlopen, tmp_path):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "HEARTBEAT_OK"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        cfg = TinManConfig(
            heartbeat_md=str(tmp_path / "HEARTBEAT.md"),
            log_file=str(tmp_path / "heartbeat.log"),
            notify_stdout=False,
            notify_c3poh=True,
            c3poh_endpoint="http://localhost:7734/notify",
        )
        (tmp_path / "HEARTBEAT.md").write_text(DEFAULT_HEARTBEAT_MD)
        runner = HeartbeatRunner(cfg)
        runner.run_beat()
        assert mock_urlopen.called
