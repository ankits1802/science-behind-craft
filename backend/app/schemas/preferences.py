from typing import Literal

from app.schemas.common import APIModel

Theme = Literal["system", "light", "dark"]


class PreferencesUpdate(APIModel):
    theme: Theme | None = None
    reducedMotion: bool | None = None
    largerText: bool | None = None
    highContrast: bool | None = None
