import requests
import json
from datetime import datetime, timedelta
import os
import time

def fetch_btc_prices(cache_file="btc_prices_cache.json"):
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        cache_time = datetime.fromisoformat(cache['timestamp'])
        if datetime.now() - cache_time < timedelta(hours=24):
            print("Using the cached data")
            return cache['prices']
        else:
            print("Cache is older than 24 hrs. Fetching new data")
    else:
        print("No cache file found. Fetching new data")
    
    # Calculate the date range
    end_date = datetime.now().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)  # 30 days including end_date
    
    # Fetch data using the CoinGecko API
    url = "https://coingecko.p.rapidapi.com/coins/bitcoin/market_chart"
    querystring = {"vs_currency":"usd","days":"30"}
    headers = {
        'x-rapidapi-key': "8f05d53640msh4e942fea474e13cp129680jsna8bbe9bf3d7b",
        'x-rapidapi-host': "coingecko.p.rapidapi.com"
    }

    max_retries = 5
    for i in range(max_retries):
        response = requests.get(url, headers=headers, params=querystring)
        
        if response.status_code == 200:
            data = response.json()['prices']
            daily_prices = []
            for timestamp, price in data:
                date = datetime.fromtimestamp(timestamp / 1000).date()
                if start_date <= date <= end_date:
                    daily_prices.append([date.isoformat(), price])
            
            if len(daily_prices) > 30:
                daily_prices = daily_prices[-30:]
            elif len(daily_prices) < 30:
                raise Exception(f"Not enough data: Only got {len(daily_prices)} days")
            
            cache = {
                'timestamp': datetime.now().isoformat(),
                'prices': daily_prices
            }
            with open(cache_file, 'w') as f:
                json.dump(cache, f)
            print("New data fetched and cached.")
            return daily_prices
        elif response.status_code == 429:
            print(f"Rate limit exceeded. Retrying in {2 ** i} seconds...")
            time.sleep(2 ** i)
        else:
            raise Exception(f"Failed to fetch data: HTTP {response.status_code}")

    raise Exception("Max retries exceeded")

# Example usage:
if __name__ == "__main__":
    try:
        prices = fetch_btc_prices()
        print("\nProcessed prices:")
        for date, price in prices:
            print(f"{date}: ${price:.2f}")
        print(f"Total days: {len(prices)}")
    except Exception as e:
        print(f"An error occurred: {e}")
