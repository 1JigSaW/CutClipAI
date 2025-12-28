"""
LLM analysis service for video transcription.
Uses OpenAI API to analyze video content and find best moments.
"""

from typing import Any, Optional

from openai import OpenAI
from openai import RateLimitError, APIError

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class LLMAnalysisService:
    """
    Service for analyzing video transcriptions using LLM (OpenAI).
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.enabled = settings.USE_LLM_ANALYSIS and self.api_key is not None
        
        if self.enabled:
            try:
                # Initialize OpenAI client with api_key
                # httpx==0.27.2 is compatible with openai>=1.40.0
                self.client = OpenAI(api_key=self.api_key)
                self.model_name = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
                logger.info(f"LLM analysis enabled | provider=OpenAI | model={self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client | error={e}", exc_info=True)
                self.client = None
                self.model_name = None
                self.enabled = False
        else:
            self.client = None
            self.model_name = None
            if settings.USE_LLM_ANALYSIS and not self.api_key:
                logger.warning("LLM analysis requested but OPENAI_API_KEY not set")
            else:
                logger.debug("LLM analysis disabled")
    
    def analyze_transcription(
        self,
        segments: list[dict[str, Any]],
        total_duration: float,
    ) -> Optional[dict[str, Any]]:
        """
        Analyze video transcription using LLM to find best moments.
        
        Args:
            segments: List of transcription segments with text and timestamps
            total_duration: Total video duration in seconds
            
        Returns:
            Analysis result with best moments and scores, or None if disabled
        """
        if not self.enabled:
            logger.warning(
                f"LLM analysis is disabled | "
                f"enabled={self.enabled} | client={self.client is not None}"
            )
            return None
        
        if self.client is None:
            logger.error("LLM client is None, cannot analyze transcription")
            return None
        
        try:
            # Prepare transcription text with timestamps
            transcription_text = self._format_transcription(segments)
            
            # Create prompt for LLM analysis
            prompt = self._create_analysis_prompt(
                transcription=transcription_text,
                total_duration=total_duration,
            )
            
            import time
            llm_start = time.time()
            
            logger.info(
                f"Analyzing transcription with LLM | "
                f"segments={len(segments)} | duration={total_duration:.1f}s | "
                f"transcription_length={len(transcription_text)} chars",
            )
            
            # Call OpenAI API
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
            except RateLimitError as rate_error:
                # Handle rate limit / quota errors
                error_body = getattr(rate_error, 'body', {})
                error_code = error_body.get('error', {}).get('code', '')
                
                if error_code == 'insufficient_quota':
                    logger.error(
                        f"OpenAI API quota exceeded | "
                        f"Please check your OpenAI account billing and add credits. "
                        f"Error: {rate_error}"
                    )
                    raise ValueError(
                        "OpenAI API quota exceeded. Please check your account billing at "
                        "https://platform.openai.com/account/billing and add credits."
                    ) from rate_error
                else:
                    logger.error(f"OpenAI API rate limit error | Error: {rate_error}")
                    raise ValueError(
                        f"OpenAI API rate limit exceeded. Please try again later. Error: {rate_error}"
                    ) from rate_error
            except APIError as api_error:
                # Handle other API errors
                error_str = str(api_error)
                if "invalid_api_key" in error_str or "401" in error_str:
                    logger.error(f"OpenAI API key is invalid | Error: {api_error}")
                    raise ValueError(
                        "OpenAI API key is invalid. Please check your OPENAI_API_KEY in .env file."
                    ) from api_error
                else:
                    logger.error(f"OpenAI API error | Error: {api_error}")
                    raise ValueError(f"OpenAI API error: {api_error}") from api_error
            llm_api_time = time.time() - llm_start
            
            # Parse response
            parse_start = time.time()
            response_text = response.choices[0].message.content if response.choices else ""
            analysis = self._parse_llm_response(response_text)
            parse_time = time.time() - parse_start
            
            total_llm_time = time.time() - llm_start
            
            logger.info(
                f"LLM analysis completed | "
                f"best_moments={len(analysis.get('best_moments', []))} | "
                f"api_time={llm_api_time:.1f}s | parse_time={parse_time:.2f}s | "
                f"total_time={total_llm_time:.1f}s",
            )
            
            return analysis
            
        except Exception as e:
            logger.error(
                f"LLM analysis failed | error={e}",
                exc_info=True,
            )
            return None
    
    def _format_transcription(
        self,
        segments: list[dict[str, Any]],
    ) -> str:
        """
        Format transcription segments into text with timestamps.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            Formatted transcription text
        """
        lines = []
        for seg in segments:
            start_time = self._format_timestamp(seg.get("start", 0))
            end_time = self._format_timestamp(seg.get("end", 0))
            text = seg.get("text", "").strip()
            
            if text:
                lines.append(f"[{start_time} - {end_time}] {text}")
        
        return "\n".join(lines)
    
    def _format_timestamp(
        self,
        seconds: float,
    ) -> str:
        """
        Format seconds to MM:SS format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _create_analysis_prompt(
        self,
        transcription: str,
        total_duration: float,
    ) -> str:
        """
        Create prompt for LLM analysis.
        
        Args:
            transcription: Formatted transcription text
            total_duration: Total video duration
            
        Returns:
            Analysis prompt
        """
        min_duration = settings.CLIP_MIN_DURATION_SECONDS
        max_duration = settings.CLIP_MAX_DURATION_SECONDS
        max_clips = settings.MAX_CLIPS_COUNT
        return f"""Analyze this video transcription and identify the {max_clips} best moments for creating short clips (between {min_duration}-{max_duration} seconds each).

Video duration: {total_duration/60:.1f} minutes

Transcription:
{transcription}

Your task:
1. Identify the most engaging and interesting moments
2. Look for:
   - Hook moments (questions, strong statements, interesting facts)
   - Key insights or important information
   - Emotional or dramatic moments
   - Clear conclusions or takeaways
3. Prioritize moments from the beginning (first 20%) and end (last 20%) of the video
4. Ensure moments are diverse and cover different topics
5. CRITICAL: Ensure that the selected clip durations are strictly between {min_duration} and {max_duration} seconds. 
   - Each clip MUST be at least {min_duration} seconds long.
   - Each clip MUST NOT exceed {max_duration} seconds.
6. CRITICAL: Select exactly {max_clips} best moments if possible, but no more than {max_clips}.

For each moment, provide:
- Start time (in seconds)
- End time (in seconds)
- Score (1-10, where 10 is most engaging)
- Brief reason why this moment is interesting

Format your response as JSON:
{{
  "best_moments": [
    {{
      "start": 120.5,
      "end": 180.3,
      "score": 9.5,
      "reason": "Strong hook question that grabs attention"
    }},
    ...
  ],
  "summary": "Brief summary of video content"
}}

Return ONLY valid JSON, no additional text."""

    def _parse_llm_response(
        self,
        response_text: str,
    ) -> dict[str, Any]:
        """
        Parse LLM response into structured format.
        
        Args:
            response_text: Raw LLM response text
            
        Returns:
            Parsed analysis result
        """
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM JSON response | error={e}")
        
        # Fallback: return empty result
        return {
            "best_moments": [],
            "summary": response_text[:200] if response_text else "",
        }
    
    def score_segment_with_llm(
        self,
        segment: dict[str, Any],
        llm_analysis: Optional[dict[str, Any]],
    ) -> float:
        """
        Get LLM score for a segment if available.
        
        Args:
            segment: Segment dictionary
            llm_analysis: LLM analysis result
            
        Returns:
            LLM score (0-10) or 0 if not available
        """
        if not llm_analysis or not self.enabled:
            return 0.0
        
        segment_start = segment.get("start", 0)
        segment_end = segment.get("end", 0)
        
        best_moments = llm_analysis.get("best_moments", [])
        
        # Find matching moment in LLM analysis
        for moment in best_moments:
            moment_start = moment.get("start", 0)
            moment_end = moment.get("end", 0)
            
            # Check if segment overlaps with LLM moment
            if (segment_start <= moment_end and segment_end >= moment_start):
                score = moment.get("score", 0)
                # Normalize to 0-10 scale
                return min(score, 10.0)
        
        return 0.0

