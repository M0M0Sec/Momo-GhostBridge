"""
Tests for the CLI module.
"""

import pytest
from unittest.mock import patch, MagicMock
import argparse

from ghostbridge.cli import (
    main,
    cmd_version,
    cmd_test,
    cmd_config,
    setup_logging,
)
from ghostbridge import __version__


class TestCLIMain:
    """Test CLI main function."""

    def test_no_args_shows_help(self, capsys):
        """Test running without arguments shows help."""
        with patch("sys.argv", ["ghostbridge"]):
            result = main()
        assert result == 0

    def test_version_flag(self, capsys):
        """Test --version flag."""
        with patch("sys.argv", ["ghostbridge", "version"]):
            result = main()
        captured = capsys.readouterr()
        assert __version__ in captured.out
        assert result == 0


class TestCmdVersion:
    """Test version command."""

    def test_version_output(self, capsys):
        """Test version command output."""
        args = argparse.Namespace()
        result = cmd_version(args)
        captured = capsys.readouterr()
        assert f"GhostBridge v{__version__}" in captured.out
        assert result == 0


class TestCmdTest:
    """Test self-test command."""

    def test_self_test_runs(self, capsys):
        """Test self-test completes."""
        args = argparse.Namespace(verbose=False, config=None)
        
        with patch("ghostbridge.cli.GhostBridgeConfig"):
            result = cmd_test(args)
        
        captured = capsys.readouterr()
        assert "GhostBridge Self-Test" in captured.out


class TestCmdConfig:
    """Test config command."""

    def test_config_generate(self, capsys, tmp_path):
        """Test config generation."""
        output = tmp_path / "test_config.yml"
        args = argparse.Namespace(
            config=None,
            config_cmd="generate",
            output=str(output),
        )
        
        with patch("ghostbridge.cli.GhostBridgeConfig") as MockConfig:
            mock_config = MagicMock()
            MockConfig.return_value = mock_config
            result = cmd_config(args)
        
        assert result == 0
        mock_config.to_yaml.assert_called_once_with(str(output))

    def test_config_validate_success(self, capsys):
        """Test config validation success."""
        args = argparse.Namespace(
            config=None,
            config_cmd="validate",
        )
        
        with patch("ghostbridge.cli.GhostBridgeConfig.load"):
            result = cmd_config(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_config_validate_failure(self, capsys):
        """Test config validation failure."""
        args = argparse.Namespace(
            config="/nonexistent.yml",
            config_cmd="validate",
        )
        
        with patch("ghostbridge.cli.GhostBridgeConfig.load", side_effect=Exception("Not found")):
            result = cmd_config(args)
        
        assert result == 1


class TestSetupLogging:
    """Test logging setup."""

    def test_setup_verbose(self):
        """Test verbose logging setup."""
        import logging
        setup_logging(verbose=True)
        # Should set DEBUG level
        assert logging.getLogger().level == logging.DEBUG

    def test_setup_normal(self):
        """Test normal logging setup."""
        import logging
        setup_logging(verbose=False)
        assert logging.getLogger().level == logging.INFO

