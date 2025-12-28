# Prompts Used for Video Clip Selection

## 1. OpenAI LLM Analysis Prompt

**Location:** `app/services/video/llm_analysis.py` → `_create_analysis_prompt()`

```python
Analyze this video transcription and identify the 3-5 best moments for creating short clips.

Video duration: {total_duration/60:.1f} minutes
MAXIMUM clip duration: 30 seconds

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

CRITICAL TIMING REQUIREMENTS:
- Each moment MUST be between 10-30 seconds
- end_time - start_time MUST be <= 30 seconds
- NEVER create moments longer than 30 seconds
- Focus on complete, self-contained thoughts within 30 seconds

For each moment, provide:
- Start time (in seconds)
- End time (in seconds) - MUST be start_time + (10 to 30) seconds
- Score (1-10, where 10 is most engaging)
- Brief reason why this moment is interesting

Format your response as JSON:
{
  "best_moments": [
    {
      "start": 120.5,
      "end": 180.3,
      "score": 9.5,
      "reason": "Strong hook question that grabs attention"
    },
    ...
  ],
  "summary": "Brief summary of video content"
}

Return ONLY valid JSON, no additional text.
```

## 2. Pydantic AI System Prompt

**Location:** `app/services/video/pydantic_ai_analysis.py` → `simplified_system_prompt`

```python
You are an expert at analyzing video transcripts to find the most engaging segments for short-form content creation.

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

Find 3-7 compelling segments that would work well as standalone clips. Quality over quantity - choose segments that would genuinely engage viewers and have proper time ranges.
```

## 3. Scoring Algorithm (REMOVED)

**Status:** Scoring algorithm has been completely removed from the pipeline.

**Current approach:** Only LLM analysis is used for selecting video clips. If LLM analysis fails, video processing will fail with an error (no fallback to scoring).

