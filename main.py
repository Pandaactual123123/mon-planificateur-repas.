import os
import sqlite3
import datetime
import json
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader

# --- 1. CONFIGURATION & AI SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"themes": ["Québécois", "Mexicain", "Thaï", "BBQ"], "baby_age": "1 an", "max_prep_time": "30 min", "allergies": "Aucune"}

def load_pantry():
    try:
        with open('pantry.json', 'r', encoding='utf-8') as f:
            return [item.lower() for item in json.load(f)]
    except: return []

# --- 2. DATA & PRICE MATCH LOGIC ---
def setup_mock_db():
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE weekly_deals (merchant TEXT, product_name TEXT, price REAL, original_price REAL)')
    mock_data = [("IGA", "Porc haché", 2.49, 5.99), ("Super C", "Brocoli", 1.44, 3.50), ("Maxi", "Patates (10lb)", 2.99, 6.99)]
    cursor.executemany('INSERT INTO weekly_deals VALUES (?,?,?,?)', mock_data)
    return conn

def get_culinary_deals(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, merchant, price, original_price FROM weekly_deals")
    rows = cursor.fetchall()
    formatted = []
    for row in rows:
        discount = round((1 - (row[2]/row[3])) * 100)
        formatted.append({"product_name": row[1], "merchant": row[0], "price": f"{row[2]}$", "is_match": row[0] != "Maxi", "action": f"Via {row[0]}" if row[0] != "Maxi" else "Prix Maxi"})
    return [r[0] for r in rows], formatted

# --- 3. AI GENERATION ---
def generate_recipes(items, config):
    if not GEMINI_API_KEY: return []
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Chef expert. Crée 4 repas avec: {', '.join(items)}. Thèmes: {config['themes']}. Bébé: {config['baby_age']}. Réponds UNIQUEMENT en JSON: [{{'title':'','desc':'','baby_tip':'','required_ingredients':[]}}]"
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text.strip().replace('```json', '').replace('```', ''))
    except: return []

# --- 4. RUN ---
def main():
    config = load_config()
    db = setup_mock_db()
    items, deals = get_culinary_deals(db)
    recipes = generate_recipes(items, config)
    
    # SIMPLE HTML TEMPLATE
    html_template = """
    <!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{font-family:sans-serif;padding:20px

