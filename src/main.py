import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from uvicorn import run

from src.routers.health import router as health_router
from src.routers.product_cards import router as product_cards_router
from src.services.card_service import ProductCardService
from src.services.llm_client import llm_client
from src.settings import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.app.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await llm_client.aclose()


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title=settings.app.name,
        debug=settings.app.debug,
        lifespan=lifespan,
    )
    app.state.product_card_service = ProductCardService(llm_client=llm_client)
    app.include_router(health_router)
    app.include_router(product_cards_router)
    return app


app = create_app()


def main() -> None:
    run(
        "src.main:create_app",
        host=settings.app.host,
        port=settings.app.port,
        factory=True,
        reload=settings.app.debug,
    )


if __name__ == "__main__":
    main()
