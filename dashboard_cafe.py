import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Cafe 2023", page_icon="☕", layout="wide")

# ─── CHARGEMENT ───────────────────────────────────────────────────────────────
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
    df["location"]       = df["location"].fillna("Non renseigne")
    df["payment_method"] = df["payment_method"].fillna("Non renseigne")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["mois"]             = df["transaction_date"].dt.month
    df["mois_nom"]         = df["transaction_date"].dt.strftime("%B")
    df["jour_semaine"]     = df["transaction_date"].dt.day_name()
    df["trimestre"]        = df["transaction_date"].dt.quarter
    df["semestre"]         = df["mois"].apply(lambda x: "S1 (Jan-Juin)" if x <= 6 else "S2 (Juil-Dec)")
    df = df.drop_duplicates()
    return df

df = load_data()

# ─── CALCULS CA PERDU ────────────────────────────────────────────────────────
ca_reel_total = df["total_spent"].sum()
nb_sans_ca = df["total_spent"].isna().sum()
panier_moyen_global = df["total_spent"].mean()
ca_perdu_total = nb_sans_ca * panier_moyen_global
ca_estime_total = ca_reel_total + ca_perdu_total
ca_sans_produit = df[df["item"].isna()]["total_spent"].sum()
ca_sans_lieu = df[df["location"] == "Non renseigne"]["total_spent"].sum()
ca_sans_paiement = df[df["payment_method"] == "Non renseigne"]["total_spent"].sum()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtres")
    st.markdown("---")
    produits = sorted(df["item"].dropna().unique())
    produits_choix = st.multiselect("Produit", produits, default=produits)
    lieux = [l for l in df["location"].unique() if l != "Non renseigne"]
    lieux_choix = st.multiselect("Lieu", lieux, default=lieux)
    paiements = [p for p in df["payment_method"].unique() if p != "Non renseigne"]
    paiements_choix = st.multiselect("Mode de paiement", paiements, default=paiements)
    mois_choix = st.slider("Mois", 1, 12, (1, 12))
    st.markdown("---")
    st.caption("Cafe 2023 - 10 000 transactions")

# ─── FILTRAGE — FIX: garde les NaN item ──────────────────────────────────────
df_f = df[
    (df["item"].isin(produits_choix) | df["item"].isna()) &
    (df["location"].isin(lieux_choix + ["Non renseigne"])) &
    (df["payment_method"].isin(paiements_choix + ["Non renseigne"])) &
    (df["mois"].between(mois_choix[0], mois_choix[1]))
]

# ─── RECALCUL CA SUR DF_F ────────────────────────────────────────────────────
ca_reel_f = df_f["total_spent"].sum()
nb_sans_ca_f = df_f["total_spent"].isna().sum()
panier_moyen_f = df_f["total_spent"].mean()
ca_perdu_f = nb_sans_ca_f * panier_moyen_f
ca_estime_f = ca_reel_f + ca_perdu_f
ca_sans_lieu_f = df_f[df_f["location"] == "Non renseigne"]["total_spent"].sum()
ca_sans_paiement_f = df_f[df_f["payment_method"] == "Non renseigne"]["total_spent"].sum()
ca_sans_produit_f = df_f[df_f["item"].isna()]["total_spent"].sum()

# ─── TITRE ───────────────────────────────────────────────────────────────────
st.title("Dashboard Ventes - Cafe 2023")
st.caption(f"Donnees filtrees : {len(df_f):,} transactions sur {len(df):,} au total")
st.markdown("---")

# ─── KPI GLOBAUX ─────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("CA Reel", f"{ca_reel_f:,.0f} £")
col2.metric("CA Estime total", f"{ca_estime_f:,.0f} £", delta=f"+{ca_perdu_f:.0f}£ perdus")
col3.metric("Panier moyen", f"{panier_moyen_f:.2f} £")
col4.metric("Transactions", f"{df_f['total_spent'].notna().sum():,}")
col5.metric("Produit star", df_f.groupby("item")["total_spent"].sum().idxmax() if df_f["item"].notna().any() else "-")
col6.metric("Meilleur mois", str(int(df_f.groupby("mois")["total_spent"].sum().idxmax())) if len(df_f) > 0 else "-")

st.markdown("---")

