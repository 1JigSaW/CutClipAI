import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.utils.video.youtube import (
    get_youtube_video_id,
    is_youtube_url,
    get_youtube_video_info,
    get_youtube_video_title,
    get_video_duration,
    is_video_suitable_for_processing,
    download_youtube_video,
)


def test_video_id_extraction():
    print("\n🧪 Test 1: Video ID extraction")
    
    test_urls = [
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("not a url", None),
    ]
    
    for url, expected in test_urls:
        result = get_youtube_video_id(url=url)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {url[:50]:50s} → {result}")


def test_url_validation():
    print("\n🧪 Test 2: URL validation")
    
    test_urls = [
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://vimeo.com/123456", False),
        ("not a url", False),
    ]
    
    for url, expected in test_urls:
        result = is_youtube_url(url=url)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {url[:50]:50s} → {result}")


def test_video_info():
    print("\n🧪 Test 3: Video info extraction")
    
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"  URL: {url}")
    info = get_youtube_video_info(url=url)
    
    if info:
        print(f"  ✅ Title: {info.get('title', 'N/A')}")
        print(f"  ✅ Duration: {info.get('duration', 'N/A')}s")
        print(f"  ✅ Uploader: {info.get('uploader', 'N/A')}")
        print(f"  ✅ Views: {info.get('view_count', 'N/A'):,}")
    else:
        print(f"  ❌ Failed to get video info")


def test_video_title():
    print("\n🧪 Test 4: Video title extraction")
    
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    
    title = get_youtube_video_title(url=url)
    
    if title:
        print(f"  ✅ Title: {title}")
    else:
        print(f"  ❌ Failed to get title")


def test_video_duration():
    print("\n🧪 Test 5: Video duration")
    
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    
    duration = get_video_duration(url=url)
    
    if duration:
        print(f"  ✅ Duration: {duration}s ({duration // 60}m {duration % 60}s)")
    else:
        print(f"  ❌ Failed to get duration")


def test_video_suitability():
    print("\n🧪 Test 6: Video suitability check")
    
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    
    suitable = is_video_suitable_for_processing(
        url=url,
        min_duration=60,
        max_duration=7200,
    )
    
    print(f"  {'✅' if suitable else '❌'} Video suitable: {suitable}")


async def test_video_download():
    print("\n🧪 Test 7: Video download (short video)")
    
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    output_path = "/tmp/test_youtube_download.mp4"
    
    print(f"  URL: {url}")
    print(f"  Output: {output_path}")
    print(f"  Downloading... (this may take a minute)")
    
    success = await download_youtube_video(
        url=url,
        output_path=output_path,
        max_retries=3,
    )
    
    if success and Path(output_path).exists():
        file_size = Path(output_path).stat().st_size
        print(f"  ✅ Download successful!")
        print(f"  ✅ File size: {file_size / 1024 / 1024:.2f} MB")
        print(f"  ✅ File path: {output_path}")
    else:
        print(f"  ❌ Download failed")


async def run_all_tests():
    print("=" * 80)
    print("🚀 YouTube Download Testing Suite")
    print("=" * 80)
    
    try:
        test_video_id_extraction()
        test_url_validation()
        test_video_info()
        test_video_title()
        test_video_duration()
        test_video_suitability()
        await test_video_download()
        
        print("\n" + "=" * 80)
        print("✅ All tests completed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())

