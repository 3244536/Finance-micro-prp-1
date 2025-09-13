import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from PIL import Image
import io
import base64

# Configuration de la base de données
def init_db():
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Table des clients
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            telephone TEXT,
            description TEXT,
            date_creation TEXT NOT NULL
        )
    ''')
    
    # Table des ventes à terme
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            valeur_marchandise REAL NOT NULL,
            taux_benefice REAL NOT NULL,
            duree_mois REAL NOT NULL,
            date_creation TEXT NOT NULL,
            statut TEXT DEFAULT 'En cours',
            montant_total REAL NOT NULL,
            prochaine_echeance TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    # Table des paiements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            type_paiement TEXT NOT NULL,
            montant REAL NOT NULL,
            date_paiement TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (operation_id) REFERENCES operations (id),
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Fonction pour formater les nombres avec espaces
def format_number(number):
    return f"{number:,.0f}".replace(",", " ")

# Ajouter un client - CORRIGÉ
def ajouter_client(nom, telephone, description):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    date_creation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute('''
            INSERT INTO clients (nom, telephone, description, date_creation)
            VALUES (?, ?, ?, ?)
        ''', (nom, telephone, description, date_creation))
        
        conn.commit()
        success = True
        message = "Client ajouté avec succès!"
    except sqlite3.IntegrityError:
        success = False
        message = "Ce client existe déjà!"
    finally:
        conn.close()
    
    return success, message

# Modifier un client
def modifier_client(client_id, nom, telephone, description):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE clients 
            SET nom = ?, telephone = ?, description = ?
            WHERE id = ?
        ''', (nom, telephone, description, client_id))
        
        conn.commit()
        success = True
        message = "Client modifié avec succès!"
    except sqlite3.IntegrityError:
        success = False
        message = "Ce nom existe déjà!"
    finally:
        conn.close()
    
    return success, message

