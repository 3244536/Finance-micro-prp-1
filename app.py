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
    
    # Calcul de la mensualité normale (n-1 mois)
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
    if st.session_state.current_page == "Accueil":
        st.header("🏠 Tableau de Bord - Toutes les Ventes")
        
        ventes = get_all_ventes()
        
        if not ventes.empty:
            for _, vente in ventes.iterrows():
                solde_restant = calculer_solde_restant(vente['id'])
                statut_color = "🟢" if vente['statut'] == 'Payé' else "🟠"
                
                with st.expander(f"{statut_color} Vente #{vente['id']} - {vente['client_nom']} - {vente['montant_total']:,.0f} UM - {vente['statut']}"):
                    # Style différent pour les ventes soldées
                    if vente['statut'] == 'Payé':
                        st.success("✅ Vente entièrement payée")
                    else:
                        st.warning(f"⏳ Solde restant: {solde_restant:,.0f} UM")
                    
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
                        st.write(f"**Date vente:** {vente['date_vente']}")
                    
                    # Description de la vente
                    if vente['description_vente']:
                        st.write(f"**Description:** {vente['description_vente']}")
                    
                    # Paiements effectués
                    paiements = get_paiements_vente(vente['id'])
                    if not paiements.empty:
                        st.subheader("💳 Paiements effectués")
                        for _, paiement in paiements.iterrows():
                            st.write(f"- Mois {paiement['mois_numero']}: {paiement['montant_paye']:,.0f} UM "
                                   f"({paiement['type_paiement']}) - {paiement['date_paiement']}")
                            if paiement['description_paiement']:
                                st.caption(f"  *{paiement['description_paiement']}*")
                    
                    # Échéancier théorique
                    st.subheader("📅 Échéancier théorique")
                    echeancier = generer_echeancier(
                        vente['valeur_marchandise'], 
                        vente['taux_benefice_mensuel'], 
                        vente['duree_mois']
                    )
                    st.dataframe(echeancier, use_container_width=True)
        else:
            st.info("Aucune vente enregistrée")
    
    # PAGE CLIENTS
    elif st.session_state.current_page == "Clients":
        st.header("👥 Gestion des Clients")
        
        # Formulaire nouveau client
        with st.form("nouveau_client_form", clear_on_submit=True):
            st.subheader("➕ Nouveau Client")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nom = st.text_input("Nom complet *", placeholder="Nom et prénom", key="client_nom")
                telephone = st.text_input("Téléphone", placeholder="+222 XX XX XX XX", key="client_tel")
            
            with col2:
                description = st.text_area("Description", placeholder="Informations supplémentaires...", 
                                         height=100, key="client_desc")
            
            submitted = st.form_submit_button("✅ Enregistrer le client")
            
            if submitted:
                if nom:
                    ajouter_client(nom, telephone, description)
                    st.success(f"Client {nom} enregistré avec succès !")
                    st.session_state.form_submitted = True
                else:
                    st.error("Le nom du client est obligatoire")
        
        # Liste des clients
        st.subheader("📋 Liste des Clients")
        clients = get_clients()
        
        if not clients.empty:
            for _, client in clients.iterrows():
                with st.expander(f"{client['nom']} - {client['telephone'] or 'Sans téléphone'}"):
                    st.write(f"**Description:** {client['description'] or 'Aucune'}")
                    st.write(f"**Date création:** {client['date_creation']}")
                    
                    # Ventes du client
                    ventes = get_ventes_client(client['id'])
                    if not ventes.empty:
                        st.subheader("Ventes")
                        for _, vente in ventes.iterrows():
                            solde = calculer_solde_restant(vente['id'])
                            statut_emoji = "✅" if vente['statut'] == 'Payé' else "⏳"
                            st.write(f"{statut_emoji} **Vente #{vente['id']}:** {vente['montant_total']:,.0f} UM - "
                                   f"Solde: {solde:,.0f} UM - {vente['statut']}")
        else:
            st.info("Aucun client enregistré")
    
    # PAGE VENTES
    elif st.session_state.current_page == "Ventes":
        st.header("🛒 Nouvelle Vente à Terme")
        
        clients = get_clients()
        
        if clients.empty:
            st.warning("Aucun client enregistré. Veuillez d'abord créer un client.")
        else:
            with st.form("nouvelle_vente_form", clear_on_submit=True):
                # Sélection du client avec boutons
                st.subheader("Sélection du Client")
                client_cols = st.columns(2)
                client_id = None
                
                for i, (_, client) in enumerate(clients.iterrows()):
                    with client_cols[i % 2]:
                        if st.button(f"{client['nom']} ({client['telephone'] or 'No tel'})", 
                                   key=f"client_{client['id']}", use_container_width=True):
                            client_id = client['id']
                            st.session_state.selected_client = client_id
                
                if 'selected_client' in st.session_state:
                    client_id = st.session_state.selected_client
                    client_info = get_client_by_id(client_id)
                    st.info(f"Client sélectionné: {client_info[1]} - {client_info[2] or 'No tel'}")
                
                st.subheader("Détails de la Vente")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    valeur_marchandise = st.number_input("Valeur marchandise (UM) *", 
                                                       min_value=0.0, format="%.0f", value=1000000.0)
                
                with col2:
                    taux_benefice = st.number_input("Taux bénéfice mensuel (%) *", 
                                                  min_value=0.0, max_value=100.0, value=8.0, step=0.5) / 100
                
                with col3:
                    duree_mois = st.number_input("Durée (mois) *", min_value=1, value=6)
                
                description_vente = st.text_area("Description de la vente", 
                                               placeholder="Décrivez la marchandise ou le service...")
                
                submitted = st.form_submit_button("✅ Créer la vente")
                
                if submitted and client_id:
                    if valeur_marchandise > 0 and duree_mois > 0:
                        vente_id, montant_total, mensualite = creer_vente_terme(
                            client_id, valeur_marchandise, taux_benefice, duree_mois, description_vente
                        )
                        
                        st.success(f"Vente créée avec succès ! ID: {vente_id}")
                        
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
                        
                        st.session_state.form_submitted = True
                        if 'selected_client' in st.session_state:
                            del st.session_state.selected_client
                    else:
                        st.error("Veuillez remplir tous les champs correctement")
    
    # PAGE PAIEMENTS
    elif st.session_state.current_page == "Paiements":
        st.header("💳 Enregistrement de Paiement")
        
        ventes = get_all_ventes()
        ventes_en_cours = ventes[ventes['statut'] == 'En cours']
        
        if ventes_en_cours.empty:
            st.warning("Aucune vente en cours nécessitant un paiement.")
        else:
            # Sélection de la vente avec boutons
            st.subheader("Sélectionner une Vente")
            vente_cols = st.columns(2)
            selected_vente = None
            
            for i, (_, vente) in enumerate(ventes_en_cours.iterrows()):
                with vente_cols[i % 2]:
                    client_info = get_client_by_id(vente['client_id'])
                    if st.button(f"Vente #{vente['id']} - {client_info[1]} - {vente['montant_total']:,.0f} UM", 
                               key=f"vente_{vente['id']}", use_container_width=True):
                        selected_vente = vente
                        st.session_state.selected_vente = vente['id']
            
            if 'selected_vente' in st.session_state:
                vente_id = st.session_state.selected_vente
                vente_info = ventes[ventes['id'] == vente_id].iloc[0]
                solde_restant = calculer_solde_restant(vente_id)
                client_info = get_client_by_id(vente_info['client_id'])
                
                st.success(f"Vente sélectionnée: #{vente_id} - {client_info[1]}")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Montant total", f"{vente_info['montant_total']:,.0f} UM")
                col2.metric("Mensualité normale", f"{vente_info['mensualite']:,.0f} UM")
                col3.metric("Solde restant", f"{solde_restant:,.0f} UM")
                
                # Formulaire de paiement
                with st.form("paiement_form", clear_on_submit=True):
                    type_paiement = st.radio("Type de paiement", ["Mensualité", "Paiement anticipé"])
                    
                    if type_paiement == "Mensualité":
                        mois_numero = st.number_input("Numéro du mois", min_value=1, 
                                                    max_value=vente_info['duree_mois'], value=1)
                        montant = st.number_input("Montant", min_value=0.0, 
                                                value=float(vente_info['mensualite']), format="%.0f")
                    else:
                        mois_numero = st.number_input("Mois de paiement anticipé", min_value=1, 
                                                    max_value=vente_info['duree_mois'], value=1)
                        montant = st.number_input("Montant", min_value=0.0, 
                                                max_value=float(solde_restant), format="%.0f")
                    
                    description_paiement = st.text_input("Description du paiement", 
                                                       placeholder="Mode de paiement, référence...")
                    
                    submitted = st.form_submit_button("💳 Enregistrer le paiement")
                    
                    if submitted:
                        if montant > 0:
                            success, message = enregistrer_paiement(
                                vente_id, mois_numero, montant, 
                                "Anticipé" if type_paiement == "Paiement anticipé" else "Normal",
                                description_paiement
                            )
                            if success:
                                st.success(f"{message} Montant: {montant:,.0f} UM")
                                st.session_state.form_submitted = True
                                if 'selected_vente' in st.session_state:
                                    del st.session_state.selected_vente
                            else:
                                st.error(message)
                        else:
                            st.error("Le montant doit être supérieur à 0")

if __name__ == "__main__":
    main()
