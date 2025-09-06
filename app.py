#-*-coding:utf-8-*-
import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
import io

# --- Configuration de la base de données ---
def init_db():
  conn = sqlite3.connect('compta.db')
  cursor = conn.cursor()
  
# Table des opérations
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS Operations (
    id INTEGER PRIMARY KEY,
    client_name TEXT NOT NULL,
    montant_initial REAL NOT NULL,
    taux_benefice REAL NOT NULL,
    delais_date TEXT NOT NULL,
    paiements_effectues REAL NOT NULL DEFAULT 0.0,
    direction TEXT NOT NULL,
    type_valeur TEXT NOT NULL
    )
    """)
  
# Table des utilisateurs
cursor.execute("""
  CREATE TABLE IF NOT EXISTS Users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL
  )
  """)

# Créer un utilisateur administrateur par défaut si aucun utilisateur n'existe
cursor.execute("SELECT * FROM Users WHERE username='admin'")
if cursor.fetchone() is None:
  hashed_password = hashlib.sha256("admin".encode()).hexdigest()
  cursor.execute("INSERT INTO Users (username, password_hash) VALUES (?, ?)", ('admin', hashed_password))
  conn.commit()
  conn.close()

# --- Fonctions d'authentification ---
def hash_password(password):
  return hashlib.sha256(password.encode()).hexdigest()
  
def verify_user(username, password):
  conn = sqlite3.connect('compta.db')
  cursor = conn.cursor()
  cursor.execute("SELECT password_hash FROM Users WHERE username=?", (username,))
  result = cursor.fetchone()
  conn.close()
  if result:
    return result[0] == hash_password(password)
    return False
  
def create_user(username, password):
  conn = sqlite3.connect('compta.db')
  cursor = conn.cursor()
  try:
    hashed_password = hash_password(password):
    ursor.execute("INSERT INTO Users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    conn.close()
    return True
  except sqlite3.IntegrityError
  conn.close()
  return False

def update_password(username, new_password):
  conn = sqlite3.connect('comptabilite.db')
  cursor = conn.cursor()
  hashed_password = hash_password(new_password)
  cursor.execute("UPDATE Users SET password_hash = ? WHERE username = ?", (hashed_password, username))
  conn.commit()
  conn.close()

# --- Fonctions pour la base de données (Opérations) ---
def add_operation(client_name, montant, taux, delais, direction, type_valeur):
  conn = sqlite3.connect('compta.db')
  cursor = conn.cursor()
  montant_final = montant * (1 + taux)
  cursor.execute("INSERT INTO Operations (client_name, montant_initial, taux_benefice, delais_date, paiements_effectues, direction, type_valeur) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (client_name, montant_final, taux, delais.strftime("%Y-%m-%d"), 0.0, direction, type_valeur))
  conn.commit()
  conn.close()
  
def record_payment(op_id, montant_paye):
  conn = sqlite3.connect('compta.db')
  cursor = conn.cursor()
  cursor.execute("UPDATE Operations SET paiements_effectues = paiements_effectues + ? WHERE id = ?", (montant_paye, op_id))
  conn.commit()
  conn.close()

def get_operations():
  conn = sqlite3.connect('compta.db')
  df = pd.read_sql_query("SELECT * FROM Operations", conn)
  conn.close()
  return df

# --- Styles CSS personnalisés pour la page de bienvenue ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(to right, #6dd5ed, #2193b0);
    color: white;
}
.welcome-container {
    text-align: center;
    padding: 50px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.1);
    margin-top: 10%;
}
.welcome-title {
    font-size: 3.5em;
    font-weight: bold;
    color: white;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}
.welcome-subtitle {
    font-size: 1.5em;
    color: #e0e0e0;
    margin-bottom: 30px;
}
.login-form {
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
    width: 60%;
    margin: 20px auto;
}
.login-form label {
    color: #333;
}
</style>
""", unsafe_allow_html=True)

# --- Initialisation de la session d'état ---
if 'logged_in' not in st.session_state:
  st.session_state.logged_in = False
if 'show_register' not in st.session_state:
  st.session_state.show_register = False
