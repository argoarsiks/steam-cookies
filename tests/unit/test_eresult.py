from steam_cookies.eresult import eresult_name


def test_known_eresult_returns_its_name() -> None:
    assert eresult_name(1) == "OK"
    assert eresult_name(5) == "InvalidPassword"
    assert eresult_name(15) == "AccessDenied"


def test_unknown_eresult_returns_placeholder() -> None:
    assert eresult_name(-1) == "Unknown(-1)"
    assert eresult_name(999999) == "Unknown(999999)"
