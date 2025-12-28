import re
from typing import Any, Optional

from app.core.config import settings
from app.core.logger import get_logger
from app.services.video.llm_analysis import LLMAnalysisService

logger = get_logger(__name__)


class ScoringService:
    def __init__(
        self,
        min_duration: int = settings.CLIP_MIN_DURATION_SECONDS,
        max_duration: int = settings.CLIP_MAX_DURATION_SECONDS,
        max_clips: int = settings.MAX_CLIPS_COUNT,
        llm_service: Optional[LLMAnalysisService] = None,
    ):
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.max_clips = max_clips
        self.llm_service = llm_service or LLMAnalysisService()

    def select_best_moments(
        self,
        segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Select up to 3 best moments (20-60sec each).

        Args:
            segments: List of transcription segments

        Returns:
            List of best moments with start and end times
        """
        if not segments:
            logger.warning("No segments provided for scoring")
            return []

        logger.info(
            f"Selecting best moments from {len(segments)} segments | "
            f"min_duration={self.min_duration}s | max_duration={self.max_duration}s | "
            f"llm_enabled={self.llm_service.enabled}",
        )

        if len(segments) == 0:
            return []

        segment_durations = [seg["end"] - seg["start"] for seg in segments]
        avg_duration = sum(segment_durations) / len(segment_durations) if segment_durations else 0
        total_duration = segments[-1]["end"] if segments else 0
        
        logger.info(
            f"Segment statistics | count={len(segments)} | "
            f"avg_duration={avg_duration:.2f}s | "
            f"min_duration={min(segment_durations):.2f}s | "
            f"max_duration={max(segment_durations):.2f}s | "
            f"total_duration={total_duration:.1f}s",
        )

        # Get LLM analysis if enabled
        llm_analysis = None
        if self.llm_service.enabled:
            import time
            llm_start = time.time()
            llm_analysis = self.llm_service.analyze_transcription(
                segments=segments,
                total_duration=total_duration,
            )
            llm_time = time.time() - llm_start
            if llm_analysis:
                logger.info(
                    f"LLM analysis received | "
                    f"best_moments={len(llm_analysis.get('best_moments', []))} | "
                    f"time={llm_time:.1f}s",
                )
            else:
                logger.warning(f"LLM analysis failed or returned None | time={llm_time:.1f}s")

        continuous_clips = self._find_continuous_speech_moments(
            segments=segments,
            total_duration=total_duration,
            llm_analysis=llm_analysis,
        )
        
        logger.info(f"Found {len(continuous_clips)} continuous speech moments")

        continuous_clips.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        diverse_clips = self._select_diverse_clips(
            clips=continuous_clips,
            max_clips=self.max_clips,
        )
        
        self._log_selected_clips(clips=diverse_clips)
        
        logger.info(
            f"Selected {len(diverse_clips)} diverse clips from "
            f"{len(continuous_clips)} candidates",
        )
        
        return diverse_clips

    def _find_continuous_speech_moments(
        self,
        segments: list[dict[str, Any]],
        total_duration: float = 0.0,
        llm_analysis: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Find continuous speech moments that represent complete thoughts.
        Stops at natural boundaries: punctuation, pauses, or topic changes.

        Args:
            segments: List of transcription segments
            total_duration: Total video duration
            llm_analysis: Optional LLM analysis result

        Returns:
            List of continuous moments with start, end, score
        """
        if not segments:
            return []

        clips = []
        i = 0
        max_pause = 2.0  # Reduced pause threshold for better thought boundaries
        
        # Get total video duration for structure scoring
        if total_duration <= 0:
            total_duration = segments[-1]["end"] if segments else 0

        while i < len(segments):
            clip_start = segments[i]["start"]
            clip_segments = [segments[i]]
            j = i + 1

            while j < len(segments):
                prev_seg = segments[j - 1]
                current_seg = segments[j]
                
                prev_end = prev_seg["end"]
                current_start = current_seg["start"]
                pause = current_start - prev_end

                current_clip_duration = current_seg["end"] - clip_start

                # Check if we should stop (end of thought)
                should_stop = False
                
                # Stop if pause is too long (end of thought)
                if pause > max_pause:
                    should_stop = True
                
                # Stop if clip would exceed max duration (with 2s buffer to avoid cutting mid-sentence)
                if current_clip_duration >= (self.max_duration - 2.0):
                    should_stop = True
                
                # Stop if previous segment ends with strong punctuation (end of sentence/thought)
                prev_text = prev_seg.get("text", "").strip()
                if prev_text:
                    # Strong punctuation indicates end of thought
                    if prev_text.endswith((".", "!", "?", "…")):
                        # If pause is significant (>0.5s), it's likely end of thought
                        if pause > 0.5:
                            should_stop = True
                        # If we already have a good clip (>=min_duration), stop at sentence end
                        # This prevents all clips from being exactly max_duration
                        elif current_clip_duration >= self.min_duration:
                            # Prefer shorter clips that end naturally
                            if pause > 0.3:  # Even small pause after punctuation is good stopping point
                                should_stop = True
                            # If clip is getting long (>=25s), stop at any sentence end
                            elif current_clip_duration >= 25.0:
                                should_stop = True
                
                if should_stop:
                    break
                
                clip_segments.append(current_seg)
                j += 1

            clip_end = clip_segments[-1]["end"]
            clip_duration = clip_end - clip_start

            if clip_duration >= self.min_duration:
                combined_text = " ".join([s.get("text", "") for s in clip_segments])
                
                all_words = []
                for seg in clip_segments:
                    seg_words = seg.get("words", [])
                    all_words.extend(seg_words)
                
                combined_segment = {
                    "start": clip_start,
                    "end": clip_end,
                    "text": combined_text,
                    "words": all_words,
                }
                
                score_breakdown = {}
                clip_score = self._calculate_score(
                    segment=combined_segment,
                    total_duration=total_duration,
                    llm_analysis=llm_analysis,
                    breakdown=score_breakdown,
                )
                
                llm_reason = None
                if llm_analysis:
                    for moment in llm_analysis.get("best_moments", []):
                        if (clip_start <= moment.get("end", 0) and 
                            clip_end >= moment.get("start", 0)):
                            llm_reason = moment.get("reason", "")
                            break
                
                clips.append({
                    "start": clip_start,
                    "end": clip_end,
                    "score": clip_score,
                    "text": combined_text,
                    "score_breakdown": score_breakdown,
                    "llm_reason": llm_reason,
                })

            i = j if j > i else i + 1

        return clips

    def _calculate_score_with_breakdown(
        self,
        segment: dict[str, Any],
        total_duration: float = 0.0,
        llm_analysis: Optional[dict[str, Any]] = None,
        breakdown: Optional[dict[str, float]] = None,
    ) -> float:
        """
        Calculate score with detailed breakdown for logging.
        """
        return self._calculate_score(
            segment=segment,
            total_duration=total_duration,
            llm_analysis=llm_analysis,
            breakdown=breakdown,
        )
    
    def _calculate_score(
        self,
        segment: dict[str, Any],
        total_duration: float = 0.0,
        llm_analysis: Optional[dict[str, Any]] = None,
        breakdown: Optional[dict[str, float]] = None,
    ) -> float:
        """
        Calculate score based on speech dynamics and emotion indicators.
        NO keyword matching - purely data-driven approach.
        
        Factors:
        - Speech energy (words density, pace)
        - Tempo variations (acceleration/deceleration)
        - Pause patterns (emotional pauses)
        - Punctuation (?, !, ...)
        - Word repetitions
        - Video structure (beginning/end bonus)
        - Hook patterns (questions, statements)

        Args:
            segment: Segment dictionary with optional 'words' timestamps
            total_duration: Total video duration for structure scoring

        Returns:
            Weighted score value
        """
        text = segment.get("text", "").strip()
        duration = segment.get("end", 0) - segment.get("start", 0)
        words_data = segment.get("words", [])
        start_time = segment.get("start", 0)
        
        if duration <= 0:
            return 0.0
        
        score = 0.0
        
        energy_score = self._score_energy(
            text=text,
            duration=duration,
            words_data=words_data,
        )
        score += energy_score * settings.SCORING_WEIGHT_ENERGY
        
        tempo_score = self._score_tempo_variation(words_data=words_data)
        score += tempo_score * settings.SCORING_WEIGHT_TEMPO_VARIATION
        
        pause_score = self._score_pauses(words_data=words_data)
        score += pause_score * settings.SCORING_WEIGHT_PAUSES
        
        punctuation_score = self._score_punctuation(text=text)
        score += punctuation_score * settings.SCORING_WEIGHT_PUNCTUATION
        
        pace_score = self._score_speech_pace(
            text=text,
            duration=duration,
        )
        score += pace_score * settings.SCORING_WEIGHT_SPEECH_PACE
        
        # Structure bonus (beginning/end of video)
        structure_score = self._score_structure(
            start_time=start_time,
            total_duration=total_duration,
        )
        score += structure_score * settings.SCORING_WEIGHT_STRUCTURE
        
        # Hook detection bonus
        hook_score = self._score_hook_patterns(text=text)
        score += hook_score * settings.SCORING_WEIGHT_HOOK
        
        # LLM analysis bonus (if enabled)
        llm_score = 0.0
        if llm_analysis and self.llm_service.enabled:
            llm_score = self.llm_service.score_segment_with_llm(
                segment=segment,
                llm_analysis=llm_analysis,
            )
            score += llm_score * settings.SCORING_WEIGHT_LLM
        
        if breakdown is not None:
            breakdown["energy"] = energy_score
            breakdown["tempo"] = tempo_score
            breakdown["pauses"] = pause_score
            breakdown["punctuation"] = punctuation_score
            breakdown["speech_pace"] = pace_score
            breakdown["structure"] = structure_score
            breakdown["hook"] = hook_score
            breakdown["llm"] = llm_score
        
        logger.debug(
            f"Segment score breakdown | "
            f"energy={energy_score:.2f} | tempo={tempo_score:.2f} | "
            f"pauses={pause_score:.2f} | punctuation={punctuation_score:.2f} | "
            f"pace={pace_score:.2f} | structure={structure_score:.2f} | "
            f"hook={hook_score:.2f} | llm={llm_score:.2f} | total={score:.2f}",
        )
        
        return score
    
    def _score_energy(
        self,
        text: str,
        duration: float,
        words_data: list[dict[str, Any]],
    ) -> float:
        """
        Calculate speech energy based on word density and character density.
        High energy = lots of information in short time.
        """
        words = text.split()
        word_count = len(words)
        char_count = len(text.replace(" ", ""))
        
        if duration == 0:
            return 0.0
        
        words_per_second = word_count / duration
        chars_per_second = char_count / duration
        
        word_density_score = min(words_per_second * 2.0, 10.0)
        
        char_density_score = min(chars_per_second * 0.5, 10.0)
        
        short_words = sum(1 for w in words if len(w) <= 4)
        short_word_ratio = short_words / max(word_count, 1)
        
        if short_word_ratio > 0.6:
            energy_bonus = 2.0
        else:
            energy_bonus = 0.0
        
        repetitions = self._count_repetitions(words=words)
        repetition_score = min(repetitions * 1.5, 5.0)
        
        total_score = (
            word_density_score * 0.4 +
            char_density_score * 0.3 +
            energy_bonus +
            repetition_score * 0.3
        )
        
        return min(total_score, 10.0)
    
    def _score_tempo_variation(
        self,
        words_data: list[dict[str, Any]],
    ) -> float:
        """
        Analyze tempo changes within segment.
        High variation = emotional speech (speeds up, slows down).
        """
        if len(words_data) < 5:
            return 5.0
        
        word_durations = []
        for word_info in words_data:
            start = word_info.get("start", 0)
            end = word_info.get("end", 0)
            duration = end - start
            if duration > 0:
                word_durations.append(duration)
        
        if len(word_durations) < 3:
            return 5.0
        
        avg_duration = sum(word_durations) / len(word_durations)
        
        variations = [
            abs(duration - avg_duration)
            for duration in word_durations
        ]
        avg_variation = sum(variations) / len(variations)
        
        variation_ratio = avg_variation / max(avg_duration, 0.01)
        
        score = min(variation_ratio * 15.0, 10.0)
        
        return score
    
    def _score_pauses(
        self,
        words_data: list[dict[str, Any]],
    ) -> float:
        """
        Analyze pauses between words.
        Emotional speech has dramatic pauses and varied rhythm.
        """
        if len(words_data) < 2:
            return 0.0
        
        pauses = []
        for i in range(len(words_data) - 1):
            current_end = words_data[i].get("end", 0)
            next_start = words_data[i + 1].get("start", 0)
            pause = next_start - current_end
            if pause > 0:
                pauses.append(pause)
        
        if not pauses:
            return 0.0
        
        dramatic_pauses = sum(1 for p in pauses if p > 0.3)
        
        pause_variation = max(pauses) - min(pauses) if pauses else 0
        
        score = 0.0
        score += dramatic_pauses * 1.5
        score += min(pause_variation * 5.0, 5.0)
        
        return min(score, 10.0)
    
    def _score_speech_pace(
        self,
        text: str,
        duration: float,
    ) -> float:
        """
        Score based on speech pace (words per minute).
        Optimal pace indicates engaging content.
        """
        words = len(text.split())
        words_per_minute = (words / duration) * 60
        
        optimal_pace = 160
        min_good_pace = 120
        max_good_pace = 200
        
        if min_good_pace <= words_per_minute <= max_good_pace:
            deviation = abs(words_per_minute - optimal_pace)
            max_deviation = max(
                optimal_pace - min_good_pace,
                max_good_pace - optimal_pace,
            )
            score = 10.0 * (1 - deviation / max_deviation)
        else:
            score = max(0.0, 10.0 - abs(words_per_minute - optimal_pace) / 20)
        
        return score
    
    def _score_punctuation(
        self,
        text: str,
    ) -> float:
        """
        Score based on emotional punctuation.
        """
        score = 0.0
        
        questions = text.count("?")
        exclamations = text.count("!")
        ellipsis = text.count("...") + text.count("…")
        
        score += questions * 2.5
        score += exclamations * 2.0
        score += ellipsis * 1.5
        
        if exclamations > 2 or questions > 2:
            score += 3.0
        
        return min(score, 10.0)
    
    def _count_repetitions(
        self,
        words: list[str],
    ) -> int:
        """
        Count immediate word repetitions (e.g., "this this this").
        Indicates emotion/emphasis.
        """
        repetitions = 0
        for i in range(len(words) - 1):
            if words[i].lower() == words[i + 1].lower():
                repetitions += 1
        return repetitions
    
    def _select_diverse_clips(
        self,
        clips: list[dict[str, Any]],
        max_clips: int,
    ) -> list[dict[str, Any]]:
        """
        Select diverse clips avoiding too similar content.
        
        Args:
            clips: Sorted list of clips by score (best first)
            max_clips: Maximum number of clips to select
        
        Returns:
            List of diverse clips
        """
        if len(clips) <= max_clips:
            return clips
        
        selected = [clips[0]]
        
        for candidate in clips[1:]:
            if len(selected) >= max_clips:
                break
            
            is_diverse = True
            candidate_words = set(candidate["text"].lower().split())
            
            for selected_clip in selected:
                selected_words = set(selected_clip["text"].lower().split())
                
                common_words = candidate_words & selected_words
                similarity = len(common_words) / max(len(candidate_words), 1)
                
                time_distance = abs(candidate["start"] - selected_clip["start"])
                
                if similarity > 0.5 and time_distance < 120:
                    is_diverse = False
                    logger.debug(
                        f"Rejecting similar clip | similarity={similarity:.2f} | "
                        f"time_distance={time_distance:.0f}s",
                    )
                    break
            
            if is_diverse:
                selected.append(candidate)
        
        return selected
    
    def _score_structure(
        self,
        start_time: float,
        total_duration: float,
    ) -> float:
        """
        Score based on video structure position.
        Beginning and end of video are more important.
        
        Args:
            start_time: Start time of segment in seconds
            total_duration: Total video duration in seconds
            
        Returns:
            Structure score (0-10)
        """
        if total_duration <= 0:
            return 5.0  # Neutral score if duration unknown
        
        position_ratio = start_time / total_duration
        
        # Beginning bonus (first 10% of video)
        if position_ratio <= 0.1:
            # Linear decay from 10.0 to 5.0
            score = 10.0 - (position_ratio / 0.1) * 5.0
        # End bonus (last 10% of video)
        elif position_ratio >= 0.9:
            # Linear increase from 5.0 to 10.0
            score = 5.0 + ((position_ratio - 0.9) / 0.1) * 5.0
        # Middle section (neutral)
        else:
            score = 5.0
        
        return min(score, 10.0)
    
    def _score_hook_patterns(
        self,
        text: str,
    ) -> float:
        """
        Detect hook patterns that grab attention.
        
        Hook patterns:
        - Questions at the start
        - Strong statements/claims
        - Numbers/facts
        - Contrasts ("but", "however", "actually")
        - Personal stories ("I", "me", "my")
        
        Args:
            text: Segment text
            
        Returns:
            Hook score (0-10)
        """
        if not text:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        words = text.split()
        first_words = " ".join(words[:5]).lower() if len(words) >= 5 else text_lower
        
        # Questions at the start (strong hook)
        if first_words.startswith(("знаете", "знаешь", "знали", "знали ли", "do you", "did you", "have you", "are you", "is it", "what if", "what", "why", "how")):
            score += 5.0
        
        # Questions anywhere
        if "?" in text:
            question_count = text.count("?")
            score += min(question_count * 1.5, 3.0)
        
        # Strong statements/claims
        strong_starters = ("вот", "это", "так вот", "дело в том", "here's", "this is", "the thing is", "here's the thing")
        if any(first_words.startswith(starter) for starter in strong_starters):
            score += 3.0
        
        # Numbers and facts (indicates important information)
        import re
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 2:
            score += 2.0
        elif len(numbers) == 1:
            score += 1.0
        
        # Contrasts (creates interest)
        contrast_words = ("но", "однако", "хотя", "впрочем", "но на самом деле", "but", "however", "although", "though", "actually", "in fact")
        contrast_count = sum(1 for word in contrast_words if word in text_lower)
        score += min(contrast_count * 1.5, 3.0)
        
        # Personal stories (engaging)
        personal_words = ("я", "мне", "меня", "мой", "моя", "i", "me", "my", "i'm", "i've", "i'll")
        personal_count = sum(1 for word in personal_words if word in text_lower)
        if personal_count >= 3:
            score += 2.0
        elif personal_count >= 1:
            score += 1.0
        
        return min(score, 10.0)
    
    def _log_selected_clips(
        self,
        clips: list[dict[str, Any]],
    ) -> None:
        """
        Log detailed information about selected clips with reasons.
        
        Args:
            clips: List of selected clips
        """
        logger.info("=" * 60)
        logger.info("🎯 SELECTED BEST MOMENTS:")
        
        for idx, clip in enumerate(clips, 1):
            duration = clip["end"] - clip["start"]
            preview = clip["text"][:100] + "..." if len(clip["text"]) > 100 else clip["text"]
            
            reasons = []
            if clip.get("llm_reason"):
                reasons.append(f"LLM: {clip['llm_reason']}")
            if clip.get("score_breakdown"):
                breakdown = clip["score_breakdown"]
                breakdown_parts = []
                if breakdown.get("energy", 0) > 0:
                    breakdown_parts.append(f"energy={breakdown['energy']:.1f}")
                if breakdown.get("tempo", 0) > 0:
                    breakdown_parts.append(f"tempo={breakdown['tempo']:.1f}")
                if breakdown.get("pauses", 0) > 0:
                    breakdown_parts.append(f"pauses={breakdown['pauses']:.1f}")
                if breakdown.get("punctuation", 0) > 0:
                    breakdown_parts.append(f"punctuation={breakdown['punctuation']:.1f}")
                if breakdown.get("speech_pace", 0) > 0:
                    breakdown_parts.append(f"pace={breakdown['speech_pace']:.1f}")
                if breakdown.get("structure", 0) > 0:
                    breakdown_parts.append(f"structure={breakdown['structure']:.1f}")
                if breakdown.get("hook", 0) > 0:
                    breakdown_parts.append(f"hook={breakdown['hook']:.1f}")
                if breakdown.get("llm", 0) > 0:
                    breakdown_parts.append(f"llm={breakdown['llm']:.1f}")
                if breakdown_parts:
                    reasons.append(f"Score breakdown: {', '.join(breakdown_parts)}")
            
            logger.info(
                f"\n#{idx} | Score: {clip['score']:.2f} | "
                f"Duration: {duration:.1f}s | "
                f"Time: {clip['start']:.1f}s-{clip['end']:.1f}s"
            )
            if reasons:
                logger.info(f"   Reasons: {' | '.join(reasons)}")
            logger.info(f"   Text: {preview}")
        
        logger.info("=" * 60)

