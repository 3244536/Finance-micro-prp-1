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
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    # Table des paiements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vente_id INTEGER NOT NULL,
            mois_numero INTEGER NOT NULL,
            montant_paye REAL NOT NULL,
            date_paiement TEXT NOT NULL,
            type_paiement TEXT DEFAULT 'Normal',
            FOREIGN KEY (vente_id) REFERENCES ventes_terme (id)
        )
    ''')
    
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

# Créer une vente à terme
def creer_vente_terme(client_id, valeur_marchandise, taux_benefice_mensuel, duree_mois):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Calcul du montant total avec bénéfice
    montant_total = valeur_marchandise * (1 + taux_benefice_mensuel * duree_mois)
    
    # Calcul de la mensualité normale (n-1 mois)
    mensualite = (montant_total - valeur_marchandise) / duree_mois
    
    date_vente = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO ventes_terme (client_id, valeur_marchandise, taux_benefice_mensuel, 
                                 duree_mois, date_vente, montant_total, mensualite)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, valeur_marchandise, taux_benefice_mensuel, duree_mois, 
          date_vente, montant_total, mensualite))
    
    vente_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return vente_id, montant_total, mensualite

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

# Enregistrer un paiement
def enregistrer_paiement(vente_id, mois_numero, montant_paye, type_paiement="Normal"):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    date_paiement = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO paiements (vente_id, mois_numero, montant_paye, date_paiement, type_paiement)
        VALUES (?, ?, ?, ?, ?)
    ''', (vente_id, mois_numero, montant_paye, date_paiement, type_paiement))
    
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
        echeancier.append({'Mois': mois, 'Montant': montant_mois})
    
    return pd.DataFrame(echeancier)

