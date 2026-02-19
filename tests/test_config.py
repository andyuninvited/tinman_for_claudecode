"""Tests for TinMan config loading, presets, and env var overrides."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from tinman.config import TinManConfig, PRESETS, PRESET_SANE


class TestDefaults:
    def test_sane_defaults(self):
        cfg = TinManConfig()
        assert cfg.interval_minutes == 30
        assert cfg.notify_only is True
        assert cfg.max_actions_per_run == 0
        assert cfg.require_confirmation is True

    def test_sane_preset_values(self):
        assert PRESET_SANE["interval_minutes"] == 30
        assert PRESET_SANE["notify_only"] is True

    def test_all_presets_exist(self):
        for name in ("sane", "paranoid", "chaos"):
            assert name in PRESETS


class TestPresets:
    def test_paranoid_tighter_than_sane(self):
        p = PRESETS["paranoid"]
        s = PRESETS["sane"]
        assert p["interval_minutes"] <= s["interval_minutes"]
        assert p["notify_only"] is True

    def test_chaos_is_active(self):
        c = PRESETS["chaos"]
        assert c["notify_only"] is False
        assert c["max_actions_per_run"] > 0
        assert c["require_confirmation"] is False

    def test_from_dict_applies_preset(self):
        cfg = TinManConfig.from_dict({**PRESETS["paranoid"], "preset": "paranoid"})
        assert cfg.interval_minutes == 15
        assert cfg.preset == "paranoid"


class TestLoadFromFile:
    def test_load_from_json(self, tmp_path):
        config_file = tmp_path / "tinman.json"
        config_file.write_text(json.dumps({"interval_minutes": 45, "notify_only": True}))
        cfg = TinManConfig.load(str(config_file))
        assert cfg.interval_minutes == 45

    def test_load_nonexistent_returns_defaults(self):
        cfg = TinManConfig.load("/nonexistent/path/tinman.json")
        assert cfg.interval_minutes == 30

    def test_load_preset_from_file(self, tmp_path):
        config_file = tmp_path / "tinman.json"
        config_file.write_text(json.dumps({"preset": "paranoid"}))
        cfg = TinManConfig.load(str(config_file))
        assert cfg.interval_minutes == 15


class TestEnvVarOverrides:
    def test_interval_env_var(self, monkeypatch):
        monkeypatch.setenv("TINMAN_INTERVAL_MINUTES", "10")
        cfg = TinManConfig.load()
        assert cfg.interval_minutes == 10

    def test_notify_only_env_var_true(self, monkeypatch):
        monkeypatch.setenv("TINMAN_NOTIFY_ONLY", "true")
        cfg = TinManConfig.load()
        assert cfg.notify_only is True

    def test_notify_only_env_var_false(self, monkeypatch):
        monkeypatch.setenv("TINMAN_NOTIFY_ONLY", "false")
        cfg = TinManConfig.load()
        assert cfg.notify_only is False

    def test_env_var_overrides_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "tinman.json"
        config_file.write_text(json.dumps({"interval_minutes": 60}))
        monkeypatch.setenv("TINMAN_INTERVAL_MINUTES", "5")
        cfg = TinManConfig.load(str(config_file))
        assert cfg.interval_minutes == 5


class TestSave:
    def test_save_and_reload(self, tmp_path):
        cfg = TinManConfig(interval_minutes=42, notify_only=True)
        saved = cfg.save(str(tmp_path / "config.json"))
        reloaded = TinManConfig.load(str(saved))
        assert reloaded.interval_minutes == 42

    def test_save_creates_directory(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "config.json"
        cfg = TinManConfig()
        cfg.save(str(target))
        assert target.exists()