# Supprimer un client
def supprimer_client(client_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    try:
        # Vérifier si le client a des opérations
        cursor.execute('SELECT COUNT(*) FROM operations WHERE client_id = ?', (client_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Impossible de supprimer: le client a des opérations en cours!"
        
        cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        conn.commit()
        success = True
        message = "Client supprimé avec succès!"
    except Exception as e:
        success = False
        message = f"Erreur lors de la suppression: {str(e)}"
    finally:
        conn.close()
    
    return success, message

# Obtenir tous les clients
def get_clients():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query("SELECT * FROM clients ORDER BY nom", conn)
    conn.close()
    return df

# Créer une opération
def creer_operation(client_id, valeur_marchandise, taux_benefice, duree_mois):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Calcul du montant total
    montant_total = valeur_marchandise * (1 + taux_benefice * duree_mois)
    
    date_creation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calcul de la prochaine échéance (1 mois après la création)
    prochaine_echeance = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    cursor.execute('''
        INSERT INTO operations (client_id, valeur_marchandise, taux_benefice, 
                              duree_mois, date_creation, montant_total, prochaine_echeance)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, valeur_marchandise, taux_benefice, duree_mois, 
          date_creation, montant_total, prochaine_echeance))
    
    operation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return operation_id, montant_total

# Obtenir toutes les opérations
def get_operations():
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT o.*, c.nom as client_nom, c.telephone 
        FROM operations o 
        JOIN clients c ON o.client_id = c.id 
        ORDER BY o.date_creation DESC
    ''', conn)
    conn.close()
    return df

# Modifier une opération
def modifier_operation(operation_id, valeur_marchandise, taux_benefice, duree_mois):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    # Recalculer le montant total
    montant_total = valeur_marchandise * (1 + taux_benefice * duree_mois)
    
    cursor.execute('''
        UPDATE operations 
        SET valeur_marchandise = ?, taux_benefice = ?, duree_mois = ?, montant_total = ?
        WHERE id = ?
    ''', (valeur_marchandise, taux_benefice, duree_mois, montant_total, operation_id))
    
    conn.commit()
    conn.close()
    return True, "Opération modifiée avec succès!"

# Supprimer une opération
def supprimer_operation(operation_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    try:
        # Supprimer d'abord les paiements associés
        cursor.execute('DELETE FROM paiements WHERE operation_id = ?', (operation_id,))
        
        # Puis supprimer l'opération
        cursor.execute('DELETE FROM operations WHERE id = ?', (operation_id,))
        
        conn.commit()
        success = True
        message = "Opération supprimée avec succès!"
    except Exception as e:
        success = False
        message = f"Erreur lors de la suppression: {str(e)}"
    finally:
        conn.close()
    
    return success, message

# Enregistrer un paiement
def enregistrer_paiement(operation_id, client_id, type_paiement, montant, description=""):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    
    date_paiement = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute('''
            INSERT INTO paiements (operation_id, client_id, type_paiement, montant, date_paiement, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (operation_id, client_id, type_paiement, montant, date_paiement, description))
        
        # Mettre à jour la prochaine échéance si c'est un paiement ordinaire
        if type_paiement == "Ordinaire":
            cursor.execute('SELECT prochaine_echeance FROM operations WHERE id = ?', (operation_id,))
            result = cursor.fetchone()
            if result and result[0]:
                current_date = datetime.strptime(result[0], "%Y-%m-%d")
                new_date = (current_date + timedelta(days=30)).strftime("%Y-%m-%d")
                cursor.execute('UPDATE operations SET prochaine_echeance = ? WHERE id = ?', (new_date, operation_id))
        
        # Vérifier si l'opération est terminée
        cursor.execute('SELECT SUM(montant) FROM paiements WHERE operation_id = ?', (operation_id,))
        total_paye = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT montant_total FROM operations WHERE id = ?', (operation_id,))
        result = cursor.fetchone()
        montant_total = result[0] if result else 0
        
        if total_paye >= montant_total:
            cursor.execute('UPDATE operations SET statut = "Terminé" WHERE id = ?', (operation_id,))
        
        conn.commit()
        success = True
        message = "Paiement enregistré avec succès!"
    except Exception as e:
        success = False
        message = f"Erreur lors de l'enregistrement: {str(e)}"
    finally:
        conn.close()
    
    return success, message

# Obtenir les paiements d'une opération
def get_paiements_operation(operation_id):
    conn = sqlite3.connect('ventes_terme.db')
    df = pd.read_sql_query('''
        SELECT p.*, c.nom as client_nom 
        FROM paiements p 
        JOIN clients c ON p.client_id = c.id 
        WHERE p.operation_id = ?
        ORDER BY p.date_paiement DESC
    ''', conn, params=(operation_id,))
    conn.close()
    return df

# Obtenir le total des paiements pour une opération
def get_total_paiements(operation_id):
    conn = sqlite3.connect('ventes_terme.db')
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(montant) FROM paiements WHERE operation_id = ?', (operation_id,))
    result = cursor.fetchone()
    total = result[0] if result and result[0] else 0
    conn.close()
    return total

# Interface Streamlit
def main():
    st.set_page_config(page_title="Gestion Commerciale", page_icon="💰", layout="wide", initial_sidebar_state="expanded")
    
    # CSS personnalisé avec des couleurs éclatantes
    st.markdown("""
    
    """)
    
    # Initialisation de la base de données
    init_db()
    
    # Navigation avec boutons colorés
    st.sidebar.markdown("<h1 style='text-align: center; color: #FFD700;'>💰 GESTION COMMERCIALE</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🏠 ACCUEIL", use_container_width=True, key="accueil_btn"):
            st.session_state.current_page = "Accueil"
        if st.button("👥 CLIENTS", use_container_width=True, key="clients_btn"):
            st.session_state.current_page = "Clients"
    with col2:
        if st.button("📊 OPÉRATIONS", use_container_width=True, key="operations_btn"):
            st.session_state.current_page = "Opérations"
        if st.button("💳 PAIEMENTS", use_container_width=True, key="paiements_btn"):
            st.session_state.current_page = "Paiements"
    
    # Initialiser la page courante
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Accueil"
    
    # PAGE ACCUEIL
    if st.session_state.current_page == "Accueil":
        st.markdown("<h1 style='text-align: center; color: #FFD700;'>🏠 TABLEAU DE BORD</h1>", unsafe_allow_html=True)
        
        operations = get_operations()
        operations_en_cours = operations[operations['statut'] == 'En cours']
        
        if not operations_en_cours.empty:
            st.markdown(f"<h2 style='color: #FF6B6B;'>📋 {len(operations_en_cours)} OPÉRATIONS EN COURS</h2>", unsafe_allow_html=True)
            
            for _, op in operations_en_cours.iterrows():
                total_paye = get_total_paiements(op['id'])
                reste_a_payer = op['montant_total'] - total_paye
                
                st.markdown(f"""
                <div class='operation-en-cours'>
                    <h3>👤 {op['client_nom']} - 📞 {op['telephone'] or 'N/A'}</h3>
                    <p><strong>💵 Valeur marchandise:</strong> {format_number(op['valeur_marchandise'])}</p>
                    <p><strong>📈 Taux bénéfice:</strong> {op['taux_benefice']*100}%</p>
                    <p><strong>⏰ Durée:</strong> {op['duree_mois']} mois</p>
                    <p><strong>💰 Montant total:</strong> {format_number(op['montant_total'])}</p>
                    <p><strong>💳 Total payé:</strong> {format_number(total_paye)}</p>
                    <p><strong>⚖️ Reste à payer:</strong> {format_number(reste_a_payer)}</p>
                    <p><strong>📅 Prochaine échéance:</strong> {op['prochaine_echeance']}</p>
                    <p><strong>🎯 Prochain paiement:</strong> {format_number(op['montant_total'] / op['duree_mois'])}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune opération en cours")
        
        # Métriques globales
        st.markdown("<h2 style='color: #4ECDC4;'>📊 MÉTRIQUES GLOBALES</h2>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_montant = operations['montant_total'].sum() if not operations.empty else 0
            st.markdown(f"""
            <div class='metric-card'>
                <h3>💰 TOTAL</h3>
                <h2>{format_number(total_montant)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <h3>📈 EN COURS</h3>
                <h2>{len(operations_en_cours)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            operations_terminees = operations[operations['statut'] == 'Terminé'] if not operations.empty else pd.DataFrame()
            st.markdown(f"""
            <div class='metric-card'>
                <h3>✅ TERMINÉES</h3>
                <h2>{len(operations_terminees)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            clients_count = len(get_clients())
            st.markdown(f"""
            <div class='metric-card'>
                <h3>👥 CLIENTS</h3>
                <h2>{clients_count}</h2>
            </div>
            """, unsafe_allow_html=True)
    
    # PAGE CLIENTS
    elif st.session_state.current_page == "Clients":
        st.markdown("<h1 style='text-align: center; color: #FFD700;'>👥 GESTION DES CLIENTS</h1>", unsafe_allow_html=True)
        
        # Ajouter client
        with st.expander("➕ AJOUTER UN CLIENT", expanded=True):
            with st.form("ajouter_client_form", clear_on_submit=True):
                nom = st.text_input("Nom complet *", placeholder="Nom et prénom")
                telephone = st.text_input("Téléphone", placeholder="+222 XX XX XX XX")
                description = st.text_area("Description", placeholder="Informations supplémentaires...")
                
                if st.form_submit_button("✅ AJOUTER LE CLIENT"):
                    if nom:
                        success, message = ajouter_client(nom, telephone, description)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Le nom est obligatoire!")
        
        # Liste des clients
        st.markdown("<h2 style='color: #FF6B6B;'>📋 LISTE DES CLIENTS</h2>", unsafe_allow_html=True)
        clients = get_clients()
        
        if not clients.empty:
            for _, client in clients.iterrows():
                with st.expander(f"👤 {client['nom']} - 📞 {client['telephone'] or 'N/A'}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"✏️ MODIFIER", key=f"mod_{client['id']}"):
                            st.session_state.edit_client = client['id']
                    
                    with col2:
                        if st.button(f"❌ SUPPRIMER", key=f"del_{client['id']}"):
                            success, message = supprimer_client(client['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    
                    with col3:
                        st.write(f"**📅 Créé le:** {client['date_creation']}")
                    
                    st.write(f"**📝 Description:** {client['description'] or 'Aucune'}")
                    
                    # Modification du client
                    if 'edit_client' in st.session_state and st.session_state.edit_client == client['id']:
                        with st.form(f"modifier_client_{client['id']}"):
                            new_nom = st.text_input("Nom", value=client['nom'])
                            new_tel = st.text_input("Téléphone", value=client['telephone'] or "")
                            new_desc = st.text_area("Description", value=client['description'] or "")
                            
                            if st.form_submit_button("💾 SAUVEGARDER"):
                                success, message = modifier_client(client['id'], new_nom, new_tel, new_desc)
                                if success:
                                    st.success(message)
                                    del st.session_state.edit_client
                                    st.rerun()
                                else:
                                    st.error(message)
        else:
            st.info("Aucun client enregistré")
    
    # PAGE OPÉRATIONS
    elif st.session_state.current_page == "Opérations":
        st.markdown("<h1 style='text-align: center; color: #FFD700;'>📊 GESTION DES OPÉRATIONS</h1>", unsafe_allow_html=True)
        
        clients = get_clients()
        
        # Ajouter opération
        with st.expander("➕ NOUVELLE OPÉRATION", expanded=True):
            if clients.empty:
                st.warning("Aucun client disponible. Veuillez d'abord créer un client.")
            else:
                with st.form("ajouter_operation_form", clear_on_submit=True):
                    client_sel = st.selectbox("Client *", options=clients['nom'].tolist())
                    valeur = st.number_input("Valeur marchandise *", min_value=0, step=1000, value=1000000)
                    taux = st.number_input("Taux bénéfice (%) *", min_value=0, step=1, value=8) / 100
                    duree = st.number_input("Durée (mois) *", min_value=0.0, step=0.5, value=6.0, format="%.1f")
                    
                    if st.form_submit_button("✅ CRÉER L'OPÉRATION"):
                        client_id = clients[clients['nom'] == client_sel].iloc[0]['id']
                        op_id, montant_total = creer_operation(client_id, valeur, taux, duree)
                        st.success(f"Opération #{op_id} créée! Montant total: {format_number(montant_total)}")
        
        # Liste des opérations
        st.markdown("<h2 style='color: #FF6B6B;'>📋 LISTE DES OPÉRATIONS</h2>", unsafe_allow_html=True)
        operations = get_operations()
        
        if not operations.empty:
            for _, op in operations.iterrows():
                total_paye = get_total_paiements(op['id'])
                css_class = "operation-termine" if op['statut'] == 'Terminé' else "operation-en-cours"
                
                st.markdown(f"""
                <div class='{css_class}'>
                    <h3>🔢 #{op['id']} - 👤 {op['client_nom']} - 🏷️ {op['statut']}</h3>
                    <p><strong>💵 Valeur:</strong> {format_number(op['valeur_marchandise'])}</p>
                    <p><strong>📈 Taux:</strong> {op['taux_benefice']*100}%</p>
                    <p><strong>⏰ Durée:</strong> {op['duree_mois']} mois</p>
                    <p><strong>💰 Total:</strong> {format_number(op['montant_total'])}</p>
                    <p><strong>💳 Payé:</strong> {format_number(total_paye)}</p>
                    <p><strong>📅 Créé le:</strong> {op['date_creation']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"✏️ MODIFIER", key=f"mod_op_{op['id']}"):
                        st.session_state.edit_op = op['id']
                with col2:
                    if st.button(f"❌ SUPPRIMER", key=f"del_op_{op['id']}"):
                        success, message = supprimer_operation(op['id'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                with col3:
                    if st.button(f"💳 PAIEMENTS", key=f"pay_op_{op['id']}"):
                        st.session_state.view_payments = op['id']
                
                # Modification opération
                if 'edit_op' in st.session_state and st.session_state.edit_op == op['id']:
                    with st.form(f"modifier_operation_{op['id']}"):
                        new_valeur = st.number_input("Valeur marchandise", value=op['valeur_marchandise'], min_value=0, step=1000)
                        new_taux = st.number_input("Taux bénéfice (%)", value=op['taux_benefice']*100, min_value=0, step=1) / 100
                        new_duree = st.number_input("Durée (mois)", value=op['duree_mois'], min_value=0.0, step=0.5, format="%.1f")
                        
                        if st.form_submit_button("💾 SAUVEGARDER"):
                            success, message = modifier_operation(op['id'], new_valeur, new_taux, new_duree)
                            if success:
                                st.success(message)
                                del st.session_state.edit_op
                                st.rerun()
                            else:
                                st.error(message)
        else:
            st.info("Aucune opération enregistrée")
    
    # PAGE PAIEMENTS
    elif st.session_state.current_page == "Paiements":
        st.markdown("<h1 style='text-align: center; color: #FFD700;'>💳 GESTION DES PAIEMENTS</h1>", unsafe_allow_html=True)
        
        operations = get_operations()
        clients = get_clients()
        
        # Ajouter paiement
        with st.expander("➕ NOUVEAU PAIEMENT", expanded=True):
            if operations.empty:
                st.warning("Aucune opération disponible.")
            else:
                with st.form("ajouter_paiement_form", clear_on_submit=True):
                    # Sélection opération
                    op_options = [f"#{op['id']} - {op['client_nom']} - {format_number(op['montant_total'])}" 
                                for _, op in operations.iterrows()]
                    op_sel = st.selectbox("Opération *", options=op_options)
                    op_id = int(op_sel.split(' - ')[0].replace('#', ''))
                    
                    # Type de paiement
                    type_paiement = st.radio("Type de paiement *", ["Ordinaire", "Anticipé"])
                    
                    # Calcul du montant
                    op_info = operations[operations['id'] == op_id].iloc[0]
                    montant_ordinaire = op_info['montant_total'] / op_info['duree_mois']
                    
                    if type_paiement == "Ordinaire":
                        montant = st.number_input("Montant *", min_value=0, value=int(montant_ordinaire), step=1000)
                    else:
                        montant = st.number_input("Montant *", min_value=0, step=1000)
                    
                    description = st.text_input("Description", placeholder="Mode de paiement, référence...")
                    
                    if st.form_submit_button("✅ ENREGISTRER LE PAIEMENT"):
                        client_id = op_info['client_id']
                        success, message = enregistrer_paiement(op_id, client_id, type_paiement, montant, description)
                        if success:
                            st.success(f"{message} Montant: {format_number(montant)}")
                        else:
                            st.error(message)
        
        # Liste des paiements
        st.markdown("<h2 style='color: #FF6B6B;'>📋 HISTORIQUE DES PAIEMENTS</h2>", unsafe_allow_html=True)
        
        for _, op in operations.iterrows():
            paiements = get_paiements_operation(op['id'])
            if not paiements.empty:
                st.markdown(f"<h3>🔢 Opération #{op['id']} - 👤 {op['client_nom']}</h3>", unsafe_allow_html=True)
                for _, pay in paiements.iterrows():
                    st.markdown(f"""
                    <div class='card'>
                        <p><strong>💳 Type:</strong> {pay['type_paiement']}</p>
                        <p><strong>💰 Montant:</strong> {format_number(pay['montant'])}</p>
                        <p><strong>📅 Date:</strong> {pay['date_paiement']}</p>
                        <p><strong>📝 Description:</strong> {pay['description'] or 'Aucune'}</p>
                    </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
