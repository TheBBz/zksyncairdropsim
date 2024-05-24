# utils.py
import aiohttp
from decimal import Decimal
from django.utils import timezone
from .models import EthUsdRate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from asgiref.sync import sync_to_async
import os
from dotenv import load_dotenv

load_dotenv()

@retry(retry=retry_if_exception_type(Exception), stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_eth_to_usd_rate():
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=ETH'
    api_key = os.getenv('COINMARKETCAP_API_KEY')
    if not api_key:
        raise ValueError("COINMARKETCAP_API_KEY environment variable is not set")

    headers = {
        'X-CMC_PRO_API_KEY': api_key,
        'Accepts': 'application/json'
    }
    
    print("Headers used for request:", headers)  # Debugging output

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch ETH to USD rate: {response.status} {response.reason}")
                    raise Exception(f"Failed to fetch ETH to USD rate: {response.status} {response.reason}")
                data = await response.json()
                if 'data' not in data or 'ETH' not in data['data'] or 'quote' not in data['data']['ETH'] or 'USD' not in data['data']['ETH']['quote'] or 'price' not in data['data']['ETH']['quote']['USD']:
                    print(f"Unexpected response format: {data}")
                    raise Exception(f"Unexpected response format: {data}")
                return Decimal(data['data']['ETH']['quote']['USD']['price'])
        except Exception as e:
            print(f"Exception occurred while fetching ETH to USD rate: {e}")
            raise

async def get_eth_to_usd_rate():
    rate_entry = await sync_to_async(EthUsdRate.objects.first)()
    if rate_entry is None or timezone.now() - rate_entry.timestamp > timezone.timedelta(hours=1):
        rate = await fetch_eth_to_usd_rate()
        if rate_entry is None:
            rate_entry = EthUsdRate(rate=rate, timestamp=timezone.now())
        else:
            rate_entry.rate = rate
            rate_entry.timestamp = timezone.now()
        await sync_to_async(rate_entry.save)()
    return rate_entry.rate
