from app.core.celery_app import celery_app
from app.services.billing.pricing import PricingService
from app.services.billing.wallet import WalletService
from app.services.video.pipeline import VideoPipeline


@celery_app.task(
    name="process_video_task",
)
def process_video_task(
    file_path: str,
    user_id: int,
) -> dict:
    """
    Celery task to process video through full pipeline.

    Args:
        file_path: Path to video file
        user_id: Telegram user ID

    Returns:
        Dictionary with clip paths or "no_coins" status
    """
    pipeline = VideoPipeline()
    wallet_service = WalletService()
    pricing_service = PricingService()

    try:
        clip_paths = pipeline.process(file_path=file_path)

        clips_count = len(clip_paths)
        cost = pricing_service.calculate_cost(clips_count=clips_count)

        charged = wallet_service.charge_coins(
            user_id=user_id,
            amount=cost,
        )

        if not charged:
            return {
                "status": "no_coins",
                "message": "Insufficient balance",
            }

        return {
            "status": "success",
            "clips_count": clips_count,
            "clip_paths": clip_paths,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }

