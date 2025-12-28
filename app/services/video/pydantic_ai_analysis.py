"""
LLM analysis service using Pydantic AI (like supoclip).
Provides structured analysis of video transcripts to find best moments.
"""

import logging
from typing import Any, List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class TranscriptSegment(BaseModel):
    """Represents a relevant segment of transcript with precise timing."""
    start_time: str = Field(description="Start timestamp in MM:SS format")
    end_time: str = Field(description="End timestamp in MM:SS format")
    text: str = Field(description="The transcript text for this segment")
    relevance_score: float = Field(
        description="Relevance score from 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(description="Explanation for why this segment is relevant")


class TranscriptAnalysis(BaseModel):
    """Analysis result for transcript segments."""
    most_relevant_segments: List[TranscriptSegment]
    summary: str = Field(description="Brief summary of the video content")
    key_topics: List[str] = Field(description="List of main topics discussed")


simplified_system_prompt = """You are an expert at analyzing video transcripts to find the most engaging segments for short-form content creation.

CORE OBJECTIVES:
1. Identify segments that would be compelling on social media platforms
2. Focus on complete thoughts, insights, or entertaining moments
3. Prioritize content with hooks, emotional moments, or valuable information
4. Each segment should be engaging and worth watching

SEGMENT SELECTION CRITERIA:
1. STRONG HOOKS: Attention-grabbing opening lines
2. VALUABLE CONTENT: Tips, insights, interesting facts, stories
3. EMOTIONAL MOMENTS: Excitement, surprise, humor, inspiration
4. COMPLETE THOUGHTS: Self-contained ideas that make sense alone
5. ENTERTAINING: Content people would want to share

TIMING GUIDELINES:
- Segments MUST be between 10-30 seconds for optimal engagement
- MAXIMUM segment duration: 30 seconds (end_time - start_time <= 30 seconds)
- CRITICAL: start_time MUST be different from end_time (minimum 10 seconds apart)
- Focus on natural content boundaries rather than arbitrary time limits
- Include enough context for the segment to be understandable
- NEVER create segments longer than 30 seconds

TIMESTAMP REQUIREMENTS - EXTREMELY IMPORTANT:
- Use EXACT timestamps as they appear in the transcript
- Never modify timestamp format (keep MM:SS structure)
- start_time MUST be LESS THAN end_time (start_time < end_time)
- MINIMUM segment duration: 10 seconds (end_time - start_time >= 10 seconds)
- Look at transcript ranges like [02:25 - 02:35] and use different start/end times
- NEVER use the same timestamp for both start_time and end_time
- Example: start_time: "02:25", end_time: "02:35" (NOT "02:25" and "02:25")

Find 3-7 compelling segments that would work well as standalone clips. Quality over quantity - choose segments that would genuinely engage viewers and have proper time ranges."""


class PydanticAIAnalysisService:
    """
    Service for analyzing video transcriptions using Pydantic AI.
    Based on supoclip/backend structure.
    """

    def __init__(self):
        if not settings.USE_LLM_ANALYSIS:
            self.agent = None
            logger.info("LLM analysis disabled")
            return

        try:
            self.agent = Agent(
                model=settings.LLM,
                result_type=TranscriptAnalysis,
                system_prompt=simplified_system_prompt
            )
            logger.info(f"Pydantic AI analysis service initialized | model={settings.LLM}")
        except Exception as e:
            logger.error(f"Failed to initialize Pydantic AI agent | error={e}")
            self.agent = None

    async def analyze_transcript(
        self,
        transcript: str,
    ) -> Optional[TranscriptAnalysis]:
        """
        Analyze video transcript using Pydantic AI to find best moments.

        Args:
            transcript: Formatted transcript text with timestamps

        Returns:
            Analysis result with best moments, or None if disabled/failed
        """
        if not self.agent:
            logger.debug("LLM analysis disabled, skipping")
            return None

        try:
            logger.info(
                f"Starting Pydantic AI analysis | transcript_length={len(transcript)} chars"
            )

            result = await self.agent.run(
                f"""Analyze this video transcript and identify the most engaging segments for short-form content.

Find segments that would be compelling as standalone clips for social media.

Transcript:
{transcript}"""
            )

            analysis = result.data
            logger.info(
                f"Pydantic AI analysis found {len(analysis.most_relevant_segments)} segments"
            )

            validated_segments = self._validate_segments(analysis.most_relevant_segments)

            final_analysis = TranscriptAnalysis(
                most_relevant_segments=validated_segments,
                summary=analysis.summary,
                key_topics=analysis.key_topics
            )

            logger.info(
                f"Selected {len(validated_segments)} segments for processing"
            )
            if validated_segments:
                logger.info(
                    f"Top segment score: {validated_segments[0].relevance_score:.2f}"
                )

            return final_analysis

        except Exception as e:
            logger.error(
                f"Error in Pydantic AI transcript analysis | error={e}",
                exc_info=True
            )
            return TranscriptAnalysis(
                most_relevant_segments=[],
                summary=f"Analysis failed: {str(e)}",
                key_topics=[]
            )

    def _validate_segments(
        self,
        segments: List[TranscriptSegment],
    ) -> List[TranscriptSegment]:
        """
        Validate and filter segments.

        Args:
            segments: List of segments to validate

        Returns:
            List of valid segments
        """
        validated_segments = []

        for segment in segments:
            if not segment.text.strip() or len(segment.text.split()) < 3:
                logger.warning(
                    f"Skipping segment with insufficient content: "
                    f"'{segment.text[:50]}...'"
                )
                continue

            if segment.start_time == segment.end_time:
                logger.warning(
                    f"Skipping segment with identical start/end times: "
                    f"{segment.start_time}"
                )
                continue

            try:
                start_parts = segment.start_time.split(':')
                end_parts = segment.end_time.split(':')

                start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])
                end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])

                duration = end_seconds - start_seconds

                if duration <= 0:
                    logger.warning(
                        f"Skipping segment with invalid duration: "
                        f"{segment.start_time} to {segment.end_time} = {duration}s"
                    )
                    continue

                if duration < 5:
                    logger.warning(
                        f"Skipping segment too short: {duration}s (min 5s required)"
                    )
                    continue

                validated_segments.append(segment)
                logger.info(
                    f"Validated segment: {segment.start_time}-{segment.end_time} "
                    f"({duration}s)"
                )

            except (ValueError, IndexError) as e:
                logger.warning(
                    f"Skipping segment with invalid timestamp format: "
                    f"{segment.start_time}-{segment.end_time}: {e}"
                )
                continue

        validated_segments.sort(key=lambda x: x.relevance_score, reverse=True)
        return validated_segments

    def format_transcript_for_analysis(
        self,
        segments: List[dict[str, Any]],
    ) -> str:
        """
        Format transcription segments into text with timestamps for AI analysis.

        Args:
            segments: List of transcription segments with start, end, text

        Returns:
            Formatted transcript text
        """
        lines = []
        for seg in segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "").strip()

            if text:
                start_time = self._format_timestamp(start)
                end_time = self._format_timestamp(end)
                lines.append(f"[{start_time} - {end_time}] {text}")

        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

