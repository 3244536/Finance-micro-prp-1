import streamlit as st
import pandas as pd
import datetime

# -*- coding: utf-8 -*-

# --- Styles CSS personnalisés pour la page de bienvenue ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(to right, #6dd5ed, #2193b0); /* Bleu dégradé */
    color: white;
}
.welcome-container {
    text-align: center;
    padding: 50px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.1); /* Fond semi-transparent */
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
            # Simulation : Pour une vraie application, vous vérifieriez le mot de passe dans une base de données.
            # Ici, on simule une connexion réussie pour un utilisateur "admin".
            if username == "admin" and password == "admin":
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
            # Simulation : Dans une vraie app, on créerait un utilisateur dans la base de données.
            st.success(f"Utilisateur '{new_username}' créé avec succès ! Veuillez vous connecter.")
            st.session_state.show_register = False
            st.experimental_rerun()
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
        if new_password != confirm_new_password:
            st.error("Les mots de passe ne correspondent pas.")
        else:
            # Simulation : Dans une vraie app, on mettrait à jour le mot de passe dans la base de données.
            st.success("Votre mot de passe a été réinitialisé avec succès ! Vous pouvez maintenant vous connecter.")
            st.session_state.show_forgot_password = False
            st.experimental_rerun()

    if st.button("Retour à la connexion"):
        st.session_state.show_forgot_password = False
        st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- Logique d'affichage des pages ---
if not st.session_state.logged_in:
    if st.session_state.show_register:
        register_page()
    elif st.session_state.show_forgot_password:
        forgot_password_page()
    else:
        welcome_page()
else:
    # Simuler une page principale
    st.title("Tableau de bord de l'application")
    st.info(f"Bonjour {st.session_state.current_user}, vous êtes bien connecté.")
    if st.button("Se déconnecter"):
        st.session_state.logged_in = False
        st.experimental_rerun()
