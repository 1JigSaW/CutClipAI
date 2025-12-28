from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.database import init_db
from app.core.logger import get_logger, setup_logging
from app.routers import billing, video

logger = get_logger(__name__)
setup_logging(level="INFO")


def create_app(
    app_name: str,
) -> FastAPI:
    """
    Create FastAPI application.
    """
    application = FastAPI(
        title=app_name,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """
        Handle validation errors with detailed logging.

        Args:
            request: Request object
            exc: Validation error exception

        Returns:
            JSON error response
        """
        logger.error(
            f"Validation error | path={request.url.path} | method={request.method} | "
            f"errors={exc.errors()} | body_size={len(await request.body()) if hasattr(request, 'body') else 0}",
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": str(exc.body) if hasattr(exc, "body") else None,
            },
        )

    @application.on_event("startup")
    def startup_event():
        logger.info("Starting FastAPI application")
        try:
            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(
                f"Database initialization failed | error={e} | "
                f"API will continue but database features may not work"
            )

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
