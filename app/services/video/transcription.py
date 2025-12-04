from typing import Any, Optional

from app.core.logger import get_logger

logger = get_logger(__name__)


class TranscriptionCache:
    
    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}
    
    def set(
        self,
        video_path: str,
        transcription_result: dict[str, Any],
    ) -> None:
        self._cache[video_path] = transcription_result
        segments_count = len(transcription_result.get("segments", []))
        logger.debug(
            f"Cached transcription result | video_path={video_path} | "
            f"segments_count={segments_count}",
        )
    
    def get(
        self,
        video_path: str,
    ) -> Optional[dict[str, Any]]:
        result = self._cache.get(video_path)
        if result:
            segments_count = len(result.get("segments", []))
            logger.debug(
                f"Retrieved cached transcription | video_path={video_path} | "
                f"segments_count={segments_count}",
            )
        return result
    
    def clear(
        self,
        video_path: Optional[str] = None,
    ) -> None:
        if video_path:
            if video_path in self._cache:
                del self._cache[video_path]
                logger.debug(f"Cleared cache for video | video_path={video_path}")
        else:
            self._cache.clear()
            logger.debug("Cleared all transcription cache")


_global_cache = TranscriptionCache()


def get_transcription_cache() -> TranscriptionCache:
    return _global_cache

