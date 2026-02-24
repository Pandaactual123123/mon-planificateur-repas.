import os
import sqlite3
import datetime
import json
import google.generativeai as genai
from jinja2 import Template

# --- 1. CONFIGURATION & AI SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"themes": ["Québécois", "Mexicain", "Thaï", "BBQ"], "baby_age": "1 an"}

# --- 2. DATA ---
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
        formatted.append({"product_name": row[0], "merchant": row[1], "price": f"{row[2]}$", "action": f"Via {row[1]}" if row[1] != "Maxi" else "Prix Maxi"})
    return [r[0] for r in rows], formatted

# --- 3. AI GENERATION ---
def generate_recipes(items, config):
    if not GEMINI_API_KEY: return [{"title": "Erreur Clé API", "desc": "Configurez GEMINI_API_KEY dans les Secrets GitHub.", "baby_tip": "", "required_ingredients": []}]
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Tu es un chef. Crée 4 repas avec ces ingrédients: {', '.join(items)}. Thèmes: {config['themes']}. Bébé: {config['baby_age']}. Réponds UNIQUEMENT en JSON: [{{'title':'','desc':'','baby_tip':'','required_ingredients':[]}}]"
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text.strip().replace('```json', '').replace('```', ''))
    except:
        return [{"title": "En attente", "desc": "L'IA n'a pas pu générer les recettes cette fois.", "baby_tip": "", "required_ingredients": []}]

# --- 4. RUN ---
def main():
    config = load_config()
    db = setup_mock_db()
    items, deals = get_culinary_deals(db)
    recipes = generate_recipes(items, config)
    
    html_template = """
    <!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{font-family:sans-serif;padding:20px;background:#f4f4f4}.card{background:white;padding:15px;margin-bottom:10px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}h1{color:#e74c3c}.tag{background:#e74c3c;color:white;padding:2px 6px;border-radius:4px;font-size:12px;float:right}</style></head>
    <body><h1>Mon Panificateur - {{ date }}</h1>
    <h2>Deals Price Match</h2>{% for d in deals %}<div class='card'><span class='tag'>{{ d.action }}</span><b>{{ d.product_name }}</b> - {{ d.price }}</div>{% endfor %}
    <h2>Menu</h2>{% for r in recipes %}<div class='card'><h3>{{ r.title }}</h3><p>{{ r.desc }}</p><small>👶 Astuce bébé: {{ r.baby_tip }}</small></div>{% endfor %}
    </body></html>
    """
    t = Template(html_template)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(t.render(date=datetime.date.today().strftime('%d/%m/%Y'), deals=deals, recipes=recipes))

if __name__ == "__main__":
    main()
