import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Configuration de la base de données
def init_db():
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Table des clients
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            telephone TEXT,
            description TEXT,
            date_creation TEXT NOT NULL
        )
    ''')
    
    # Table des ventes à terme
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
    
    # Correction pour les bases de données existantes sans la colonne 'description_vente'
    cursor.execute("PRAGMA table_info(ventes_terme)")
    colonnes_ventes = [info[1] for info in cursor.fetchall()]
    if 'description_vente' not in colonnes_ventes:
        cursor.execute("ALTER TABLE ventes_terme ADD COLUMN description_vente TEXT")

    # Table des paiements
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

    # Correction pour les bases de données existantes sans la colonne 'description_paiement'
    cursor.execute("PRAGMA table_info(paiements)")
    colonnes_paiements = [info[1] for info in cursor.fetchall()]
    if 'description_paiement' not in colonnes_paiements:
        cursor.execute("ALTER TABLE paiements ADD COLUMN description_paiement TEXT")

    conn.commit()
    conn.close()

# Ajouter un client
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

# Obtenir tous les clients
def get_clients():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query("SELECT * FROM clients ORDER BY nom", conn)
    conn.close()
    return df

# Obtenir un client par ID
def get_client_by_id(client_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    client = cursor.fetchone()
    conn.close()
    return client

# Créer une vente à terme
def creer_vente_terme(client_id, valeur_marchandise, taux_benefice_mensuel, duree_mois, description_vente):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Calcul du montant total avec bénéfice
    montant_total = valeur_marchandise * (1 + taux_benefice_mensuel * duree_mois)
    
    # Calcul de la mensualité normale
    mensualite = (montant_total - valeur_marchandise) / duree_mois
    
    date_vente = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO ventes_terme (client_id, valeur_marchandise, taux_benefice_mensuel, 
                                 duree_mois, date_vente, montant_total, mensualite, description_vente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, valeur_marchandise, taux_benefice_mensuel, duree_mois, 
          date_vente, montant_total, mensualite, description_vente))
    
    vente_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return vente_id, montant_total, mensualite

# Obtenir toutes les ventes
def get_all_ventes():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT vt.*, c.nom as client_nom, c.telephone 
        FROM ventes_terme vt 
        JOIN clients c ON vt.client_id = c.id 
        ORDER BY vt.date_vente DESC
    ''', conn)
    conn.close()
    return df

# Obtenir les ventes d'un client
def get_ventes_client(client_id):
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT vt.*, c.nom as client_nom 
        FROM ventes_terme vt 
        JOIN clients c ON vt.client_id = c.id 
        WHERE vt.client_id = ?
        ORDER BY vt.date_vente DESC
    ''', conn, params=(client_id,))
    conn.close()
    return df

# Obtenir tous les paiements d'une vente
def get_paiements_vente(vente_id):
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT * FROM paiements 
        WHERE vente_id = ? 
        ORDER BY mois_numero
    ''', conn, params=(vente_id,))
    conn.close()
    return df

# Vérifier si un paiement existe pour un mois donné
def paiement_existe(vente_id, mois_numero):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM paiements WHERE vente_id = ? AND mois_numero = ?
    ''', (vente_id, mois_numero))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# Enregistrer un paiement
def enregistrer_paiement(vente_id, mois_numero, montant_paye, type_paiement="Normal", description_paiement=""):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Vérifier si le paiement pour ce mois existe déjà
    if paiement_existe(vente_id, mois_numero):
        conn.close()
        return False, "Un paiement pour ce mois existe déjà et ne peut pas être modifié."
    
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

# Calculer le solde restant
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

# Générer l'échéancier
def generer_echeancier(valeur_marchandise, taux_benefice, duree_mois):
    montant_total = valeur_marchandise * (1 + taux_benefice * duree_mois)
    mensualite_interet = (montant_total - valeur_marchandise) / duree_mois
    
    echeancier = []
    for mois in range(1, duree_mois + 1):
        if mois < duree_mois:
            montant_mois = mensualite_interet
        else:
            montant_mois = valeur_marchandise + mensualite_interet
        echeancier.append({'Mois': mois, 'Montant à payer': montant_mois})
    
    return pd.DataFrame(echeancier)

# Interface Streamlit
def main():
    st.set_page_config(page_title="Ventes à Terme", page_icon="💰", layout="wide")
    
    # Initialisation de la base de données
    init_db()
    
    st.title("💰 Gestion des Ventes à Terme")
    
    # Menu de navigation avec boutons
    st.sidebar.header("Navigation")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🏠 Accueil", use_container_width=True):
            st.session_state.current_page = "Accueil"
        if st.button("👥 Clients", use_container_width=True):
            st.session_state.current_page = "Clients"
    with col2:
        if st.button("🛒 Ventes", use_container_width=True):
            st.session_state.current_page = "Ventes"
        if st.button("💳 Paiements", use_container_width=True):
            st.session_state.current_page = "Paiements"
    
    # Initialiser la page courante
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Accueil"
    
    # Réinitialiser les formulaires après soumission
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    # PAGE ACCUEIL - Détails des ventes
    if
