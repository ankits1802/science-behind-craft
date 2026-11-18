from typing import Literal

from pydantic import Field

from app.models.enums import AGE_BANDS, CREDIT_MODES, GENDERS
from app.research.testimony import ARTISAN_CRAFTS_MAX, CREDIT_NAME_MAX, CREDIT_SHORT_NAME_MAX
from app.research.vocabulary import AnswerLanguage
from app.schemas.common import APIModel

__all__ = ["ArtisanCredit", "ArtisanProfileUpdate", "RecordingConsentRequest", "StudentProfileUpdate"]


class StudentProfileUpdate(APIModel):
    ageBand: Literal[*AGE_BANDS]
    gender: Literal[*GENDERS]


class ArtisanCredit(APIModel):
    mode: Literal[*CREDIT_MODES]
    name: str | None = Field(default=None, max_length=CREDIT_NAME_MAX)
    shortName: str | None = Field(default=None, max_length=CREDIT_SHORT_NAME_MAX)


class ArtisanProfileUpdate(APIModel):
    craftSlugs: list[str] = Field(min_length=1, max_length=ARTISAN_CRAFTS_MAX)
    districtLgd: int = Field(ge=1)
    spokenLanguage: AnswerLanguage
    adultConfirmed: bool
    credit: ArtisanCredit


class RecordingConsentRequest(APIModel):
    noticeVersion: str = Field(min_length=1, max_length=40)
    language: AnswerLanguage
