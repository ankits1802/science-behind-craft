from datetime import UTC, date, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.scripts import send_alert_digest
from app.services import mailer
from app.services.alert_digest import DIGEST_SUBJECT, digest_mail, send_alert_digests, week_of, weekly_digest
from app.services.mailer import Mail

from ..contracts.learning_golden import ALERTS, AlertsFixture, learning

WEB = "https://kalavigyan.example.org"


def golden() -> AlertsFixture:
    return AlertsFixture.model_validate(learning(ALERTS))


class Untouched:
    def __call__(self) -> Any:
        raise AssertionError("the digest opened the database while it is switched off")


class Outbox:
    def __init__(self) -> None:
        self.sent: list[Mail] = []

    async def __call__(self, mail: Mail) -> bool:
        self.sent.append(mail)
        return True


@pytest.mark.parametrize(
    ("now", "monday"),
    [
        (datetime(2026, 11, 23, 3, 30, tzinfo=UTC), date(2026, 11, 23)),
        (datetime(2026, 11, 22, 20, 0, tzinfo=UTC), date(2026, 11, 23)),
        (datetime(2026, 11, 22, 18, 0, tzinfo=UTC), date(2026, 11, 16)),
        (datetime(2026, 11, 29, 18, 29, tzinfo=UTC), date(2026, 11, 23)),
    ],
)
def test_a_digest_is_dated_by_its_monday_in_india_time(now: datetime, monday: date) -> None:
    assert week_of(now) == monday


def test_the_weekly_digest_is_the_week_s_unread_notes_with_the_settings_link() -> None:
    fixture = golden()
    items = [note.payload for note in fixture.notifications.items]
    assert weekly_digest(items, week=date(2026, 11, 23), web_url=f"{WEB}/") == fixture.digest
    with pytest.raises(ValidationError):
        weekly_digest(items, week=date(2026, 11, 23), web_url="http://localhost:3000")


def test_the_digest_mail_names_each_explainer_and_its_new_findings() -> None:
    mail = digest_mail("reader@example.org", golden().digest, web_url=WEB)
    assert (mail.to, mail.subject, mail.html) == ("reader@example.org", DIGEST_SUBJECT, None)
    lines = mail.text.splitlines()
    assert "How is Kutch Ajrakh made, and why does its water matter?" in lines
    assert "Kutch Ajrakh: 4 new findings (3 in Geography and water, 1 in History)" in lines
    for item in golden().digest.items:
        at = lines.index(item.question)
        assert lines[at + 2] == f"{WEB}/ask?explainer={item.explainer_id}"
    assert not any(line.endswith(f"{WEB}/ask") for line in lines)
    assert lines[-1] == f"Stop these emails in Settings: {WEB}/settings"


async def test_no_digest_is_sent_while_the_setting_is_off() -> None:
    outbox = Outbox()
    report = await send_alert_digests(
        Untouched(), now=datetime(2026, 11, 23, 3, 30, tzinfo=UTC), enabled=False, web_url=WEB, send=outbox
    )
    assert outbox.sent == []
    assert report.as_dict() == {
        "enabled": False,
        "weekOf": None,
        "readers": 0,
        "sent": 0,
        "failed": 0,
        "ok": True,
    }


async def test_the_digest_script_sends_nothing_with_the_default_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outbox = Outbox()
    monkeypatch.setattr(mailer, "send", outbox)
    report = await send_alert_digest.run()
    assert (report["enabled"], report["sent"], outbox.sent) == (False, 0, [])
