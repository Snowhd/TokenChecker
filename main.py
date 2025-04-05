import logging as logger
import os
import asyncio
from discord import Discord

COLOR_MAP = {
    'DEBUG': '\033[37m',
    'INFO': '\033[36m',
    'WARNING': '\033[33m',
    'ERROR': '\033[31m',
    'CRITICAL': '\033[41m',
}
RESET = '\033[0m'

class ColorFormatter(logger.Formatter):
    def format(self, record):
        log_color = COLOR_MAP.get(record.levelname, '')
        message = super().format(record)
        return f"{log_color}{message}{RESET}"

class TokenChecker:
    def __init__(self, tokens: list[str]):
        self.clients = [Discord(token) for token in tokens]

    async def check_token(self, client: Discord, index: int):
        try:
            async with client:
                if not await client.token_is_valid():
                    logger.warning(f"[{index}] invalid token → {client.token[:10]}...")
                    return None

                results = await asyncio.gather(
                    client.account_is_more_then_year_old(),
                    client.nitro_expires_in(),
                    client.get_server_boosts_left(),
                    client.get_verification_status(),
                    client.has_nitro_subscription(),
                    client.get_nitro_type(),
                    client.get_username(),
                    client.get_email(),
                    client.get_phone(),
                    client.get_mfa_enabled(),
                    return_exceptions=True
                )

                for result in results:
                    if isinstance(result, Exception):
                        raise result

                (
                    account_age_check,
                    nitro_expiry,
                    boosts,
                    verified,
                    has_nitro,
                    nitro_type,
                    user_tag,
                    email,
                    phone,
                    mfa_enabled
                ) = results

                days = nitro_expiry[0][0] if nitro_expiry else 0
                hours = nitro_expiry[0][1] if nitro_expiry else 0
                minutes = nitro_expiry[0][2] if nitro_expiry else 0
                seconds = nitro_expiry[0][3] if nitro_expiry else 0

                verification_status = 'email verified' if email else ('phone fully verified' if phone else 'not verified')
                logger.info(f"[{index}] Token={client.token[:10]}... Status={'valid' if verified else 'invalid'} Age={'>1 year' if account_age_check else '<1 year'} Verification={verification_status} HasNitro={has_nitro} NitroExpiry={days}d {hours}h {minutes}m {seconds}s LeftBoosts={boosts}")

                return client.token

        except Exception as e:
            logger.error(f"[{index}] couldn't process token {client.token[:10]}...: {str(e)[:100]}")
            return None

    async def check_tokens(self):
        valid_tokens = []
        invalid_tokens = []

        logger.info("=== starting token checks ===")
        logger.info(f"found {len(self.clients)} tokens: ")

        semaphore = asyncio.Semaphore(10)

        async def limited_check(client, index):
            async with semaphore:
                return await self.check_token(client, index)

        tasks = [limited_check(client, i) for i, client in enumerate(self.clients, 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if result and not isinstance(result, Exception):
                valid_tokens.append(result)
            else:
                invalid_tokens.append(None)

        logger.info("=== finished token checks ===")
        self.write_to_file("./data/valid_tokens.txt", valid_tokens)
        self.write_to_file("./data/invalid_tokens.txt", [t for t in self.clients if t.token not in valid_tokens])

    def write_to_file(self, file: str, tokens: list):
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w") as f:
            if "invalid" in file:
                f.write("\n".join([client.token for client in tokens]))
            else:
                f.write("\n".join(tokens))
        logger.info(f"✔️ {len(tokens)} tokens saved in '{file}'.")

def read_tokens_from_file(file: str) -> list[str]:
    filepath = os.path.join(os.path.dirname(__file__), file)

    if not os.path.exists(filepath):
        logger.error(f"❌ file not found: {filepath}")
        return []
    with open(filepath, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

async def main():
    tokens = read_tokens_from_file("./data/tokens.txt")
    checker = TokenChecker(tokens)
    try:
        await checker.check_tokens()
    finally:
        await asyncio.gather(*[client.close_session() for client in checker.clients])

if __name__ == "__main__":
    handler = logger.StreamHandler()
    handler.setFormatter(ColorFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s'
    ))

    logger.basicConfig(
        level=logger.INFO,
        handlers=[handler]
    )

    asyncio.run(main())
