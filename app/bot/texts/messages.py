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

📺 *How to use:*
• Send a video file (up to 4GB)
• Paste a YouTube link (e.g., https://www.youtube.com/watch?v=...)
• Share a Google Drive link

Ready to start? Just send me a video or link! 🚀
"""

BALANCE_MESSAGE = """
💰 *Your Balance:* `{balance}` coins

💡 *Pricing:* 1 clip = 1 coin
━━━━━━━━━━━━━━━━━━
Need more? Use the buttons below! 👇
"""

VIDEO_UPLOAD_INSTRUCTIONS_MESSAGE = """
📤 *Ready to create clips?*

Send me:
• A video file (up to 4GB)
• A YouTube link (just paste the URL!)
• A Google Drive link

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
✅ *Payment Successful!*

`{amount}` coins have been added to your wallet.
Current balance: `{balance}` coins.

You're all set! Send me a video or link to start creating clips. 🎬
"""

BUY_COINS_MESSAGE = """
💎 *Top Up Your Balance*

Choose a package that fits your needs. Each clip generated costs 1 coin. 

Payments are handled securely via **Telegram Stars** ⭐.
"""

VIDEO_REQUIREMENTS_MESSAGE = """
📤 *Video Submission Guide*

📋 *Formats:* MP4, MOV, AVI
🎬 *Output:* Up to {max_clips} viral clips per video
💰 *Cost:* 1 coin per clip

💾 *Direct Upload:* Up to 4 GB (Telegram limit)
🔗 *Links:* **Google Drive** or **YouTube**

*How to use Google Drive:*
1️⃣ Upload your video to [Google Drive](https://drive.google.com/)
2️⃣ Right-click the file ➔ **Share** ➔ **Share**
3️⃣ Under "General access" select **"Anyone with the link"**
4️⃣ Click **"Copy link"** and paste it here!

*YouTube:* 
1️⃣ Copy the video URL from YouTube
2️⃣ Paste it here (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...)
3️⃣ Works with any YouTube video, including age-restricted content 📺

💰 *Your Balance:* `{balance}` coins
Send me a video file or link to start! 📥
"""

HELP_MESSAGE = """
📖 *How to use CutClipAI*

1️⃣ **Upload Video:** 
   • Send a video file (up to 4GB)
   • Paste a YouTube link (e.g., https://www.youtube.com/watch?v=...)
   • Share a Google Drive link

2️⃣ **AI Processing:** Our AI will analyze the video, find the best moments, and generate subtitles.

3️⃣ **Get Clips:** You'll receive ready-to-use vertical (9:16) clips for Shorts, Reels, or TikTok.

📋 *Requirements:*
• Video duration: Up to 3 hours
• Formats: MP4, MOV, AVI
• YouTube: Works with any video, including age-restricted content
• Google Drive: Make sure access is set to "Anyone with the link"

💰 *Pricing:*
• 1 generated clip = 1 coin
• Top up your balance using Telegram Stars in the "Balance" menu

Need help? Contact support or try sending a video now! 🚀
"""

DOWNLOADING_MESSAGE = """
⬇️ *Downloading video from Google Drive...*

This may take a few minutes depending on the file size.
"""

DOWNLOADING_YOUTUBE_MESSAGE = """
⬇️ *Downloading video from YouTube...*

I'm grabbing the best quality for you! 📺
"""

INVALID_GOOGLE_DRIVE_LINK_MESSAGE = """
❌ *Invalid Google Drive link!*

Please send a valid sharing link.
Make sure the file access is set to **"Anyone with the link"**.
"""

YOUTUBE_DOWNLOAD_ERROR_MESSAGE = """
❌ *Failed to download YouTube video*

The video could not be downloaded. This might happen if:
• The video is too large or processing takes too long
• The video is unavailable or private
• The service is temporarily overloaded

Please try again in a few minutes or try a different video.
"""

INVALID_YOUTUBE_LINK_MESSAGE = """
❌ *Invalid YouTube link!*

Please check the link and try again.
Make sure you're using a valid YouTube URL (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...)
"""

