from __future__ import annotations

from .evaluation import GoldenQuestion

__all__ = ["GOLDEN_QUESTIONS"]

AJRAKH = "Kutch-Ajrakh"
BAGH = "Bagh-Prints-Of-Madhya-Pradesh"
BAGRU = "Bagru-Hand-Block-Print"
KALAMKARI = "Machilipatnam-Kalamkari"
SANGANERI = "Sanganeri-Hand-Block-Printing"
AKOLA = "Block-Printing-Of-Akola"

GOLDEN_QUESTIONS: tuple[GoldenQuestion, ...] = (
    GoldenQuestion(
        key="ajrakh-saran-river",
        craft_slug=AJRAKH,
        question="What dried up the river Saran in Dhamadka?",
        expected=("seed-1370e9e4530bde40d95b",),
    ),
    GoldenQuestion(
        key="ajrakh-khatri-invitation",
        craft_slug=AJRAKH,
        question="Which ruler invited Khatri printers from Sindh to Kutch?",
        expected=("seed-23c545bf0f188e4f5adf", "seed-5f782292134e07393396"),
        fields=("HISTORY",),
    ),
    GoldenQuestion(
        key="ajrakh-neerani",
        craft_slug=AJRAKH,
        question="Which ingredients go into neerani?",
        expected=("seed-afdbf6ac058a9044478c",),
    ),
    GoldenQuestion(
        key="ajrakh-madder-pink-whites",
        craft_slug=AJRAKH,
        question="Why does madder leave a pinkish tinge on the whites?",
        expected=("seed-3b388d593cdc9aa74f51",),
        fields=("CHEMISTRY",),
    ),
    GoldenQuestion(
        key="ajrakh-kut-black",
        craft_slug=AJRAKH,
        question="How does kut turn black on harde-treated cloth?",
        expected=("seed-116b395b80705f3ff151",),
    ),
    GoldenQuestion(
        key="ajrakh-iron-groundwater",
        craft_slug=AJRAKH,
        question="How much iron did testing find in the groundwater?",
        expected=("seed-ba277ff363773bd99b0f", "seed-2e4abe1e3cbe1ba67d01"),
        fields=("GEOGRAPHY",),
    ),
    GoldenQuestion(
        key="ajrakh-cool-final-wash",
        craft_slug=AJRAKH,
        question="Why is the final wash done early in the morning?",
        expected=("seed-dfa400fe0681c1f89b8f", "seed-d2f46851eca4a4174213"),
    ),
    GoldenQuestion(
        key="ajrakh-colour-meanings",
        craft_slug=AJRAKH,
        question="What do red, black, white and blue stand for in ajrakh?",
        expected=("seed-6637ffc5cdc197b6076c",),
        fields=("DESIGN",),
    ),
    GoldenQuestion(
        key="bagh-dry-river",
        craft_slug=BAGH,
        question="Where is the cloth washed when the Bagh river is dry?",
        expected=("seed-db1ae7b4b46856b5a8fa", "seed-cef358cfac297e4d01c9", "seed-e819ca3c077155f4d6ba"),
    ),
    GoldenQuestion(
        key="bagh-ismail-khatri",
        craft_slug=BAGH,
        question="When did Ismail Khatri settle in Bagh?",
        expected=("seed-38efd49a75192fd3e57a", "seed-891d196f29e98b3cf103"),
    ),
    GoldenQuestion(
        key="bagh-dhavda-flowers",
        craft_slug=BAGH,
        question="What is dhavda ka phool used for?",
        expected=("seed-0950b33057c9d3bca8bf",),
    ),
    GoldenQuestion(
        key="bagh-harda-tinge",
        craft_slug=BAGH,
        question="Why is the yellowish tinge from harda essential?",
        expected=("seed-b30c6a450530921cee7a",),
        fields=("CHEMISTRY",),
    ),
    GoldenQuestion(
        key="bagru-syahi",
        craft_slug=BAGRU,
        question="What is syahi made from?",
        expected=("seed-2b9c639651cae3c36fc7", "seed-4b5a2faf9688e0e0768b"),
    ),
    GoldenQuestion(
        key="bagru-block-names",
        craft_slug=BAGRU,
        question="What are the rekh, gadh and datta blocks?",
        expected=("seed-fe81bc7cc5d9a0f86743",),
    ),
    GoldenQuestion(
        key="bagru-indigo-dips",
        craft_slug=BAGRU,
        question="How many times can a fabric be dipped in the indigo vat?",
        expected=("seed-55a24b22dcf32d81f35c",),
    ),
    GoldenQuestion(
        key="kalamkari-iron-black",
        craft_slug=KALAMKARI,
        question="How is the black colour made from iron scraps and jaggery?",
        expected=("seed-c8b48523584b47823bb4",),
    ),
    GoldenQuestion(
        key="kalamkari-revival",
        craft_slug=KALAMKARI,
        question="Who revived kalamkari in 1952?",
        expected=("seed-c538ce2bf75942a377b0",),
    ),
    GoldenQuestion(
        key="kalamkari-chintz-names",
        craft_slug=KALAMKARI,
        question="What did the English and the Dutch call this cloth?",
        expected=("seed-eddba63971aabe884e52",),
    ),
    GoldenQuestion(
        key="sanganer-watt",
        craft_slug=SANGANERI,
        question="What did Sir George Watt call Sanganer?",
        expected=("seed-58729ccddca9fd865802",),
    ),
    GoldenQuestion(
        key="akola-motifs",
        craft_slug=AKOLA,
        question="Which four motifs survive in Akola dabu printing?",
        expected=("seed-39d2a34fc011307c70be",),
    ),
    GoldenQuestion(
        key="indigo-reducing-bacteria",
        craft_slug=None,
        question="How do bacteria turn indigo into leucoindigo?",
        expected=("seed-a16a0906bd1fa81c6de0",),
        fields=("CHEMISTRY",),
    ),
    GoldenQuestion(
        key="iron-tannate-complex",
        craft_slug=None,
        question="What complexes do ferrous ions form with tannins?",
        expected=("seed-94b38fa8e0010c0f2be6",),
        fields=("CHEMISTRY",),
    ),
)
