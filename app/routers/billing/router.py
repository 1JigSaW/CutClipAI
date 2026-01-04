from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.core.config import settings
from app.services.billing.wallet import WalletService

router = APIRouter(
    prefix="/billing",
    tags=["billing"],
)

wallet_service = WalletService()


def verify_api_key(
    x_api_key: str = Header(None),
):
    """
    Verify API secret key.
    """
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )


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
    x_api_key: str = Header(None),
):
    """
    Get user's coin balance.
    """
    verify_api_key(x_api_key=x_api_key)
    
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
    x_api_key: str = Header(None),
):
    """
    Buy coins and add to user's wallet.
    """
    verify_api_key(x_api_key=x_api_key)
    
    if request.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive",
        )

    new_balance = wallet_service.add_coins(
        user_id=request.user_id,
        amount=request.amount,
        description="Coins purchase via API",
    )

    return BuyCoinsResponse(
        user_id=request.user_id,
        new_balance=new_balance,
    )

