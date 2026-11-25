import re
from datetime import timedelta

from app.services.naming import EXPORTS_PREFIX
from app.services.page_export_files import PAGE_EXPORT_OWNER
from app.services.stored_document_versions import KEPT_VERSIONS_MAX, PAGE_REVALIDATE

from .golden import REPO

TERRAFORM = REPO / "infra" / "terraform"
WEB_PAGES = REPO / "frontend" / "lib" / "sitePagesContract.ts"


def read(path: str) -> str:
    return (TERRAFORM / path).read_text(encoding="utf-8")


def rule(rules: str, name: str) -> str:
    found = re.search(rf'rule \{{\n    id     = "{name}"\n(.*?)\n  \}}\n', rules, re.DOTALL)
    assert found is not None, name
    return found.group(1)


def default(name: str) -> str:
    found = re.search(rf'variable "{name}" \{{[^}}]*default\s+= ([^\n]+)\n', read("variables.tf"))
    assert found is not None, name
    return found.group(1).strip('"')


def test_a_page_keeps_one_version_an_hour_for_as_long_as_a_cached_page_can_name_one() -> None:
    web = re.search(r"STATIC_PAGE_REVALIDATE_SECONDS = ([\d_]+);", WEB_PAGES.read_text(encoding="utf-8"))
    assert web is not None
    assert timedelta(seconds=int(web.group(1).replace("_", ""))) == PAGE_REVALIDATE
    assert KEPT_VERSIONS_MAX == 7 * 24


def test_a_page_export_leaves_the_bucket_within_two_days_and_other_exports_keep_their_week() -> None:
    rules = read("s3.tf")
    pages = rule(rules, "expire-page-exports")
    assert 'prefix = "exports/${var.page_export_owner}/"' in pages
    assert "days = var.page_export_days" in pages
    assert f"{EXPORTS_PREFIX}/{default('page_export_owner')}/" == f"{EXPORTS_PREFIX}/{PAGE_EXPORT_OWNER}/"
    assert (default("page_export_days"), default("export_noncurrent_days")) == ("1", "1")
    exports = rule(rules, "expire-exports")
    assert 'prefix = "exports/"' in exports
    assert "noncurrent_days = var.export_noncurrent_days" in exports
    assert default("export_days") == "7"
    backups = rule(rules, "keep-weekly-dumps")
    assert "noncurrent" not in backups and "days = var.weekly_dump_days" in backups
