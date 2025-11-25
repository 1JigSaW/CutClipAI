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

