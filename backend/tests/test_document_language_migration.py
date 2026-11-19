from sqlalchemy import UniqueConstraint

from app.models import MonographDocument

from .migration_scripts import migration


def test_the_language_migration_keys_documents_by_subject_language_and_version_as_the_model_does() -> None:
    step = migration("0045_document_language")
    table = MonographDocument.__table__
    (unique,) = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    assert [column.name for column in unique.columns] == ["subjectKind", "subjectSlug", "language", "version"]
    named = "_".join([table.name, *(column.name for column in unique.columns), "key"])
    assert named == step.NEW_KEY
    assert step.OLD_KEY == "MonographDocument_subjectKind_subjectSlug_version_key"
    assert (step.revision, step.down_revision) == ("0045_document_language", "0044_contributed_origin")
    assert table.c.language.server_default.arg == step.ENGLISH == "en"
