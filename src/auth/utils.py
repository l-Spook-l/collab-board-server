import httpx

from src.core.config import settings


async def get_auth0_public_key() -> dict:
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    return response.json()
