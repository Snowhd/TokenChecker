import logging as logger
import os
import Discord


class TokenChecker:

    def __init__(self, tokens: list[str]):
        self.clients = [Discord.Discord(token) for token in tokens]

    def check_tokens(self):
        valid_tokens = []
        invalid_tokens = []

        for client in reversed(self.clients):
            try:
                if not client.token_is_valid():
                    invalid_tokens.append(client.token)
                    continue

                account_is_more_then_a_year_old = client.account_is_more_then_year_old()
                days, hours, minutes, seconds = client.nitro_expires_in()[0]
                server_boosts_left = client.get_server_boosts_left()
                verified = client.get_verification_status()
                has_nitro = client.has_nitro_subscription()

                logger.info(
                    f"Token: {client.token}\n"
                    f"  - Status: {'Verified' if verified else 'Unverified'}\n"
                    f"  - Valid Age: {'1+ years' if account_is_more_then_a_year_old else 'Under a year'}\n"
                    f"  - Has Nitro: {has_nitro}\n"
                    f"  - Nitro Expiry: {days} days {hours} hours {minutes} minutes\n"
                    f"  - Boosts Left: {server_boosts_left}"
                )
                valid_tokens.append(client.token)
            except Exception as e:
                logger.error(f"Error processing token {client.token}: {e}")
                invalid_tokens.append(client.token)

        self.write_to_file("./data/valid_tokens.txt", valid_tokens)
        self.write_to_file("./data/invalid_tokens.txt", invalid_tokens)

    def write_to_file(self, file: str, tokens: list[str]):
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w") as filepath:
            filepath.write("\n".join(tokens))
        logger.info(f"Wrote {len(tokens)} tokens to {file}")


def read_tokens_from_file(file: str) -> list[str]:
    filepath = os.path.join(os.path.dirname(__file__), file)

    if not os.path.exists(filepath):
        logger.error(f"File {filepath} does not exist.")
        return []
    with open(filepath, "r") as file:
        return [line.strip() for line in file.readlines() if line.strip()]


if __name__ == "__main__":
    logger.basicConfig(
        level=logger.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logger.StreamHandler()
        ]
    )


    tokens = read_tokens_from_file("./data/tokens.txt")
    TokenChecker(tokens).check_tokens()
