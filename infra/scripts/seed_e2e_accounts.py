import argparse
import base64
import hashlib
import os
import secrets
import subprocess
import sys

REGION = "ap-south-1"
REPO = "cxacraftecosystem-ui/KalaVigyan"
GITHUB_USER = "ankits1802"
PARAMETER_PATH = "/kalavigyan/e2e"
ACCOUNTS = {
    "PROFESSOR": "e2e-professor@kalavigyan.example",
    "ADMIN": "e2e-admin@kalavigyan.example",
}
PASSWORD_BYTES = 32
TOTP_SECRET_BYTES = 20


def log(message):
    print(message, file=sys.stderr, flush=True)


def fingerprint(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def new_password():
    return secrets.token_urlsafe(PASSWORD_BYTES)


def new_totp_secret():
    return base64.b32encode(secrets.token_bytes(TOTP_SECRET_BYTES)).decode("ascii").rstrip("=")


GENERATORS = {"PASSWORD": new_password, "TOTP_SECRET": new_totp_secret}


class Parameters:
    def __init__(self, client):
        self.client = client

    def get(self, name):
        try:
            return self.client.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
        except self.client.exceptions.ParameterNotFound:
            return None

    def put(self, name, value):
        self.client.put_parameter(
            Name=name, Value=value, Type="SecureString", Overwrite=True, Tier="Standard"
        )


def settle(params, *, rotate):
    values = {}
    for role, email in ACCOUNTS.items():
        values[f"E2E_{role}_EMAIL"] = email
        for part, generate in GENERATORS.items():
            name = f"E2E_{role}_{part}"
            path = f"{PARAMETER_PATH}/{name}"
            current = None if rotate else params.get(path)
            value = current or generate()
            if value == current:
                log(f"{path}: kept (sha256 {fingerprint(value)})")
            else:
                params.put(path, value)
                log(f"{path}: written as SecureString (sha256 {fingerprint(value)})")
            values[name] = value
    return values


def gh_secret_set(name, value):
    token = subprocess.run(
        ["gh", "auth", "token", "--user", GITHUB_USER], capture_output=True, text=True, check=True
    ).stdout.strip()
    done = subprocess.run(
        ["gh", "secret", "set", name, "--repo", REPO],
        input=value,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GH_TOKEN": token},
    )
    if done.returncode != 0:
        detail = done.stderr.replace(value, "<value>").strip()[:300] if value else done.stderr.strip()[:300]
        raise SystemExit(f"gh secret set {name} failed: {detail}")


def main(argv=None, *, params=None, set_secret=gh_secret_set):
    parser = argparse.ArgumentParser(
        description=(
            f"Generate the Professor and Admin E2E passwords and two-step secrets on this machine, store them "
            f"under {PARAMETER_PATH} in Parameter Store and as GitHub secrets on {REPO}. Values are never printed."
        )
    )
    parser.add_argument("--rotate", action="store_true", help="replace the stored values with new ones")
    parser.add_argument("--skip-github", action="store_true", help="write Parameter Store only")
    options = parser.parse_args(argv)
    if params is None:
        import boto3

        params = Parameters(boto3.client("ssm", region_name=REGION))
    values = settle(params, rotate=options.rotate)
    if not options.skip_github:
        for name, value in values.items():
            set_secret(name, value)
            log(f"GitHub secret {name}: set (sha256 {fingerprint(value)})")
    log("Next: dispatch E2E accounts (gh workflow run e2e-accounts.yml --repo " + REPO + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
