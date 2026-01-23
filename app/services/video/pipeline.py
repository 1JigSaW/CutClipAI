import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.core.logger import get_logger
from app.services.video.assemblyai_subtitles import AssemblyAISubtitlesService
from app.services.video.assemblyai_transcription import AssemblyAITranscriptionService
from app.services.video.clipping import ClippingService
from app.services.video.flow_integration import FlowIntegrationService
from app.services.video.llm_analysis import LLMAnalysisService
from app.utils.video.files import create_temp_dir

logger = get_logger(__name__)


class VideoPipeline:
    def __init__(
        self,
        assemblyai_service: Optional[AssemblyAITranscriptionService] = None,
        llm_analysis_service: Optional[LLMAnalysisService] = None,
        flow_service: Optional[FlowIntegrationService] = None,
        clipping_service: Optional[ClippingService] = None,
    ):
        self.assemblyai_service = assemblyai_service or AssemblyAITranscriptionService()
        self.llm_analysis_service = llm_analysis_service or LLMAnalysisService()
        self.flow_service = flow_service or FlowIntegrationService()
        
        logger.info(
            f"VideoPipeline initialized | "
            f"assemblyai_enabled=True | "
            f"llm_enabled={self.llm_analysis_service.enabled} | "
            f"flow_enabled={self.flow_service.enabled}"
        )

        self.clipping_service = clipping_service or ClippingService()
        self.assemblyai_subtitles_service = AssemblyAISubtitlesService()

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

        logger.info(
            f"Extracted {len(segments)} segments from video | file_path={file_path}",
        )

        logger.error(
            "Old process() method is deprecated. Use process_optimized() instead. "
            "Scoring service has been removed - only LLM analysis is supported."
        )
        raise NotImplementedError(
            "Scoring service removed. Use process_optimized() with LLM analysis only."
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

    async def process_optimized_async(
        self,
        file_path: str,
        user_id: Optional[int] = None,
    ) -> list[str]:
        """
        Optimized async pipeline using AssemblyAI + Pydantic AI + Flow.
        Based on supoclip/backend structure.

        Args:
            file_path: Path to input video file
            user_id: Optional user ID for Flow integration

        Returns:
            List of paths to generated clip files
        """
        logger.info(
            f"Starting optimized async video pipeline | file_path={file_path}",
        )

        trim_start = time.time()
        trimmed_path = self.clipping_service.trim_to_max_duration(
            file_path=file_path,
        )
        trim_time = time.time() - trim_start

        logger.info(
            f"Video trimmed | trimmed_path={trimmed_path} | time={trim_time:.1f}s",
        )

        if self.flow_service.enabled and user_id is not None:
            flow_task_id = await self.flow_service.upload_video_to_flow(
                video_path=str(trimmed_path),
                user_id=user_id,
            )
            if flow_task_id:
                logger.info(f"Video uploaded to Flow | flow_task_id={flow_task_id}")

        transcription_start = time.time()
        
        # Ensure trimmed_path is a Path object for easier manipulation
        trimmed_path_obj = Path(trimmed_path)
        
        # We no longer pre-crop the entire video here as it's too slow and heavy.
        # Instead, we will do crop + cut + subtitles in one pass using FFmpeg for each clip.
        
        logger.info(
            f"Starting AssemblyAI transcription | video_path={trimmed_path}",
        )

        transcription_result = self.assemblyai_service.transcribe(
            video_path=trimmed_path,
            use_cache=True,
        )
        
        transcription_time = time.time() - transcription_start
        segments_count = len(transcription_result.get("segments", []))

        logger.info(
            f"AssemblyAI transcription completed | "
            f"segments_count={segments_count} | time={transcription_time:.1f}s",
        )

        segments = transcription_result.get("segments", [])
        # Calculate total duration from last segment end time
        if segments:
            total_duration = max(seg.get("end", 0.0) for seg in segments)
        else:
            total_duration = 0.0

        llm_analysis_start = time.time()
        
        logger.info(
            f"Starting LLM analysis | "
            f"llm_enabled={self.llm_analysis_service.enabled} | "
            f"client={self.llm_analysis_service.client is not None} | "
            f"segments_count={len(segments)} | "
            f"total_duration={total_duration:.1f}s"
        )
        
        # LLMAnalysisService.analyze_transcription is synchronous, not async
        llm_analysis = self.llm_analysis_service.analyze_transcription(
            segments=segments,
            total_duration=total_duration,
        )
        
        llm_analysis_time = time.time() - llm_analysis_start
        
        logger.info(
            f"LLM analysis result | "
            f"result={llm_analysis is not None} | "
            f"has_best_moments={llm_analysis.get('best_moments') if llm_analysis else False} | "
            f"time={llm_analysis_time:.1f}s"
        )

        if llm_analysis and llm_analysis.get("best_moments"):
            best_moments_list = llm_analysis.get("best_moments", [])
            
            # Log what we got
            current_max_clips = settings.MAX_CLIPS_COUNT
            logger.info(f"LLM returned {len(best_moments_list)} moments. Max allowed by config: {current_max_clips}")

            # Truncate to MAX_CLIPS_COUNT if LLM returned more
            if len(best_moments_list) > current_max_clips:
                logger.info(
                    f"Truncating {len(best_moments_list)} moments to {current_max_clips}"
                )
                best_moments_list = best_moments_list[:current_max_clips]

            logger.info(
                f"LLM analysis completed | "
                f"segments_found={len(best_moments_list)} | "
                f"time={llm_analysis_time:.1f}s"
            )

            best_moments = []
            for moment in best_moments_list:
                best_moments.append({
                    "start": float(moment.get("start", 0)),
                    "end": float(moment.get("end", 0)),
                    "text": moment.get("reason", ""),  # Use reason as text description
                    "score": float(moment.get("score", 0)),
                    "reasoning": moment.get("reason", ""),
                })
            
            logger.info(f"Final best_moments list for processing: {best_moments}")
        else:
            logger.error(
                f"LLM analysis failed or not available | "
                f"time={llm_analysis_time:.1f}s | "
                f"Video processing cannot continue without LLM analysis"
            )
            raise ValueError(
                "LLM analysis is required but failed. "
                "Please check LLM configuration and API keys."
            )

        def process_single_clip(
            idx: int,
            moment: dict[str, Any],
        ) -> tuple[int, str]:
            clip_duration = moment['end'] - moment['start']
            max_duration = settings.CLIP_MAX_DURATION_SECONDS
            min_duration = settings.CLIP_MIN_DURATION_SECONDS
            
            if clip_duration > max_duration:
                logger.error(
                    f"Clip {idx} duration ({clip_duration:.1f}s) exceeds max ({max_duration}s). "
                    f"Clip range: {moment['start']:.2f}s - {moment['end']:.2f}s. "
                    f"Skipping this clip."
                )
                return None, None
            
            if clip_duration < min_duration:
                if clip_duration >= min_duration - 5.0:
                    logger.info(
                        f"Clip {idx} duration ({clip_duration:.1f}s) is below minimum ({min_duration}s), "
                        f"but within increased tolerance. Processing anyway."
                    )
                else:
                    logger.error(
                        f"Clip {idx} duration ({clip_duration:.1f}s) is too short. "
                        f"Skipping this clip."
                    )
                    return None, None
            
            logger.info(
                f"🎬 Processing clip {idx}/{len(best_moments)} | "
                f"start={moment['start']:.2f}s | end={moment['end']:.2f}s | "
                f"duration={clip_duration:.2f}s",
            )

            output_dir = create_temp_dir()
            final_clip_path = output_dir / f"final_clip_{idx}.mp4"
            
            try:
                from app.services.video.moviepy_subtitles import create_optimized_clip
                
                logger.info(
                    f"📝 Clip {idx} | Processing with MoviePy | "
                    f"trimmed_video={Path(trimmed_path).name} | "
                    f"clip_time={moment['start']:.2f}s-{moment['end']:.2f}s"
                )
                
                success = create_optimized_clip(
                    video_path=Path(trimmed_path),
                    start_time=moment["start"],
                    end_time=moment["end"],
                    output_path=final_clip_path,
                    add_subtitles=True,
                    font_family="Arial",
                    font_size=25,
                    font_color="#FFFF00"
                )
                
                if success and final_clip_path.exists():
                    file_size = final_clip_path.stat().st_size
                    logger.info(
                        f"✅ Clip {idx} processed successfully | "
                        f"size={file_size / (1024 * 1024):.2f}MB | "
                        f"subtitles=yes"
                    )
                    return idx, str(final_clip_path)
                else:
                    logger.error(
                        f"❌ Clip {idx} processing failed | "
                        f"success={success} | exists={final_clip_path.exists()}"
                    )
                    return None, None
                    
            except Exception as e:
                logger.error(
                    f"Failed to process clip {idx} | error={e}",
                    exc_info=True,
                )
                return None, None

        clip_paths_dict = {}
        max_workers = min(
            len(best_moments),
            settings.CLIP_PROCESSING_MAX_WORKERS,
        )
        
        logger.info(
            f"Processing {len(best_moments)} clips in parallel | "
            f"max_workers={max_workers} | best_moments_count={len(best_moments)}"
        )

        clips_start = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_clip = {
                executor.submit(
                    process_single_clip,
                    idx=idx,
                    moment=moment,
                ): (idx, moment)
                for idx, moment in enumerate(best_moments, 1)
            }

            for future in as_completed(future_to_clip):
                idx, moment = future_to_clip[future]
                try:
                    clip_idx, clip_path = future.result()
                    if clip_idx is not None and clip_path is not None:
                        clip_paths_dict[clip_idx] = clip_path
                        logger.info(f"Clip {clip_idx} processed successfully: {clip_path}")
                    else:
                        logger.warning(
                            f"Clip {idx} was skipped (returned None) | "
                            f"start={moment['start']:.2f}s | end={moment['end']:.2f}s"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to process clip {idx} | "
                        f"start={moment['start']:.2f}s | end={moment['end']:.2f}s | "
                        f"error={e}",
                        exc_info=True
                    )

        clips_time = time.time() - clips_start
        clip_paths = [clip_paths_dict[i] for i in sorted(clip_paths_dict.keys())]

        total_time = time.time() - trim_start

        logger.info(
            f"Optimized pipeline completed | clips_count={len(clip_paths)} | "
            f"total_time={total_time:.1f}s ({total_time/60:.1f}min) | "
            f"clip_paths={clip_paths}"
        )

        return clip_paths

    def process_optimized(
        self,
        file_path: str,
        user_id: Optional[int] = None,
    ) -> list[str]:
        """
        Synchronous wrapper for async pipeline.
        Maintains backward compatibility.

        Args:
            file_path: Path to input video file
            user_id: Optional user ID for Flow integration

        Returns:
            List of paths to generated clip files
        """
        return asyncio.run(self.process_optimized_async(file_path, user_id))

