from app.research.composition import FOLLOW_UPS_MAX
from app.services.answer_lede import Opening
from app.services.follow_ups import LEFT_OPEN_QUESTIONS, left_open_follow_ups

INDIGO = "How does indigo turn blue on Kutch Ajrakh cloth?"
WATER = "How does the water of Kachchh shape Kutch Ajrakh?"


def test_the_answer_s_own_open_questions_lead_and_the_question_itself_never_returns() -> None:
    offered = [
        "Why do the darkest blues need more dips?",
        INDIGO.upper(),
        "why do the darkest blues need more dips",
    ]
    assert left_open_follow_ups((INDIGO,), offered, [], "Kutch Ajrakh") == [
        "Why do the darkest blues need more dips?"
    ]


def test_fields_the_question_touched_but_the_answer_did_not_show_are_offered_after() -> None:
    indigo = left_open_follow_ups(
        (INDIGO,), ["What feeds the bacteria in the naand?"], ["HISTORY"], "Kutch Ajrakh"
    )
    water = left_open_follow_ups((WATER,), [], ["CLIMATE", "ECOLOGY"], "Kutch Ajrakh")
    assert indigo == ["What feeds the bacteria in the naand?", "Where does Kutch Ajrakh come from?"]
    assert water == [
        "How does the weather shape Kutch Ajrakh?",
        "What does Kutch Ajrakh take from its surroundings?",
    ]
    assert indigo != water


def test_an_answer_for_any_craft_offers_only_its_own_open_questions_and_at_most_five() -> None:
    offered = [f"Open question {n}?" for n in range(8)]
    assert left_open_follow_ups((INDIGO,), offered, ["HISTORY"], None) == offered[:FOLLOW_UPS_MAX]
    assert set(LEFT_OPEN_QUESTIONS) == {
        "OVERVIEW",
        "PROCESS",
        "CHEMISTRY",
        "PHYSICS",
        "MATERIALS",
        "GEOGRAPHY",
        "GEOLOGY",
        "CLIMATE",
        "ECOLOGY",
        "BOTANY",
        "HISTORY",
        "ECONOMICS",
        "DESIGN",
        "HEALTH",
        "SOCIETY",
        "POLICY",
    }


def test_an_echo_of_the_english_rendering_of_a_hindi_question_never_returns() -> None:
    hindi = "अजरख को फिटकरी लाल क्यों रखती है?"
    english = "Why does alum keep Ajrakh red?"
    asked = Opening(english=english).asked(hindi)
    assert asked == (hindi, english)
    offered = ["Why does alum keep Ajrakh red", "What feeds the bacteria in the naand?"]
    assert left_open_follow_ups(asked, offered, [], "Kutch Ajrakh") == [
        "What feeds the bacteria in the naand?"
    ]
    assert Opening().asked(INDIGO) == (INDIGO,)
