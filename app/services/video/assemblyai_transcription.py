"""
AssemblyAI transcription service.
Replaces Whisper with AssemblyAI API for better accuracy and word-level timing.
Based on supoclip/backend structure.
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import assemblyai as aai
from moviepy import VideoFileClip

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class AssemblyAITranscriptionService:
    """
    Service for transcribing videos using AssemblyAI API.
    Supports large files by splitting into chunks.
    """

    def __init__(self):
        if not settings.ASSEMBLY_AI_API_KEY:
            raise ValueError("ASSEMBLY_AI_API_KEY not set in configuration")
        
        aai.settings.api_key = settings.ASSEMBLY_AI_API_KEY
        self.transcriber = aai.Transcriber()
        self.max_file_size_mb = 2000.0
        
        logger.info("AssemblyAI transcription service initialized")

    def transcribe(
        self,
        video_path: str | Path,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Transcribe video using AssemblyAI.

        Args:
            video_path: Path to video file
            use_cache: Whether to use cached transcript if available

        Returns:
            Dictionary with transcription result containing:
            - segments: List of segments with text and timestamps
            - words: List of words with precise timing (for subtitles)
            - text: Full transcript text
        """
        if isinstance(video_path, str):
            video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(f"Starting AssemblyAI transcription | video_path={video_path}")

        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        logger.info(f"Video file size: {file_size_mb:.2f} MB")

        cache_path = video_path.with_suffix('.assemblyai_cache.json')
        
        if use_cache and cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    cached_data = json.load(f)
                    logger.info(f"Using cached transcription | cache_path={cache_path}")
                    return cached_data
            except Exception as e:
                logger.warning(f"Failed to load cache, will transcribe | error={e}")

        config_obj = aai.TranscriptionConfig(
            speaker_labels=False,
            punctuate=True,
            format_text=True,
            speech_model=aai.SpeechModel.best,
            language_detection=True  # Enable automatic language detection (supports multiple languages including Russian)
        )

        if file_size_mb > self.max_file_size_mb:
            logger.info(
                f"Large file detected ({file_size_mb:.2f} MB > {self.max_file_size_mb} MB). "
                f"Splitting into chunks..."
            )
            result = self._transcribe_large_file(
                video_path=video_path,
                config=config_obj
            )
        else:
            result = self._transcribe_single_file(
                video_path=video_path,
                config=config_obj
            )

        if use_cache:
            try:
                with open(cache_path, 'w') as f:
                    json.dump(result, f, indent=2)
                cache_size = cache_path.stat().st_size
                words_count = len(result.get('words', []))
                logger.info(
                    f"✅ Cached transcription result | "
                    f"cache_path={cache_path} | "
                    f"cache_size={cache_size} bytes | "
                    f"words_count={words_count} | "
                    f"file_exists={cache_path.exists()}"
                )
            except Exception as e:
                logger.error(
                    f"❌ Failed to cache transcription | "
                    f"cache_path={cache_path} | error={e}",
                    exc_info=True
                )

        return result

    def _transcribe_single_file(
        self,
        video_path: Path,
        config: aai.TranscriptionConfig,
    ) -> Dict[str, Any]:
        """Transcribe a single video file."""
        max_retries = 3
        retry_delay = 5

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Starting AssemblyAI transcription | "
                    f"attempt={attempt}/{max_retries} | video_path={video_path}"
                )

                transcript = self.transcriber.transcribe(str(video_path), config=config)

                if transcript.status == aai.TranscriptStatus.error:
                    error_msg = f"AssemblyAI transcription failed: {transcript.error}"
                    logger.error(error_msg)

                    if attempt < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue

                    raise Exception(error_msg)

                return self._format_transcript_result(transcript, offset=0.0)

            except Exception as e:
                error_str = str(e)
                logger.error(
                    f"AssemblyAI error (attempt {attempt}/{max_retries}): {error_str}"
                )

                if "502" in error_str or "Bad Gateway" in error_str:
                    if attempt < max_retries:
                        logger.warning(
                            f"502 Bad Gateway error. Retrying in {retry_delay} seconds..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        file_size_mb = video_path.stat().st_size / (1024 * 1024)
                        raise Exception(
                            f"AssemblyAI service unavailable (502 Bad Gateway). "
                            f"File size: {file_size_mb:.2f} MB. "
                            f"Please try again later or use a smaller video file."
                        )

                if attempt == max_retries:
                    raise Exception(
                        f"Failed to transcribe video after {max_retries} attempts: {error_str}"
                    )

                time.sleep(retry_delay)
                retry_delay *= 2

        raise Exception("Failed to transcribe video after all retry attempts")

    def _transcribe_large_file(
        self,
        video_path: Path,
        config: aai.TranscriptionConfig,
    ) -> Dict[str, Any]:
        """Transcribe large file by splitting into chunks."""
        chunks = self._split_video_into_chunks(
            video_path=video_path,
            max_chunk_size_mb=self.max_file_size_mb
        )

        chunk_transcripts = []
        chunks_to_cleanup = []

        try:
            for i, chunk_info in enumerate(chunks):
                chunk_path = chunk_info['path']
                offset = chunk_info['offset']

                if not chunk_info.get('is_original', False):
                    chunks_to_cleanup.append(chunk_path)

                logger.info(
                    f"Transcribing chunk {i+1}/{len(chunks)} | "
                    f"chunk_path={chunk_path.name} | offset={offset:.1f}s"
                )

                max_retries = 3
                retry_delay = 5
                chunk_transcript = None

                for attempt in range(1, max_retries + 1):
                    try:
                        chunk_transcript = self.transcriber.transcribe(
                            str(chunk_path),
                            config=config
                        )

                        if chunk_transcript.status == aai.TranscriptStatus.error:
                            error_msg = (
                                f"AssemblyAI transcription failed for chunk {i+1}: "
                                f"{chunk_transcript.error}"
                            )
                            logger.error(error_msg)

                            if attempt < max_retries:
                                logger.info(
                                    f"Retrying chunk {i+1} in {retry_delay} seconds..."
                                )
                                time.sleep(retry_delay)
                                retry_delay *= 2
                                continue

                            raise Exception(error_msg)

                        break

                    except Exception as e:
                        error_str = str(e)
                        logger.error(
                            f"AssemblyAI error for chunk {i+1} "
                            f"(attempt {attempt}/{max_retries}): {error_str}"
                        )

                        if "502" in error_str or "Bad Gateway" in error_str:
                            if attempt < max_retries:
                                logger.warning(
                                    f"502 Bad Gateway for chunk {i+1}. "
                                    f"Retrying in {retry_delay} seconds..."
                                )
                                time.sleep(retry_delay)
                                retry_delay *= 2
                                continue
                            else:
                                raise Exception(
                                    f"AssemblyAI service unavailable for chunk {i+1}. "
                                    f"File may still be too large after splitting."
                                )

                        if attempt == max_retries:
                            raise Exception(
                                f"Failed to transcribe chunk {i+1} "
                                f"after {max_retries} attempts: {error_str}"
                            )

                        time.sleep(retry_delay)
                        retry_delay *= 2

                if chunk_transcript is None:
                    raise Exception(f"Failed to get transcript for chunk {i+1}")

                words_list = chunk_transcript.words if chunk_transcript.words else []
                chunk_transcripts.append({
                    'transcript': chunk_transcript,
                    'offset': offset,
                    'words': words_list
                })

                logger.info(
                    f"Chunk {i+1}/{len(chunks)} transcribed successfully | "
                    f"words={len(words_list)}"
                )

            return self._merge_chunk_transcripts(chunk_transcripts)

        finally:
            for chunk_path in chunks_to_cleanup:
                try:
                    if chunk_path.exists():
                        chunk_path.unlink()
                        logger.info(f"Cleaned up chunk | chunk_path={chunk_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup chunk {chunk_path}: {e}")

            chunk_dir = video_path.parent / f"{video_path.stem}_chunks"
            if chunk_dir.exists() and chunk_dir.is_dir():
                try:
                    if not any(chunk_dir.iterdir()):
                        chunk_dir.rmdir()
                        logger.info(f"Cleaned up chunk directory | dir={chunk_dir}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup chunk directory {chunk_dir}: {e}"
                    )

    def _split_video_into_chunks(
        self,
        video_path: Path,
        max_chunk_size_mb: float,
    ) -> List[Dict[str, Any]]:
        """
        Split large video file into smaller chunks for processing.

        Args:
            video_path: Path to the video file
            max_chunk_size_mb: Maximum size of each chunk in MB

        Returns:
            List of dictionaries with chunk info
        """
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        logger.info(f"Splitting video | file_size={file_size_mb:.2f} MB")

        video = VideoFileClip(str(video_path))
        total_duration = video.duration
        video.close()

        chunks = []
        chunk_dir = video_path.parent / f"{video_path.stem}_chunks"
        chunk_dir.mkdir(exist_ok=True)

        bytes_per_second = (file_size_mb * 1024 * 1024) / total_duration
        target_bytes_per_chunk = max_chunk_size_mb * 1024 * 1024
        safety_factor = 0.85

        if file_size_mb <= max_chunk_size_mb:
            logger.info("Video is small enough, no splitting needed")
            return [{
                'path': video_path,
                'start_time': 0.0,
                'end_time': total_duration,
                'duration': total_duration,
                'offset': 0.0,
                'is_original': True
            }]

        chunk_index = 0
        current_start = 0.0

        while current_start < total_duration:
            remaining_duration = total_duration - current_start
            remaining_size_mb = (remaining_duration * bytes_per_second) / (1024 * 1024)

            if remaining_size_mb <= max_chunk_size_mb:
                current_end = total_duration
            else:
                target_duration = (target_bytes_per_chunk * safety_factor) / bytes_per_second
                current_end = current_start + target_duration
                current_end = min(current_end, total_duration)

            chunk_path = chunk_dir / f"chunk_{chunk_index:03d}.mp4"

            logger.info(
                f"Creating chunk {chunk_index} | "
                f"start={current_start:.1f}s | end={current_end:.1f}s | "
                f"target_size=<={max_chunk_size_mb} MB"
            )

            try:
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-ss', str(current_start),
                    '-t', str(current_end - current_start),
                    '-c', 'copy',
                    '-avoid_negative_ts', 'make_zero',
                    '-y',
                    str(chunk_path)
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg error: {result.stderr}")
                    raise Exception(f"Failed to create chunk {chunk_index}: {result.stderr}")

                chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
                logger.info(f"Chunk {chunk_index} created | size={chunk_size_mb:.2f} MB")

                if chunk_size_mb > max_chunk_size_mb:
                    logger.warning(
                        f"Chunk {chunk_index} is too large "
                        f"({chunk_size_mb:.2f} MB > {max_chunk_size_mb} MB). "
                        f"Removing and stopping."
                    )
                    chunk_path.unlink()
                    break

                chunks.append({
                    'path': chunk_path,
                    'start_time': 0.0,
                    'end_time': current_end - current_start,
                    'duration': current_end - current_start,
                    'offset': current_start,
                    'is_original': False
                })

                chunk_index += 1
                current_start = current_end

            except subprocess.TimeoutExpired:
                logger.error(f"Timeout creating chunk {chunk_index}")
                raise Exception(f"Timeout splitting video chunk {chunk_index}")
            except Exception as e:
                logger.error(f"Error creating chunk {chunk_index}: {e}")
                raise

        logger.info(f"Video split into {len(chunks)} chunks")
        return chunks

    def _merge_chunk_transcripts(
        self,
        chunk_transcripts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Merge transcripts from multiple video chunks with correct timing offsets."""
        all_words = []

        for chunk_data in chunk_transcripts:
            offset_ms = chunk_data['offset'] * 1000
            words = chunk_data['words']

            for word in words:
                adjusted_word = {
                    'text': word.text,
                    'start': word.start + offset_ms,
                    'end': word.end + offset_ms,
                    'confidence': getattr(word, 'confidence', 1.0)
                }
                all_words.append(adjusted_word)

        all_words.sort(key=lambda w: w['start'])

        all_segments = []
        for chunk_data in chunk_transcripts:
            offset = chunk_data['offset']
            transcript = chunk_data['transcript']

            if hasattr(transcript, 'utterances') and transcript.utterances:
                for utterance in transcript.utterances:
                    all_segments.append({
                        'start': utterance.start / 1000.0 + offset,
                        'end': utterance.end / 1000.0 + offset,
                        'text': utterance.text
                    })
            elif hasattr(transcript, 'segments') and transcript.segments:
                for segment in transcript.segments:
                    all_segments.append({
                        'start': segment.start / 1000.0 + offset,
                        'end': segment.end / 1000.0 + offset,
                        'text': segment.text
                    })

        full_text = ' '.join([seg['text'] for seg in all_segments])

        return {
            'segments': all_segments,
            'words': all_words,
            'text': full_text
        }

    def _format_transcript_result(
        self,
        transcript: Any,
        offset: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Format AssemblyAI transcript result into standard format.

        Args:
            transcript: AssemblyAI transcript object
            offset: Time offset in seconds (for merged chunks)

        Returns:
            Formatted transcript dictionary
        """
        segments = []
        words = []

        if transcript.words:
            for word in transcript.words:
                words.append({
                    'text': word.text,
                    'start': (word.start / 1000.0) + offset,
                    'end': (word.end / 1000.0) + offset,
                    'confidence': getattr(word, 'confidence', 1.0)
                })

        if hasattr(transcript, 'segments') and transcript.segments:
            for segment in transcript.segments:
                segments.append({
                    'start': (segment.start / 1000.0) + offset,
                    'end': (segment.end / 1000.0) + offset,
                    'text': segment.text
                })
        elif transcript.text:
            if words:
                first_word_start = words[0]['start']
                last_word_end = words[-1]['end']
                segments.append({
                    'start': first_word_start,
                    'end': last_word_end,
                    'text': transcript.text
                })
            else:
                segments.append({
                    'start': 0.0,
                    'end': 0.0,
                    'text': transcript.text
                })

        return {
            'segments': segments,
            'words': words,
            'text': transcript.text or ''
        }

