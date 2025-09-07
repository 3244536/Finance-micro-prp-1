import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# --- Configuration de la base de données ---
def init_db():
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            telephone TEXT,
            description TEXT,
            date_creation TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventes_terme (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            valeur_marchandise REAL NOT NULL,
            taux_benefice_mensuel REAL NOT NULL,
            duree_mois INTEGER NOT NULL,
            date_vente TEXT NOT NULL,
            statut TEXT DEFAULT 'En cours',
            montant_total REAL NOT NULL,
            mensualite REAL NOT NULL,
            description_vente TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    cursor.execute("PRAGMA table_info(ventes_terme)")
    colonnes_ventes = [info[1] for info in cursor.fetchall()]
    if 'description_vente' not in colonnes_ventes:
        cursor.execute("ALTER TABLE ventes_terme ADD COLUMN description_vente TEXT")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vente_id INTEGER NOT NULL,
            mois_numero INTEGER NOT NULL,
            montant_paye REAL NOT NULL,
            date_paiement TEXT NOT NULL,
            type_paiement TEXT DEFAULT 'Normal',
            description_paiement TEXT,
            FOREIGN KEY (vente_id) REFERENCES ventes_terme (id)
        )
    ''')

    cursor.execute("PRAGMA table_info(paiements)")
    colonnes_paiements = [info[1] for info in cursor.fetchall()]
    if 'description_paiement' not in colonnes_paiements:
        cursor.execute("ALTER TABLE paiements ADD COLUMN description_paiement TEXT")

    conn.commit()
    conn.close()

# --- Fonctions CRUD et Logique Métier ---

def ajouter_client(nom, telephone, description):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    date_creation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO clients (nom, telephone, description, date_creation)
        VALUES (?, ?, ?, ?)
    ''', (nom, telephone, description, date_creation))
    conn.commit()
    conn.close()

def get_clients():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query("SELECT * FROM clients ORDER BY nom", conn)
    conn.close()
    return df

def get_client_by_id(client_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    client = cursor.fetchone()
    conn.close()
    return client

def creer_vente_terme(client_id, valeur_marchandise, taux_benefice_mensuel, duree_mois, description_vente):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Calcul du montant total et de la mensualité
    # Le taux_benefice_mensuel est appliqué sur la valeur de la marchandise pour calculer le bénéfice par mois
    benefice_total = valeur_marchandise * taux_benefice_mensuel * duree_mois
    montant_total = valeur_marchandise + benefice_total
    
    # La mensualité inclut une partie du capital et une partie du bénéfice
    mensualite = montant_total / duree_mois
    
    date_vente = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO ventes_terme (client_id, valeur_marchandise, taux_benefice_mensuel, 
                                 duree_mois, date_vente, statut, montant_total, mensualite, description_vente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, valeur_marchandise, taux_benefice_mensuel, duree_mois, 
          date_vente, 'En cours', montant_total, mensualite, description_vente))
    
    vente_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return vente_id, montant_total, mensualite

def get_all_ventes():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT vt.*, c.nom as client_nom, c.telephone 
        FROM ventes_terme vt 
        LEFT JOIN clients c ON vt.client_id = c.id 
        ORDER BY vt.date_vente DESC
    ''', conn)
    conn.close()
    return df

def get_ventes_client(client_id):
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT vt.*, c.nom as client_nom 
        FROM ventes_terme vt 
        LEFT JOIN clients c ON vt.client_id = c.id 
        WHERE vt.client_id = ?
        ORDER BY vt.date_vente DESC
    ''', conn, params=(client_id,))
    conn.close()
    return df

