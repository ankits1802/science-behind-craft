import getpass
import sys

__all__ = ["read_password"]


def read_password(prompt: str = "Password: ") -> str:
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return sys.stdin.readline().rstrip("\r\n")
