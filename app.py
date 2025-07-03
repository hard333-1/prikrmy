# app.py (ÚPLNE NOVÝ, FINÁLNY OBSAH)
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv # Pre lokálne načítanie .env súboru

# Načíta premenné z .env súboru (musí byť na začiatku)
load_dotenv() 

from database import (
   init_db, add_prikrm, get_all_prikrmy, get_prikrm_by_id, update_prikrm,
   delete_prikrm, get_prikrmy_by_kategoria, get_all_categories,
   update_prikrm_quantity, get_category_by_name, add_new_category, update_category_image
)

app = Flask(__name__)
# Tajný kľúč načítaný z premenných prostredia (pre lokálne testovanie môžete mať fallback)
app.secret_key = os.environ.get('SECRET_KEY', 'VAST_TAJNY_A_KOMPLEXNY_KLUC_KTORY_NIKTO_NEUHADNE') 
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Limit pre veľkosť súboru (16MB)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
   return '.' in filename and \
          filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Flask-Login konfigurácia ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Názov routy, kam sa presmeruje neprihlásený užívateľ

# Jednoduchá trieda užívateľa pre Flask-Login
class User(UserMixin):
   def __init__(self, id, username, password_hash):
       self.id = str(id) # ID musí byť reťazec pre Flask-Login
       self.username = username
       self.password_hash = password_hash

   @staticmethod
   def get(user_id):
       # Toto by v reálnej aplikácii načítalo užívateľa z databázy (napr. Back4App User triedy)
       # Pre zjednodušenie stále používame lokálny slovník
       for user_key, user_obj in users_db.items():
           if user_obj.id == user_id:
               return user_obj
       return None

# Namiesto databázy užívateľov použijeme pre zjednodušenie slovník
# Heslá sú HASHOVANÉ! Nikdy neukladajte hesla ako čistý text.
users_db = {
   "lukas": User("1", "lukas", generate_password_hash("Filipenko2014")),
   "majka": User("2", "majka", generate_password_hash("Filipenko2014"))
}

@login_manager.user_loader
def load_user(user_id):
   """
   Táto funkcia sa volá Flask-Loginom na načítanie užívateľa z jeho ID
   uloženého v session.
   """
   return User.get(user_id)

# --- Routy pre prihlásenie/odhlásenie ---
@app.route('/login', methods=['GET', 'POST'])
def login():
   if current_user.is_authenticated:
       # Ak je užívateľ už prihlásený, presmeruj ho na domovskú stránku
       return redirect(url_for('index'))

   if request.method == 'POST':
       username = request.form['username']
       password = request.form['password']
       
       user = None
       if username in users_db:
           user = users_db[username]

       # Overenie hesla
       if user and check_password_hash(user.password_hash, password):
           login_user(user) # Prihlási užívateľa
           flash('Úspešne ste sa prihlásili!', 'success')
           # Presmerovanie na pôvodnú stránku, na ktorú sa chcel užívateľ dostať
           next_page = request.args.get('next')
           return redirect(next_page or url_for('index'))
       else:
           flash('Nesprávne meno alebo heslo.', 'error')
   return render_template('login.html')

@app.route('/logout')
@login_required # Zabezpečí, že sa môže odhlásiť len prihlásený užívateľ
def logout():
   logout_user() # Odhlási užívateľa
   flash('Boli ste odhlásení.', 'info')
   return redirect(url_for('login')) # Presmerovanie na prihlasovaciu stránku

# --- Inicializácia Back4App pri štarte aplikácie ---
with app.app_context():
   init_db() # Inicializuje pripojenie k Back4App
   # Tiež skontrolujte a vytvorte upload adresár pre statické súbory, ak neexistuje
   if not os.path.exists(app.config['UPLOAD_FOLDER']):
       os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Hlavné routy aplikácie (vyžadujú prihlásenie) ---
