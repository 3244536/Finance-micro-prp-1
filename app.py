import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuration de la base de données
def init_db():
    conn = sqlite3.connect('operations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT NOT NULL,
            produit TEXT NOT NULL,
            quantite INTEGER NOT NULL,
            prix_unitaire REAL NOT NULL,
            type_operation TEXT NOT NULL,
            date_operation TEXT NOT NULL,
            statut TEXT DEFAULT 'En cours'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            email TEXT,
            telephone TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Ajouter une opération
def ajouter_operation(client, produit, quantite, prix_unitaire, type_operation):
    conn = sqlite3.connect('operations.db')
    cursor = conn.cursor()
    
    total = quantite * prix_unitaire
    date_op = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO operations (client, produit, quantite, prix_unitaire, type_operation, date_operation)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (client, produit, quantite, prix_unitaire, type_operation, date_op))
    
    conn.commit()
    conn.close()
    return total

# Obtenir toutes les opérations
def get_operations():
    conn = sqlite3.connect('operations.db')
    df = pd.read_sql_query("SELECT * FROM operations ORDER BY date_operation DESC", conn)
    conn.close()
    return df

# Obtenir les statistiques
def get_stats():
    conn = sqlite3.connect('operations.db')
    cursor = conn.cursor()
    
    # Total des ventes
    cursor.execute("SELECT SUM(quantite * prix_unitaire) FROM operations WHERE type_operation = 'Vente'")
    total_ventes = cursor.fetchone()[0] or 0
    
    # Total des achats
    cursor.execute("SELECT SUM(quantite * prix_unitaire) FROM operations WHERE type_operation = 'Achat'")
    total_achats = cursor.fetchone()[0] or 0
    
    # Nombre total d'opérations
    cursor.execute("SELECT COUNT(*) FROM operations")
    total_operations = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_ventes': total_ventes,
        'total_achats': total_achats,
        'benefice': total_ventes - total_achats,
        'total_operations': total_operations
    }

# Interface Streamlit
def main():
    st.set_page_config(page_title="Gestion Commerciale", page_icon="💰", layout="wide")
    
    # Initialisation de la base de données
    init_db()
    
    st.title("💰 Gestion des Opérations Commerciales")
    
    # Menu de navigation
    menu = st.sidebar.selectbox("Navigation", ["Tableau de bord", "Nouvelle Opération", "Historique", "Statistiques"])
    
    if menu == "Tableau de bord":
        st.header("📊 Tableau de Bord")
        
        # Statistiques rapides
        stats = get_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Ventes", f"{stats['total_ventes']:,.2f} €")
        with col2:
            st.metric("Total Achats", f"{stats['total_achats']:,.2f} €")
        with col3:
            st.metric("Bénéfice", f"{stats['benefice']:,.2f} €", 
                     delta_color="inverse" if stats['benefice'] < 0 else "normal")
        with col4:
            st.metric("Opérations", stats['total_operations'])
        
        # Dernières opérations
        st.subheader("📋 Dernières Opérations")
        operations = get_operations()
        if not operations.empty:
            st.dataframe(operations.head(10), use_container_width=True)
        else:
            st.info("Aucune opération enregistrée")
    
    elif menu == "Nouvelle Opération":
        st.header("➕ Nouvelle Opération")
        
        with st.form("nouvelle_operation"):
            col1, col2 = st.columns(2)
            
            with col1:
                client = st.text_input("Client/Fournisseur", placeholder="Nom du client ou fournisseur")
                produit = st.text_input("Produit/Service", placeholder="Nom du produit ou service")
                quantite = st.number_input("Quantité", min_value=1, value=1)
            
            with col2:
                prix_unitaire = st.number_input("Prix Unitaire (€)", min_value=0.0, format="%.2f")
                type_operation = st.selectbox("Type d'opération", ["Vente", "Achat"])
                date_operation = st.date_input("Date", datetime.now())
            
            submitted = st.form_submit_button("Enregistrer l'opération")
            
            if submitted:
                if client and produit and quantite > 0 and prix_unitaire > 0:
                    total = ajouter_operation(client, produit, quantite, prix_unitaire, type_operation)
                    st.success(f"✅ Opération enregistrée ! Total : {total:,.2f} €")
                else:
                    st.error("❌ Veuillez remplir tous les champs correctement")
    
    elif menu == "Historique":
        st.header("📜 Historique des Opérations")
        
        operations = get_operations()
        
        if not operations.empty:
            # Filtres
            col1, col2, col3 = st.columns(3)
            
            with col1:
                types = st.multiselect("Filtrer par type", options=operations['type_operation'].unique())
            with col2:
                clients = st.multiselect("Filtrer par client", options=operations['client'].unique())
            with col3:
                statuts = st.multiselect("Filtrer par statut", options=operations['statut'].unique())
            
            # Application des filtres
            filtered_ops = operations.copy()
            if types:
                filtered_ops = filtered_ops[filtered_ops['type_operation'].isin(types)]
            if clients:
                filtered_ops = filtered_ops[filtered_ops['client'].isin(clients)]
            if statuts:
                filtered_ops = filtered_ops[filtered_ops['statut'].isin(statuts)]
            
            st.dataframe(filtered_ops, use_container_width=True)
            
            # Export des données
            csv = filtered_ops.to_csv(index=False)
            st.download_button(
                label="📥 Exporter en CSV",
                data=csv,
                file_name="operations_commerciales.csv",
                mime="text/csv"
            )
        else:
            st.info("Aucune opération à afficher")
    
    elif menu == "Statistiques":
        st.header("📈 Statistiques Détaillées")
        
        stats = get_stats()
        operations = get_operations()
        
        if not operations.empty:
            # Graphique des ventes vs achats
            st.subheader("Ventes vs Achats")
            ventes_achats = operations.groupby('type_operation')['quantite'].sum()
            st.bar_chart(ventes_achats)
            
            # Top 5 clients
            st.subheader("Top 5 Clients")
            top_clients = operations.groupby('client')['quantite'].sum().nlargest(5)
            st.bar_chart(top_clients)
            
            # Répartition par produit
            st.subheader("Répartition par Produit")
            produits = operations.groupby('produit')['quantite'].sum()
            st.table(produits.sort_values(ascending=False))
        else:
            st.info("Pas assez de données pour afficher les statistiques")

if __name__ == "__main__":
    main()
