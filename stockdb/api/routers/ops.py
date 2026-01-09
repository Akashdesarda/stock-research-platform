import os
from datetime import datetime

import polars as pl
from fastapi import APIRouter, status
from fastapi.responses import ORJSONResponse
from stocksense.config import get_settings
from stocksense.data import StockDataDB

from api.models import (
    APITags,
    PromptCacheInput,
    PromptCacheOutput,
    PromptSearchInput,
)

settings = get_settings(os.getenv("CONFIG_FILE"))

router = APIRouter(prefix="/api/operation", tags=[APITags.ops])


@router.post("/prompt/search", response_model=PromptCacheOutput)
async def search_prompt_cache(query: PromptSearchInput) -> ORJSONResponse:
    """Retrieve LLM response from cache"""
    key = query.get_cache_key()
    prompt_cache_table = StockDataDB(
        settings.stockdb.data_base_path / "common/prompt_cache"
    )

    result = await prompt_cache_table.polars_filter(
        (pl.col("prompt_hash") == key)
        & (pl.col("last_modified") + pl.duration(days=pl.col("ttl")) > datetime.now())
    ).collect_async()
    if not result.is_empty():
        return ORJSONResponse(result.select("response", "thinking").to_dicts()[0])
    else:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": f"No cached response found for the given prompt and '{query.agent}' agent."
            },
        )
    # TODO - Add Tier 2 - Vector DB Storage


@router.put("/prompt/cache")
async def cache_prompt_response(cache_data: PromptCacheInput) -> ORJSONResponse:
    """Store LLM response in cache for future reuse"""
    # Tier 1 - Store in StockDB Delta Table as Hash
    prompt_cache_table = StockDataDB(
        settings.stockdb.data_base_path / "common/prompt_cache"
    )

    current_cache_df = pl.LazyFrame({
        "prompt_hash": cache_data.get_cache_key(),
        "prompt": cache_data.prompt,
        "response": cache_data.response,
        "thinking": cache_data.thinking,
        "agent": cache_data.agent,
        "model": cache_data.model,
        "ttl": cache_data.ttl,
        "last_modified": datetime.now(),
    })

    prompt_cache_table.merge(
        current_cache_df.collect(),
        predicate="s.prompt_hash = t.prompt_hash",
    )

    # TODO - Add Tier 2 - Vector DB Storage

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Prompt cache stored successfully."},
    )
