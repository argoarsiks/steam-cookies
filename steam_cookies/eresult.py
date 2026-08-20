"""Steam's EResult codes, for turning the ``x-eresult`` response header into a
readable name in diagnostics. Values per Steamworks' public EResult enum.
"""

ERESULT_NAMES: dict[int, str] = {
    0: "Invalid",
    1: "OK",
    2: "Fail",
    3: "NoConnection",
    5: "InvalidPassword",
    6: "LoggedInElsewhere",
    7: "InvalidProtocolVer",
    8: "InvalidParam",
    9: "FileNotFound",
    10: "Busy",
    11: "InvalidState",
    15: "AccessDenied",
    16: "Timeout",
    17: "Banned",
    18: "AccountNotFound",
    19: "InvalidSteamID",
    20: "ServiceUnavailable",
    21: "NotLoggedOn",
    24: "InsufficientPrivilege",
    25: "LimitExceeded",
    26: "Revoked",
    27: "Expired",
    34: "LogonSessionReplaced",
    48: "TryAnotherCM",
    50: "AlreadyLoggedInElsewhere",
    63: "AccountLogonDenied",
    65: "InvalidLoginAuthCode",
    84: "RateLimitExceeded",
    85: "AccountLoginDeniedNeedTwoFactor",
    88: "TwoFactorCodeMismatch",
}


def eresult_name(eresult: int) -> str:
    return ERESULT_NAMES.get(eresult, f"Unknown({eresult})")
