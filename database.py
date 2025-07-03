# database.py (ÚPLNE NOVÝ, FINÁLNY OBSAH pre priame volania Parse REST API)
import os
import requests
import json

# Načítanie API kľúčov z premenných prostredia
APPLICATION_ID = os.environ.get('B4A_APP_ID')
JAVASCRIPT_KEY = os.environ.get('B4A_JS_KEY')
MASTER_KEY = os.environ.get('B4A_MASTER_KEY') # Používame Master Key pre server-side operácie

# Základná URL pre Parse REST API na Back4App
BASE_URL = "https://parseapi.back4app.com/classes/"

HEADERS = {
   "X-Parse-Application-Id": APPLICATION_ID,
   "X-Parse-REST-API-Key": JAVASCRIPT_KEY, # Pre väčšinu operácií stačí REST API Key
   "Content-Type": "application/json"
}

MASTER_HEADERS = {
   "X-Parse-Application-Id": APPLICATION_ID,
   "X-Parse-Master-Key": MASTER_KEY, # Master Key pre privilegované operácie
   "Content-Type": "application/json"
}

def init_db():
   """Inicializuje pripojenie k Back4App (len kontrola kľúčov)."""
   if not APPLICATION_ID or not JAVASCRIPT_KEY or not MASTER_KEY:
       raise ValueError("Back4App API kľúče nie sú nastavené v premenných prostredia!")
   print("Back4App pripojenie inicializované (pomocou priamych REST volaní).")

# --- Pomocné funkcie pre Parse Pointers ---
def create_pointer(class_name, object_id):
   """Vytvorí Parse Pointer objekt pre prepojenie tried."""
   return {
       "__type": "Pointer",
       "className": class_name,
       "objectId": object_id
   }

# --- Funkcie pre správu KATEGÓRIÍ ---
def get_category_by_name(nazov):
   url = f"{BASE_URL}Kategoria"
   params = {"where": json.dumps({"nazov": nazov})}
   response = requests.get(url, headers=HEADERS, params=params) # BEZ verify=False
   response.raise_for_status() # Vyhodí chybu pre HTTP chyby (4xx, 5xx)
   data = response.json()
   if data and data['results']:
       return data['results'][0] # Vráti prvú nájdenú kategóriu
   return None

def add_new_category(nazov, obrazok_path=None):
   url = f"{BASE_URL}Kategoria"
   payload = {"nazov": nazov}
   if obrazok_path:
       payload["obrazok_path"] = obrazok_path
   
   response = requests.post(url, headers=MASTER_HEADERS, data=json.dumps(payload)) # BEZ verify=False
   response.raise_for_status()
   data = response.json()
   return data.get('objectId') # Vráti objectId novej kategórie

def update_category_image(category_id, obrazok_path):
   url = f"{BASE_URL}Kategoria/{category_id}"
   payload = {"obrazok_path": obrazok_path}
   response = requests.put(url, headers=MASTER_HEADERS, data=json.dumps(payload)) # BEZ verify=False
   response.raise_for_status()
   return True

def get_all_categories():
   url = f"{BASE_URL}Kategoria"
   response = requests.get(url, headers=MASTER_HEADERS) # BEZ verify=False
   response.raise_for_status()
   data = response.json()
   return data.get('results', [])

# --- Funkcie pre správu PRÍKRMOV ---
def add_prikrm(nazov_prikrmu, category_id, vek_od_mesiace, datum_spotreby, mnozstvo, poznamky, obrazok, status):
   url = f"{BASE_URL}Prikrm"
   payload = {
       "nazov_prikrmu": nazov_prikrmu,
       "category": create_pointer("Kategoria", category_id), # Vytvorenie pointera
       "vek_od_mesiace": vek_od_mesiace,
       "datum_spotreby": datum_spotreby,
       "mnozstvo": mnozstvo,
       "poznamky": poznamky,
       "obrazok": obrazok,
       "status": status
   }
   response = requests.post(url, headers=MASTER_HEADERS, data=json.dumps(payload)) # BEZ verify=False
   response.raise_for_status()
   return True

