# views.py

import asyncio
import aiohttp
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .utils import get_eth_to_usd_rate
from .models import EthUsdRate
from web3 import Web3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from .api_key_manager import etherscan_api_key_manager
from dotenv import load_dotenv
from asgiref.sync import async_to_sync

load_dotenv()

web3 = Web3(Web3.HTTPProvider(os.getenv('WEB3_PROVIDER_URL')))

ZKSYNC_API_URL = os.getenv('ZKSYNC_API_URL')
ETHERSCAN_API_URL = os.getenv('ETHERSCAN_API_URL')
BRIDGE_CONTRACT_ADDRESS = os.getenv('BRIDGE_CONTRACT_ADDRESS')

translations = {
    'en': {
        'eth_to_usd_rate': "ETH to USD rate",
        'days_of_activity': "Days of activity",
        'weeks_of_activity': "Weeks of activity",
        'months_of_activity': "Months of activity",
        'unique_contract_interactions': "Unique contract interactions",
        'volume_in_eth': "Volume in ETH",
        'volume_in_usd': "Volume in USD",
        'volume_bridged_in_eth': "Volume bridged in ETH",
        'volume_bridged_in_usd': "Volume bridged in USD",
        'points': "Points",
        'total_zks': "Total ZKS"
    },
    'es': {
        'eth_to_usd_rate': "Tasa de ETH a USD",
        'days_of_activity': "Días de actividad",
        'weeks_of_activity': "Semanas de actividad",
        'months_of_activity': "Meses de actividad",
        'unique_contract_interactions': "Interacciones únicas con contratos",
        'volume_in_eth': "Volumen en ETH",
        'volume_in_usd': "Volumen en USD",
        'volume_bridged_in_eth': "Volumen puenteado en ETH",
        'volume_bridged_in_usd': "Volumen puenteado en USD",
        'points': "Puntos",
        'total_zks': "Total ZKS"
    }
}

async def fetch_zksync_transactions(wallet_address):
    all_transactions = []
    async with aiohttp.ClientSession() as session:
        page = 1
        while True:
            url = f"{ZKSYNC_API_URL}?module=account&action=txlist&address={wallet_address}&page={page}&offset=10"
            try:
                async with session.get(url) as response:
                    response_data = await response.json()
                    if response.status == 200:
                        if response_data['status'] == '1':
                            transactions = response_data['result']
                            if not transactions:
                                break
                            all_transactions.extend(transactions)
                            page += 1
                        elif response_data['status'] == '0' and response_data['message'] == 'No transactions found':
                            break
                        else:
                            print(f"Error: zkSync API returned status {response_data['status']} with message {response_data['message']}")
                            raise Exception("Unexpected response format or status code not 200")
                    else:
                        print(f"Error: HTTP status code {response.status} from zkSync API")
                        print(await response.text())
                        raise Exception(f"HTTP status code {response.status} from zkSync API")
            except Exception as e:
                print(f"Exception occurred while fetching transactions from zkSync API: {e}")
                raise
    return all_transactions

async def fetch_zksync_balance(wallet_address):
    url = f"{ZKSYNC_API_URL}?module=account&action=balance&address={wallet_address}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response_data = await response.json()
                if response.status == 200 and response_data['status'] == '1':
                    balance = response_data['result']
                    return Decimal(web3.from_wei(int(balance), 'ether'))
                else:
                    print(f"Error: zkSync API returned status {response_data['status']} with message {response_data['message']}")
                    raise Exception("Unexpected response format or status code not 200")
        except Exception as e:
            print(f"Exception occurred while fetching balance from zkSync API: {e}")
            raise

