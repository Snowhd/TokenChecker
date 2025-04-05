import logging as logger
import os
import discord

# ANSI-Farbcodes für verschiedene Log-Levels
COLOR_MAP = {
    'DEBUG': '\033[37m',      # Grau
    'INFO': '\033[36m',       # Cyan
    'WARNING': '\033[33m',    # Gelb
    'ERROR': '\033[31m',      # Rot
    'CRITICAL': '\033[41m',   # Rot mit Hintergrund
}
RESET = '\033[0m'


class ColorFormatter(logger.Formatter):
    def format(self, record):
        log_color = COLOR_MAP.get(record.levelname, '')
        message = super().format(record)
        return f"{log_color}{message}{RESET}"


class TokenChecker:
    def __init__(self, tokens: list[str]):
        self.clients = [discord.Discord(token) for token in tokens]

    def check_tokens(self):
        valid_tokens = []
        invalid_tokens = []

        logger.info("=== starting token checks ===")
        logger.info(f"found {len(self.clients)} tokens: ")

        for i, client in enumerate(reversed(self.clients), 1):
            try:
                if not client.token_is_valid():
                    logger.warning(f"[{i}] invalid token → {client.token[:10]}...")
                    invalid_tokens.append(client.token)
                    continue

                account_age_check = client.account_is_more_then_year_old()
                days, hours, minutes, seconds = client.nitro_expires_in()[0]
                server_boosts_left = client.get_server_boosts_left()
                verified = client.get_verification_status()
                has_nitro = client.has_nitro_subscription()
                nitro_type = client.get_nitro_type()
                user_tag = client.get_username()
                email = client.get_email()
                phone = client.get_phone()
                mfa_enabled = client.get_mfa_enabled()

                logger.info("-" * 50)
                logger.info(f"[{i}] Token: {client.token[:10]}... ({user_tag})")
                logger.info(f"  • Email: {email}")
                logger.info(f"  • Phone: {phone}")
                logger.info(f"  • Status: {'✅ verified' if verified else '❌ not verified'}")
                logger.info(f"  • MFA enabled: {mfa_enabled}")
                logger.info(f"  • Age: {'✅ >1 year' if account_age_check else '❌ <1 year'}")
                logger.info(f"  • Nitro: {'✅' if has_nitro else '❌'} – Type: {nitro_type}")
                logger.info(f"  • Nitro expires in: {days}d {hours}h {minutes}m")
                logger.info(f"  • Boosts left: {server_boosts_left}")
                logger.info("-" * 50)

                valid_tokens.append(client.token)
            except Exception as e:
                logger.error(f"[{i}] couldn't process token {client.token[:10]}...: {e}")
                invalid_tokens.append(client.token)

        logger.info("=== finished token checks ===")
        self.write_to_file("./data/valid_tokens.txt", valid_tokens)
        self.write_to_file("./data/invalid_tokens.txt", invalid_tokens)

    def write_to_file(self, file: str, tokens: list[str]):
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w") as f:
            f.write("\n".join(tokens))
        logger.info(f"✔️ {len(tokens)} tokens saved in '{file}'.")


def read_tokens_from_file(file: str) -> list[str]:
    filepath = os.path.join(os.path.dirname(__file__), file)

    if not os.path.exists(filepath):
        logger.error(f"❌ file not found: {filepath}")
        return []
    with open(filepath, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


if __name__ == "__main__":
    handler = logger.StreamHandler()
    handler.setFormatter(ColorFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s'
    ))

    logger.basicConfig(
        level=logger.INFO,
        handlers=[handler]
    )

    tokens = read_tokens_from_file("./data/tokens.txt")
    TokenChecker(tokens).check_tokens()
