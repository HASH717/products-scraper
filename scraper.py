import os
import time
import json
import random
from typing import List
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import openai
import tiktoken

# Load environment variables (API keys, etc.)
load_dotenv()

# Set up Selenium WebDriver for Chrome
def setup_selenium():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")  # Run in headless mode (no UI)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Path to your chromedriver.exe
    service = Service(r"./chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_html_selenium(url):
    driver = setup_selenium()
    try:
        print(f"Attempting to fetch content from URL: {url}")
        driver.get(url)
        
        # Wait until specific elements (like products) are present
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[class*=product]')))
        print("Successfully located product elements on page.")

        # Scrolling to load dynamic content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        html = driver.page_source
        print(f"HTML content fetched successfully from {url}")
        return html

    except Exception as e:
        print(f"Failed to fetch content from {url}: {e}")
        return None
    finally:
        driver.quit()

def clean_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for element in soup.find_all(['header', 'footer', 'nav']):
            element.decompose()
        cleaned_html = str(soup)
        print("HTML content cleaned successfully (headers/footers removed).")
        return cleaned_html
    
    except Exception as e:
        print(f"Error during cleaning HTML: {e}")
        return html_content  # Return the original HTML if cleaning fails.

def trim_to_token_limit(text, model, max_tokens=125000):
    try:
        encoder = tiktoken.encoding_for_model(model)
        tokens = encoder.encode(text)
        if len(tokens) > max_tokens:
            trimmed_text = encoder.decode(tokens[:max_tokens])
            print(f"Trimmed content to fit within the {max_tokens}-token limit.")
            return trimmed_text
        return text
    except Exception as e:
        print(f"Error during token trimming: {e}")
        return text  # Return original text if something fails

def extract_product_with_price(markdown, prompt, model_used):
    openai.api_key = os.getenv('OPENAI_API_KEY')
    system_message = {
        "role": "system",
        "content": "You are an assistant specialized in extracting product names and prices."
    }
    user_message = {
        "role": "user",
        "content": f"{prompt}\n\nContent:\n\n{markdown}"
    }

    try:
        print("Sending content to OpenAI API for processing...")
        completion = openai.ChatCompletion.create(
            model=model_used,
            messages=[system_message, user_message]
        )
        response_text = completion.choices[0].message['content'].strip()
        print("Received response back from the OpenAI API.")
        return response_text
    except Exception as e:
        print(f"Failed to extract text: {e}")
        return None

# Improved parsing function
def parse_product_output(extracted_text: str):
    try:
        # Initialize default values
        product_name = "Unknown"
        product_price = "Unknown"
        
        # Split text into lines and parse each line
        lines = extracted_text.splitlines()
        for line in lines:
            line = line.strip()  # Clean up any leading/trailing whitespace
            
            # Extract product name
            if "Product Name" in line:
                product_name = line.split("**Product Name:**")[-1].strip()
            elif "Price" in line:
                product_price = line.split("**Price:**")[-1].strip()

        return product_name, product_price
    except Exception as e:
        print(f"Error parsing product output: {e}")
        return "Failed to Parse", "Failed to Parse"

def scrape_from_csv(urls: List[str], prompt: str, model_used: str):
    results = []
    for url in urls:
        print(f"\nProcessing URL: {url}")
        html_content = fetch_html_selenium(url)
        
        if not html_content:
            print(f"Failed to fetch HTML content from {url}, skipping to the next URL.")
            results.append({
                'store_url': url,
                'product_name': 'Failed to Fetch',
                'product_price': 'Failed to Fetch'
            })
            continue

        cleaned_html = clean_html(html_content)

        # Trim the cleaned HTML content to fit within the token limit
        trimmed_html = trim_to_token_limit(cleaned_html, model_used)
        
        print(f"Fetched Content (Truncated) from {url}:\n", cleaned_html[:2000])
        
        extracted_text = extract_product_with_price(trimmed_html, prompt, model_used)
        
        if extracted_text:
            product_name, product_price = parse_product_output(extracted_text)
            
            if '**Product Name**' not in product_name and '**Price**' not in product_price: 
                print(f"Successfully extracted product name and price for {url}.")
            else:
                print(f"Sanitization required: Product Name {product_name}, Price {product_price}")
            
            results.append({
                'store_url': url,
                'product_name': product_name,
                'product_price': product_price,
            })
        else:
            print(f"Failed to extract useful data from {url}.")
            results.append({
                'store_url': url,
                'product_name': 'Failed to Extract',
                'product_price': 'Failed to Extract',
            })
    
    return results

def calculate_price(input_text, output_text, model):
    try:
        encoder = tiktoken.encoding_for_model(model)
        input_token_count = len(encoder.encode(input_text))
        output_token_count = len(encoder.encode(output_text))
        input_cost = input_token_count * pricing[model]["input"]
        output_cost = output_token_count * pricing[model]["output"]
        total_cost = input_cost + output_cost
        return input_token_count, output_token_count, total_cost
    except Exception as e:
        print(f"Error during cost calculation: {e}")
        return 0, 0, 0

if __name__ == "__main__":
    urls = [
        'https://example.com/product-page-1',
        'https://example.com/product-page-2',
    ]
    model_used = "gpt-4-turbo"
    prompt = "Please extract one product name and its price from the content provided. List them as comma-separated values."
    
    # Scrape each URL provided
    results = scrape_from_csv(urls, prompt, model_used)
    print(f"\nFinal Results:\n{results}")