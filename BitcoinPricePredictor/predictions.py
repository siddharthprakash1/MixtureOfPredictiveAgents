import dotenv
import os
import json
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
import requests
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

dotenv.load_dotenv()

console = Console()

def fetch_btc_prices(cache_file="btc_prices_cache.json"):
    logging.info("Fetching BTC prices from cache")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        logging.info("Cache file loaded successfully")
        return cache
    else:
        logging.error("Cache file not found")
        console.print("[bold red]Error:[/bold red] Cache file not found.")
        return None

def extract_price(response):
    logging.debug(f"Extracting price from response: {response}")
    # Try to match a price with or without a dollar sign
    price_match = re.search(r'(?:\$)?(\d+(?:\.\d{2})?)', response)
    if price_match:
        price = float(price_match.group(1))
        logging.info(f"Extracted price: {price}")
        return price
    logging.warning("Failed to extract price from response")
    return None

def ollama_response(prompt, system, model):
    logging.info(f"Running Ollama model: {model}")
    try:
        command = ["ollama", "run", model]
        logging.debug(f"Executing command: {' '.join(command)}")
        result = subprocess.run(command, input=prompt, capture_output=True, text=True, encoding='utf-8', check=True)
        logging.info("Ollama command executed successfully")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running model {model}: {e}")
        console.print(f"[bold red]Error running model {model}:[/bold red] {e}")
        console.print(f"Stderr: {e.stderr}")
        return None
    
def get_current_bitcoin_price():
    logging.info("Fetching current Bitcoin price")
    url = "https://coingecko.p.rapidapi.com/simple/price"
    querystring = {"ids": "bitcoin", "vs_currencies": "usd"}
    headers = {
        'x-rapidapi-key': "8f05d53640msh4e942fea474e13cp129680jsna8bbe9bf3d7b",
        'x-rapidapi-host': "coingecko.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        price = response.json()['bitcoin']['usd']
        logging.info(f"Current Bitcoin price fetched: ${price}")
        return price
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Bitcoin price: {str(e)}")
        console.print(f"[bold red]Error fetching Bitcoin price:[/bold red] {str(e)}")
        if response:
            logging.error(f"Response status code: {response.status_code}")
            logging.error(f"Response content: {response.text}")
            console.print(f"Response status code: {response.status_code}")
            console.print(f"Response content: {response.text}")
        return None

system = """You are an expert cryptocurrency analyst specializing in bitcoin price prediction.
Your task is to predict the price of bitcoin for the next day based on your extensive Bitcoin and Crypto knowledge.
You also have 30 days of historical Bitcoin price data as a trend indicator.
The last data point is from 24 hrs ago and you need to predict the price for the current time.
Analyze the data, consider trends, volatility, patterns, and your deep knowledge about Bitcoin and Crypto market.
Then make your prediction based on this analysis.
Be 100% objective but be slightly more negative than positive.
Just predict the price as you see it from your analysis of the data and your great knowledge about Bitcoin and Crypto market.
Your response must only be the predicted price in USD formatted as a number with 2 decimal places.
Do not include any explanation, dollar signs, or additional text in your response.
"""

ollama_models = ["llama3", "deepseek-coder-v2", "mistral", "codellama", "qween2", "llava:latest"]
all_models = ollama_models
predictions = []

try:
    logging.info("Script started")
    historical_data = fetch_btc_prices()
    if historical_data is None:
        raise FileNotFoundError("Cache file not found")
    
    current_price = get_current_bitcoin_price()
    
    if current_price is None:
        raise Exception("Failed to fetch current Bitcoin price. Check the error messages above for more details.")

    console.print(f"\n[bold green]Current Bitcoin price:[/bold green]${current_price:.2f}")
    
    prompt = f"""
    Use your extensive bitcoin and crypto knowledge to predict the BTC price in 24h.
    Be 100% objective but be slightly more negative than positive.
    Think outside the box and act super smart.
    Here is the 30 days of historical bitcoin price data:
    {json.dumps(historical_data)}
    Do not include any explanation, dollar signs, or additional text in your response.
    Provide only the predicted price as a number with 2 decimal places.
    """
    
    prediction_table = Table(title="Model Predictions")
    prediction_table.add_column("Model", style="cyan", no_wrap=True)
    prediction_table.add_column("Predictions", style="magenta")
    
    for model in all_models:
        console.print(f"\n[bold blue]Model:[/bold blue] {model}")
        logging.info(f"Processing model: {model}")
        
        response = ollama_response(prompt, system, model)
        console.print(f"[dim]Raw response:[/dim] {response}")
        logging.debug(f"Raw response from {model}: {response}")
        
        if response:
            prediction = extract_price(response)
            console.print(f"[italic]Extracted prediction:[/italic] {prediction}")
            
            if prediction is not None:
                predictions.append(prediction)
                console.print(f"[green]Prediction:[/green] ${prediction:.2f}")
                prediction_table.add_row(model, f"${prediction:.2f}")
                logging.info(f"Prediction for {model}: ${prediction:.2f}")
            else:
                console.print("[red]Unable to determine the prediction from response")
                logging.warning(f"Unable to determine prediction for {model}")
        else:
            console.print("[red]No response received from model")
            logging.warning(f"No response received from {model}")

    if predictions:
        average_prediction = sum(predictions) / len(predictions)
        corrected_prediction = average_prediction * 0.96
        delta = average_prediction - current_price
        delta_percent = (delta / current_price) * 100
        corrected_delta = corrected_prediction - current_price 
        corrected_delta_percent = (corrected_delta / current_price) * 100
        
        results_md = f"""
        # Aggregated Results
        - **Average predicted price:** ${average_prediction:.2f}
        - **Corrected prediction (4% lower):** ${corrected_prediction:.2f}
        - **Current price:** ${current_price:.2f}
        
        # Deltas
        - **Original:** ${delta:.2f} ({delta_percent:.2f}%)
        - **Corrected:** ${corrected_delta:.2f} ({corrected_delta_percent:.2f}%)
        
        # Accuracy
        - **Original:** {100 - abs(delta_percent):.2f}%
        - **Corrected:** {100 - abs(corrected_delta_percent):.2f}%
        """
        
        console.print("\n")
        console.print(prediction_table)
        console.print(Panel(Markdown(results_md), title="Results Summary", expand=False))
        logging.info("Results summary generated")
    else:
        console.print("[yellow]No valid predictions were made.")
        logging.warning("No valid predictions were made")

except FileNotFoundError as e:
    logging.error(f"File not found error: {str(e)}")
    console.print(f"[bold red]Error:[/bold red] {str(e)}")
    console.print("[yellow]Please run the caching script to generate the btc_prices_cache.json file before running this script.")
except Exception as e:
    logging.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
    console.print(f"[bold red]An unexpected error occurred:[/bold red] {str(e)}")

logging.info("Script finished")