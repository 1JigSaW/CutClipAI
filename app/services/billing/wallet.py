from typing import Optional
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user.user import User
from app.models.transaction.transaction import Transaction, TransactionType
from app.core.logger import get_logger

logger = get_logger(__name__)


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
        Get user's coin balance from PostgreSQL.
        Creates user if they don't exist.

        Args:
            user_id: Telegram user ID

        Returns:
            Current balance in coins
        """
        with SessionLocal() as session:
            user = session.query(User).filter(User.telegram_id == user_id).first()

            if user is None:
                logger.info(
                    f"Creating new user | telegram_id={user_id} | "
                    f"start_balance={self.start_balance}"
                )
                user = User(
                    telegram_id=user_id,
                    balance=self.start_balance,
                )
                session.add(user)
                session.commit()
                return self.start_balance

            return user.balance

    def add_coins(
        self,
        user_id: int,
        amount: int,
        description: Optional[str] = None,
        transaction_type: TransactionType = TransactionType.PURCHASE,
    ) -> int:
        """
        Add coins to user's wallet in PostgreSQL.

        Args:
            user_id: Telegram user ID
            amount: Amount of coins to add
            description: Optional transaction description
            transaction_type: Type of transaction (PURCHASE or REFUND)

        Returns:
            New balance after adding coins
        """
        with SessionLocal() as session:
            user = session.query(User).filter(User.telegram_id == user_id).first()

            if user is None:
                # Create user if doesn't exist (e.g. first transaction is a purchase)
                user = User(
                    telegram_id=user_id,
                    balance=self.start_balance + amount,
                )
                session.add(user)
                session.flush()  # To get user.id for transaction
            else:
                user.balance += amount

            # Record transaction
            transaction = Transaction(
                user_id=user.id,
                type=transaction_type,
                amount=amount,
                description=description,
            )
            session.add(transaction)
            
            session.commit()
            
            logger.info(
                f"Coins added | user_id={user_id} | amount={amount} | "
                f"type={transaction_type} | new_balance={user.balance}"
            )
            return user.balance

    def charge_coins(
        self,
        user_id: int,
        amount: int,
        description: Optional[str] = None,
    ) -> bool:
        """
        Charge coins from user's wallet in PostgreSQL.

        Args:
            user_id: Telegram user ID
            amount: Amount of coins to charge
            description: Optional transaction description

        Returns:
            True if successful, False if insufficient balance
        """
        with SessionLocal() as session:
            user = session.query(User).filter(User.telegram_id == user_id).first()

            if user is None:
                # If user doesn't exist, we check if start_balance is enough
                if self.start_balance < amount:
                    return False
                
                user = User(
                    telegram_id=user_id,
                    balance=self.start_balance - amount,
                )
                session.add(user)
                session.flush()
            else:
                if user.balance < amount:
                    return False
                user.balance -= amount

            # Record transaction
            transaction = Transaction(
                user_id=user.id,
                type=TransactionType.CHARGE,
                amount=-amount,  # Charge is negative amount in transaction history
                description=description,
            )
            session.add(transaction)
            
            session.commit()
            
            logger.info(
                f"Coins charged | user_id={user_id} | amount={amount} | "
                f"new_balance={user.balance}"
            )
            return True

