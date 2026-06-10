import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Café 2023",
    page_icon="☕",
    layout="wide"
)

# ─── CHARGEMENT ET NETTOYAGE ──────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("dirty_cafe_sales.csv", sep=",", encoding="utf-8")

    # Renommer les colonnes
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Remplacer ERROR et UNKNOWN par NaN
    df.replace(["ERROR", "UNKNOWN"], np.nan, inplace=True)

    # Convertir en vrais chiffres
    df["total_spent"]    = pd.to_numeric(df["total_spent"], errors="coerce")
    df["quantity"]       = pd.to_numeric(df["quantity"], errors="coerce")
    df["price_per_unit"] = pd.to_numeric(df["price_per_unit"], errors="coerce")

    # Reconstruire total_spent
    mask_ts = df["total_spent"].isna() & df["quantity"].notna() & df["price_per_unit"].notna()
    df.loc[mask_ts, "total_spent"] = df.loc[mask_ts, "quantity"] * df.loc[mask_ts, "price_per_unit"]

    # Reconstruire quantity
    mask_q = df["quantity"].isna() & df["total_spent"].notna() & df["price_per_unit"].notna()
    df.loc[mask_q, "quantity"] = df.loc[mask_q, "total_spent"] / df.loc[mask_q, "price_per_unit"]

    # Reconstruire price_per_unit
    mask_p = df["price_per_unit"].isna() & df["total_spent"].notna() & df["quantity"].notna()
    df.loc[mask_p, "price_per_unit"] = df.loc[mask_p, "total_spent"] / df.loc[mask_p, "quantity"]

    # Reconstruire items via prix fixe
    prix_to_item = {1.0: "Cookie", 1.5: "Tea", 2.0: "Coffee", 5.0: "Salad"}
    mask_item = df["item"].isna() & df["price_per_unit"].isin(prix_to_item.keys())
    df.loc[mask_item, "item"] = df.loc[mask_item, "price_per_unit"].map(prix_to_item)

    # Colonnes texte
    df["location"]       = df["location"].fillna("Non renseigné")
    df["payment_method"] = df["payment_method"].fillna("Non renseigné")

    # Dates
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["mois"]             = df["transaction_date"].dt.month
    df["mois_nom"]         = df["transaction_date"].dt.strftime("%B")
    df["jour_semaine"]     = df["transaction_date"].dt.day_name()
    df["trimestre"]        = df["transaction_date"].dt.quarter

    df = df.drop_duplicates()
    return df

df = load_data()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("☕ Filtres")
    st.markdown("---")

    # Filtre produit
    produits = sorted(df["item"].dropna().unique())
    produits_choix = st.multiselect(
        "Produit",
        produits,
        default=produits
    )

    # Filtre lieu
    lieux = [l for l in df["location"].unique() if l != "Non renseigné"]
    lieux_choix = st.multiselect(
        "Lieu",
        lieux,
        default=lieux
    )

    # Filtre paiement
    paiements = [p for p in df["payment_method"].unique() if p != "Non renseigné"]
    paiements_choix = st.multiselect(
        "Mode de paiement",
        paiements,
        default=paiements
    )

    # Filtre mois
    mois_choix = st.slider("Mois", 1, 12, (1, 12))

    st.markdown("---")
    st.caption("Données : Café 2023 — 10 000 transactions")

# ─── FILTRAGE ────────────────────────────────────────────────────────────────
df_f = df[
    (df["item"].isin(produits_choix)) &
    (df["location"].isin(lieux_choix + ["Non renseigné"])) &
    (df["payment_method"].isin(paiements_choix + ["Non renseigné"])) &
    (df["mois"].between(mois_choix[0], mois_choix[1]))
]

# ─── TITRE ───────────────────────────────────────────────────────────────────
st.title("☕ Dashboard Ventes — Café 2023")
st.caption(f"Données filtrées : {len(df_f):,} transactions sur {len(df):,} au total")
st.markdown("---")

# ─── KPI ─────────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("CA Total", f"{df_f['total_spent'].sum():,.0f} £")
col2.metric("Panier moyen", f"{df_f['total_spent'].mean():.2f} £")
col3.metric("Transactions", f"{df_f['total_spent'].notna().sum():,}")
col4.metric("Produit star", df_f.groupby("item")["total_spent"].sum().idxmax() if len(df_f) > 0 else "-")
col5.metric("Meilleur mois", str(int(df_f.groupby("mois")["total_spent"].sum().idxmax())) if len(df_f) > 0 else "-")

st.markdown("---")

