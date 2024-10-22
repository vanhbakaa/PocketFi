from bot.config import settings
import requests
import re
from bot.utils import logger

baseUrl = "https://gm.pocketfi.org"

block_pattern = re.compile(r"""
    Oe\s*=\s*\{         # Matches 'Oe = {'
    \s*addressActivityHook:\s*"/addressActivity",\s*
    getStableCoinsAndEth:\s*"/getStableCoinsAndEth",\s*
    startMonitoring:\s*"/startMonitoring",\s*
    listNotificationsForUser:\s*"/listNotificationsForUser",\s*
    tgSwap:\s*"/tgSwap",\s*
    tgMakeSwap:\s*"/tgMakeSwap",\s*
    tgUserWallets:\s*"/tgUserWallets",\s*
    knownTokens:\s*"/knownTokens",\s*
    fetchRoute:\s*"/fetchRoute",\s*
    swap:\s*"/swap",\s*
    balances:\s*"/balances",\s*
    history:\s*"/history",\s*
    totalBalance:\s*"/totalBalance",\s*
    address:\s*"/address",\s*
    transfer:\s*"/transfer",\s*
    subscription:\s*"/getCopyTrades",\s*
    postSubscription:\s*"/startMonitoringCopyTrade",\s*
    cancelSubscription:\s*"/cancelCopyTrade",\s*
    getUserTransaction:\s*"/getUserSwaps",\s*
    createPresetSwap:\s*"/createPresetSwap",\s*
    getPresetTokens:\s*"/getPresetTokens",\s*
    createUserMining:\s*"/mining/createUserMining",\s*
    getUserMining:\s*"/mining/getUserMining",\s*
    claimMining:\s*"/mining/claimMining",\s*
    miningTasks:\s*"/boost/tasks",\s*
    setTonWallet:\s*"/mining/setTonWallet",\s*
    miningGuilds:\s*"/mining/guilds",\s*
    miningAlliancesGuilds:\s*"/mining/alliances/guilds",\s*
    miningAlliances:\s*"/mining/alliances",\s*
    setMiningAlliance:\s*"/mining/alliances/set",\s*
    getMiningReferralStats:\s*"/mining/referralStats",\s*
    burnPunks:\s*"/burnPunks",\s*
    confirmSubscription:\s*"/confirmSubscription",\s*
    activateDailyBoost:\s*"/boost/activateDailyBoost",\s*
    getAirdrops:\s*"/boost/tasks",\s*
    checkEmoji:\s*"/boost/checkEmoji",\s*
    checkStakingPunks:\s*"/boost/checkPunkStaking",\s*
    listFriends:\s*"/mining/listFriends",\s*
    v2:\s*\{                 # Matches 'v2: {'
    \s*simulateTonSwap:\s*"/v2/tc/simulate-swap",\s*
    tonSwap:\s*"/v2/tc/swap"\s*
    \}\s*                    # Matches '}'
\}
""", re.VERBOSE)


def get_main_js_format(base_url):
    try:
        response = requests.get(base_url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        content = response.text
        matches = re.findall(r'src="([^"]*index-[^"]+\.js)"', content)
        if matches:
            # Return all matches, sorted by length (assuming longer is more specific)
            return sorted(set(matches), key=len, reverse=True)
        else:
            return None
    except requests.RequestException as e:
        logger.warning(f"Error fetching the base URL: {e}")
        return None

def get_base_api(url):
    try:
        logger.info("Checking for changes in api...")
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
        if settings.ADVANCED_CHECKER:
            if block_pattern.search(content):
                match = re.search(r'Du\s*=\s*"([^"]+)"', content)
                header = re.search(r'"x-paf-t":\s*"([A-Za-z0-9=]+)"', content)

                if match and header:
                    # print(match)
                    # print(header.group(1))
                    return [True, match.group(1), header.group(1)]
                else:
                    logger.info("Could not find 'api' in the content.")
                    return None
            else:
                return None
        else:
            match = re.search(r'Du\s*=\s*"([^"]+)"', content)
            header = re.search(r'"x-paf-t":\s*"([A-Za-z0-9=]+)"', content)

            if match and header:
                # print(match)
                # print(header.group(1))
                return [match.group(1), header.group(1)]
            else:
                logger.info("Could not find 'api' in the content.")
                return None
    except requests.RequestException as e:
        logger.warning(f"Error fetching the JS file: {e}")
        return None


def check_base_url():
    base_url = "https://pocketfi.app/mining"
    main_js_formats = get_main_js_format(base_url)

    if main_js_formats:
        for format in main_js_formats:
            logger.info(f"Trying format: {format}")
            full_url = f"https://pocketfi.app{format}"
            result = get_base_api(full_url)
            # print(f"{result} | {baseUrl}")
            if settings.ADVANCED_CHECKER:
                if result is None:
                    return False

                if baseUrl in result[1] and result[2] == "Abvx2NzMTM==" and result[0]:
                    logger.success(f"<green>No change in all api!</green>")
                    return True
                return False
            else:
                if baseUrl in result[0] and result[1] == "Abvx2NzMTM==":
                    logger.success("<green>No change in api!</green>")
                    return True
            return False
        else:
            logger.warning("Could not find 'baseURL' in any of the JS files.")
            return False
    else:
        logger.info("Could not find any main.js format. Dumping page content for inspection:")
        try:
            response = requests.get(base_url)
            print(response.text[:1000])  # Print first 1000 characters of the page
            return False
        except requests.RequestException as e:
            logger.warning(f"Error fetching the base URL for content dump: {e}")
            return False