if 'show_forgot_password' not in st.session_state:
  st.session_state.show_forgot_password = False
if 'show_user_management' not in st.session_state:
  st.session_state.show_user_management = False

# --- Page de bienvenue et de connexion ---
def welcome_page():
  st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
  st.markdown('<h1 class="welcome-title">Bienvenue dans Finance Micro Pro</h1>', unsafe_allow_html=True)
  st.markdown('<p class="welcome-subtitle">Gérez vos opérations, clients et bilans avec précision.</p>', unsafe_allow_html=True)
  st.markdown('</div>', unsafe_allow_html=True)
  st.markdown('<div class="login-form">', unsafe_allow_html=True)
  st.subheader("Connexion")
  
  username = st.text_input("Nom d'utilisateur", key="login_username")
  password = st.text_input("Mot de passe", type="password", key="login_password")
  col1, col2, col3 = st.columns(3)
  with col1:
    if st.button("Se connecter", key="login_button"):
      if verify_user(username, password):
        st.session_state.logged_in = True
        st.session_state.current_user = username
        st.experimental_rerun()
      else:
        st.error("Nom d'utilisateur ou mot de passe incorrect.")
  with col2:
    if st.button("S'inscrire", key="show_register_button"):
      st.session_state.show_register = True
      st.experimental_rerun()
  with col3:
    if st.button("Mot de passe oublié ?", key="forgot_password_button"):
      st.session_state.show_forgot_password = True
      st.experimental_rerun()
      st.markdown('</div>', unsafe_allow_html=True)

# --- Page d'enregistrement ---
def register_page():
  st.markdown('<div class="login-form">', unsafe_allow_html=True)
  st.subheader("Créer un Nouvel Utilisateur")
  new_username = st.text_input("Nouveau Nom d'utilisateur", key="new_username")
  new_password = st.text_input("Nouveau Mot de passe", type="password", key="new_password")
  confirm_password = st.text_input("Confirmer le Mot de passe", type="password", key="confirm_password")
  if st.button("Enregistrer l'utilisateur"):
    if new_password == confirm_password:
      if create_user(new_username, new_password):
        st.success("Utilisateur créé avec succès ! Veuillez vous connecter.")
        st.session_state.show_register = False
        st.experimental_rerun()
      else:
        st.error("Ce nom d'utilisateur existe déjà.")
    else:
      st.error("Les mots de passe ne correspondent pas.")
      if st.button("Retour à la connexion"):
        st.session_state.show_register = False
        st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- Page de réinitialisation de mot de passe ---