# ─── ONGLETS ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Produits",
    "📅 Temps",
    "📍 Lieu",
    "💳 Paiement",
    "📋 Données brutes"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRODUITS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Analyse par produit")

    recap = df_f.groupby("item").agg(
        CA_total     = ("total_spent", "sum"),
        Nb_ventes    = ("total_spent", "count"),
        Panier_moyen = ("total_spent", "mean"),
        Qte_vendue   = ("quantity", "sum")
    ).round(2).sort_values("CA_total", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig, ax = plt.subplots(figsize=(7, 4))
        ca = recap["CA_total"].sort_values()
        ax.barh(ca.index, ca.values, color="steelblue")
        ax.set_title("CA total par produit (£)")
        ax.set_xlabel("CA (£)")
        st.pyplot(fig)
        plt.close()

    with col2:
        fig, ax = plt.subplots(figsize=(7, 4))
        panier = recap["Panier_moyen"].sort_values()
        ax.barh(panier.index, panier.values, color="orange")
        ax.set_title("Panier moyen par produit (£)")
        ax.set_xlabel("£ par transaction")
        st.pyplot(fig)
        plt.close()

    col3, col4 = st.columns(2)

    with col3:
        fig, ax = plt.subplots(figsize=(7, 4))
        vol = recap["Qte_vendue"].sort_values()
        ax.barh(vol.index, vol.values, color="green")
        ax.set_title("Volume vendu par produit")
        ax.set_xlabel("Quantité")
        st.pyplot(fig)
        plt.close()

    with col4:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.pie(
            recap["CA_total"],
            labels=recap.index,
            autopct="%1.1f%%",
            startangle=90
        )
        ax.set_title("Répartition du CA")
        st.pyplot(fig)
        plt.close()

    st.markdown("**Tableau récapitulatif**")
    st.dataframe(recap, use_container_width=True)

    with st.expander("💡 Interprétation"):
        st.write("""
        - **Salad** est le produit n°1 en CA (19 070£) avec le panier moyen le plus élevé (15.03£)
        - **Coffee** est le plus commandé en volume mais seulement 6ème en CA — panier moyen de 6.07£
        - **Cookie** est le moins rentable (2.97£ de panier moyen)
        - Les produits premium (Salad, Sandwich, Smoothie) représentent plus de 50% du CA total
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TEMPS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Analyse temporelle")

    col1, col2 = st.columns(2)

    with col1:
        fig, ax = plt.subplots(figsize=(7, 4))
        ca_mois = df_f.groupby("mois")["total_spent"].sum()
        ax.plot(ca_mois.index, ca_mois.values, marker="o", color="steelblue", linewidth=2)
        ax.set_title("CA par mois")
        ax.set_xlabel("Mois")
        ax.set_ylabel("CA (£)")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"], rotation=45)
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        plt.close()

    with col2:
        fig, ax = plt.subplots(figsize=(7, 4))
        ordre_jours = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        labels_jours = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
        ca_jour = df_f.groupby("jour_semaine")["total_spent"].sum().reindex(ordre_jours)
        ax.bar(labels_jours, ca_jour.values, color="orange")
        ax.set_title("CA par jour de la semaine")
        ax.set_ylabel("CA (£)")
        ax.grid(True, alpha=0.3, axis="y")
        st.pyplot(fig)
        plt.close()

    col3, col4 = st.columns(2)

    with col3:
        fig, ax = plt.subplots(figsize=(7, 4))
        ca_trim = df_f.groupby("trimestre")["total_spent"].sum()
        ax.bar(["T1","T2","T3","T4"], ca_trim.values, color="green")
        ax.set_title("CA par trimestre")
        ax.set_ylabel("CA (£)")
        ax.grid(True, alpha=0.3, axis="y")
        st.pyplot(fig)
        plt.close()

    with col4:
        fig, ax = plt.subplots(figsize=(7, 4))
        vol_mois = df_f.groupby("mois")["total_spent"].count()
        ax.bar(range(1,13), vol_mois.values, color="steelblue", alpha=0.7)
        ax.set_title("Nombre de transactions par mois")
        ax.set_xlabel("Mois")
        ax.set_ylabel("Nb transactions")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"], rotation=45)
        ax.grid(True, alpha=0.3, axis="y")
        st.pyplot(fig)
        plt.close()

    with st.expander("💡 Interprétation"):
        st.write("""
        - Le café tourne de façon **très régulière toute l'année** — saisonnalité quasi inexistante
        - Écart de seulement ~700£ entre le meilleur et le pire mois
        - Le CA est distribué uniformément sur les 7 jours de la semaine
        - **T2 (Avril-Juin)** est le meilleur trimestre — raison inconnue, à investiguer
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LIEU
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Analyse par lieu")
    st.info("Les transactions 'Non renseigné' sont exclues de cette analyse (40% du fichier)")

    df_lieu = df_f[df_f["location"] != "Non renseigné"]

    col1, col2 = st.columns(2)

    with col1:
        fig, ax = plt.subplots(figsize=(7, 4))
        ca_lieu = df_lieu.groupby("location")["total_spent"].sum()
        ax.bar(ca_lieu.index, ca_lieu.values, color=["steelblue","orange"])
        ax.set_title("CA total par lieu")
        ax.set_ylabel("CA (£)")
        ax.grid(True, alpha=0.3, axis="y")
        st.pyplot(fig)
        plt.close()

    with col2:
        fig, ax = plt.subplots(figsize=(7, 4))
        panier_lieu = df_lieu.groupby("location")["total_spent"].mean()
        ax.bar(panier_lieu.index, panier_lieu.values, color=["steelblue","orange"])
        ax.set_title("Panier moyen par lieu (£)")
        ax.set_ylabel("£ par transaction")
        ax.grid(True, alpha=0.3, axis="y")
        st.pyplot(fig)
        plt.close()

    col3, col4 = st.columns(2)

    with col3:
        fig, ax = plt.subplots(figsize=(7, 5))
        ca_produit_lieu = df_lieu.groupby(["item","location"])["total_spent"].sum().unstack()
        ca_produit_lieu.plot(kind="bar", ax=ax, color=["steelblue","orange"])
        ax.set_title("CA par produit selon le lieu")
        ax.set_ylabel("CA (£)")
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, alpha=0.3, axis="y")
        st.pyplot(fig)
        plt.close()

    with col4:
        fig, ax = plt.subplots(figsize=(7, 4))
        nb_lieu = df_lieu.groupby("location")["total_spent"].count()
        ax.pie(nb_lieu.values, labels=nb_lieu.index, autopct="%1.1f%%",
               colors=["steelblue","orange"], startangle=90)
        ax.set_title("Répartition des transactions")
        st.pyplot(fig)
        plt.close()

    with st.expander("💡 Interprétation"):
        st.write("""
        - In-store et Takeaway sont **parfaitement équilibrés** en CA et en nombre de transactions
        - Panier moyen quasi identique : 9.03£ In-store vs 8.80£ Takeaway
        - Aucun produit n'a de préférence marquée pour un canal (écart max de 5%)
        - Les deux canaux sont stratégiquement aussi importants l'un que l'autre
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PAIEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Analyse par mode de paiement")
    st.info("Les transactions 'Non renseigné' sont exclues de cette analyse")

    df_paie = df_f[df_f["payment_method"] != "Non renseigné"]

    col1, col2 = st.columns(2)

    with col1:
        fig, ax = plt.subplots(figsize=(7, 4))
        nb_paie = df_paie.groupby("payment_method")["total_spent"].count()
        ax.pie(nb_paie.values, labels=nb_paie.index, autopct="%1.1f%%",
               colors=["steelblue","orange","green"], startangle=90)
        ax.set_title("Répartition des transactions")
        st.pyplot(fig)
        plt.close()

    with col2:
        fig, ax = plt.subplots(figsize=(7, 4))
        panier_paie = df_paie.groupby("payment_method")["total_spent"].mean().round(2)
        ax.bar(panier_paie.index, panier_paie.values, color=["steelblue","orange","green"])
        ax.set_title("Panier moyen par mode de paiement (£)")
        ax.set_ylabel("£ par transaction")
        ax.grid(True, alpha=0.3, axis="y")
        st.pyplot(fig)
        plt.close()

    with st.expander("💡 Interprétation"):
        st.write("""
        - Les 3 modes de paiement sont **parfaitement équilibrés** (~33% chacun)
        - Écart de seulement 60£ sur le CA total entre le meilleur et le pire mode
        - Le comportement d'achat est **indépendant du moyen de paiement**
        - Supprimer un mode de paiement ferait perdre ~33% des transactions
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — DONNÉES BRUTES
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Données brutes filtrées")
    st.write(f"{len(df_f):,} lignes affichées")
    st.dataframe(df_f, use_container_width=True)

    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Télécharger les données filtrées",
        data=csv,
        file_name="cafe_sales_filtre.csv",
        mime="text/csv"
    )
