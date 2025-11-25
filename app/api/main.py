from fastapi import FastAPI

from app.core.database import init_db
from app.routers import billing, video


def create_app(
    app_name: str,
) -> FastAPI:
    """
    Create FastAPI application.
    """
    application = FastAPI(
        title=app_name,
    )

    @application.on_event("startup")
    def startup_event():
        init_db()

    application.include_router(router=video.router)
    application.include_router(router=billing.router)

    @application.get(
        path="/health",
        tags=["health"],
    )
    def healthcheck() -> dict:
        """
        Healthcheck endpoint.
        """
        return {
            "status": "ok",
            "service": app_name,
        }

    return application


app = create_app(
    app_name="CutClipAI",
)
