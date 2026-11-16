import datetime as dt

import pytest
import requests

from geo_etl.layers import chirps

TODAY = dt.date(2026, 11, 17)
TIFS = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs/"


def response(status: int, text: str = "") -> requests.Response:
    made = requests.Response()
    made.status_code = status
    made._content = text.encode("utf-8")
    made.url = "fixture"
    return made


class FakeServer:
    def __init__(self, answers: dict[tuple[str, str], list]):
        self.answers = answers
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url))
        queue = self.answers[(method, url)]
        answer = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(answer, Exception):
            raise answer
        return response(*answer) if isinstance(answer, tuple) else response(answer)


def serve(monkeypatch, answers) -> FakeServer:
    server = FakeServer(answers)
    monkeypatch.setattr(chirps.requests, "request", server)
    return server


def head(year: int) -> tuple[str, str]:
    return ("HEAD", f"{TIFS}chirps-v3.0.{year}.tif")


def test_the_annual_url_is_the_published_name():
    assert chirps.annual_url(2025) == f"{TIFS}chirps-v3.0.2025.tif"


def test_latest_year_is_last_year_when_its_file_exists(monkeypatch, sleeps):
    server = serve(monkeypatch, {head(2025): [200]})
    assert chirps.latest_year(TODAY) == 2025
    assert server.calls == [head(2025)]
    assert sleeps == []


def test_latest_year_steps_back_only_on_404(monkeypatch, sleeps):
    server = serve(monkeypatch, {head(2025): [404], head(2024): [200]})
    assert chirps.latest_year(TODAY) == 2024
    assert server.calls == [head(2025), head(2024)]


def test_a_timeout_is_retried_not_taken_for_a_missing_year(monkeypatch, sleeps):
    timeout = requests.ConnectTimeout("stalled")
    server = serve(monkeypatch, {head(2025): [timeout, timeout, 200]})
    assert chirps.latest_year(TODAY) == 2025
    assert server.calls == [head(2025)] * 3
    assert sleeps == [5.0, 10.0]


def test_an_unreachable_probe_falls_back_to_the_listing(monkeypatch, sleeps):
    listing = (
        '<a href="chirps-v3.0.2023.tif">chirps-v3.0.2023.tif</a> '
        '<a href="chirps-v3.0.2024.tif">chirps-v3.0.2024.tif</a> '
        '<a href="chirps-v3.0.2025.tif.aux.xml">chirps-v3.0.2025.tif.aux.xml</a> '
        '<a href="chirps-v3.0.2026.tif">chirps-v3.0.2026.tif</a>'
    )
    server = serve(monkeypatch, {head(2025): [requests.ReadTimeout("stalled")], ("GET", TIFS): [(200, listing)]})
    assert chirps.latest_year(TODAY) == 2024
    assert server.calls == [head(2025)] * 4 + [("GET", TIFS)]
    assert sleeps == [5.0, 10.0, 15.0]


def test_a_server_error_is_retried_then_falls_back(monkeypatch, sleeps):
    listing = '<a href="chirps-v3.0.2025.tif">chirps-v3.0.2025.tif</a>'
    server = serve(monkeypatch, {head(2025): [503, 502, 503, 504], ("GET", TIFS): [(200, listing)]})
    assert chirps.latest_year(TODAY) == 2025
    assert server.calls[-1] == ("GET", TIFS)


def test_probe_and_listing_both_unreachable_names_both(monkeypatch, sleeps):
    serve(monkeypatch, {head(2025): [requests.ConnectionError("refused")], ("GET", TIFS): [503]})
    with pytest.raises(RuntimeError, match=r"unreachable: probe .*refused.*; listing .*503"):
        chirps.latest_year(TODAY)


def test_four_missing_years_fail_without_a_listing(monkeypatch, sleeps):
    server = serve(monkeypatch, {head(year): [404] for year in (2025, 2024, 2023, 2022)})
    with pytest.raises(RuntimeError, match="no CHIRPS v3.0 annual file for 2022 to 2025"):
        chirps.latest_year(TODAY)
    assert ("GET", TIFS) not in server.calls


def test_a_listing_that_is_not_found_fails_naming_it(monkeypatch, sleeps):
    serve(monkeypatch, {head(2025): [requests.ReadTimeout("stalled")], ("GET", TIFS): [404]})
    with pytest.raises(RuntimeError, match=f"{TIFS} answered 404"):
        chirps.latest_year(TODAY)


def test_a_listing_without_a_recent_year_fails(monkeypatch, sleeps):
    listing = '<a href="chirps-v3.0.2019.tif">chirps-v3.0.2019.tif</a>'
    serve(monkeypatch, {head(2025): [requests.ReadTimeout("stalled")], ("GET", TIFS): [(200, listing)]})
    with pytest.raises(RuntimeError, match="lists no CHIRPS v3.0 annual file for 2022 to 2025"):
        chirps.latest_year(TODAY)
