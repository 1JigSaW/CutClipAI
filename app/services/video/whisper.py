from pathlib import Path
from typing import Any, Optional

import torch
import whisper

from app.core.config import settings
from app.core.logger import get_logger
from app.services.video.transcription import get_transcription_cache

logger = get_logger(__name__)


class WhisperService:
    def __init__(
        self,
        model_name: str = settings.WHISPER_MODEL,
        model: Optional[Any] = None,
    ):
        self._detect_device()
        
        if model is not None:
            logger.debug(f"Using provided Whisper model | model_name={model_name}")
            self.model = model
        else:
            logger.info(f"Loading Whisper model | model_name={model_name} | device={self.device}")
            self.model = whisper.load_model(
                name=model_name,
                device=self.device,
            )
            logger.info(
                f"Whisper model loaded successfully | "
                f"model_name={model_name} | device={self.device} | "
                f"gpu_available={self.gpu_available}",
            )
        
        self.cache = get_transcription_cache()
    
    def _detect_device(self) -> None:
        if settings.FORCE_CPU:
            self.gpu_available = False
            self.device = "cpu"
            logger.info(
                f"💻 Forced CPU mode (FORCE_CPU=True) | device={self.device}",
            )
            return
        
        self.gpu_available = torch.cuda.is_available()
        
        if self.gpu_available:
            self.device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(
                f"🚀 GPU detected and enabled | name={gpu_name} | "
                f"memory={gpu_memory:.1f}GB | device={self.device}",
            )
        else:
            self.device = "cpu"
            logger.info(
                f"💻 No GPU detected, using CPU | device={self.device}",
            )

    def transcribe_full(
        self,
        video_path: str,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        Transcribe full video with word timestamps.
        Results are cached to avoid repeated transcription.

        Args:
            video_path: Path to video file
            use_cache: Whether to use cached results if available

        Returns:
            Full Whisper transcription result with segments and word timestamps
        """
        if use_cache:
            cached_result = self.cache.get(video_path=video_path)
            if cached_result is not None:
                logger.info(
                    f"Using cached transcription | video_path={video_path}",
                )
                return cached_result

        logger.info(
            f"Starting full transcription with word timestamps | video_path={video_path}",
        )

        result = self.model.transcribe(
            audio=video_path,
            verbose=False,
            word_timestamps=True,
        )

        segments_count = len(result.get("segments", []))
        logger.info(
            f"Transcription completed | video_path={video_path} | "
            f"segments_count={segments_count}",
        )

        if use_cache:
            self.cache.set(
                video_path=video_path,
                transcription_result=result,
            )

        return result

    def extract_segments(
        self,
        video_path: str,
    ) -> list[dict[str, Any]]:
        """
        Extract transcription segments from video.
        Uses cached full transcription if available.

        Args:
            video_path: Path to video file

        Returns:
            List of segments with start, end, and text
        """
        result = self.transcribe_full(
            video_path=video_path,
            use_cache=True,
        )

        segments = []
        for segment in result.get("segments", []):
            segment_data = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
            
            if "words" in segment:
                segment_data["words"] = segment["words"]
            
            segments.append(segment_data)

        return segments

