import aiohttp
import json
import numpy as np
import hashlib
from typing import List, Dict, Any
import logging

from config import config

logger = logging.getLogger(__name__)

class AIService:

    def __init__(self):
        self.api_key = config.DASHSCOPE_API_KEY
        self.base_url = config.DASHSCOPE_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def get_embedding(self, text: str) -> List[float]:
        if not self.api_key:
            error_msg = "Invalid API key. Please configure a valid DashScope API key."
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{self.base_url}/embeddings",
                        headers=self.headers,
                        json={
                            "model": config.EMBEDDING_MODEL,
                            "input": text,
                            "encoding_format": "float"
                        },
                        timeout=config.EMBEDDING_TIMEOUT
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        embedding = result["data"][0]["embedding"]
                        logger.info(f"Generated embedding: {len(embedding)} dimensions")
                        return embedding
                    else:
                        error_text = await response.text()
                        error_msg = f"API error {response.status}: {error_text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            raise Exception(f"Failed to generate embedding: {str(e)}")

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.api_key:
            error_msg = "Invalid API key. Please configure a valid DashScope API key."
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            data = {
                "model": config.CHAT_MODEL,
                "messages": messages,
                "stream": False,
                "max_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.7)
            }

            logger.info(f"Calling DashScope API with model: {config.CHAT_MODEL}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=data,
                        timeout=config.API_TIMEOUT
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        error_msg = f"Chat API error {response.status}: {error_text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            raise Exception(f"Failed to get chat completion: {str(e)}")

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

ai_service = AIService()