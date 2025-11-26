START_MESSAGE = """
👋 Welcome to CutClipAI! 🎬

I'm your AI-powered assistant for creating engaging video clips with automatic subtitles.

✨ What I can do:

• Create short clips (20-60 seconds) from your videos
• Generate automatic subtitles using AI
• Select the most engaging moments
• Format videos in 9:16 aspect ratio for vertical content
"""

BALANCE_MESSAGE = """
💰 Your balance: {balance} coins

💡 Pricing: 1 clip = 1 coin
"""

VIDEO_UPLOAD_INSTRUCTIONS_MESSAGE = """
📤 Ready to create clips?

Send me a video file or tap the button below to get started!

I'll automatically:
1. Analyze your video
2. Select the best moments
3. Add subtitles
4. Create up to 3 clips for you

⏱️ Processing usually takes a few minutes.
"""

NO_COINS_MESSAGE = """
❌ Insufficient balance!

You need {required} coins, but you have {balance}.

Buy more coins to continue.
"""

CLIPS_READY_MESSAGE = """
✅ Your clips are ready!

{clips_count} clips generated.
"""

PROCESSING_MESSAGE = """
⏳ Processing your video in the background...

🔄 What I'm doing:
• Analyzing video content
• Generating transcriptions with AI
• Selecting the best moments
• Creating clips with subtitles

⏱️ Estimated time: 3-10 minutes

Please wait, I'll notify you as soon as your clips are ready! 🎬
"""

ERROR_MESSAGE = """
❌ An error occurred while processing your video.

Please try again later.
"""

COINS_ADDED_MESSAGE = """
✅ {amount} coins added!

Your new balance: {balance} coins
"""

BUY_COINS_MESSAGE = """
💰 Buy coins:

1 clip = 1 coin
"""

VIDEO_REQUIREMENTS_MESSAGE = """
📤 Video requirements:

📋 Supported formats: MP4, MOV, AVI
⏱️ Maximum duration: 30 minutes
🎬 Up to 3 clips per video

Send me a video file to start processing!
"""

