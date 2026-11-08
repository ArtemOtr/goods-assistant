import logging

from fastapi import APIRouter, HTTPException, Request

from src.schemas.product_card import ProductCard, ProductCardRequest
from src.services.card_service import ProductCardService, UnsupportedGeneratedFactsError
from src.services.llm_client import LLMConfigurationError

router = APIRouter(prefix="/v1/product-cards", tags=["product-cards"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=ProductCard)
async def generate_product_card(
    body: ProductCardRequest,
    request: Request,
) -> ProductCard:
    service: ProductCardService = request.app.state.product_card_service

    try:
        return await service.generate(body)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UnsupportedGeneratedFactsError as exc:
        logger.warning("Generated content failed fact validation: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Product card generation failed")
        raise HTTPException(status_code=502, detail="Failed to generate product card") from exc
