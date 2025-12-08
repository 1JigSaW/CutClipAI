from app.core.config import settings
from app.services.billing.wallet import WalletService


def validate_user_id(
    user_id: int,
) -> bool:
    """
    Validate user ID.

    Args:
        user_id: Telegram user ID

    Returns:
        True if valid
    """
    return user_id > 0


def validate_amount(
    amount: int,
) -> bool:
    """
    Validate coin amount.

    Args:
        amount: Amount of coins

    Returns:
        True if valid
    """
    return amount > 0


def check_balance_for_video_processing(
    user_id: int,
    wallet_service: WalletService | None = None,
) -> tuple[bool, int, int]:
    """
    Check if user has sufficient balance for maximum video processing cost.

    Args:
        user_id: Telegram user ID
        wallet_service: Optional WalletService instance. If None, creates new instance.

    Returns:
        Tuple of (has_sufficient_balance, balance, required_cost)
    """
    if wallet_service is None:
        wallet_service = WalletService()
    
    max_cost = settings.MAX_CLIPS_COUNT * settings.COINS_PER_CLIP
    balance = wallet_service.get_balance(user_id=user_id)
    
    has_sufficient_balance = balance >= max_cost
    
    return (
        has_sufficient_balance,
        balance,
        max_cost,
    )

