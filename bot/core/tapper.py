import asyncio
from time import time
from urllib.parse import unquote, quote

import aiohttp
from aiocfscrape import CloudflareScraper
from pyrogram import Client
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.types import InputBotAppShortName
from pyrogram.raw.functions.messages import RequestAppWebView
from bot.core.agents import generate_random_user_agent, fetch_version
from bot.config import settings

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers

from random import randint, uniform
from bot.utils.ps import check_base_url
import sys

api_login = "https://gm.pocketfi.org/mining/getUserMining"


class Tapper:
    def __init__(self, tg_client: Client):
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.first_name = ''
        self.last_name = ''
        self.user_id = ''
        self.Total_Point_Earned = 0
        self.Total_Game_Played = 0
        self.can_claim = 0
        self.new_account = False

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if settings.REF_LINK == '':
            ref_param = "6624523270"
        else:
            ref_param = settings.REF_LINK.split('=')[1]
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('pocketfi_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | FloodWait {fl}")
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotAppShortName(bot_id=peer, short_name="Mining"),
                platform='android',
                write_allowed=True,
                start_param=ref_param
            ))

            auth_url = web_view.url
            tg_web_data = unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    async def get_info_data(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(api_login, ssl=False)
            response.raise_for_status()

            response_json = await response.json()
            if response_json['userMining'] is None:
                self.new_account = True
                return
            else:
                logger.info(
                    f"{self.session_name} | <white>Balance: </white><cyan>{response_json['userMining']['gotAmount']}</cyan> | <white>Speed: </white><cyan>{response_json['userMining']['speed']}</cyan> | <white>Available for claim: </white><red>{response_json['userMining']['miningAmount']}</red>")
                self.can_claim = float(response_json['userMining']['miningAmount'])

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def claim(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post("https://gm.pocketfi.org/mining/claimMining", ssl=False)
            response.raise_for_status()

            # response_json = await response.json()

            if response.status == 200:
                logger.success(f"{self.session_name} <green>Successfully claimed {self.can_claim} $switch!</green>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claim mining reward: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def claim_daily_rw(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post("https://bot.pocketfi.org/boost/activateDailyBoost", ssl=False)
            response.raise_for_status()

            # response_json = await response.json()
            if response.status == 200:
                logger.success(f"{self.session_name} <green>Successfully claimed daily reward!</green>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claim daily reward: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def create_new_account(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post("https://gm.pocketfi.org/mining/createUserMining", ssl=False)
            response.raise_for_status()

            # response_json = await response.json()
            if response.status == 200:
                logger.success(f"{self.session_name} <green>Successfully created new account!</green>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when create account!: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_daily(self, http_client: aiohttp.ClientSession):
        response = await http_client.get("https://bot.pocketfi.org/boost/tasks?boostType=general", ssl=False)

        if response.status == 200:
            data = await response.json()
            for task in data['tasks']['daily']:
                if task['code'] == "dailyReward":
                    if task['doneAmount'] == 0:
                        await self.claim_daily_rw(http_client)
                    else:
                        return
        else:
            logger.info(f"{self.session_name} | Failed to fetch tasks list")

    async def run(self, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        chrome_ver = fetch_version(headers['User-Agent'])
        headers['Sec-Ch-Ua'] = f'"Chromium";v="{chrome_ver}", "Android WebView";v="{chrome_ver}", "Not.A/Brand";v="99"'
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        token_live_time = randint(1 * 3600, 3 * 3600)
        while True:
            can_run = True
            try:
                if check_base_url() is False:
                    can_run = False
                    if settings.ADVANCED_ANTI_DETECTION:
                        logger.warning(
                            "<yellow>Detected index js file change. Contact me to check if it's safe to continue: https://t.me/vanhbakaaa</yellow>")
                    else:
                        logger.warning(
                            "<yellow>Detected api change! Stoped the bot for safety. Contact me here to update the bot: https://t.me/vanhbakaaa</yellow>")

                if can_run:
                    if time() - access_token_created_time >= token_live_time:
                        tg_web_data = await self.get_tg_web_data(proxy=proxy)
                        http_client.headers['telegramrawdata'] = tg_web_data
                        access_token_created_time = time()
                        token_live_time = randint(1 * 3600, 3 * 3600)

                        await asyncio.sleep(delay=randint(10, 15))

                    await self.get_info_data(http_client)
                    if self.new_account is True:
                        await self.create_new_account(http_client)
                        await asyncio.sleep(1)
                        await self.get_info_data(http_client)
                    await self.check_daily(http_client)
                    if self.can_claim > 0.2:
                        await self.claim(http_client)

                    sleep_time = round(uniform(2, 4), 1)

                    logger.info(f"{self.session_name} | Sleep <y>{sleep_time}</y> hours")
                    await asyncio.sleep(delay=sleep_time * 3600)
                else:
                    await asyncio.sleep(120)
                    logger.info(f"{self.session_name} | Sleep <y>{120}</y> seconds...")
            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        sleep_ = randint(1, 30)
        logger.info(f"{tg_client.name} | Start after {sleep_}s...")
        await asyncio.sleep(sleep_)
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
