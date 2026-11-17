from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

__all__ = ["LESSON_WORDS", "LessonWords", "lesson_words"]


@dataclass(frozen=True)
class LessonWords:
    question: str
    reading: str
    sources: str
    answers: str

    def question_title(self, number: int) -> str:
        return f"{self.question} {number}"


LESSON_WORDS: Mapping[str, LessonWords] = MappingProxyType(
    {
        "en": LessonWords("Question", "Reading list", "Sources", "Answers"),
        "hi": LessonWords("प्रश्न", "पठन सूची", "स्रोत", "उत्तर"),
        "bn": LessonWords("প্রশ্ন", "পাঠ্য তালিকা", "সূত্র", "উত্তর"),
        "ta": LessonWords("கேள்வி", "வாசிப்புப் பட்டியல்", "ஆதாரங்கள்", "விடைகள்"),
        "te": LessonWords("ప్రశ్న", "పఠన జాబితా", "మూలాలు", "సమాధానాలు"),
        "mr": LessonWords("प्रश्न", "वाचन सूची", "स्रोत", "उत्तरे"),
        "gu": LessonWords("પ્રશ્ન", "વાંચન યાદી", "સ્રોતો", "જવાબો"),
        "kn": LessonWords("ಪ್ರಶ್ನೆ", "ಓದುವ ಪಟ್ಟಿ", "ಮೂಲಗಳು", "ಉತ್ತರಗಳು"),
        "ml": LessonWords("ചോദ്യം", "വായനാ പട്ടിക", "സ്രോതസ്സുകൾ", "ഉത്തരങ്ങൾ"),
        "or": LessonWords("ପ୍ରଶ୍ନ", "ପଠନ ତାଲିକା", "ଉତ୍ସ", "ଉତ୍ତର"),
        "pa": LessonWords("ਪ੍ਰਸ਼ਨ", "ਪੜ੍ਹਨ ਸੂਚੀ", "ਸਰੋਤ", "ਉੱਤਰ"),
        "as": LessonWords("প্ৰশ্ন", "পঠন তালিকা", "উৎস", "উত্তৰ"),
        "ur": LessonWords("سوال", "مطالعے کی فہرست", "مآخذ", "جوابات"),
    }
)


def lesson_words(language: str) -> LessonWords:
    words = LESSON_WORDS.get(language)
    if words is None:
        raise ValueError(f"no lesson words for language {language!r}")
    return words