# Interface Streamlit
def main():
    st.set_page_config(page_title="Ventes à Terme", page_icon="💰", layout="wide")
    
    # Initialisation de la base de données
    init_db()
    
    st.title("💰 Gestion des Ventes à Terme")
    
    # Menu de navigation
    menu = st.sidebar.selectbox("Navigation", [
        "Nouveau Client", 
        "Nouvelle Vente", 
        "Paiement", 
        "Clients", 
        "Détails Vente"
    ])
    
    if menu == "Nouveau Client":
        st.header("👥 Nouveau Client")
        
        with st.form("nouveau_client"):
            col1, col2 = st.columns(2)
            
            with col1:
                nom = st.text_input("Nom complet *", placeholder="Nom et prénom")
                telephone = st.text_input("Téléphone", placeholder="+222 XX XX XX XX")
            
            with col2:
                description = st.text_area("Description", placeholder="Informations supplémentaires...", height=100)
            
            submitted = st.form_submit_button("Enregistrer le client")
            
            if submitted:
                if nom:
                    ajouter_client(nom, telephone, description)
                    st.success(f"✅ Client {nom} enregistré avec succès !")
                else:
                    st.error("❌ Le nom du client est obligatoire")
    
    elif menu == "Nouvelle Vente":
        st.header("🛒 Nouvelle Vente à Terme")
        
        clients = get_clients()
        
        if clients.empty:
            st.warning("Aucun client enregistré. Veuillez d'abord créer un client.")
        else:
            with st.form("nouvelle_vente"):
                # Sélection du client
                client_options = {f"{row['nom']} ({row['telephone']})": row['id'] for _, row in clients.iterrows()}
                client_sel = st.selectbox("Client *", options=list(client_options.keys()))
                client_id = client_options[client_sel]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    valeur_marchandise = st.number_input("Valeur marchandise (UM) *", min_value=0.0, format="%.0f")
                
                with col2:
                    taux_benefice = st.number_input("Taux bénéfice mensuel (%) *", min_value=0.0, max_value=100.0, value=8.0) / 100
                
                with col3:
                    duree_mois = st.number_input("Durée (mois) *", min_value=1, value=6)
                
                submitted = st.form_submit_button("Créer la vente")
                
                if submitted:
                    if valeur_marchandise > 0 and duree_mois > 0:
                        vente_id, montant_total, mensualite = creer_vente_terme(
                            client_id, valeur_marchandise, taux_benefice, duree_mois
                        )
                        
                        st.success(f"✅ Vente créée avec succès ! ID: {vente_id}")
                        
                        # Affichage des détails
                        st.subheader("📋 Détails de la vente")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Valeur marchandise", f"{valeur_marchandise:,.0f} UM")
                        col2.metric("Montant total", f"{montant_total:,.0f} UM")
                        col3.metric("Mensualité", f"{mensualite:,.0f} UM")
                        
                        # Échéancier
                        st.subheader("📅 Échéancier de paiement")
                        echeancier = generer_echeancier(valeur_marchandise, taux_benefice, duree_mois)
                        st.dataframe(echeancier, use_container_width=True)
                    else:
                        st.error("❌ Veuillez remplir tous les champs correctement")
    
    elif menu == "Paiement":
        st.header("💳 Enregistrement de Paiement")
        
        clients = get_clients()
        
        if clients.empty:
            st.warning("Aucun client enregistré.")
        else:
            # Sélection du client
            client_options = {f"{row['nom']} ({row['telephone']})": row['id'] for _, row in clients.iterrows()}
            client_sel = st.selectbox("Sélectionner un client", options=list(client_options.keys()))
            client_id = client_options[client_sel]
            
            # Ventes du client
            ventes = get_ventes_client(client_id)
            
            if ventes.empty:
                st.warning("Ce client n'a aucune vente en cours.")
            else:
                vente_options = {f"Vente #{row['id']} - {row['montant_total']:,.0f} UM": row['id'] for _, row in ventes.iterrows()}
                vente_sel = st.selectbox("Sélectionner une vente", options=list(vente_options.keys()))
                vente_id = vente_options[vente_sel]
                
                # Informations sur la vente
                vente_info = ventes[ventes['id'] == vente_id].iloc[0]
                solde_restant = calculer_solde_restant(vente_id)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Montant total", f"{vente_info['montant_total']:,.0f} UM")
                col2.metric("Mensualité normale", f"{vente_info['mensualite']:,.0f} UM")
                col3.metric("Solde restant", f"{solde_restant:,.0f} UM")
                
                # Formulaire de paiement
                with st.form("paiement_form"):
                    type_paiement = st.radio("Type de paiement", ["Mensualité", "Paiement anticipé"])
                    
                    if type_paiement == "Mensualité":
                        mois_numero = st.number_input("Numéro du mois", min_value=1, max_value=vente_info['duree_mois'], value=1)
                        montant = st.number_input("Montant", min_value=0.0, value=float(vente_info['mensualite']), format="%.0f")
                    else:
                        mois_numero = st.number_input("Mois de paiement anticipé", min_value=1, max_value=vente_info['duree_mois'], value=1)
                        montant = st.number_input("Montant", min_value=0.0, max_value=float(solde_restant), format="%.0f")
                    
                    submitted = st.form_submit_button("Enregistrer le paiement")
                    
                    if submitted:
                        if montant > 0:
                            enregistrer_paiement(vente_id, mois_numero, montant, 
                                               "Anticipé" if type_paiement == "Paiement anticipé" else "Normal")
                            st.success(f"✅ Paiement de {montant:,.0f} UM enregistré !")
                        else:
                            st.error("❌ Le montant doit être supérieur à 0")
    
    elif menu == "Clients":
        st.header("👥 Liste des Clients")
        
        clients = get_clients()
        
        if not clients.empty:
            for _, client in clients.iterrows():
                with st.expander(f"{client['nom']} - {client['telephone'] or 'Sans téléphone'}"):
                    st.write(f"**Description:** {client['description'] or 'Aucune'}")
                    st.write(f"**Date création:** {client['date_creation']}")
                    
                    # Ventes du client
                    ventes = get_ventes_client(client['id'])
                    if not ventes.empty:
                        st.subheader("Ventes en cours")
                        for _, vente in ventes.iterrows():
                            solde = calculer_solde_restant(vente['id'])
                            st.write(f"**Vente #{vente['id']}:** {vente['montant_total']:,.0f} UM - "
                                   f"Solde: {solde:,.0f} UM - {vente['statut']}")
        else:
            st.info("Aucun client enregistré")
    
    elif menu == "Détails Vente":
        st.header("📊 Détails des Ventes")
        
        ventes_conn = sqlite3.connect('ventes_terme.db')
        ventes_df = pd.read_sql_query('''
            SELECT vt.*, c.nom as client_nom, c.telephone
            FROM ventes_terme vt 
            JOIN clients c ON vt.client_id = c.id 
            ORDER BY vt.date_vente DESC
        ''', ventes_conn)
        ventes_conn.close()
        
        if not ventes_df.empty:
            for _, vente in ventes_df.iterrows():
                with st.expander(f"Vente #{vente['id']} - {vente['client_nom']} - {vente['montant_total']:,.0f} UM"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Client:** {vente['client_nom']}")
                        st.write(f"**Téléphone:** {vente['telephone'] or 'Non renseigné'}")
                        st.write(f"**Valeur marchandise:** {vente['valeur_marchandise']:,.0f} UM")
                        st.write(f"**Taux bénéfice:** {vente['taux_benefice_mensuel']*100}% par mois")
                    
                    with col2:
                        st.write(f"**Durée:** {vente['duree_mois']} mois")
                        st.write(f"**Montant total:** {vente['montant_total']:,.0f} UM")
                        st.write(f"**Mensualité:** {vente['mensualite']:,.0f} UM")
                        st.write(f"**Statut:** {vente['statut']}")
                    
                    # Paiements
                    paiements = get_paiements_vente(vente['id'])
                    if not paiements.empty:
                        st.subheader("Paiements effectués")
                        st.dataframe(paiements, use_container_width=True)
                    
                    # Échéancier théorique
                    st.subheader("Échéancier théorique")
                    echeancier = generer_echeancier(
                        vente['valeur_marchandise'], 
                        vente['taux_benefice_mensuel'], 
                        vente['duree_mois']
                    )
                    st.dataframe(echeancier, use_container_width=True)
        else:
            st.info("Aucune vente enregistrée")

if __name__ == "__main__":
    main()
