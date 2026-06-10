import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Café 2023",
    page_icon="☕",
    layout="wide"
)

# ─── CHARGEMENT ET NETTOYAGE ──────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("cafe_sales_clean.csv", sep=",", encoding="utf-8")

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df.replace(["ERROR", "UNKNOWN"], np.nan, inplace=True)

    df["total_spent"]    = pd.to_numeric(df["total_spent"], errors="coerce")
    df["quantity"]       = pd.to_numeric(df["quantity"], errors="coerce")
    df["price_per_unit"] = pd.to_numeric(df["price_per_unit"], errors="coerce")

    mask_ts = df["total_spent"].isna() & df["quantity"].notna() & df["price_per_unit"].notna()
    df.loc[mask_ts, "total_spent"] = df.loc[mask_ts, "quantity"] * df.loc[mask_ts, "price_per_unit"]

    mask_q = df["quantity"].isna() & df["total_spent"].notna() & df["price_per_unit"].notna()
    df.loc[mask_q, "quantity"] = df.loc[mask_q, "total_spent"] / df.loc[mask_q, "price_per_unit"]

    mask_p = df["price_per_unit"].isna() & df["total_spent"].notna() & df["quantity"].notna()
    df.loc[mask_p, "price_per_unit"] = df.loc[mask_p, "total_spent"] / df.loc[mask_p, "quantity"]

    prix_to_item = {1.0: "Cookie", 1.5: "Tea", 2.0: "Coffee", 5.0: "Salad"}
    mask_item = df["item"].isna() & df["price_per_unit"].isin(prix_to_item.keys())
    df.loc[mask_item, "item"] = df.loc[mask_item, "price_per_unit"].map(prix_to_item)

    df["location"]       = df["location"].fillna("Non renseigné")
    df["payment_method"] = df["payment_method"].fillna("Non renseigné")

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

    produits = sorted(df["item"].dropna().unique())
    produits_choix = st.multiselect("Produit", produits, default=produits)

    lieux = [l for l in df["location"].unique() if l != "Non renseigné"]
    lieux_choix = st.multiselect("Lieu", lieux, default=lieux)

    paiements = [p for p in df["payment_method"].unique() if p != "Non renseigné"]
    paiements_choix = st.multiselect("Mode de paiement", paiements, default=paiements)

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
    ).round(2).sort_values("CA_total", ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            recap.sort_values("CA_total"),
            x="CA_total", y="item",
            orientation="h",
            title="CA total par produit (£)",
            color="CA_total",
            color_continuous_scale="Blues",
            labels={"CA_total": "CA (£)", "item": "Produit"}
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            recap.sort_values("Panier_moyen"),
            x="Panier_moyen", y="item",
            orientation="h",
            title="Panier moyen par produit (£)",
            color="Panier_moyen",
            color_continuous_scale="Oranges",
            labels={"Panier_moyen": "£ par transaction", "item": "Produit"}
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig = px.bar(
            recap.sort_values("Qte_vendue"),
            x="Qte_vendue", y="item",
            orientation="h",
            title="Volume vendu par produit",
            color="Qte_vendue",
            color_continuous_scale="Greens",
            labels={"Qte_vendue": "Quantité", "item": "Produit"}
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.pie(
            recap,
            values="CA_total",
            names="item",
            title="Répartition du CA par produit"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Tableau récapitulatif**")
    st.dataframe(recap, use_container_width=True)

    with st.expander("💡 Interprétation"):
        st.write("""
        - **Salad** est le produit n°1 en CA avec le panier moyen le plus élevé (15.03£)
        - **Coffee** est le plus commandé en volume mais seulement 6ème en CA (6.07£ de panier)
        - **Cookie** est le moins rentable (2.97£ de panier moyen)
        - Les produits premium (Salad, Sandwich, Smoothie) représentent plus de 50% du CA
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TEMPS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Analyse temporelle")

    col1, col2 = st.columns(2)

    with col1:
        ca_mois = df_f.groupby("mois")["total_spent"].sum().reset_index()
        ca_mois.columns = ["Mois", "CA"]
        fig = px.line(
            ca_mois, x="Mois", y="CA",
            title="CA par mois",
            markers=True,
            labels={"CA": "CA (£)", "Mois": "Mois"}
        )
        fig.update_traces(line_color="steelblue", marker_size=8)
        fig.update_xaxes(tickvals=list(range(1,13)),
                         ticktext=["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        ordre_jours = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        labels_jours = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
        ca_jour = df_f.groupby("jour_semaine")["total_spent"].sum().reindex(ordre_jours).reset_index()
        ca_jour.columns = ["Jour", "CA"]
        ca_jour["Jour"] = labels_jours
        fig = px.bar(
            ca_jour, x="Jour", y="CA",
            title="CA par jour de la semaine",
            color="CA",
            color_continuous_scale="Oranges",
            labels={"CA": "CA (£)"}
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        ca_trim = df_f.groupby("trimestre")["total_spent"].sum().reset_index()
        ca_trim.columns = ["Trimestre", "CA"]
        ca_trim["Trimestre"] = ["T1","T2","T3","T4"]
        fig = px.bar(
            ca_trim, x="Trimestre", y="CA",
            title="CA par trimestre",
            color="CA",
            color_continuous_scale="Greens",
            labels={"CA": "CA (£)"}
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        ca_produit_mois = df_f.groupby(["mois","item"])["total_spent"].sum().reset_index()
        fig = px.line(
            ca_produit_mois, x="mois", y="total_spent",
            color="item",
            title="CA par produit et par mois",
            markers=True,
            labels={"total_spent": "CA (£)", "mois": "Mois", "item": "Produit"}
        )
        fig.update_xaxes(tickvals=list(range(1,13)),
                         ticktext=["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"])
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("💡 Interprétation"):
        st.write("""
        - Le café tourne de façon **très régulière toute l'année** — saisonnalité quasi inexistante
        - Écart de seulement ~700£ entre le meilleur et le pire mois
        - Le CA est distribué uniformément sur les 7 jours de la semaine
        - **T2 (Avril-Juin)** est le meilleur trimestre
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LIEU
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Analyse par lieu")
    st.info("Les transactions 'Non renseigné' sont exclues (40% du fichier)")

    df_lieu = df_f[df_f["location"] != "Non renseigné"]

    col1, col2 = st.columns(2)

    with col1:
        ca_lieu = df_lieu.groupby("location")["total_spent"].sum().reset_index()
        ca_lieu.columns = ["Lieu", "CA"]
        fig = px.bar(
            ca_lieu, x="Lieu", y="CA",
            title="CA total par lieu",
            color="Lieu",
            labels={"CA": "CA (£)"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        panier_lieu = df_lieu.groupby("location")["total_spent"].mean().reset_index()
        panier_lieu.columns = ["Lieu", "Panier moyen"]
        fig = px.bar(
            panier_lieu, x="Lieu", y="Panier moyen",
            title="Panier moyen par lieu (£)",
            color="Lieu",
            labels={"Panier moyen": "£ par transaction"}
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        ca_produit_lieu = df_lieu.groupby(["item","location"])["total_spent"].sum().reset_index()
        fig = px.bar(
            ca_produit_lieu, x="item", y="total_spent",
            color="location",
            barmode="group",
            title="CA par produit selon le lieu",
            labels={"total_spent": "CA (£)", "item": "Produit", "location": "Lieu"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        nb_lieu = df_lieu.groupby("location")["total_spent"].count().reset_index()
        nb_lieu.columns = ["Lieu", "Nb transactions"]
        fig = px.pie(
            nb_lieu, values="Nb transactions", names="Lieu",
            title="Répartition des transactions par lieu"
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("💡 Interprétation"):
        st.write("""
        - In-store et Takeaway sont **parfaitement équilibrés** en CA et en nombre de transactions
        - Panier moyen quasi identique : 9.03£ In-store vs 8.80£ Takeaway
        - Aucun produit n'a de préférence marquée pour un canal
        - Les deux canaux sont stratégiquement aussi importants l'un que l'autre
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PAIEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Analyse par mode de paiement")
    st.info("Les transactions 'Non renseigné' sont exclues")

    df_paie = df_f[df_f["payment_method"] != "Non renseigné"]

    col1, col2 = st.columns(2)

    with col1:
        nb_paie = df_paie.groupby("payment_method")["total_spent"].count().reset_index()
        nb_paie.columns = ["Paiement", "Nb transactions"]
        fig = px.pie(
            nb_paie, values="Nb transactions", names="Paiement",
            title="Répartition des transactions par mode de paiement"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        panier_paie = df_paie.groupby("payment_method")["total_spent"].mean().reset_index()
        panier_paie.columns = ["Paiement", "Panier moyen"]
        fig = px.bar(
            panier_paie, x="Paiement", y="Panier moyen",
            title="Panier moyen par mode de paiement (£)",
            color="Paiement",
            labels={"Panier moyen": "£ par transaction"}
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        ca_produit_paie = df_paie.groupby(["item","payment_method"])["total_spent"].sum().reset_index()
        fig = px.bar(
            ca_produit_paie, x="item", y="total_spent",
            color="payment_method",
            barmode="group",
            title="CA par produit selon le mode de paiement",
            labels={"total_spent": "CA (£)", "item": "Produit", "payment_method": "Paiement"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        ca_paie = df_paie.groupby("payment_method")["total_spent"].sum().reset_index()
        ca_paie.columns = ["Paiement", "CA"]
        fig = px.bar(
            ca_paie, x="Paiement", y="CA",
            title="CA total par mode de paiement",
            color="Paiement",
            labels={"CA": "CA (£)"}
        )
        st.plotly_chart(fig, use_container_width=True)

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
