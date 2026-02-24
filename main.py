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

def load_pantry():
    try:
        with open('pantry.json', 'r', encoding='utf-8') as f:
            return [item.lower() for item in json.load(f)]
    except: return []

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
    if not GEMINI_API_KEY: return []
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Chef expert. Crée 4 repas avec: {', '.join(items)}. Thèmes: {config['themes']}. Bébé: {config['baby_age']}. Réponds UNIQUEMENT en JSON: [{{'title':'','desc':'','baby_tip':'','required_ingredients':['item1', 'item2']}}]"
    try:
        res = model.generate_content(prompt)
        text = res.text.strip().replace('```json', '').replace('```', '')
        return json.loads(text)
    except: return []

# --- 4. RUN ---
def main():
    config = load_config()
    pantry = load_pantry()
    db = setup_mock_db()
    items, deals = get_culinary_deals(db)
    recipes = generate_recipes(items, config)
    
    # Consolidate Grocery List
    all_ing = []
    for r in recipes: all_ing.extend(r.get('required_ingredients', []))
    shopping_list = sorted(list(set([i for i in all_ing if not any(p in i.lower() for p in pantry)])))

    html_template = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root { --primary: #e74c3c; --bg: #f4f7f6; --card: #ffffff; --text: #2d3436; }
            body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 15px; margin: 0; }
            .container { max-width: 600px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 25px; background: white; padding: 20px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
            h1 { margin: 0; font-weight: 800; font-size: 1.5rem; color: var(--primary); }
            h2 { font-weight: 800; font-size: 1.1rem; text-transform: uppercase; margin-top: 30px; color: #636e72; }
            .card { background: var(--card); padding: 18px; margin-bottom: 12px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #edf2f7; }
            .deal-item { display: flex; justify-content: space-between; align-items: center; }
            .tag { background: var(--primary); color: white; padding: 5px 12px; border-radius: 20px; font-size: 10px; font-weight: 800; text-transform: uppercase; }
            .recipe-title { font-size: 1.2rem; color: #2d3436; margin: 0 0 8px 0; font-weight: 700; }
            .baby-box { background: #fff5f5; border: 1px solid #fed7d7; padding: 12px; border-radius: 10px; font-size: 0.85rem; margin-top: 15px; color: #c53030; }
            .check-item { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f1f2f6; }
            input[type="checkbox"] { width: 18px; height: 18px; accent-color: var(--primary); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>🍴 MON PLANIFICATEUR</h1><small>{{ date }}</small></div>
            
            <h2>💰 IMBATTABLES MAXI (Price Match)</h2>
            {% for d in deals %}<div class="card deal-item">
                <div><div style="font-weight:600; color:#636e72; font-size: 0.8rem;">{{ d.product_name }}</div><div style="font-size:1.3rem; font-weight:800">{{ d.price }}</div></div>
                <span class="tag">{{ d.action }}</span>
            </div>{% endfor %}
            
            <h2>📅 MENU DE LA SEMAINE</h2>
            {% for r in recipes %}<div class="card">
                <h3 class="recipe-title">{{ r.title }}</h3><p style="margin:0; font-size:0.95rem; color:#4a4a4a">{{ r.desc }}</p>
                <div class="baby-box">👶 <b>BÉBÉ:</b> {{ r.baby_tip }}</div>
            </div>{% endfor %}

            <h2>🛒 LISTE DE COURSE CONSOLIDÉE</h2>
            <div class="card">
                {% for item in shopping_list %}<div class="check-item"><input type="checkbox"> <span>{{ item }}</span></div>{% endfor %}
                {% if not shopping_list %}<p style="font-size:0.9rem; color:#b2bec3">Tout est déjà dans votre garde-manger !</p>{% endif %}
            </div>
        </div>
    </body>
    </html>
    """
    t = Template(html_template)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(t.render(date=datetime.date.today().strftime('%d %B %Y'), deals=deals, recipes=recipes, shopping_list=shopping_list))

if __name__ == "__main__":
    main()
