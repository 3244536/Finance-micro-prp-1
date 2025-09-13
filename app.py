import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import base64

# --- Fonctions de la Base de Données ---

def init_db():
    """Initialise la base de données et crée les tables si elles n'existent pas."""
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()

    # Table des clients (Modifié)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            telephone TEXT,
            description TEXT
        )
    ''')

    # Table des opérations (Modifié)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            valeur_marchandise INTEGER NOT NULL,
            taux_benefice INTEGER NOT NULL,
            duree_mois REAL NOT NULL,
            date_creation TEXT NOT NULL,
            statut TEXT DEFAULT 'En cours',
            montant_total REAL NOT NULL,
            montant_benefice REAL NOT NULL,
            montant_mensualite REAL NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
        )
    ''')

    # Table des paiements (Modifié)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER NOT NULL,
            type_paiement TEXT NOT NULL,
            montant INTEGER NOT NULL,
            date_paiement TEXT NOT NULL,
            FOREIGN KEY (operation_id) REFERENCES operations (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# Fonctions pour gérer les clients
def ajouter_client(nom, telephone, description):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO clients (nom, telephone, description) VALUES (?, ?, ?)', (nom, telephone, description))
        conn.commit()
        return True, "Client ajouté avec succès!"
    except sqlite3.IntegrityError:
        return False, "Ce client existe déjà!"
    finally:
        conn.close()

def modifier_client(client_id, nom, telephone, description):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE clients SET nom = ?, telephone = ?, description = ? WHERE id = ?', (nom, telephone, description, client_id))
        conn.commit()
        return True, "Client modifié avec succès!"
    except sqlite3.IntegrityError:
        return False, "Ce nom existe déjà!"
    finally:
        conn.close()

def supprimer_client(client_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    # On gère la suppression en cascade via la configuration de la table
    cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()
    return True, "Client et ses opérations/paiements supprimés avec succès!"

def get_clients():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query("SELECT * FROM clients ORDER BY nom", conn)
    conn.close()
    return df

# Fonctions pour gérer les opérations
def creer_operation(client_id, valeur_marchandise, taux_benefice, duree_mois):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    montant_total = valeur_marchandise * (1 + taux_benefice / 100)
    montant_benefice = valeur_marchandise * (taux_benefice / 100)
    montant_mensualite = montant_total / duree_mois
    date_creation = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute('''
        INSERT INTO operations (client_id, valeur_marchandise, taux_benefice, duree_mois, date_creation, 
                                montant_total, montant_benefice, montant_mensualite)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, valeur_marchandise, taux_benefice, duree_mois, date_creation, montant_total, montant_benefice, montant_mensualite))
    
    operation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return operation_id, montant_total

def get_operations():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT o.*, c.nom AS client_nom, c.telephone
        FROM operations o
        JOIN clients c ON o.client_id = c.id
        ORDER BY o.date_creation DESC
    ''', conn)
    conn.close()
    return df

def modifier_operation(operation_id, valeur_marchandise, taux_benefice, duree_mois):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    montant_total = valeur_marchandise * (1 + taux_benefice / 100)
    montant_benefice = valeur_marchandise * (taux_benefice / 100)
    montant_mensualite = montant_total / duree_mois
    
    cursor.execute('''
        UPDATE operations
        SET valeur_marchandise = ?, taux_benefice = ?, duree_mois = ?, montant_total = ?,
            montant_benefice = ?, montant_mensualite = ?
        WHERE id = ?
    ''', (valeur_marchandise, taux_benefice, duree_mois, montant_total, montant_benefice, montant_mensualite, operation_id))
    
    conn.commit()
    conn.close()
    return True, "Opération modifiée avec succès!"

def supprimer_operation(operation_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM operations WHERE id = ?', (operation_id,))
    conn.commit()
    conn.close()
    return True, "Opération et ses paiements supprimés avec succès!"

# Fonctions pour gérer les paiements
def enregistrer_paiement(operation_id, type_paiement, montant):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    date_paiement = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('SELECT client_id FROM operations WHERE id = ?', (operation_id,))
    client_id = cursor.fetchone()[0]
    
    cursor.execute('''
        INSERT INTO paiements (operation_id, client_id, type_paiement, montant, date_paiement)
        VALUES (?, ?, ?, ?, ?)
    ''', (operation_id, client_id, type_paiement, montant, date_paiement))
    
    # Vérifier si l'opération est terminée
    cursor.execute('SELECT SUM(montant) FROM paiements WHERE operation_id = ?', (operation_id,))
    total_paye = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT montant_total FROM operations WHERE id = ?', (operation_id,))
    montant_total = cursor.fetchone()[0]
    
    if total_paye >= montant_total:
        cursor.execute('UPDATE operations SET statut = "Terminé" WHERE id = ?', (operation_id,))
    
    conn.commit()
    conn.close()
    return True, "Paiement enregistré avec succès!"

def supprimer_paiement(paiement_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM paiements WHERE id = ?', (paiement_id,))
    conn.commit()
    conn.close()
    return True, "Paiement supprimé avec succès!"

def get_paiements_operation(operation_id):
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT p.*, o.client_id, c.nom as client_nom
        FROM paiements p
        JOIN operations o ON p.operation_id = o.id
        JOIN clients c ON o.client_id = c.id
        WHERE p.operation_id = ?
        ORDER BY p.date_paiement DESC
    ''', conn, params=(operation_id,))
    conn.close()
    return df

def get_total_paiements(operation_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(montant) FROM paiements WHERE operation_id = ?', (operation_id,))
    total = cursor.fetchone()[0] or 0
    conn.close()
    return total

def get_prochaine_echeance(operation_id, duree_mois):
    """Calcule la date de la prochaine échéance pour une opération."""
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date_creation FROM operations WHERE id = ?', (operation_id,))
    date_creation_str = cursor.fetchone()[0]
    date_creation = datetime.strptime(date_creation_str, "%Y-%m-%d")

    cursor.execute('SELECT COUNT(*) FROM paiements WHERE operation_id = ? AND type_paiement = "Ordinaire"', (operation_id,))
    paiements_ordinaires_comptes = cursor.fetchone()[0]

    if paiements_ordinaires_comptes >= duree_mois:
        return "Opération terminée"
    else:
        prochaine_date = date_creation + timedelta(days=30 * (paiements_ordinaires_comptes + 1))
        return prochaine_date.strftime("%Y-%m-%d")

def get_all_paiements():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT p.*, c.nom as client_nom, o.id as operation_id
        FROM paiements p
        JOIN clients c ON p.client_id = c.id
        JOIN operations o ON p.operation_id = o.id
        ORDER BY p.date_paiement DESC
    ''', conn)
    conn.close()
    return df

# --- Fonctions utilitaires ---
def format_number(number):
    """Formate un nombre avec des espaces pour les milliers."""
    return f"{number:,.0f}".replace(",", " ")

# Fonction pour charger une image en base64
def get_image_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# --- Interface Streamlit ---

def main():
    st.set_page_config(page_title="Gestion Commerciale", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

    # CSS personnalisé avec des couleurs éclatantes et images
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #ff758c 0%, #ff7eb3 100%);
        color: #FFFFFF;
    }
    .st-emotion-cache-18ni343, .st-emotion-cache-163ttv1 {
        background: rgba(255, 255, 255, 0.1);
    }
    .card {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        border: 3px solid #FFD700;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        margin: 10px 0;
    }
    .operation-en-cours {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #FF6B6B;
        margin: 10px 0;
        color: #333;
    }
    .operation-termine {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #008000;
        margin: 10px 0;
        color: #333;
    }
    .btn-primary {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%) !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 25px !important;
        font-weight: bold !important;
        margin: 5px !important;
    }
    .btn-secondary {
        background: linear-gradient(135deg, #4ECDC4 0%, #556270 100%) !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 25px !important;
        font-weight: bold !important;
        margin: 5px !important;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.9);
        padding: 15px;
        border-radius: 15px;
        border: 2px solid #FFD700;
        text-align: center;
        margin: 10px;
        color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #FFD700;
        text-shadow: 2px 2px 4px #000000;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialisation de la base de données
    init_db()
    
    # Navigation avec boutons colorés
    st.sidebar.markdown("<h1 style='text-align: center; color: #FFD700;'>💰 GESTION COMMERCIALE</h1>", unsafe_allow_html=True)
    
    if st.sidebar.button("🏠 ACCUEIL", use_container_width=True, type="primary"):
        st.session_state.current_page = "Accueil"
    if st.sidebar.button("👥 CLIENTS", use_container_width=True, type="primary"):
        st.session_state.current_page = "Clients"
    if st.sidebar.button("📊 OPÉRATIONS", use_container_width=True, type="primary"):
        st.session_state.current_page = "Opérations"
    if st.sidebar.button("💳 PAIEMENTS", use_container_width=True, type="primary"):
        st.session_state.current_page = "Paiements"

    # Initialiser la page courante
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Accueil"
    
    # --- GESTION DES PAGES ---
    
    # PAGE ACCUEIL
    if st.session_state.current_page == "Accueil":
        st.title("🏠 TABLEAU DE BORD")
        
        operations = get_operations()
        operations_en_cours = operations[operations['statut'] == 'En cours']
        
        st.header("📋 OPÉRATIONS EN COURS")
        if not operations_en_cours.empty:
            for _, op in operations_en_cours.iterrows():
                total_paye = get_total_paiements(op['id'])
                reste_a_payer = op['montant_total'] - total_paye
                
                prochaine_echeance = get_prochaine_echeance(op['id'], op['duree_mois'])
                
                # Montant du prochain paiement
                montant_prochain_paiement = op['montant_mensualite']
                
                st.markdown(f"""
                <div class='operation-en-cours'>
                    <h3>👤 {op['client_nom']}</h3>
                    <p><strong>🎯 Prochain paiement:</strong> {format_number(montant_prochain_paiement)}</p>
                    <p><strong>📅 Prochaine échéance:</strong> {prochaine_echeance}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune opération en cours.")
    
    # PAGE CLIENTS
    elif st.session_state.current_page == "Clients":
        st.title("👥 GESTION DES CLIENTS")
        
        # Ajouter client
        with st.expander("➕ AJOUTER UN CLIENT", expanded=False):
            with st.form("ajouter_client_form", clear_on_submit=True):
                nom = st.text_input("Nom complet *", placeholder="Nom et prénom")
                telephone = st.text_input("Téléphone", placeholder="XX XX XX XX")
                description = st.text_area("Description", placeholder="Informations supplémentaires...")
                
                if st.form_submit_button("✅ AJOUTER LE CLIENT"):
                    if nom:
                        success, message = ajouter_client(nom, telephone, description)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Le nom est obligatoire!")

        # Liste des clients
        st.subheader("📋 LISTE DES CLIENTS")
        clients = get_clients()
        
        if not clients.empty:
            for _, client in clients.iterrows():
                with st.expander(f"👤 {client['nom']} - 📞 {client['telephone'] or 'N/A'}"):
                    st.write(f"**📝 Description:** {client['description'] or 'Aucune'}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✏️ Modifier", key=f"mod_btn_{client['id']}", use_container_width=True):
                            st.session_state.edit_client_id = client['id']
                    with col2:
                        if st.button(f"❌ Supprimer", key=f"del_btn_{client['id']}", use_container_width=True):
                            success, message = supprimer_client(client['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

                    # Formulaire de modification
                    if 'edit_client_id' in st.session_state and st.session_state.edit_client_id == client['id']:
                        with st.form(f"mod_form_{client['id']}", clear_on_submit=False):
                            new_nom = st.text_input("Nouveau Nom", value=client['nom'])
                            new_tel = st.text_input("Nouveau Téléphone", value=client['telephone'] or "")
                            new_desc = st.text_area("Nouvelle Description", value=client['description'] or "")
                            
                            if st.form_submit_button("💾 Sauvegarder"):
                                success, message = modifier_client(client['id'], new_nom, new_tel, new_desc)
                                if success:
                                    st.success(message)
                                    del st.session_state.edit_client_id
                                    st.rerun()
                                else:
                                    st.error(message)
        else:
            st.info("Aucun client enregistré.")
    
    # PAGE OPÉRATIONS
    elif st.session_state.current_page == "Opérations":
        st.title("📊 GESTION DES OPÉRATIONS")
        
        clients = get_clients()
        
        with st.expander("➕ NOUVELLE OPÉRATION", expanded=False):
            if clients.empty:
                st.warning("Aucun client disponible. Veuillez d'abord créer un client.")
            else:
                with st.form("ajouter_operation_form", clear_on_submit=True):
                    client_options = {client['nom']: client['id'] for _, client in clients.iterrows()}
                    client_sel = st.selectbox("Client *", options=list(client_options.keys()))
                    valeur = st.number_input("Valeur de marchandise (entier naturel) *", min_value=1, step=1, value=1000000)
                    taux = st.number_input("Taux de bénéfice (%) (entier naturel) *", min_value=0, step=1, value=8)
                    duree = st.number_input("Durée en mois (décimal) *", min_value=0.1, step=0.1, value=6.0)
                    
                    if st.form_submit_button("✅ CRÉER L'OPÉRATION"):
                        client_id = client_options[client_sel]
                        op_id, montant_total = creer_operation(client_id, valeur, taux, duree)
                        st.success(f"Opération #{op_id} créée pour {client_sel}! Montant total: {format_number(montant_total)}")
                        st.rerun()
        
        st.subheader("📋 LISTE DES OPÉRATIONS")
        operations = get_operations()
        
        if not operations.empty:
            for _, op in operations.iterrows():
                css_class = "operation-termine" if op['statut'] == 'Terminé' else "operation-en-cours"
                total_paye = get_total_paiements(op['id'])
                reste_a_payer = op['montant_total'] - total_paye
                
                with st.container():
                    st.markdown(f"""
                    <div class='{css_class}'>
                        <h3>🔢 #{op['id']} - 👤 {op['client_nom']}</h3>
                        <p><strong>🏷️ Statut:</strong> {op['statut']}</p>
                        <p><strong>💵 Valeur:</strong> {format_number(op['valeur_marchandise'])}</p>
                        <p><strong>📈 Taux:</strong> {op['taux_benefice']}%</p>
                        <p><strong>⏰ Durée:</strong> {op['duree_mois']} mois</p>
                        <p><strong>💰 Montant Total:</strong> {format_number(op['montant_total'])}</p>
                        <p><strong>⚖️ Reste à payer:</strong> {format_number(reste_a_payer)}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✏️ Modifier", key=f"mod_op_{op['id']}", use_container_width=True):
                            st.session_state.edit_op_id = op['id']
                    with col2:
                        if st.button(f"❌ Supprimer", key=f"del_op_{op['id']}", use_container_width=True):
                            success, message = supprimer_operation(op['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

                    # Formulaire de modification
                    if 'edit_op_id' in st.session_state and st.session_state.edit_op_id == op['id']:
                        with st.form(f"mod_form_op_{op['id']}", clear_on_submit=False):
                            new_valeur = st.number_input("Valeur marchandise", value=int(op['valeur_marchandise']), min_value=1, step=1)
                            new_taux = st.number_input("Taux de bénéfice (%)", value=int(op['taux_benefice']), min_value=0, step=1)
                            new_duree = st.number_input("Durée (mois)", value=op['duree_mois'], min_value=0.1, step=0.1)
                            
                            if st.form_submit_button("💾 SAUVEGARDER"):
                                success, message = modifier_operation(op['id'], new_valeur, new_taux, new_duree)
                                if success:
                                    st.success(message)
                                    del st.session_state.edit_op_id
                                    st.rerun()
                                else:
                                    st.error(message)
        else:
            st.info("Aucune opération enregistrée.")
    
    # PAGE PAIEMENTS
    elif st.session_state.current_page == "Paiements":
        st.title("💳 GESTION DES PAIEMENTS")
        
        operations = get_operations()
        
        with st.expander("➕ NOUVEAU PAIEMENT", expanded=False):
            if operations.empty:
                st.warning("Aucune opération disponible pour enregistrer un paiement.")
            else:
                with st.form("ajouter_paiement_form", clear_on_submit=True):
                    op_options = [f"#{op['id']} - {op['client_nom']} - Total: {format_number(op['montant_total'])}" for _, op in operations.iterrows()]
                    op_sel = st.selectbox("Opération *", options=op_options)
                    op_id = int(op_sel.split(' - ')[0].replace('#', ''))
                    
                    op_info = operations[operations['id'] == op_id].iloc[0]
                    montant_mensuel = op_info['montant_mensualite']

                    type_paiement = st.radio("Type de paiement *", ["Ordinaire", "Anticipé"])
                    
                    if type_paiement == "Ordinaire":
                        montant_suggere = int(montant_mensuel)
                    else:
                        montant_suggere = int(op_info['montant_benefice']) # Suggestion pour paiement anticipé

                    montant = st.number_input("Montant (entier naturel) *", min_value=1, step=1, value=montant_suggere)
                    
                    if st.form_submit_button("✅ ENREGISTRER LE PAIEMENT"):
                        success, message = enregistrer_paiement(op_id, type_paiement, montant)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        
        st.subheader("📋 HISTORIQUE DES PAIEMENTS")
        all_paiements = get_all_paiements()
        
        if not all_paiements.empty:
            for _, pay in all_paiements.iterrows():
                st.markdown(f"""
                <div class='card'>
                    <p><strong>Opération #{pay['operation_id']}</strong></p>
                    <p><strong>👤 Client:</strong> {pay['client_nom']}</p>
                    <p><strong>💳 Type:</strong> {pay['type_paiement']}</p>
                    <p><strong>💰 Montant:</strong> {format_number(pay['montant'])}</p>
                    <p><strong>📅 Date:</strong> {pay['date_paiement']}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"❌ Supprimer", key=f"del_pay_{pay['id']}"):
                    success, message = supprimer_paiement(pay['id'])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Aucun paiement enregistré.")

if __name__ == "__main__":
    main()