def forgot_password_page():
  st.markdown('<div class="login-form">', unsafe_allow_html=True)
  st.subheader("Réinitialiser le Mot de Passe")
  st.warning("Pour des raisons de sécurité, veuillez entrer votre nom d'utilisateur et votre nouveau mot de passe.")
  
  reset_username = st.text_input("Nom d'utilisateur", key="reset_username")
  new_password = st.text_input("Nouveau Mot de passe", type="password", key="new_reset_password")
  confirm_new_password = st.text_input("Confirmer le Nouveau Mot de passe", type="password", key="confirm_reset_password")
  
  if st.button("Réinitialiser le mot de passe"):
    conn = sqlite3.connect('comptabilite.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM Users WHERE username=?", (reset_username,))
    user_exists = cursor.fetchone()
    conn.close()
    if not user_exists:
      st.error("Ce nom d'utilisateur n'existe pas.")
    elif new_password != confirm_new_password:
      st.error("Les mots de passe ne correspondent pas.")
    else:
    update_password(reset_username, new_password)
    st.success("Votre mot de passe a été réinitialisé avec succès ! Vous pouvez maintenant vous connecter.")
    st.session_state.show_forgot_password = False
    st.experimental_rerun()
    if st.button("Retour à la connexion"):
      st.session_state.show_forgot_password = False
      st.experimental_rerun()
      st.markdown('</div>', unsafe_allow_html=True)

# --- Application principale ---
def main_app():
  st.sidebar.title(f"Bienvenue, {st.session_state.current_user}!")
  if st.sidebar.button("Se déconnecter"):
    st.session_state.logged_in = False
    st.experimental_rerun()
    
# --- Bouton pour créer des utilisateurs (visible uniquement pour l'admin)
  if st.session_state.current_user == 'admin':
    st.sidebar.markdown("---")
    if st.sidebar.button("Gérer les Utilisateurs"):
      st.session_state.show_user_management = True
      st.experimental_rerun()
      
# --- Affichage conditionnel des sections de l'application ---
    if st.session_state.show_user_management:
      manage_users_page()
    else:
# --- Section des notifications ---
      st.subheader("Notifications")
      today = datetime.date.today()
      df_operations = get_operations()
      
      if not df_operations.empty:
        df_operations['delais_date'] = pd.to_datetime(df_operations['delais_date']).dt.date
        operations_a_notifier = df_operations[(df_operations['delais_date'] < today) & (df_operations['montant_initial'] > df_operations['paiements_effectues']) & (df_operations['direction'] == 'Crédit')]
        if not operations_a_notifier.empty:
          st.error("🚨 Délai expiré pour les opérations suivantes :")
          st.dataframe(operations_a_notifier[['client_name', 'montant_initial', 'paiements_effectues', 'delais_date']])
        else:
          st.success("🎉 Aucun délai expiré pour le moment.")
# --- Formulaire pour ajouter une opération ---
          st.markdown("---")
          st.subheader("Ajouter une Nouvelle Opération")
          with st.form("ajout_operation_form"):
            client_name = st.text_input("Nom du client", key="client_name")
            col1, col2 = st.columns(2)
            with col1:
              direction = st.radio("Direction", ["Crédit", "Débit"])
            with col2:
              type_valeur = st.radio("Type de valeur", ["Espèces", "Nature"])
              montant = st.number_input("Montant Initial", min_value=0.0, format="%.2f", key="montant_initial")
              taux_benefice = st.number_input("Taux de Bénéfice (%)", min_value=0.0, format="%.2f", key="taux_benefice") / 100
              delais = st.date_input("Délai de paiement", key="delais")
              submitted = st.form_submit_button("Ajouter l'Opération")
              if submitted and client_name and montant > 0:
                add_operation(client_name, montant, taux_benefice, delais, direction, type_valeur)
                st.success("Opération ajoutée avec succès !")
                st.experimental_rerun()
# --- Section de bilan ---
                st.markdown("---")
                st.subheader("Bilan par Client")
                df_operations = get_operations()
              if not df_operations.empty:
                df_operations['solde'] = df_operations.apply(
                  lambda row: row['montant_initial'] - row['paiements_effectues'] if row['direction'] == 'Crédit' else row['paiements_effectues'] - row['montant_initial'],
                  axis=1)
                bilan_detaille = df_operations.groupby(['client_name', 'type_valeur']).agg(Total_Crédit=('montant_initial', lambda x: x[df_operations.loc[x.index, 'direction'] == 'Crédit'].sum()),Total_Débit=('montant_initial', lambda x: x[df_operations.loc[x.index, 'direction'] == 'Débit'].sum()),Solde_Net=('solde', 'sum')).reset_index()
                st.dataframe(bilan_detaille, use_container_width=True)
                st.markdown("---")
                st.subheader("Solde Total par Client")
                bilan_global = df_operations.groupby('client_name').agg(Solde_Total=('solde', 'sum')).reset_index()
                st.dataframe(bilan_global, use_container_width=True)

# --- Bouton de téléchargement de la situation client en image ---
                st.markdown("---")
                st.subheader("Télécharger la Situation Client")
              if not bilan_detaille.empty:
                data_for_image = bilan_detaille[['client_name', 'type_valeur', 'Solde_Net']].copy()
                data_for_image['Solde_Net'] = data_for_image['Solde_Net'].apply(lambda x: f"{x:,.2f} €")
                fig, ax = plt.subplots(figsize=(10, len(data_for_image) * 0.5 + 1))
                ax.axis('off')
                table = ax.table(cellText=data_for_image.values,colLabels=data_for_image.columns, cellLoc = 'center', loc = 'center', colColours=["#f5f5f5"]*len(data_for_image.columns))
                table.auto_set_font_size(False)
                table.set_fontsize(12)
                table.scale(1.2, 1.2)
                ax.set_title("Situation Clients - Finance Micro Pro", fontsize=16, pad=20)
                buf = io.BytesIO()
                plt.savefig(buf, format="png", bbox_inches='tight', dpi=300)
                st.download_button(
                  label="Télécharger la situation en image", data=buf.getvalue(), file_name="situation_clients.png", mime="image/png"
                  )
                plt.close(fig)
              else:
                st.info("Aucune donnée de bilan à télécharger pour le moment.")
# --- Enregistrer un paiement (uniquement pour les crédits en espèces) --
                st.markdown("---")
                st.subheader("Enregistrer un Paiement en Espèces")
                df_operations_credit_especes = df_operations[(df_operations['direction'] == 'Crédit') & (df_operations['type_valeur'] == 'Espèces')]
                if not df_operations_credit_especes.empty:
                  operations_unpaid = df_operations_credit_especes[df_operations_credit_especes['montant_initial'] > df_operations_credit_especes['paiements_effectues']]
                  if not operations_unpaid.empty:
                    op_list = operations_unpaid.apply(lambda row: f"ID: {row['id']} - {row['client_name']} ({row['montant_initial'] - row['paiements_effectues']:.2f} €)", axis=1).tolist()
                    selected_op = st.selectbox("Sélectionner l'opération à payer", options=op_list)
                    if selected_op:
                      op_id = int(selected_op.split(' - ')[0].replace('ID: ', ''))
                      solde_restant = operations_unpaid[operations_unpaid['id'] == op_id]['montant_initial'].iloc[0] - operations_unpaid[operations_unpaid['id'] == op_id]['paiements_effectues'].iloc[0]
                      montant_paye = st.number_input(f"Montant du paiement (reste: {solde_restant:.2f} €)", min_value=0.0, max_value=solde_restant, format="%.2f")
                      
                      if st.button("Enregistrer le Paiement"):
                        record_payment(op_id, montant_paye)
                        st.success("Paiement enregistré avec succès !")
                        st.experimental_rerun()
                      else:
                        st.info("🎉 Toutes les opérations de crédit en espèces ont été payées.")
                      else:
                        st.info("Aucune opération de crédit en espèces en cours pour le moment.")
# --- Page de gestion des utilisateurs (accessible uniquement par l'admin) ---
def manage_users_page():
  st.subheader("Gérer les Utilisateurs")
  if st.session_state.current_user != 'admin':
    st.warning("Vous n'avez pas les permissions pour accéder à cette page.")
    if st.button("Retour à l'application principale"):
      st.session_state.show_user_management = False
      st.experimental_rerun()
      return
      st.markdown("---")
      st.write("### Créer un Nouvel Utilisateur")
      with st.form("create_user_form"):
        new_user_username = st.text_input("Nom d'utilisateur", key="create_user_username")
        new_user_password = st.text_input("Mot de passe", type="password", key="create_user_password")
        if st.form_submit_button("Créer l'utilisateur"):
          if new_user_username and new_user_password:
            if create_user(new_user_username, new_user_password):
              st.success(f"Utilisateur '{new_user_username}' créé avec succès !")
            else:
              st.error(f"Erreur : Le nom d'utilisateur '{new_user_username}' existe déjà.")
            else:
              st.warning("Veuillez remplir tous les champs.")
              st.markdown("---")
              st.write("### Liste des Utilisateurs")
              conn = sqlite3.connect('comptabilite.db')
              df_users = pd.read_sql_query("SELECT id, username FROM Users", conn)
              conn.close()
              st.dataframe(df_users, use_container_width=True)
              if st.button("Retour à l'application principale"):
                st.session_state.show_user_management = False
                st.experimental_rerun()

# --- Logique d'affichage des pages ---
              if not st.session_state.logged_in:
                if st.session_state.show_register:
                  register_page()
                elif st.session_state.show_forgot_password:
                  forgot_password_page()
                else:
                  welcome_page()
                else:
                  main_app()
                  init_db()
 
