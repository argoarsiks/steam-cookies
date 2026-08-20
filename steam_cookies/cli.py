import argparse
import asyncio
import sys

from steam_cookies.client import SteamWebSessionClient
from steam_cookies.cm_client import SteamCMClient
from steam_cookies.exceptions import SteamCookiesError
from steam_cookies.schemas import SteamWebCookies


def _print_cookies(cookies: SteamWebCookies) -> None:
    print(f"steamid:          {cookies.steamid}")
    print(f"steamLoginSecure: {cookies.steam_login_secure}")
    print(f"sessionid:        {cookies.session_id}")


async def _run_rest(refresh_token: str) -> None:
    async with SteamWebSessionClient() as client:
        cookies = await client.get_web_cookies(refresh_token)
    _print_cookies(cookies)


async def _run_cm(refresh_token: str, account_name: str) -> None:
    async with SteamCMClient() as client:
        cookies = await client.get_web_cookies(refresh_token, account_name)
    _print_cookies(cookies)


def _run_extract_token(account_name: str) -> None:
    from steam_cookies.local_client import read_local_refresh_token

    print(read_local_refresh_token(account_name))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="steam_cookies")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rest = subparsers.add_parser(
        "rest", help="Exchange a refresh token via the public REST endpoint"
    )
    rest.add_argument("refresh_token")

    cm = subparsers.add_parser("cm", help="Exchange a refresh token via a real CM session")
    cm.add_argument("refresh_token")
    cm.add_argument("account_name", help="Login name, not persona/display name")

    extract = subparsers.add_parser(
        "extract-token",
        help="Read the refresh token from the local Steam client's storage (Windows only)",
    )
    extract.add_argument("account_name", help="Login name, not persona/display name")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        if args.command == "rest":
            asyncio.run(_run_rest(args.refresh_token))
        elif args.command == "cm":
            asyncio.run(_run_cm(args.refresh_token, args.account_name))
        elif args.command == "extract-token":
            _run_extract_token(args.account_name)
    except SteamCookiesError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