@app.route('/')
@login_required
def index():
   kategorie = get_all_categories() # Načíta kategórie s ich ID a obrazok_path
   return render_template('index.html', kategorie=kategorie)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_new_prikrm():
   kategorie = get_all_categories() # Získaj existujúce kategórie
   
   if request.method == 'POST':
       nazov_prikrmu = request.form['nazov_prikrmu']
       vybrana_kategoria_nazov = request.form['kategoria']
       nova_kategoria_nazov = request.form.get('nova_kategoria_text', '').strip()
       
       category_id = None
       
       # Logika pre spracovanie kategórie (existujúca vs. nová)
       if vybrana_kategoria_nazov == 'Iné':
           if not nova_kategoria_nazov:
               flash('Prosím, zadajte názov novej kategórie.', 'error')
               return render_template('add_prikrm.html', form_data=request.form, kategorie=kategorie)
           
           existing_new_category = get_category_by_name(nova_kategoria_nazov)
           if existing_new_category:
               category_id = existing_new_category['objectId']
               flash(f'Kategória "{nova_kategoria_nazov}" už existuje, príkrm bol priradený k nej.', 'info')
           else:
               # Spracovanie obrázka pre NOVÚ kategóriu
               kategoria_obrazok_path = None
               if 'nova_kategoria_obrazok' in request.files:
                   file = request.files['nova_kategoria_obrazok']
                   if file and allowed_file(file.filename):
                       filename = secure_filename(file.filename)
                       filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                       file.save(filepath)
                       kategoria_obrazok_path = url_for('static', filename=f'uploads/{filename}')
                   elif file.filename != '':
                       flash('Nepovolený typ súboru pre obrázok novej kategórie.', 'error')
               
               category_id = add_new_category(nova_kategoria_nazov, kategoria_obrazok_path)
               if not category_id:
                   flash('Chyba pri vytváraní novej kategórie.', 'error')
                   return render_template('add_prikrm.html', form_data=request.form, kategorie=kategorie)
               flash(f'Nová kategória "{nova_kategoria_nazov}" bola úspešne pridaná!', 'success')
           
       else: # Bola vybraná existujúca kategória
           selected_category = get_category_by_name(vybrana_kategoria_nazov)
           if selected_category:
               category_id = selected_category['objectId']
           else:
               flash('Vybraná kategória nebola nájdená.', 'error')
               return render_template('add_prikrm.html', form_data=request.form, kategorie=kategorie)

       # Spracovanie dát príkrmu
       vek_od_mesiace = request.form.get('vek_od_mesiace')
       datum_spotreby = request.form['datum_spotreby']
       mnozstvo = request.form.get('mnozstvo')
       poznamky = request.form['poznamky']
       status = request.form['status']

       obrazok_path = None # Pre obrázok príkrmu
       if 'obrazok' in request.files:
           file = request.files['obrazok']
           if file and allowed_file(file.filename):
               filename = secure_filename(file.filename)
               filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
               file.save(filepath)
               obrazok_path = url_for('static', filename=f'uploads/{filename}')
           elif file.filename != '':
               flash('Nepovolený typ súboru pre obrázok príkrmu.', 'error')

       try:
           vek_od_mesiace = int(vek_od_mesiace) if vek_od_mesiace else None
           mnozstvo = int(mnozstvo) if mnozstvo else None
       except ValueError:
           flash('Vek od a množstvo musia byť celé čísla.', 'error')
           return render_template('add_prikrm.html', form_data=request.form, kategorie=kategorie)

       if not nazov_prikrmu or not category_id:
           flash('Názov príkrmu a kategória sú povinné polia.', 'error')
           return render_template('add_prikrm.html', form_data=request.form, kategorie=kategorie)

       add_prikrm(nazov_prikrmu, category_id, vek_od_mesiace, datum_spotreby, mnozstvo, poznamky, obrazok_path, status)
       flash('Príkrm bol úspešne pridaný!', 'success')
       return redirect(url_for('index'))
   
   return render_template('add_prikrm.html', form_data={}, kategorie=kategorie)

@app.route('/prikrm/<string:prikrm_id>') # Zmena na string, lebo Parse objectId je string
@login_required
def prikrm_detail(prikrm_id):
   prikrm = get_prikrm_by_id(prikrm_id)
   if prikrm is None:
       flash('Príkrm nebol nájdený.', 'error')
       return redirect(url_for('index'))
   return render_template('prikrm_detail.html', prikrm=prikrm)

