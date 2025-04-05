import aiohttp
import asyncio
import logging as logger
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def calculate_time_left(expiration_date: str) -> tuple[int, int, int, int]:
    current_date = datetime.now(timezone.utc)
    subscription_end = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
    remaining_time = subscription_end - current_date

    days = remaining_time.days
    total_seconds = remaining_time.total_seconds()
    hours = (total_seconds // 3600) % 24
    minutes = (total_seconds // 60) % 60
    seconds = total_seconds % 60

    return days, int(hours), int(minutes), int(seconds)


class Discord:
    def __init__(self, token: str):
        self.uri = "https://discord.com/api/v9/users/@me"
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None
        self._user_cache: Optional[Dict[str, Any]] = None
        self._subscriptions_cache: Optional[list] = None
        self._boosts_cache: Optional[list] = None

    async def __aenter__(self):
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close_session()

    async def init_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": self.token},
                timeout=aiohttp.ClientTimeout(total=10)
            )

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(self, method: str, url: str) -> Optional[dict]:
        await self.init_session()
        while True:
            try:
                async with self.session.request(method, url) as response:
                    if response.status == 429:
                        retry_after = float(response.headers.get("Retry-After", 30))
                        logger.warning(f"Ratelimit reached! Retrying in {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status == 200:
                        return await response.json()
                    else:
                        logger.debug(f"Request to {url} failed with status {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.warning("Request timed out, retrying...")

                continue

    async def _get_user_data(self) -> Optional[dict]:
        if self._user_cache is None:
            self._user_cache = await self._request("GET", self.uri)
        return self._user_cache

    async def _get_subscriptions(self) -> list:
        if self._subscriptions_cache is None:
            url = f"{self.uri}/billing/subscriptions"
            self._subscriptions_cache = await self._request("GET", url) or []
        return self._subscriptions_cache

    async def _get_boosts(self) -> list:
        if self._boosts_cache is None:
            url = f"{self.uri}/guilds/premium/subscription-slots"
            self._boosts_cache = await self._request("GET", url) or []
        return self._boosts_cache

    async def token_is_valid(self) -> bool:
        return await self._get_user_data() is not None

    async def has_nitro_subscription(self) -> bool:
        data = await self._get_user_data()
        return data and data.get("premium_type", 0) >= 1

    async def get_nitro_type(self) -> str:
        data = await self._get_user_data()
        if not data:
            raise Exception("Token Invalid!")

        types = {
            0: "None",
            1: "Nitro Classic",
            2: "Nitro",
            3: "Nitro Basic"
        }
        return types.get(data.get("premium_type", 0), "Unknown")

    async def nitro_expires_in(self) -> list[tuple[int, int, int, int]]:
        subs = await self._get_subscriptions()
        if not isinstance(subs, list):
            return [(0, 0, 0, 0)]

        return [calculate_time_left(sub["current_period_end"]) for sub in subs]

    async def get_server_boosts_left(self) -> int:
        boosts = await self._get_boosts()
        return sum(
            1 for boost in boosts
            if boost.get("premium_guild_subscription") and not boost.get("canceled", True)
        )

    async def get_verification_status(self) -> bool:
        data = await self._get_user_data()
        return data.get("verified", False) if data else False

    async def account_is_more_then_year_old(self) -> bool:
        data = await self._get_user_data()
        if not data:
            return False

        epoch = 1420070400000
        timestamp = (int(data["id"]) >> 22) + epoch
        creation_date = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        return (datetime.now(timezone.utc) - creation_date).days > 360

    async def get_email(self) -> str:
        data = await self._get_user_data()
        return data.get("email", "") if data else ""

    async def get_username(self) -> str:
        data = await self._get_user_data()
        return data.get("username", "Unknown") if data else "Unknown"

    async def get_phone(self) -> str:
        data = await self._get_user_data()
        return data.get("phone", "") if data else ""

    async def get_mfa_enabled(self) -> bool:
        data = await self._get_user_data()
        return data.get("mfa_enabled", False) if data else False

    async def get_all_data_parallel(self) -> dict:

        user_data, subs, boosts = await asyncio.gather(
            self._get_user_data(),
            self._get_subscriptions(),
            self._get_boosts()
        )

        return {
            "valid": user_data is not None,
            "username": user_data.get("username") if user_data else "Unknown",
            "nitro": self.get_nitro_type.__wrapped__(self),
            "email": user_data.get("email") if user_data else "",
            "phone": user_data.get("phone") if user_data else "",
            "mfa_enabled": user_data.get("mfa_enabled") if user_data else False,
            "verified": user_data.get("verified") if user_data else False,
            "account_age": await self.account_is_more_then_year_old(),
            "boosts_left": sum(
                1 for b in boosts
                if b.get("premium_guild_subscription") and not b.get("canceled", True)
            ),
            "subscriptions": [
                calculate_time_left(sub["current_period_end"])
                for sub in subs
                if isinstance(subs, list)
            ]
        }
