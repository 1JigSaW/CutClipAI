from app.core.config import settings
from app.core.redis_client import redis_client


class WalletService:
    def __init__(
        self,
        start_balance: int = settings.START_BALANCE_COINS,
    ):
        self.start_balance = start_balance

    def get_balance(
        self,
        user_id: int,
    ) -> int:
        """
        Get user's coin balance.

        Args:
            user_id: Telegram user ID

        Returns:
            Current balance in coins
        """
        key = f"wallet:{user_id}"
        balance = redis_client.get(key=key)

        if balance is None:
            redis_client.set(
                key=key,
                value=self.start_balance,
            )
            return self.start_balance

        return int(balance)

    def add_coins(
        self,
        user_id: int,
        amount: int,
    ) -> int:
        """
        Add coins to user's wallet.

        Args:
            user_id: Telegram user ID
            amount: Amount of coins to add

        Returns:
            New balance after adding coins
        """
        key = f"wallet:{user_id}"
        current_balance = self.get_balance(user_id=user_id)
        new_balance = current_balance + amount
        redis_client.set(
            key=key,
            value=new_balance,
        )
        return new_balance

    def charge_coins(
        self,
        user_id: int,
        amount: int,
    ) -> bool:
        """
        Charge coins from user's wallet.

        Args:
            user_id: Telegram user ID
            amount: Amount of coins to charge

        Returns:
            True if successful, False if insufficient balance
        """
        current_balance = self.get_balance(user_id=user_id)

        if current_balance < amount:
            return False

        key = f"wallet:{user_id}"
        new_balance = current_balance - amount
        redis_client.set(
            key=key,
            value=new_balance,
        )
        return True

