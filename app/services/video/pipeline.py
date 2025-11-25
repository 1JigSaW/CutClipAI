from pathlib import Path
from typing import Optional

from app.services.video.clipping import ClippingService
from app.services.video.scoring import ScoringService
from app.services.video.subtitles import SubtitlesService
from app.services.video.whisper import WhisperService


class VideoPipeline:
    def __init__(
        self,
        whisper_service: Optional[WhisperService] = None,
        scoring_service: Optional[ScoringService] = None,
        clipping_service: Optional[ClippingService] = None,
        subtitles_service: Optional[SubtitlesService] = None,
    ):
        self.whisper_service = whisper_service or WhisperService()
        self.scoring_service = scoring_service or ScoringService()
        self.clipping_service = clipping_service or ClippingService()
        self.subtitles_service = subtitles_service or SubtitlesService()

    def process(
        self,
        file_path: str,
    ) -> list[str]:
        """
        Run full pipeline: trim → whisper → scoring → clipping → subtitles.

        Args:
            file_path: Path to input video file

        Returns:
            List of paths to generated clip files
        """
        trimmed_path = self.clipping_service.trim_to_max_duration(
            file_path=file_path,
        )

        segments = self.whisper_service.extract_segments(
            video_path=trimmed_path,
        )

        best_moments = self.scoring_service.select_best_moments(
            segments=segments,
        )

        clip_paths = []
        for moment in best_moments:
            clip_path = self.clipping_service.cut_clip(
                video_path=trimmed_path,
                start_time=moment["start"],
                end_time=moment["end"],
            )

            cropped_clip_path = self.clipping_service.crop_9_16(
                input_path=clip_path,
            )

            srt_path = self.subtitles_service.generate_srt(
                video_path=cropped_clip_path,
            )

            final_clip_path = self.subtitles_service.burn_subtitles(
                video_path=cropped_clip_path,
                srt_path=srt_path,
            )

            clip_paths.append(final_clip_path)

        return clip_paths

