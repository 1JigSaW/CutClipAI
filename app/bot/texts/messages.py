START_MESSAGE = """
👋 *Welcome to CutClipAI!* 🎬

I'm your AI-powered assistant for creating engaging video clips with automatic subtitles.

💰 *Your Balance:* `{balance}` coins
💡 *Note:* Each clip generated costs 1 coin.

✨ *What I can do:*
• Create up to {max_clips} clips (20-60 seconds each)
• Generate automatic subtitles using AI
• Select the most engaging moments
• Format videos in 9:16 aspect ratio

Ready to start? Send me a video file or a Google Drive link! 🚀
"""

BALANCE_MESSAGE = """
💰 *Your Balance:* `{balance}` coins

💡 *Pricing:* 1 clip = 1 coin
━━━━━━━━━━━━━━━━━━
Need more? Use the buttons below! 👇
"""

VIDEO_UPLOAD_INSTRUCTIONS_MESSAGE = """
📤 *Ready to create clips?*

Send me a video file or tap the button below to get started!

I'll automatically:
1. Analyze your video
2. Select the best moments
3. Add subtitles
4. Create up to {max_clips} clips for you

💰 *Remaining Balance:* `{balance}` coins
⏱️ *Processing usually takes 3-10 minutes.*
"""

NO_COINS_MESSAGE = """
⚠️ *Insufficient balance!*

You need at least `{required}` coins for full processing, but you only have `{balance}`.

To continue, please top up your balance. 💳
"""

CLIPS_READY_MESSAGE = """
🎉 *Your clips are ready!*

`{clips_count}` clips generated.
💰 *New Balance:* `{balance}` coins
━━━━━━━━━━━━━━━━━━
Check them out below! 👇
"""

PROCESSING_MESSAGE = """
⏳ *AI is hard at work...*

🔄 *What I'm doing:*
• Analyzing video content
• Generating transcriptions with AI
• Selecting the best moments
• Creating clips with subtitles

⏱️ *Estimated time:* 3-10 minutes
💰 *Balance after processing:* `~{balance}` coins (est.)

I'll notify you the second they are ready! 🎬
"""

ERROR_MESSAGE = """
❌ *An error occurred while processing your video.*

Please try again later or contact support.
"""

COINS_ADDED_MESSAGE = """
✅ `{amount}` coins added!

Your new balance: `{balance}` coins.
"""

BUY_COINS_MESSAGE = """
💰 *Buy coins:*

`1 clip = 1 coin`
"""

VIDEO_REQUIREMENTS_MESSAGE = """
📤 *Video Submission Guide*

📋 *Formats:* MP4, MOV, AVI
⏱️ *Max duration:* 30 minutes
🎬 *Output:* Up to {max_clips} viral clips per video
💰 *Cost:* 1 coin per clip

💾 *Direct Upload:* Up to 4 GB (Telegram limit)
🔗 *For larger files:* Please use a **Google Drive link**

*How to use Google Drive:*
1️⃣ Upload your video to [Google Drive](https://drive.google.com/)
2️⃣ Right-click the file ➔ **Share** ➔ **Share**
3️⃣ Under "General access" select **"Anyone with the link"**
4️⃣ Click **"Copy link"** and paste it here!

💰 *Your Balance:* `{balance}` coins
Send me a video file or link to start! 📥
"""

DOWNLOADING_MESSAGE = """
⬇️ *Downloading video from Google Drive...*

This may take a few minutes depending on the file size.
"""

INVALID_GOOGLE_DRIVE_LINK_MESSAGE = """
❌ *Invalid Google Drive link!*

Please send a valid sharing link.
Make sure the file access is set to **"Anyone with the link"**.
"""