# ─── ONGLETS ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "Produits",
    "Temps",
    "Saisonnalite",
    "S1 vs S2",
    "Lieu",
    "Paiement",
    "Analyse libre",
    "Comparateur",
    "Top N",
    "Exploration (Pygwalker)",
    "Qualite des donnees"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 - PRODUITS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Analyse par produit")

    recap = df_f.groupby("item").agg(
        CA_total     = ("total_spent", "sum"),
        Nb_ventes    = ("total_spent", "count"),
        Panier_moyen = ("total_spent", "mean"),
        Qte_vendue   = ("quantity", "sum")
    ).round(2).sort_values("CA_total", ascending=False).reset_index()

    if ca_sans_produit_f > 0:
        st.warning(f"CA non attribue a un produit : {ca_sans_produit_f:.2f} £ — la vente a eu lieu mais on ne sait pas quel produit a ete vendu.")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(recap.sort_values("CA_total"), x="CA_total", y="item", orientation="h",
                     title="CA total par produit (£)", color="CA_total",
                     color_continuous_scale="Blues", labels={"CA_total": "CA (£)", "item": "Produit"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("La Salad domine le CA grace a son prix unitaire eleve (5£) malgre un volume moyen.")

    with col2:
        fig = px.bar(recap.sort_values("Panier_moyen"), x="Panier_moyen", y="item", orientation="h",
                     title="Panier moyen par produit (£)", color="Panier_moyen",
                     color_continuous_scale="Oranges", labels={"Panier_moyen": "£/transaction", "item": "Produit"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Salad et Smoothie sont les produits premium. Cookie et Tea sont les produits d'entree de gamme.")

    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(recap.sort_values("Qte_vendue"), x="Qte_vendue", y="item", orientation="h",
                     title="Volume vendu par produit", color="Qte_vendue",
                     color_continuous_scale="Greens", labels={"Qte_vendue": "Quantite", "item": "Produit"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Coffee est le plus commande en volume mais seulement 6eme en CA — opportunite d'upsell.")

    with col4:
        fig = px.pie(recap, values="CA_total", names="item", title="Repartition du CA par produit")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Salad, Sandwich et Smoothie representent plus de 50% du CA total.")

    st.dataframe(recap, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 - TEMPS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Analyse temporelle")

    col1, col2 = st.columns(2)
    with col1:
        ca_mois = df_f.groupby("mois")["total_spent"].sum().reset_index()
        ca_mois.columns = ["Mois", "CA"]
        x = np.array(ca_mois["Mois"], dtype=float)
        y = ca_mois["CA"].values
        coef = np.polyfit(x, y, 1)
        tendance = np.polyval(coef, x)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=ca_mois["CA"], mode="lines+markers",
                                  name="CA reel", line=dict(color="steelblue", width=2), marker=dict(size=8)))
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=tendance, mode="lines",
                                  name=f"Tendance (+{coef[0]:.0f}£/mois)", line=dict(color="red", dash="dash")))
        fig.update_layout(title="CA par mois + tendance",
                          xaxis=dict(tickvals=list(range(1,13)),
                                     ticktext=["Jan","Fev","Mar","Avr","Mai","Juin","Juil","Aou","Sep","Oct","Nov","Dec"]))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Tendance : +{coef[0]:.0f}£ par mois — croissance de 0.7% sur l'annee.")

    with col2:
        ordre_jours = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        labels_jours = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
        ca_jour = df_f.groupby("jour_semaine")["total_spent"].sum().reindex(ordre_jours).reset_index()
        ca_jour["jour_semaine"] = labels_jours
        fig = px.bar(ca_jour, x="jour_semaine", y="total_spent", title="CA par jour de la semaine",
                     color="total_spent", color_continuous_scale="Oranges",
                     labels={"total_spent": "CA (£)", "jour_semaine": "Jour"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("CA uniforme 7j/7 — pas de pic weekend, pas de creux lundi.")

    col3, col4 = st.columns(2)
    with col3:
        transactions_par_jour = df_f.groupby("transaction_date")["transaction_id"].count()
        fig = px.histogram(transactions_par_jour, nbins=20,
                           title="Distribution transactions par jour",
                           labels={"value": "Nb transactions", "count": "Nb jours"})
        fig.add_vline(x=transactions_par_jour.mean(), line_dash="dash", line_color="red",
                      annotation_text=f"Moyenne : {transactions_par_jour.mean():.0f}")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Entre 14 et 40 transactions/jour — la moyenne de 26 cache une vraie variabilite.")

    with col4:
        ca_trim = df_f.groupby("trimestre")["total_spent"].sum().reset_index()
        ca_trim["trimestre"] = ["T1","T2","T3","T4"]
        fig = px.bar(ca_trim, x="trimestre", y="total_spent", title="CA par trimestre",
                     color="total_spent", color_continuous_scale="Greens",
                     labels={"total_spent": "CA (£)", "trimestre": "Trimestre"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("T2 (Avril-Juin) est le meilleur trimestre.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 - SAISONNALITE
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Saisonnalite par produit")

    ca_produit_mois = df_f.groupby(["mois","item"])["total_spent"].sum().unstack().fillna(0)
    ca_produit_mois_norm = ca_produit_mois.div(ca_produit_mois.mean()).round(2)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(ca_produit_mois.reset_index().melt(id_vars="mois", var_name="Produit", value_name="CA"),
                      x="mois", y="CA", color="Produit", markers=True,
                      title="CA par produit et par mois",
                      labels={"CA": "CA (£)", "mois": "Mois"})
        fig.update_xaxes(tickvals=list(range(1,13)),
                         ticktext=["Jan","Fev","Mar","Avr","Mai","Juin","Juil","Aou","Sep","Oct","Nov","Dec"])
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Survolez chaque courbe pour voir les details.")

    with col2:
        fig = px.imshow(ca_produit_mois_norm.T,
                        title="Heatmap saisonnalite (1.0 = moyenne)",
                        color_continuous_scale="RdYlGn",
                        labels=dict(x="Mois", y="Produit", color="Index"),
                        x=["Jan","Fev","Mar","Avr","Mai","Juin","Juil","Aou","Sep","Oct","Nov","Dec"])
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Vert = au-dessus de la moyenne, Rouge = en dessous.")

    variation = (ca_produit_mois_norm.max() - ca_produit_mois_norm.min()).round(2).reset_index()
    variation.columns = ["Produit", "Variation"]
    variation = variation.sort_values("Variation", ascending=False)

    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(variation, x="Produit", y="Variation",
                     title="Amplitude de la saisonnalite par produit",
                     color="Variation", color_continuous_scale="Reds",
                     labels={"Variation": "Amplitude (max-min normalise)"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Smoothie et Sandwich sont les plus saisonniers — Cookie est le plus stable.")

    with col4:
        st.markdown("### Insights cles")
        st.markdown("""
        **Sandwich** -> pic en janvier (+28%), chute en ete

        **Smoothie** -> chute en janvier (-30%), remonte en ete

        **Juice** -> chute en juillet/aout (-25%) — contre-intuitif

        **Cookie** -> le plus stable — achat reflexe toutes saisons

        **Recommandation** : adapter le menu selon la saison.
        """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 - S1 vs S2
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Comparaison S1 vs S2")

    s1 = df_f[df_f["mois"] <= 6]
    s2 = df_f[df_f["mois"] > 6]

    col1, col2, col3 = st.columns(3)
    col1.metric("CA S1", f"{s1['total_spent'].sum():,.0f} £",
                delta=f"{((s2['total_spent'].sum()-s1['total_spent'].sum())/s1['total_spent'].sum()*100):.1f}% vs S2")
    col2.metric("Panier moyen S1", f"{s1['total_spent'].mean():.2f} £",
                delta=f"{s2['total_spent'].mean()-s1['total_spent'].mean():.2f}£ vs S2")
    col3.metric("Transactions S1", f"{s1['total_spent'].count():,}",
                delta=f"{s2['total_spent'].count()-s1['total_spent'].count()} vs S2")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        ca_semestre = df_f.groupby(["semestre","item"])["total_spent"].sum().reset_index()
        fig = px.bar(ca_semestre, x="item", y="total_spent", color="semestre", barmode="group",
                     title="CA par produit - S1 vs S2",
                     labels={"total_spent": "CA (£)", "item": "Produit", "semestre": "Semestre"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Sandwich domine en S1, Salad compense en S2.")

    with col2:
        panier_s1 = s1.groupby("item")["total_spent"].mean()
        panier_s2 = s2.groupby("item")["total_spent"].mean()
        diff = (panier_s2 - panier_s1).round(2).reset_index()
        diff.columns = ["Produit", "Variation"]
        diff = diff.sort_values("Variation")
        fig = px.bar(diff, x="Produit", y="Variation",
                     title="Variation du panier moyen S1 -> S2 (£)",
                     color="Variation", color_continuous_scale=["red","white","green"],
                     color_continuous_midpoint=0,
                     labels={"Variation": "£ (+ = hausse en S2)"})
        fig.add_hline(y=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Sandwich perd 0.54£ en S2, Salad gagne exactement 0.54£ — compensation parfaite.")

    st.info("Opportunite : developper une version estivale du Sandwich pour maintenir le panier en S2.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 - LIEU
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Analyse par lieu")

    pct_non_lieu = ca_sans_lieu_f / ca_reel_f * 100
    st.warning(f"CA sans lieu identifie : {ca_sans_lieu_f:,.0f}£ soit {pct_non_lieu:.1f}% du CA — on ne sait pas si ces ventes etaient In-store ou Takeaway.")

    df_lieu = df_f[df_f["location"] != "Non renseigne"]

    col1, col2 = st.columns(2)
    with col1:
        ca_lieu = df_lieu.groupby("location")["total_spent"].sum().reset_index()
        fig = px.bar(ca_lieu, x="location", y="total_spent",
                     title="CA total par lieu (transactions renseignees)",
                     color="location", labels={"total_spent": "CA (£)", "location": "Lieu"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("In-store et Takeaway sont quasi a egalite — sur les 60% de transactions renseignees.")

    with col2:
        ca_lieu_total = df_f.groupby("location")["total_spent"].sum().reset_index()
        fig = px.pie(ca_lieu_total, values="total_spent", names="location",
                     title="Repartition du CA par lieu (avec Non renseigne)",
                     color_discrete_map={"In-store": "steelblue", "Takeaway": "orange", "Non renseigne": "lightgrey"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Le 'Non renseigne' represente 40% du CA — analyses par lieu incompletes.")

    col3, col4 = st.columns(2)
    with col3:
        panier_lieu = df_lieu.groupby("location")["total_spent"].mean().reset_index()
        fig = px.bar(panier_lieu, x="location", y="total_spent", title="Panier moyen par lieu (£)",
                     color="location", labels={"total_spent": "£/transaction", "location": "Lieu"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Ecart de 0.23£ entre In-store et Takeaway — comportement d'achat identique.")

    with col4:
        ca_produit_lieu = df_lieu.groupby(["item","location"])["total_spent"].sum().reset_index()
        fig = px.bar(ca_produit_lieu, x="item", y="total_spent", color="location", barmode="group",
                     title="CA par produit selon le lieu",
                     labels={"total_spent": "CA (£)", "item": "Produit", "location": "Lieu"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Aucun produit n'a de preference marquee pour un canal.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 - PAIEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("Analyse par mode de paiement")

    pct_non_paie = ca_sans_paiement_f / ca_reel_f * 100
    st.warning(f"CA sans mode de paiement identifie : {ca_sans_paiement_f:,.0f}£ soit {pct_non_paie:.1f}% du CA.")

    df_paie = df_f[df_f["payment_method"] != "Non renseigne"]

    col1, col2 = st.columns(2)
    with col1:
        nb_paie = df_paie.groupby("payment_method")["total_spent"].count().reset_index()
        fig = px.pie(nb_paie, values="total_spent", names="payment_method",
                     title="Repartition des transactions (renseignees)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Les 3 modes de paiement sont parfaitement equilibres a ~33% chacun.")

    with col2:
        ca_paie_total = df_f.groupby("payment_method")["total_spent"].sum().reset_index()
        fig = px.pie(ca_paie_total, values="total_spent", names="payment_method",
                     title="Repartition du CA par paiement (avec Non renseigne)",
                     color_discrete_map={"Credit Card": "steelblue", "Cash": "orange",
                                          "Digital Wallet": "green", "Non renseigne": "lightgrey"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Le 'Non renseigne' represente 31% du CA — analyses par paiement incompletes.")

    col3, col4 = st.columns(2)
    with col3:
        panier_paie = df_paie.groupby("payment_method")["total_spent"].mean().reset_index()
        fig = px.bar(panier_paie, x="payment_method", y="total_spent",
                     title="Panier moyen par mode de paiement",
                     color="payment_method",
                     labels={"total_spent": "£/transaction", "payment_method": "Paiement"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Ecart de 0.13£ entre les 3 modes — comportement d'achat independant du paiement.")

    with col4:
        ca_produit_paie = df_paie.groupby(["item","payment_method"])["total_spent"].sum().reset_index()
        fig = px.bar(ca_produit_paie, x="item", y="total_spent", color="payment_method", barmode="group",
                     title="CA par produit selon le paiement",
                     labels={"total_spent": "CA (£)", "item": "Produit", "payment_method": "Paiement"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Repartition equilibree sur tous les produits.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 - ANALYSE LIBRE
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.subheader("Analyse personnalisee")

    axes_possibles = {
        "Produit": "item", "Lieu": "location", "Mode de paiement": "payment_method",
        "Mois": "mois", "Jour de la semaine": "jour_semaine",
        "Trimestre": "trimestre", "Semestre": "semestre"
    }
    metriques_possibles = {
        "CA total (£)": "sum", "Panier moyen (£)": "mean",
        "Nombre de transactions": "count", "Quantite vendue": "sum_qty"
    }

    col_params1, col_params2, col_params3, col_params4 = st.columns(4)
    with col_params1:
        axe_x = st.selectbox("Grouper par", list(axes_possibles.keys()))
    with col_params2:
        metrique = st.selectbox("Mesurer", list(metriques_possibles.keys()))
    with col_params3:
        couleur_par = st.selectbox("Couleur", ["Aucune"] + list(axes_possibles.keys()))
    with col_params4:
        type_graph = st.selectbox("Type", ["Barres", "Ligne", "Camembert", "Barres horizontales", "Scatter", "Area"])

    col_x = axes_possibles[axe_x]
    agg = metriques_possibles[metrique]

    if agg == "sum_qty":
        df_graph = df_f.groupby(col_x)["quantity"].sum().reset_index()
        df_graph.columns = [col_x, "valeur"]
    elif agg == "sum":
        df_graph = df_f.groupby(col_x)["total_spent"].sum().reset_index()
        df_graph.columns = [col_x, "valeur"]
    elif agg == "mean":
        df_graph = df_f.groupby(col_x)["total_spent"].mean().reset_index()
        df_graph.columns = [col_x, "valeur"]
    else:
        df_graph = df_f.groupby(col_x)["total_spent"].count().reset_index()
        df_graph.columns = [col_x, "valeur"]

    df_graph["valeur"] = df_graph["valeur"].round(2)

    if type_graph == "Barres":
        fig = px.bar(df_graph, x=col_x, y="valeur", color=col_x,
                     title=f"{metrique} par {axe_x}", labels={"valeur": metrique, col_x: axe_x})
    elif type_graph == "Barres horizontales":
        fig = px.bar(df_graph.sort_values("valeur"), x="valeur", y=col_x, orientation="h",
                     color=col_x, title=f"{metrique} par {axe_x}",
                     labels={"valeur": metrique, col_x: axe_x})
    elif type_graph == "Ligne":
        fig = px.line(df_graph, x=col_x, y="valeur", markers=True,
                      title=f"{metrique} par {axe_x}", labels={"valeur": metrique, col_x: axe_x})
    elif type_graph == "Area":
        fig = px.area(df_graph, x=col_x, y="valeur",
                      title=f"{metrique} par {axe_x}", labels={"valeur": metrique, col_x: axe_x})
    elif type_graph == "Scatter":
        fig = px.scatter(df_graph, x=col_x, y="valeur", color=col_x, size="valeur",
                         title=f"{metrique} par {axe_x}", labels={"valeur": metrique, col_x: axe_x})
    else:
        fig = px.pie(df_graph, values="valeur", names=col_x, title=f"{metrique} par {axe_x}")

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_graph.sort_values("valeur", ascending=False), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 - COMPARATEUR
# ══════════════════════════════════════════════════════════════════════════════
with tab8:
    st.subheader("Comparateur de produits")
    produits_dispo = sorted(df_f["item"].dropna().unique())
    col_a, col_b = st.columns(2)
    with col_a:
        produit_1 = st.selectbox("Produit A", produits_dispo, index=0)
    with col_b:
        produit_2 = st.selectbox("Produit B", produits_dispo, index=1)

    if produit_1 != produit_2:
        def get_stats(produit):
            d = df_f[df_f["item"] == produit]
            return {
                "CA total (£)": round(d["total_spent"].sum(), 2),
                "Panier moyen (£)": round(d["total_spent"].mean(), 2),
                "Nb transactions": d["total_spent"].count(),
                "Quantite vendue": round(d["quantity"].sum(), 0),
                "Prix unitaire (£)": round(d["price_per_unit"].mean(), 2)
            }

        stats1 = get_stats(produit_1)
        stats2 = get_stats(produit_2)
        cols = st.columns(len(stats1))
        for i, (key, val1) in enumerate(stats1.items()):
            val2 = stats2[key]
            delta = round(val1 - val2, 2)
            cols[i].metric(f"{key}", f"{val1}", delta=f"{delta} vs {produit_2}")

        categories = list(stats1.keys())
        max_vals = {k: max(stats1[k], stats2[k]) for k in categories}
        vals1_norm = [stats1[k] / max_vals[k] * 100 if max_vals[k] > 0 else 0 for k in categories]
        vals2_norm = [stats2[k] / max_vals[k] * 100 if max_vals[k] > 0 else 0 for k in categories]

        col1, col2 = st.columns(2)
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=vals1_norm + [vals1_norm[0]], theta=categories + [categories[0]],
                                          fill="toself", name=produit_1))
            fig.add_trace(go.Scatterpolar(r=vals2_norm + [vals2_norm[0]], theta=categories + [categories[0]],
                                          fill="toself", name=produit_2))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                              title=f"{produit_1} vs {produit_2} - Radar")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            df_comp = df_f[df_f["item"].isin([produit_1, produit_2])]
            ca_comp_mois = df_comp.groupby(["mois","item"])["total_spent"].sum().reset_index()
            fig = px.line(ca_comp_mois, x="mois", y="total_spent", color="item", markers=True,
                          title="Evolution du CA par mois",
                          labels={"total_spent": "CA (£)", "mois": "Mois", "item": "Produit"})
            fig.update_xaxes(tickvals=list(range(1,13)),
                             ticktext=["Jan","Fev","Mar","Avr","Mai","Juin","Juil","Aou","Sep","Oct","Nov","Dec"])
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 - TOP N
# ══════════════════════════════════════════════════════════════════════════════
with tab9:
    st.subheader("Top N produits")
    n_produits = st.slider("Nombre de produits", min_value=1,
                           max_value=len(df_f["item"].dropna().unique()), value=3)
    metrique_top = st.radio("Classer par", ["CA total", "Panier moyen", "Volume vendu"], horizontal=True)

    recap_top = df_f.groupby("item").agg(
        CA_total     = ("total_spent", "sum"),
        Panier_moyen = ("total_spent", "mean"),
        Qte_vendue   = ("quantity", "sum")
    ).round(2).reset_index()

    if metrique_top == "CA total":
        top_df = recap_top.nlargest(n_produits, "CA_total")
        y_col, label = "CA_total", "CA total (£)"
    elif metrique_top == "Panier moyen":
        top_df = recap_top.nlargest(n_produits, "Panier_moyen")
        y_col, label = "Panier_moyen", "Panier moyen (£)"
    else:
        top_df = recap_top.nlargest(n_produits, "Qte_vendue")
        y_col, label = "Qte_vendue", "Quantite vendue"

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(top_df.sort_values(y_col), x=y_col, y="item", orientation="h",
                     title=f"Top {n_produits} - {metrique_top}",
                     color=y_col, color_continuous_scale="Blues",
                     labels={y_col: label, "item": "Produit"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(top_df, values=y_col, names="item", title=f"Repartition - Top {n_produits}")
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(top_df.sort_values(y_col, ascending=False), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 10 - PYGWALKER
# ══════════════════════════════════════════════════════════════════════════════
with tab10:
    st.subheader("Exploration libre des donnees")
    st.markdown("Glisse-depose les colonnes pour construire n'importe quel graphique — comme Tableau ou PowerBI.")

    try:
        import pygwalker as pyg
        from pygwalker.api.streamlit import StreamlitRenderer
        renderer = StreamlitRenderer(df_f, spec="./gw_config.json", spec_io_mode="rw")
        renderer.explorer()
    except ImportError:
        st.error("Pygwalker n'est pas installe. Ajoute 'pygwalker' dans ton requirements.txt")
        st.info("Pour l'installer : pip install pygwalker")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 11 - QUALITE DES DONNEES
# ══════════════════════════════════════════════════════════════════════════════
with tab11:
    st.subheader("Qualite des donnees")
    st.error("Probleme structurel : 25 a 28% d'erreurs systeme par mois en continu sur toute l'annee 2023.")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("CA reel", f"{ca_reel_f:,.0f} £")
    col2.metric("CA perdu", f"{ca_perdu_f:.0f} £", delta="-0.4% du CA", delta_color="inverse")
    col3.metric("CA sans produit", f"{ca_sans_produit_f:,.0f} £", delta="-5.8% du CA", delta_color="inverse")
    col4.metric("CA sans lieu", f"{ca_sans_lieu_f:,.0f} £", delta="-39.7% du CA", delta_color="inverse")
    col5.metric("CA sans paiement", f"{ca_sans_paiement_f:,.0f} £", delta="-31.2% du CA", delta_color="inverse")

    st.markdown("---")
    st.markdown("""
    **Le vrai probleme n'est pas le CA perdu (357£ soit 0.4%) — c'est l'INFORMATION perdue :**
    - 39.7% du CA : on ne sait pas si c'etait In-store ou Takeaway
    - 31.2% du CA : on ne sait pas comment c'etait paye
    - 5.8% du CA : on ne sait pas quel produit a ete vendu

    **Toutes les decisions strategiques basees sur ces analyses sont donc incompletes.**
    """)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        manquants = {"item": 480, "transaction_date": 460, "total_spent": 40,
                     "quantity": 38, "price_per_unit": 38}
        fig = px.bar(x=list(manquants.keys()), y=list(manquants.values()),
                     title="Valeurs manquantes apres nettoyage",
                     color=list(manquants.values()), color_continuous_scale="Reds",
                     labels={"x": "Colonne", "y": "Nb valeurs manquantes"})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        taux_erreur_mois = {1: 27.5, 2: 26.5, 3: 27.2, 4: 28.0, 5: 25.7, 6: 24.8,
                            7: 25.8, 8: 25.4, 9: 26.5, 10: 26.4, 11: 24.9, 12: 25.9}
        fig = px.line(x=list(taux_erreur_mois.keys()), y=list(taux_erreur_mois.values()),
                      title="Taux d'erreur par mois (%)", markers=True,
                      labels={"x": "Mois", "y": "Taux d'erreur (%)"})
        fig.add_hline(y=26.3, line_dash="dash", line_color="red",
                      annotation_text="Moyenne : 26.3%")
        fig.update_xaxes(tickvals=list(range(1,13)),
                         ticktext=["Jan","Fev","Mar","Avr","Mai","Juin","Juil","Aou","Sep","Oct","Nov","Dec"])
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        statut_data = {"Complet": 9048, "Produit manquant": 453, "Date manquante": 435,
                       "CA manquant": 40, "Produit + Date manquants": 24}
        fig = px.pie(values=list(statut_data.values()), names=list(statut_data.keys()),
                     title="Categorisation des 10 000 transactions",
                     color_discrete_map={"Complet": "green", "Produit manquant": "orange",
                                          "Date manquante": "yellow", "CA manquant": "red",
                                          "Produit + Date manquants": "darkred"})
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.markdown("### Actions prioritaires")
        st.markdown("""
        1. Rendre location et payment_method obligatoires a la caisse
        2. Horodatage automatique des transactions
        3. Alerte si une caisse depasse 5% d'erreurs sur une journee
        4. Verification automatique : total = quantity x price_per_unit

        ### Impact si corrige
        - +26% de donnees recuperees
        - 35 337£ de CA attribuable a un lieu
        - 27 775£ de CA attribuable a un mode de paiement
        """)

    st.markdown("---")
    st.subheader("Donnees brutes filtrees")
    st.dataframe(df_f, use_container_width=True)
    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button(label="Telecharger les donnees filtrees", data=csv,
                       file_name="cafe_sales_filtre.csv", mime="text/csv")