async def fetch_mainnet_bridge_interactions(wallet_address, bridge_contract_address):
    all_transactions = []
    async with aiohttp.ClientSession() as session:
        page = 1
        retries = 0
        while True:
            current_api_key = etherscan_api_key_manager.get_current_key()
            url = (f"{ETHERSCAN_API_URL}?module=account&action=txlist&address={wallet_address}"
                   f"&startblock=0&endblock=99999999&page={page}&offset=10&sort=asc&apikey={current_api_key}")
            try:
                async with session.get(url) as response:
                    response_data = await response.json()
                    if response.status == 200:
                        if response_data['status'] == '1':
                            transactions = response_data['result']
                            if not transactions:
                                break
                            all_transactions.extend(transactions)
                            page += 1
                        elif response_data['status'] == '0' and response_data['message'] == 'No transactions found':
                            break
                        elif response_data['message'] == 'Max rate limit reached':
                            print(f"Rate limit reached with API key: {current_api_key}")
                            etherscan_api_key_manager.switch_key()
                            retries += 1
                            if retries > len(etherscan_api_key_manager.api_keys):
                                raise Exception("All API keys have reached the rate limit")
                        else:
                            print(f"Error: Etherscan API returned status {response_data['status']} with message {response_data['message']}")
                            print(f"Response data: {response_data}")
                            raise Exception("Unexpected response format or status code not 200")
                    else:
                        print(f"Error: HTTP status code {response.status} from Etherscan API")
                        print(await response.text())
                        raise Exception(f"HTTP status code {response.status} from Etherscan API")
            except Exception as e:
                print(f"Exception occurred while fetching transactions from Etherscan API: {e}")
                raise
            finally:
                await asyncio.sleep(1)  # Add delay to prevent hitting rate limit

    bridge_volume_eth = Decimal(0)
    bridge_count = 0

    for tx in all_transactions:
        to_address = tx['to']
        value_eth = Decimal(web3.from_wei(int(tx['value']), 'ether'))
        if to_address.lower() == bridge_contract_address.lower():
            bridge_volume_eth += value_eth
            bridge_count += 1

    return bridge_volume_eth, bridge_count

def analyze_transactions(transactions, eth_to_usd_rate):
    activity = {'daily': 0, 'weekly': 0, 'monthly': 0}
    volume_eth = Decimal(0)
    fees_eth = Decimal(0)
    unique_contracts = set()

    today = datetime.now(timezone.utc)
    one_day_ago = today - timedelta(days=1)
    one_week_ago = today - timedelta(weeks=1)
    one_month_ago = today - timedelta(days=30)

    daily_activity = set()
    weekly_activity = set()
    monthly_activity = set()

    for tx in transactions:
        tx_time = datetime.fromtimestamp(int(tx['timeStamp']), tz=timezone.utc)
        value_eth = Decimal(web3.from_wei(int(tx['value']), 'ether'))
        gas_fee_eth = Decimal(web3.from_wei(int(tx.get('gasUsed', 0)) * int(tx.get('gasPrice', 0)), 'ether'))
        to_address = tx['to']

        daily_activity.add(tx_time.date())
        weekly_activity.add(tx_time.isocalendar()[:2])
        monthly_activity.add((tx_time.year, tx_time.month))

        volume_eth += value_eth
        fees_eth += gas_fee_eth

        if to_address not in unique_contracts:
            unique_contracts.add(to_address)

    activity['daily'] = len(daily_activity)
    activity['weekly'] = len(weekly_activity)
    activity['monthly'] = len(monthly_activity)

    volume_usd = volume_eth * eth_to_usd_rate
    fees_usd = fees_eth * eth_to_usd_rate

    return activity, volume_eth, volume_usd, fees_eth, fees_usd, unique_contracts

async def check_zksync_lite_activity(wallet_address):
    url = f"https://api.zksync.io/api/v0.1/account/{wallet_address}/history/0/1"  # Fetch the latest transaction
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response_data = await response.json()
                if response.status == 200 and response_data:
                    return True  # There is at least one transaction
                else:
                    return False  # No transactions found or unexpected response
        except Exception as e:
            print(f"Exception occurred while fetching zkSync Lite transactions: {e}")
            return False  # Treat exceptions as no activity

