from typing import Literal

from app.research.vocabulary import ANSWER_LANGUAGES
from app.schemas.common import APIModel

AUTO_ANSWER_LANGUAGE = "auto"
Theme = Literal["system", "light", "dark"]
PreferredAnswerLanguage = Literal[AUTO_ANSWER_LANGUAGE, *ANSWER_LANGUAGES]


class PreferencesUpdate(APIModel):
    theme: Theme | None = None
    reducedMotion: bool | None = None
    largerText: bool | None = None
    highContrast: bool | None = None
    answerLanguage: PreferredAnswerLanguage | None = None
    alertDigest: bool | None = None
