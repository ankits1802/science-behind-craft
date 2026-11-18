from app.composer.candidates import compose_request
from app.composer.composer import ModelComposer, lede_form, reply_form
from app.composer.prompt import LEDE_SYSTEM_PROMPT, REGENERATE_SYSTEM_PROMPT, compose_message, lede_message
from app.research.composition import ComposeFocus
from app.research.reading_style import style_paragraph

from ..planner.fakes import FakeModel
from .fixtures import QUESTION, pack, replacements
from .test_lede_compose import ALUM, HARDE, UNQUOTED, lede_reply, request


def focused(style: str | None):
    focus = ComposeFocus(discipline="PROCESS", title="How it is made")
    return compose_request(pack(), QUESTION, focus=focus, style=style)


def test_a_styled_section_request_differs_only_by_the_paragraph() -> None:
    plain, young = focused(None), focused("CHILD")
    assert plain.candidates == young.candidates and plain.focus == young.focus
    assert compose_message(plain) == compose_message(young)
    plain_form, young_form = reply_form(plain), reply_form(young)
    assert plain_form.schema == young_form.schema
    assert young_form.system == f"{plain_form.system}\n\n{style_paragraph('CHILD')}"


def test_a_styled_lede_differs_only_by_the_paragraph() -> None:
    plain, teen = request(), request().model_copy(update={"style": "TEEN"})
    assert lede_message(plain) == lede_message(teen)
    assert lede_form(plain).schema == lede_form(teen).schema
    assert lede_form(plain).system == LEDE_SYSTEM_PROMPT
    assert lede_form(teen).system == f"{LEDE_SYSTEM_PROMPT}\n\n{style_paragraph('TEEN')}"


async def test_the_regenerate_keeps_the_readers_register() -> None:
    model = FakeModel([lede_reply(ALUM, UNQUOTED), replacements((0, HARDE))])
    styled_request = request().model_copy(update={"style": "UNDERGRADUATE"})
    await ModelComposer(model=model).lede(styled_request)
    paragraph = style_paragraph("UNDERGRADUATE")
    assert [call["system"] for call in model.calls] == [
        f"{LEDE_SYSTEM_PROMPT}\n\n{paragraph}",
        f"{REGENERATE_SYSTEM_PROMPT}\n\n{paragraph}",
    ]
    assert "Failed sentence 0: UNCITED" in model.calls[1]["user"]