def get_paiements_vente(vente_id):
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT * FROM paiements 
        WHERE vente_id = ? 
        ORDER BY mois_numero ASC, date_paiement ASC
    ''', conn, params=(vente_id,))
    conn.close()
    return df

def paiement_existe(vente_id, mois_numero):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM paiements WHERE vente_id = ? AND mois_numero = ?
    ''', (vente_id, mois_numero))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def enregistrer_paiement(vente_id, mois_numero, montant_paye, type_paiement="Normal", description_paiement=""):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Pour les paiements anticipés, on peut permettre plusieurs paiements pour un même "mois logique"
    # si le mois_numero est une indication du mois qu'il est censé couvrir.
    # Pour simplifier, on vérifie ici si un paiement NORMAL existe déjà pour ce mois_numero.
    # Si c'est un anticipé, on l'autorise toujours.
    if type_paiement == "Normal" and paiement_existe(vente_id, mois_numero):
        conn.close()
        return False, "Un paiement normal pour ce mois existe déjà."
    
    date_paiement = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO paiements (vente_id, mois_numero, montant_paye, date_paiement, type_paiement, description_paiement)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (vente_id, mois_numero, montant_paye, date_paiement, type_paiement, description_paiement))
    
    # Vérifier si la vente est complètement payée
    cursor.execute('''
        SELECT SUM(montant_paye) FROM paiements WHERE vente_id = ?
    ''', (vente_id,))
    total_paye = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT montant_total FROM ventes_terme WHERE id = ?
    ''', (vente_id,))
    montant_total = cursor.fetchone()[0]
    
    if total_paye >= montant_total:
        cursor.execute('''
            UPDATE ventes_terme SET statut = 'Payé' WHERE id = ?
        ''', (vente_id,))
    
    conn.commit()
    conn.close()
    return True, "Paiement enregistré avec succès."

def calculer_solde_restant(vente_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT SUM(montant_paye) FROM paiements WHERE vente_id = ?
    ''', (vente_id,))
    total_paye = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT montant_total FROM ventes_terme WHERE id = ?
    ''', (vente_id,))
    montant_total = cursor.fetchone()[0]
    
    conn.close()
    
    return montant_total - total_paye

def generer_echeancier(valeur_marchandise, taux_benefice, duree_mois):
    benefice_total = valeur_marchandise * taux_benefice * duree_mois
    montant_total = valeur_marchandise + benefice_total
    mensualite = montant_total / duree_mois
    
    echeancier = []
    for mois in range(1, duree_mois + 1):
        echeancier.append({'Mois': mois, 'Montant à payer': mensualite})
    
    return pd.DataFrame(echeancier)

def get_next_payment_details(vente_id):
    vente = get_all_ventes()[get_all_ventes()['id'] == vente_id].iloc[0]
    paiements = get_paiements_vente(vente_id)
    
    if vente['statut'] == 'Payé':
        return "Vente entièrement payée", 0.0
    
    solde_restant = calculer_solde_restant(vente_id)
    
    if paiements.empty:
        # Premier paiement, 1 mois après la date de vente
        date_debut = datetime.strptime(vente['date_vente'], "%Y-%m-%d %H:%M:%S")
        next_payment_date = date_debut + timedelta(days=30)
        next_payment_amount = vente['mensualite']
    else:
        # Déterminer le prochain mois logique à payer
        max_mois_paye = paiements['mois_numero'].max()
        next_mois_numero = max_mois_paye + 1
        
        if next_mois_numero > vente['duree_mois']:
            return "Vente entièrement payée", 0.0
        
        # Basé sur la date du dernier paiement (ou date de vente si aucun paiement)
        last_payment_date_str = paiements['date_paiement'].max()
        date_ref = datetime.strptime(last_payment_date_str, "%Y-%m-%d %H:%M:%S")
        
        next_payment_date = date_ref + timedelta(days=30)
        next_payment_amount = vente['mensualite']
        
        # Ajuster le montant si le solde restant est inférieur à la mensualité normale
        if next_payment_amount > solde_restant:
            next_payment_amount = solde_restant

    return next_payment_date.strftime("%d/%m/%Y"), next_payment_amount

# --- Interface Streamlit ---

def main():
    st.set_page_config(page_title="Ventes à Terme", page_icon="💰", layout="wide")
    
    # Styles personnalisés
    st.markdown("""
        <style>
        .stButton>button {
            width: 100%;
            height: 3em; /* Augmente la hauteur des boutons */
            font-size: 1.1em;
            border-radius: 0.5em;
            border: 1px solid #4CAF50; /* Couleur verte */
            color: #4CAF50;
            background-color: white;
        }
        .stButton>button:hover {
            color: white;
            background-color: #4CAF50;
        }
        .stExpander {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #f9f9f9;
        }
        .stExpanderHeader {
            font-weight: bold;
            color: #333;
        }
        .metric-value {
            font-size: 2.5em !important;
            font-weight: bold !important;
            color: #007BFF !important; /* Bleu pour les métriques */
        }
        .metric-label {
            font-size: 1.1em !important;
            color: #555 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    init_db()
    
    st.title("💰 Gestion des Ventes à Terme")
    
    # Menu de navigation stylisé
    st.sidebar.header("Navigation")
    nav_buttons_container = st.sidebar.container()
    with nav_buttons_container:
        if st.button("🏠 Accueil", key="nav_home", use_container_width=True):
            st.session_state.current_page = "Accueil"
        if st.button("👥 Clients", key="nav_clients", use_container_width=True):
            st.session_state.current_page = "Clients"
        if st.button("🛒 Ventes", key="nav_ventes", use_container_width=True):
            st.session_state.current_page = "Ventes"
        if st.button("💳 Paiements", key="nav_paiements", use_container_width=True):
            st.session_state.current_page = "Paiements"
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Accueil"
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    # --- PAGE ACCUEIL ---
    if st.session_state.current_page == "Accueil":
        st.header("🏠 Tableau de Bord - Toutes les Ventes")
        
        ventes = get_all_ventes()
        
        if not ventes.empty:
            for _, vente in ventes.iterrows():
                solde_restant = calculer_solde_restant(vente['id'])
                statut_emoji = "✅" if vente['statut'] == 'Payé' else "⏳"
                
                # Récupérer les détails du prochain paiement
                next_payment_date, next_payment_amount = get_next_payment_details(vente['id'])

                # Titre de l'expander avec le statut, nom du client et montant total
                expander_title = (
                    f"{statut_emoji} Vente #{vente['id']} - "
                    f"{vente['client_nom'] if pd.notna(vente['client_nom']) else 'Client Inconnu'} - "
                    f"{vente['montant_total']:,.0f} UM "
                )
                if vente['statut'] != 'Payé' and next_payment_date != "Vente entièrement payée":
                     expander_title += f" (Proch. paiement: {next_payment_date}, {next_payment_amount:,.0f} UM)"

                with st.expander(expander_title):
                    st.markdown("---")
                    col_status, col_solde = st.columns(2)
                    with col_status:
                        if vente['statut'] == 'Payé':
                            st.success("🎉 **Vente entièrement payée !**")
                        else:
                            st.warning("⚠️ **Vente en cours.**")
                    with col_solde:
                        st.metric("Solde restant", f"{solde_restant:,.0f} UM", delta_color="off")
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Client:** {vente['client_nom'] if pd.notna(vente['client_nom']) else 'Client Inconnu'}")
                        st.markdown(f"**Téléphone:** {vente['telephone'] if pd.notna(vente['telephone']) else 'Non renseigné'}")
                        st.markdown(f"**Valeur marchandise:** `{vente['valeur_marchandise']:,.0f} UM`")
                        st.markdown(f"**Taux bénéfice:** `{vente['taux_benefice_mensuel']*100:.0f}%` par mois")
                    
                    with col2:
                        st.markdown(f"**Durée:** `{vente['duree_mois']} mois`")
                        st.markdown(f"**Montant total:** `{vente['montant_total']:,.0f} UM`")
                        st.markdown(f"**Mensualité:** `{vente['mensualite']:,.0f} UM`")
                        st.markdown(f"**Date vente:** `{vente['date_vente']}`")
                    
                    if pd.notna(vente['description_vente']) and vente['description_vente']:
                        st.markdown(f"**Description:** _{vente['description_vente']}_")
                    
                    # Paiements effectués
                    paiements = get_paiements_vente(vente['id'])
                    if not paiements.empty:
                        st.subheader("💳 Historique des Paiements")
                        for _, paiement in paiements.iterrows():
                            desc_paiement = f"*{paiement['description_paiement']}*" if pd.notna(paiement['description_paiement']) and paiement['description_paiement'] else ""
                            st.markdown(f"- **Mois {paiement['mois_numero']}:** `{paiement['montant_paye']:,.0f} UM` ({paiement['type_paiement']}) - `{paiement['date_paiement']}` {desc_paiement}")
                    
                    # Échéancier théorique
                    st.subheader("📊 Échéancier Théorique")
                    echeancier = generer_echeancier(
                        vente['valeur_marchandise'], 
                        vente['taux_benefice_mensuel'], 
                        vente['duree_mois']
                    )
                    st.dataframe(echeancier, use_container_width=True)
        else:
            st.info("ℹ️ Aucune vente enregistrée pour le moment. Allez à la page 'Ventes' pour en ajouter une !")
    
    # --- PAGE CLIENTS ---
    elif st.session_state.current_page == "Clients":
        st.header("👥 Gestion des Clients")
        
        with st.form("nouveau_client_form", clear_on_submit=True):
            st.subheader("✨ Ajouter un Nouveau Client")
            
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom complet *", placeholder="Ex: Jean Dupont", key="client_nom_input")
                telephone = st.text_input("Téléphone", placeholder="Ex: +222 45 12 34 56", key="client_tel_input")
            with col2:
                description = st.text_area("Description / Notes", placeholder="Informations supplémentaires sur le client...", height=100, key="client_desc_input")
            
            submitted = st.form_submit_button("✅ Enregistrer le Client")
            
            if submitted:
                if nom:
                    ajouter_client(nom, telephone, description)
                    st.success(f"🎉 Client **{nom}** enregistré avec succès !")
                    st.session_state.form_submitted = True
                    st.rerun() # Rafraîchit pour montrer le nouveau client
                else:
                    st.error("🚨 Le nom du client est obligatoire pour l'enregistrement.")
        
        st.subheader("📋 Liste des Clients Enregistrés")
        clients = get_clients()
        
        if not clients.empty:
            for _, client in clients.iterrows():
                with st.expander(f"👤 **{client['nom']}** - {client['telephone'] or 'Sans téléphone'}"):
                    st.markdown(f"**Description:** _{client['description'] or 'Aucune information supplémentaire.'}_")
                    st.markdown(f"**Date de création:** `{client['date_creation']}`")
                    
                    ventes_client = get_ventes_client(client['id'])
                    if not ventes_client.empty:
                        st.subheader("🛒 Ventes associées à ce client")
                        for _, vente in ventes_client.iterrows():
                            solde = calculer_solde_restant(vente['id'])
                            statut_emoji = "✅" if vente['statut'] == 'Payé' else "⏳"
                            st.markdown(
                                f"{statut_emoji} **Vente #{vente['id']}:** `{vente['montant_total']:,.0f} UM` "
                                f"- Solde restant: `{solde:,.0f} UM` - Statut: `{vente['statut']}`"
                            )
                    else:
                        st.info(f"Ce client n'a pas encore de ventes enregistrées.")
        else:
            st.info("ℹ️ Aucun client enregistré. Utilisez le formulaire ci-dessus pour en ajouter un.")
    
    # --- PAGE VENTES ---
    elif st.session_state.current_page == "Ventes":
        st.header("🛒 Créer une Nouvelle Vente à Terme")
        
        clients = get_clients()
        
        if clients.empty:
            st.warning("⚠️ Veuillez d'abord créer un client sur la page 'Clients' avant d'enregistrer une vente.")
        else:
            with st.form("nouvelle_vente_form", clear_on_submit=True):
                st.subheader("1. Sélectionner le Client")
                client_options = {f"{c['nom']} ({c['telephone'] or 'Non renseigné'})": c['id'] for _, c in clients.iterrows()}
                selected_client_display = st.selectbox(
                    "Choisir un client", 
                    options=list(client_options.keys()), 
                    key="select_client_for_sale"
                )
                client_id = client_options[selected_client_display] if selected_client_display else None
                
                if client_id:
                    client_info = get_client_by_id(client_id)
                    st.success(f"Client sélectionné: **{client_info[1]}** - {client_info[2] or 'No tel'}")
                
                st.subheader("2. Détails de la Vente")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    valeur_marchandise = st.number_input("Valeur marchandise (UM) *", 
                                                         min_value=0.0, format="%.0f", value=1000000.0)
                with col2:
                    taux_benefice_entier = st.number_input("Taux bénéfice mensuel (%) *", 
                                                    min_value=0, max_value=100, value=8, step=1, format="%d")
                    taux_benefice = taux_benefice_entier / 100
                with col3:
                    duree_mois = st.number_input("Durée (mois) *", min_value=1, value=6, format="%d")
                
                description_vente = st.text_area("Description de la marchandise ou du service", 
                                                 placeholder="Ex: 1 TV Samsung 55 pouces, un service de consultation...", height=100)
                
                submitted = st.form_submit_button("🚀 Créer la Vente")
                
                if submitted and client_id:
                    if valeur_marchandise > 0 and duree_mois > 0:
                        vente_id, montant_total, mensualite = creer_vente_terme(
                            client_id, valeur_marchandise, taux_benefice, duree_mois, description_vente
                        )
                        
                        st.success(f"🎉 Vente créée avec succès ! ID: **{vente_id}**")
                        
                        st.subheader("📋 Récapitulatif de la Nouvelle Vente")
                        col_m1, col_m2, col_m3 = st.columns(3)
                        col_m1.metric("Valeur marchandise", f"{valeur_marchandise:,.0f} UM")
                        col_m2.metric("Montant total à payer", f"{montant_total:,.0f} UM")
                        col_m3.metric("Mensualité estimée", f"{mensualite:,.0f} UM")
                        
                        st.subheader("📊 Échéancier de paiement")
                        echeancier = generer_echeancier(valeur_marchandise, taux_benefice, duree_mois)
                        st.dataframe(echeancier, use_container_width=True)
                        
                        st.session_state.form_submitted = True
                        if 'selected_client' in st.session_state: # Clear selection after submission
                            del st.session_state.selected_client
                        st.rerun() # Rafraîchit pour montrer la nouvelle vente
                    else:
                        st.error("🚨 Veuillez vérifier les champs obligatoires (valeur, durée) et les remplir correctement.")
    
    # --- PAGE PAIEMENTS ---
    elif st.session_state.current_page == "Paiements":
        st.header("💳 Enregistrer un Paiement")
        
        ventes = get_all_ventes()
        ventes_en_cours = ventes[ventes['statut'] == 'En cours']
        
        if ventes_en_cours.empty:
            st.info("ℹ️ Aucune vente en cours nécessitant un paiement pour le moment.")
        else:
            st.subheader("1. Sélectionner la Vente Concernée")
            vente_options = {
                f"Vente #{v['id']} - {v['client_nom'] or 'Client Inconnu'} - {v['montant_total']:,.0f} UM - Solde: {calculer_solde_restant(v['id']):,.0f} UM": v['id']
                for _, v in ventes_en_cours.iterrows()
            }
            selected_vente_display = st.selectbox(
                "Choisir une vente à payer",
                options=list(vente_options.keys()),
                key="select_sale_for_payment"
            )
            vente_id = vente_options[selected_vente_display] if selected_vente_display else None
            
            if vente_id:
                vente_info = ventes[ventes['id'] == vente_id].iloc[0]
                solde_restant = calculer_solde_restant(vente_id)
                client_nom_display = vente_info['client_nom'] if pd.notna(vente_info['client_nom']) else "Client Inconnu"
                
                st.success(f"Vente sélectionnée : **#{vente_id}** - Client: **{client_nom_display}**")
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Montant total de la vente", f"{vente_info['montant_total']:,.0f} UM")
                col_m2.metric("Mensualité normale", f"{vente_info['mensualite']:,.0f} UM")
                col_m3.metric("Solde restant", f"{solde_restant:,.0f} UM", delta_color="off")
                
                with st.form("paiement_form", clear_on_submit=True):
                    st.subheader("2. Détails du Paiement")
                    type_paiement = st.radio("Type de paiement", ["Mensualité", "Paiement anticipé"], key="type_paiement_radio")
                    
                    if type_paiement == "Mensualité":
                        mois_numero = st.number_input("Numéro du mois à payer", min_value=1, 
                                                      max_value=vente_info['duree_mois'], value=1, format="%d", key="mois_normal")
                        montant_suggere = min(float(vente_info['mensualite']), solde_restant)
                        montant = st.number_input("Montant du paiement (UM) *", min_value=0.0, 
                                                  value=montant_suggere, format="%.0f", key="montant_normal")
                    else: # Paiement anticipé
                        # Un paiement anticipé peut couvrir n'importe quel mois ou partie de mois non encore payé
                        mois_numero = st.number_input("Mois visé par le paiement anticipé (indicatif)", min_value=1, 
                                                      max_value=vente_info['duree_mois'], value=1, format="%d", key="mois_anticipe")
                        montant = st.number_input("Montant du paiement (UM) *", min_value=0.0, 
                                                  max_value=solde_restant, value=min(solde_restant, 100000.0), format="%.0f", key="montant_anticipe")
                    
                    description_paiement = st.text_input("Description du paiement", 
                                                         placeholder="Ex: Virement bancaire, espèce, chèque #123...", key="desc_paiement")
                    
                    submitted = st.form_submit_button("✅ Enregistrer le Paiement")
                    
                    if submitted:
                        if montant > 0:
                            success, message = enregistrer_paiement(
                                vente_id, mois_numero, montant, 
                                "Anticipé" if type_paiement == "Paiement anticipé" else "Normal",
                                description_paiement
                            )
                            if success:
                                st.success(f"🎉 {message} Montant: **{montant:,.0f} UM**")
                                st.session_state.form_submitted = True
                                # Pas besoin de supprimer selected_vente, le selectbox gère
                                st.rerun() # Rafraîchit pour montrer la mise à jour
                            else:
                                st.error(f"⚠️ {message}")
                        else:
                            st.error("🚨 Le montant du paiement doit être supérieur à 0.")

if __name__ == "__main__":
    main()
