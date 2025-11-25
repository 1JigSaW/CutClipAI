from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.billing.wallet import WalletService

router = APIRouter(
    prefix="/billing",
    tags=["billing"],
)

wallet_service = WalletService()


class BalanceResponse(BaseModel):
    user_id: int
    balance: int


class BuyCoinsRequest(BaseModel):
    user_id: int
    amount: int


class BuyCoinsResponse(BaseModel):
    user_id: int
    new_balance: int


@router.get(
    path="/balance/{user_id}",
    response_model=BalanceResponse,
)
async def get_balance(
    user_id: int,
):
    """
    Get user's coin balance.

    Args:
        user_id: Telegram user ID

    Returns:
        Current balance
    """
    balance = wallet_service.get_balance(user_id=user_id)

    return BalanceResponse(
        user_id=user_id,
        balance=balance,
    )


@router.post(
    path="/buy",
    response_model=BuyCoinsResponse,
)
async def buy_coins(
    request: BuyCoinsRequest,
):
    """
    Buy coins and add to user's wallet.

    Args:
        request: Buy coins request with user_id and amount

    Returns:
        New balance after purchase
    """
    if request.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive",
        )

    new_balance = wallet_service.add_coins(
        user_id=request.user_id,
        amount=request.amount,
    )

    return BuyCoinsResponse(
        user_id=request.user_id,
        new_balance=new_balance,
    )