def calculate_airdrop_eligibility(activity, volume_eth, volume_usd, fees_eth, fees_usd, unique_contracts, bridge_volume_eth, bridge_volume_usd, bridge_count, current_balance_usd, eth_mainnet_activity, total_transactions, zksync_lite_activity):
    zks = 0
    details = []

    daily_points = activity['daily'] * 20
    zks += daily_points
    details.append(f"Days of activity: {activity['daily']} (Points: {daily_points})")

    weekly_points = activity['weekly'] * 100
    zks += weekly_points
    details.append(f"Weeks of activity: {activity['weekly']} (Points: {weekly_points})")

    monthly_points = activity['monthly'] * 400
    zks += monthly_points
    details.append(f"Months of activity: {activity['monthly']} (Points: {monthly_points})")

    unique_contracts_points = len(unique_contracts) * 50
    zks += unique_contracts_points
    details.append(f"Unique contract interactions: {len(unique_contracts)} (Points: {unique_contracts_points})")

    volume_points = (volume_usd // 100) * 20
    zks += volume_points
    details.append(f"Volume in ETH: {volume_eth:.6f} (Volume in USD: {volume_usd:.2f}) (Points: {volume_points})")

    bridge_points = (bridge_volume_usd // 100) * 60
    zks += bridge_points
    details.append(f"Volume bridged in ETH: {bridge_volume_eth:.6f} (Volume bridged in USD: {bridge_volume_usd:.2f}) (Points: {bridge_points})")

    if current_balance_usd < 5:
        zks -= 400
        details.append(f"Current balance in USD: {current_balance_usd:.2f} (Points: -400)")

    if not eth_mainnet_activity:
        zks -= 800
        details.append("No activity on ETH mainnet (Points: -800)")

    if volume_usd < 100:
        zks -= 800
        details.append(f"Volume less than $100 (Points: -800)")

    if total_transactions < 25:
        zks -= 1200
        details.append(f"Less than 25 transactions (Points: -1200)")

    if not zksync_lite_activity:
        zks -= 500  # Deduct points if no zkSync Lite activity
        details.append("No activity on zkSync Lite (Points: -500)")

    is_eligible = zks >= 400
    details.append(f"Total ZKS: {zks}")

    return zks, is_eligible, details

@csrf_exempt
def index(request):
    if request.method == 'GET':
        return render(request, 'analyzer/index.html')
    
@csrf_exempt
def analyze_wallet(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        wallet_address = data['wallet_address']
        language = data.get('language', 'en')  # Default to English if not specified

        async def analyze_wallet_async():
            eth_to_usd_rate = await get_eth_to_usd_rate()
            if eth_to_usd_rate is None:
                return JsonResponse({"error": "Error fetching ETH to USD rate"}, status=400)

            transactions = await fetch_zksync_transactions(wallet_address)
            if transactions is None:
                return JsonResponse({"error": "Error fetching transactions or invalid response"}, status=400)

            activity, volume_eth, volume_usd, fees_eth, fees_usd, unique_contracts = analyze_transactions(transactions, eth_to_usd_rate)

            current_balance_eth = await fetch_zksync_balance(wallet_address)
            if current_balance_eth is None:
                return JsonResponse({"error": "Error fetching current balance or invalid response"}, status=400)
            current_balance_usd = current_balance_eth * eth_to_usd_rate

            bridge_volume_eth, bridge_count = await fetch_mainnet_bridge_interactions(wallet_address, BRIDGE_CONTRACT_ADDRESS)
            if bridge_volume_eth is None or bridge_count is None:
                return JsonResponse({"error": "Error fetching bridge interactions or invalid response"}, status=400)
            bridge_volume_usd = bridge_volume_eth * eth_to_usd_rate

            eth_mainnet_activity = bridge_count > 0

            total_transactions = len(transactions)

            # Check zkSync Lite activity
            zksync_lite_activity = await check_zksync_lite_activity(wallet_address)

            zks, is_eligible, details = calculate_airdrop_eligibility(
                activity, volume_eth, volume_usd, fees_eth, fees_usd, unique_contracts, bridge_volume_eth, bridge_volume_usd, bridge_count, current_balance_usd, eth_mainnet_activity, total_transactions, zksync_lite_activity
            )

            result = {
                "eth_to_usd_rate": float(eth_to_usd_rate),
                "zks": zks,
                "is_eligible": is_eligible,
                "details": details,
                "zksync_lite_activity": zksync_lite_activity
            }

            return JsonResponse(result)

        return async_to_sync(analyze_wallet_async)()

    return JsonResponse({'error': 'Invalid request method'}, status=400)