def get_all_prikrmy():
   url = f"{BASE_URL}Prikrm"
   params = {"include": "category"}
   response = requests.get(url, headers=MASTER_HEADERS, params=params) # BEZ verify=False
   response.raise_for_status()
   data = response.json()
   
   formatted_prikrmy = []
   for p in data.get('results', []):
       formatted_prikrm = p
       formatted_prikrm['id'] = p['objectId'] # Pre kompatibilitu s Flask šablónami
       
       # Ak je kategória zahrnutá, pridáme jej názov a obrázok
       if 'category' in p and isinstance(p['category'], dict):
           formatted_prikrm['kategoria_nazov'] = p['category'].get('nazov', 'Neznáma')
           formatted_prikrm['kategoria_obrazok_path'] = p['category'].get('obrazok_path')
       else:
           formatted_prikrm['kategoria_nazov'] = "Neznáma"
           formatted_prikrm['kategoria_obrazok_path'] = None
       formatted_prikrmy.append(formatted_prikrm)
   return formatted_prikrmy

def get_prikrm_by_id(prikrm_id):
   url = f"{BASE_URL}Prikrm/{prikrm_id}"
   params = {"include": "category"}
   response = requests.get(url, headers=MASTER_HEADERS, params=params) # BEZ verify=False
   response.raise_for_status()
   p = response.json()
   
   formatted_prikrm = p
   formatted_prikrm['id'] = p['objectId']
   
   if 'category' in p and isinstance(p['category'], dict):
       formatted_prikrm['kategoria_nazov'] = p['category'].get('nazov', 'Neznáma')
       formatted_prikrm['kategoria_obrazok_path'] = p['category'].get('obrazok_path')
   else:
       formatted_prikrm['kategoria_nazov'] = "Neznáma"
       formatted_prikrm['kategoria_obrazok_path'] = None
   return formatted_prikrm

def update_prikrm(prikrm_id, nazov_prikrmu, category_id, vek_od_mesiace, datum_spotreby, mnozstvo, poznamky, obrazok, status):
   url = f"{BASE_URL}Prikrm/{prikrm_id}"
   payload = {
       "nazov_prikrmu": nazov_prikrmu,
       "category": create_pointer("Kategoria", category_id),
       "vek_od_mesiace": vek_od_mesiace,
       "datum_spotreby": datum_spotreby,
       "mnozstvo": mnozstvo,
       "poznamky": poznamky,
       "obrazok": obrazok,
       "status": status
   }
   response = requests.put(url, headers=MASTER_HEADERS, data=json.dumps(payload)) # BEZ verify=False
   response.raise_for_status()
   return True

def delete_prikrm(prikrm_id):
   url = f"{BASE_URL}Prikrm/{prikrm_id}"
   response = requests.delete(url, headers=MASTER_HEADERS) # BEZ verify=False
   response.raise_for_status()
   return True

def get_prikrmy_by_kategoria(kategoria_nazov):
   category = get_category_by_name(kategoria_nazov)
   if not category:
       return []

   url = f"{BASE_URL}Prikrm"
   where_clause = {"category": create_pointer("Kategoria", category['objectId'])}
   params = {"where": json.dumps(where_clause), "include": "category"}
   
   response = requests.get(url, headers=MASTER_HEADERS, params=params) # BEZ verify=False
   response.raise_for_status()
   data = response.json()
   
   formatted_prikrmy = []
   for p in data.get('results', []):
       formatted_prikrm = p
       formatted_prikrm['id'] = p['objectId']
       if 'category' in p and isinstance(p['category'], dict):
           formatted_prikrm['kategoria_nazov'] = p['category'].get('nazov', 'Neznáma')
           formatted_prikrm['kategoria_obrazok_path'] = p['category'].get('obrazok_path')
       else:
           formatted_prikrm['kategoria_nazov'] = "Neznáma"
           formatted_prikrm['kategoria_obrazok_path'] = None
       formatted_prikrmy.append(formatted_prikrm)
   return formatted_prikrmy

def update_prikrm_quantity(prikrm_id, new_quantity):
   url = f"{BASE_URL}Prikrm/{prikrm_id}"
   payload = {"mnozstvo": new_quantity}
   response = requests.put(url, headers=MASTER_HEADERS, data=json.dumps(payload)) # BEZ verify=False
   response.raise_for_status()
   return True