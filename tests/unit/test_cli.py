import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from steam_cookies.cli import _build_parser, main
from steam_cookies.exceptions import SteamCookiesError


def test_rest_subcommand_parses_the_refresh_token() -> None:
    args = _build_parser().parse_args(["rest", "sometoken"])

    assert args.command == "rest"
    assert args.refresh_token == "sometoken"


def test_cm_subcommand_parses_token_and_account_name() -> None:
    args = _build_parser().parse_args(["cm", "sometoken", "myaccount"])

    assert args.command == "cm"
    assert args.refresh_token == "sometoken"
    assert args.account_name == "myaccount"


def test_extract_token_subcommand_parses_account_name() -> None:
    args = _build_parser().parse_args(["extract-token", "myaccount"])

    assert args.command == "extract-token"
    assert args.account_name == "myaccount"


def test_missing_subcommand_is_rejected() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])


def test_main_reports_steam_cookies_errors_as_exit_code_1(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    async def _boom(refresh_token: str) -> None:
        raise SteamCookiesError("something went wrong")

    monkeypatch.setattr("steam_cookies.cli._run_rest", _boom)

    exit_code = main(["rest", "sometoken"])

    assert exit_code == 1
    assert "Error: something went wrong" in capsys.readouterr().err


def test_main_reports_missing_optional_dependency_as_exit_code_1(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    def _missing_extra(account_name: str) -> None:
        raise ImportError("requires the 'local-client' extra")

    monkeypatch.setattr("steam_cookies.cli._run_extract_token", _missing_extra)

    exit_code = main(["extract-token", "myaccount"])

    assert exit_code == 1
    assert "local-client" in capsys.readouterr().err
