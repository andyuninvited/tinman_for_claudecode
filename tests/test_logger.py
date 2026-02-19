"""Tests for HeartbeatLogger - rotation and tail."""

import json
from pathlib import Path

import pytest

from tinman.config import TinManConfig
from tinman.logger import HeartbeatLogger


@pytest.fixture
def cfg(tmp_path):
    return TinManConfig(
        log_file=str(tmp_path / "heartbeat.log"),
        log_heartbeats=True,
        max_log_lines=10,
    )


def make_entry(status="ok", i=0):
    return {
        "timestamp": f"2025-01-0{i+1}T00:00:00Z",
        "status": status,
        "output": "HEARTBEAT_OK",
        "error": "",
        "duration_seconds": 1.0,
    }


class TestLogger:
    def test_log_creates_file(self, cfg, tmp_path):
        logger = HeartbeatLogger(cfg)
        logger.log(make_entry())
        assert (tmp_path / "heartbeat.log").exists()

    def test_log_writes_json_lines(self, cfg, tmp_path):
        logger = HeartbeatLogger(cfg)
        logger.log(make_entry(status="ok"))
        logger.log(make_entry(status="alert"))
        lines = (tmp_path / "heartbeat.log").read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["status"] == "ok"
        assert json.loads(lines[1])["status"] == "alert"

    def test_tail_returns_last_n(self, cfg, tmp_path):
        logger = HeartbeatLogger(cfg)
        for i in range(5):
            logger.log(make_entry(i=i))
        tail = logger.tail(3)
        assert len(tail) == 3
        assert tail[-1]["timestamp"] == "2025-01-05T00:00:00Z"

    def test_tail_empty_file(self, cfg):
        logger = HeartbeatLogger(cfg)
        assert logger.tail(10) == []

    def test_rotation_keeps_max_lines(self, cfg, tmp_path):
        logger = HeartbeatLogger(cfg)
        # Write 15 entries (max is 10)
        for i in range(15):
            logger.log(make_entry(i=i % 9))
        lines = (tmp_path / "heartbeat.log").read_text().splitlines()
        assert len(lines) <= 10

    def test_disabled_logging_no_file(self, tmp_path):
        cfg = TinManConfig(
            log_file=str(tmp_path / "heartbeat.log"),
            log_heartbeats=False,
        )
        logger = HeartbeatLogger(cfg)
        logger.log(make_entry())
        assert not (tmp_path / "heartbeat.log").exists()