@app.route('/edit/<string:prikrm_id>', methods=['GET', 'POST']) # Zmena na string
@login_required
def edit_prikrm(prikrm_id):
   prikrm = get_prikrm_by_id(prikrm_id)
   kategorie = get_all_categories()
   if prikrm is None:
       flash('Príkrm nebol nájdený pre úpravu.', 'error')
       return redirect(url_for('index'))

   if request.method == 'POST':
       nazov_prikrmu = request.form['nazov_prikrmu']
       vybrana_kategoria_nazov = request.form['kategoria']
       nova_kategoria_nazov = request.form.get('nova_kategoria_text', '').strip()

       category_id = None
       # Ak sa mení kategória na "Iné"
       if vybrana_kategoria_nazov == 'Iné':
           if not nova_kategoria_nazov:
               flash('Prosím, zadajte názov novej kategórie.', 'error')
               return render_template('edit_prikrm.html', prikrm=prikrm, form_data=request.form, kategorie=kategorie)
           
           existing_new_category = get_category_by_name(nova_kategoria_nazov)
           if existing_new_category:
               category_id = existing_new_category['objectId']
           else:
               # Spracovanie obrázka pre NOVÚ kategóriu pri úprave
               kategoria_obrazok_path = None
               if 'nova_kategoria_obrazok' in request.files:
                   file = request.files['nova_kategoria_obrazok']
                   if file and allowed_file(file.filename):
                       filename = secure_filename(file.filename)
                       filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                       file.save(filepath)
                       kategoria_obrazok_path = url_for('static', filename=f'uploads/{filename}')
                   elif file.filename != '':
                       flash('Nepovolený typ súboru pre obrázok novej kategórie.', 'error')
               
               category_id = add_new_category(nova_kategoria_nazov, kategoria_obrazok_path)
               if not category_id:
                   flash('Chyba pri vytváraní novej kategórie.', 'error')
                   return render_template('edit_prikrm.html', prikrm=prikrm, form_data=request.form, kategorie=kategorie)
               flash(f'Nová kategória "{nova_kategoria_nazov}" bola úspešne pridaná!', 'success')
       else: # Bola vybraná existujúca kategória
           selected_category = get_category_by_name(vybrana_kategoria_nazov)
           if selected_category:
               category_id = selected_category['objectId']
           else:
               flash('Vybraná kategória nebola nájdená.', 'error')
               return render_template('edit_prikrm.html', prikrm=prikrm, form_data=request.form, kategorie=kategorie)


       vek_od_mesiace = request.form.get('vek_od_mesiace')
       datum_spotreby = request.form['datum_spotreby']
       mnozstvo = request.form.get('mnozstvo')
       poznamky = request.form['poznamky']
       status = request.form['status']
       
       obrazok_path = prikrm['obrazok'] # Predvolene zachovať existujúci obrázok príkrmu

       if 'obrazok' in request.files:
           file = request.files['obrazok']
           if file and allowed_file(file.filename):
               filename = secure_filename(file.filename)
               filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
               file.save(filepath)
               obrazok_path = url_for('static', filename=f'uploads/{filename}')
           elif file.filename != '':
               flash('Nepovolený typ súboru pre obrázok príkrmu.', 'error')
       
       try:
           vek_od_mesiace = int(vek_od_mesiace) if vek_od_mesiace else None
           mnozstvo = int(mnozstvo) if mnozstvo else None
       except ValueError:
           flash('Vek od a množstvo musia byť celé čísla.', 'error')
           return render_template('edit_prikrm.html', prikrm=prikrm, form_data=request.form, kategorie=kategorie)

       if not nazov_prikrmu or not category_id:
           flash('Názov príkrmu a kategória sú povinné polia.', 'error')
           return render_template('edit_prikrm.html', prikrm=prikrm, form_data=request.form, kategorie=kategorie)

       update_prikrm(prikrm_id, nazov_prikrmu, category_id, vek_od_mesiace, datum_spotreby, mnozstvo, poznamky, obrazok_path, status)
       flash('Príkrm bol úspešne aktualizovaný!', 'success')
       return redirect(url_for('prikrm_detail', prikrm_id=prikrm_id))
   
   # Pre GET žiadosť načítame kategórie a odovzdáme ich do šablóny
   return render_template('edit_prikrm.html', prikrm=prikrm, form_data=prikrm, kategorie=kategorie)


@app.route('/delete/<string:prikrm_id>', methods=['POST']) # Zmena na string
@login_required
def delete_prikrm(prikrm_id):
   prikrm = get_prikrm_by_id(prikrm_id)
   if prikrm is None:
       flash('Príkrm, ktorý sa snažíte vymazať, neexistuje.', 'error')
       return redirect(url_for('index'))

   delete_prikrm(prikrm_id)
   flash('Príkrm bol úspešne vymazaný!', 'success')
   return redirect(url_for('index'))

@app.route('/kategoria/<kategoria_nazov>')
@login_required
def kategoria_list(kategoria_nazov):
   prikrmy = get_prikrmy_by_kategoria(kategoria_nazov)
   kategorie_all = get_all_categories() # Potrebné pre navigačné menu
   return render_template('kategoria_list.html', prikrmy=prikrmy, kategoria_nazov=kategoria_nazov, kategorie=kategorie_all)

# --- Routa pre AJAX aktualizáciu množstva ---
@app.route('/update_quantity/<string:prikrm_id>/<string:action>', methods=['POST']) # Zmena na string
@login_required
def update_quantity(prikrm_id, action):
   prikrm = get_prikrm_by_id(prikrm_id)
   if prikrm is None:
       return jsonify({'success': False, 'message': 'Príkrm nenájdený.'}), 404

   current_quantity = prikrm['mnozstvo'] if prikrm['mnozstvo'] is not None else 0
   
   new_quantity = current_quantity
   if action == 'increment':
       new_quantity += 1
   elif action == 'decrement':
       new_quantity -= 1
       if new_quantity < 0:
           new_quantity = 0 
   else:
       return jsonify({'success': False, 'message': 'Neplatná akcia.'}), 400

   update_prikrm_quantity(prikrm_id, new_quantity)
   return jsonify({'success': True, 'new_quantity': new_quantity}), 200

if __name__ == '__main__':
   app.run(debug=True)