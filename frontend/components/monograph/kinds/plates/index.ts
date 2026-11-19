import type { ComponentViews } from "@/lib/componentViewContract";

import { AiIllustrationView } from "./AiIllustrationView";
import { AiVideoView } from "./AiVideoView";
import { AudioPlayerView } from "./AudioPlayerView";
import { ComicView } from "./ComicView";
import { CreditsView } from "./CreditsView";
import { FilmView } from "./FilmView";
import { LabelCardView } from "./LabelCardView";
import { PicturePlateView } from "./PicturePlateView";
import { SpecimenPlateView } from "./SpecimenPlateView";
import { SwatchCardsView } from "./SwatchCardsView";
import { SwatchPairView } from "./SwatchPairView";
import { VoiceView } from "./VoiceView";

export const VIEWS: ComponentViews = {
  picture_plate: PicturePlateView,
  ai_illustration: AiIllustrationView,
  specimen_plate: SpecimenPlateView,
  label_card: LabelCardView,
  swatch_cards: SwatchCardsView,
  swatch_pair: SwatchPairView,
  film: FilmView,
  ai_video: AiVideoView,
  comic: ComicView,
  audio_player: AudioPlayerView,
  voice: VoiceView,
  credits: CreditsView
};
