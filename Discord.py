from types import NoneType

import requests
import logging as logger
from time import sleep
from datetime import datetime, timezone


def calculate_time_left(expiration_date: str) -> (int, int, int, int):
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
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": token
        })

    def __del__(self):
        self.session.close()

    def test_endpoint(self):
        pass

    def token_is_valid(self) -> bool:
        logger.debug("Checking if the token is valid...")

        response = self.session.get(url=f"{self.uri}")

        if response.status_code == 200:
            logger.debug("Token is valid")
            return True

        if response.status_code == 429:
            logger.warning("Ratelimit reached! retrying in 30 seconds...")
            sleep(15)
            return self.token_is_valid()

        logger.debug("Token is invalid")

        return False

    def has_nitro_subscription(self):
        logger.debug("Checking if the nitro subscription is available...")
        response = self.session.get(url=self.uri)

        if response.status_code == 200:
            premium_type = response.json()["premium_type"]

            #ref https://discord.com/developers/docs/resources/user#user-object-premium-types
            return premium_type >= 1

        elif response.status_code == 429:
            logger.warning("Ratelimit reached! retrying in 30 seconds...")
            sleep(15)
            return self.has_nitro_subscription()

        raise Exception("Token Invalid!")

    def nitro_expires_in(self) -> list:
        logger.debug("Checking nitro expiration time...")

        response = self.session.get(url=f"{self.uri}" + "/billing/subscriptions")

        if response.status_code == 200:

            subscriptions = response.json()

            if type(subscriptions) is not list:
                raise Exception("API returned no list")

            expiration_times = []

            for subscription in subscriptions:
                expiration_time = subscription["current_period_end"]

                (days, hours, minutes, seconds) = calculate_time_left(expiration_time)

                expiration_times.append((days, hours, minutes, seconds))


            return expiration_times
        if response.status_code == 429:
            logger.warning("Ratelimit reached! retrying in 30 seconds...")

            return self.nitro_expires_in()


        raise Exception("Token Invalid!")

    def get_server_boosts_left(self) -> int:
        response = self.session.get(url=f"{self.uri}/guilds/premium/subscription-slots")

        if response.status_code == 200:
            boosts = response.json()


            if not boosts or len(boosts) == 0:
                return 0

            boosts_left = sum(
                1 for boost in boosts
                if boost.get("premium_guild_subscription") is not NoneType and not boost.get("canceled", True)
            )
            return boosts_left

        elif response.status_code == 429:
            logger.warning("Rate limit reached while fetching server boosts.")
            return 0

        else:
            logger.error(f"Failed to fetch server boosts: {response.status_code}")
            return 0

    def get_verification_status(self) -> bool:
        response = self.session.get(url=self.uri)

        if response.status_code == 200:
            body = response.json()
            return body["verified"]

        if response.status_code == 429:
            logger.warning("Ratelimit reached! retrying in 30 seconds...")
            sleep(30)
            return self.get_verification_status()

        raise Exception("Token Invalid!")

    def account_is_more_then_year_old(self) -> bool:
        response = self.session.get(url=self.uri)
        if response.status_code == 200:
            epoch = 1420070400000

            timestamp = (int(response.json()["id"]) >> 22) + epoch
            creation_date = datetime.fromtimestamp(timestamp / 1000)
            now_date = datetime.fromtimestamp(datetime.now().timestamp())

            age = now_date - creation_date

            return age.days > 360

        if response.status_code == 429:
            logger.warning("Ratelimit reached! retrying in 30 seconds...")
            sleep(30)
            return self.account_is_more_then_year_old()

        raise Exception("Token Invalid!")