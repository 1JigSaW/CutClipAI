from app.core.config import settings


class PricingService:
    def __init__(
        self,
        coins_per_clip: int = settings.COINS_PER_CLIP,
    ):
        self.coins_per_clip = coins_per_clip

    def calculate_cost(
        self,
        clips_count: int,
    ) -> int:
        """
        Calculate cost for processing clips.

        Args:
            clips_count: Number of clips to process

        Returns:
            Total cost in coins
        """
        return clips_count * self.coins_per_clip

    def get_coins_per_clip(
        self,
    ) -> int:
        """
        Get coins per clip rate.

        Returns:
            Number of coins required per clip
        """
        return self.coins_per_clip

