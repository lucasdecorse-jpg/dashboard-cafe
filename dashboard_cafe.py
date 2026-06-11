import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Cafe Dashboard 2023", page_icon="☕", layout="wide")

# ── CSS custom ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
    border-radius: 12px;
    padding: 16px 20px;
    border-left: 4px solid #7c3aed;
    margin-bottom: 8px;
}
.kpi-label { font-size: 12px; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; }
.kpi-value { font-size: 28px; font-weight: 800; color: #f9fafb; margin: 4px 0; }
.kpi-delta-pos { font-size: 13px; color: #10b981; }
.kpi-delta-neg { font-size: 13px; color: #ef4444; }
section[data-testid="stSidebar"] { background: #111827; }
</style>
""", unsafe_allow_html=True)

MOIS_FR = ["Jan","Fev","Mar","Avr","Mai","Juin","Juil","Aou","Sep","Oct","Nov","Dec"]
ORDRE_JOURS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
JOURS_FR    = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]

PALETTE = ["#7c3aed","#2563eb","#0891b2","#059669","#d97706","#dc2626","#db2777","#65a30d"]

# ── CHARGEMENT ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("cafe_sales_clean.csv", sep=",", encoding="utf-8")
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df.replace(["ERROR", "UNKNOWN"], np.nan, inplace=True)
    for col in ["total_spent", "quantity", "price_per_unit"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    mask_ts = df["total_spent"].isna() & df["quantity"].notna() & df["price_per_unit"].notna()
    df.loc[mask_ts, "total_spent"] = df.loc[mask_ts, "quantity"] * df.loc[mask_ts, "price_per_unit"]
    mask_q = df["quantity"].isna() & df["total_spent"].notna() & df["price_per_unit"].notna()
    df.loc[mask_q, "quantity"] = df.loc[mask_q, "total_spent"] / df.loc[mask_q, "price_per_unit"]
    mask_p = df["price_per_unit"].isna() & df["total_spent"].notna() & df["quantity"].notna()
    df.loc[mask_p, "price_per_unit"] = df.loc[mask_p, "total_spent"] / df.loc[mask_p, "quantity"]
    prix_map = {1.0: "Cookie", 1.5: "Tea", 2.0: "Coffee", 5.0: "Salad"}
    mask_i = df["item"].isna() & df["price_per_unit"].isin(prix_map)
    df.loc[mask_i, "item"] = df.loc[mask_i, "price_per_unit"].map(prix_map)
    df["location"]       = df["location"].fillna("Non renseigne")
    df["payment_method"] = df["payment_method"].fillna("Non renseigne")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["mois"]         = df["transaction_date"].dt.month
    df["jour_semaine"] = df["transaction_date"].dt.day_name()
    df["trimestre"]    = df["transaction_date"].dt.quarter
    df["semestre"]     = df["mois"].apply(lambda x: "S1 Jan-Juin" if x <= 6 else "S2 Juil-Dec")
    return df.drop_duplicates()

df = load_data()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ☕ Filtres")
    st.markdown("---")
    produits_dispo = sorted(df["item"].dropna().unique())
    produits_choix = st.multiselect("Produit", produits_dispo, default=produits_dispo)
    lieux_dispo = [l for l in df["location"].unique() if l != "Non renseigne"]
    lieux_choix = st.multiselect("Lieu", lieux_dispo, default=lieux_dispo)
    paie_dispo = [p for p in df["payment_method"].unique() if p != "Non renseigne"]
    paie_choix = st.multiselect("Paiement", paie_dispo, default=paie_dispo)
    mois_range = st.slider("Periode (mois)", 1, 12, (1, 12))
    st.markdown("---")
    st.caption("Cafe 2023 — 10 000 transactions")

# ── FILTRAGE ──────────────────────────────────────────────────────────────────
df_f = df[
    (df["item"].isin(produits_choix) | df["item"].isna()) &
    (df["location"].isin(lieux_choix + ["Non renseigne"])) &
    (df["payment_method"].isin(paie_choix + ["Non renseigne"])) &
    (df["mois"].between(mois_range[0], mois_range[1]) | df["mois"].isna())
]

ca      = df_f["total_spent"].sum()
pm      = df_f["total_spent"].mean()
n_tx    = df_f["total_spent"].notna().sum()
top_p   = df_f.groupby("item")["total_spent"].sum().idxmax() if df_f["item"].notna().any() else "-"
n_manq  = df_f["total_spent"].isna().sum()
ca_est  = ca + n_manq * pm
ca_nr_lieu  = df_f[df_f["location"] == "Non renseigne"]["total_spent"].sum()
ca_nr_paie  = df_f[df_f["payment_method"] == "Non renseigne"]["total_spent"].sum()
ca_nr_item  = df_f[df_f["item"].isna()]["total_spent"].sum()

# ── HEADER ───────────────────────────────────────────────────────────────────
st.title("☕ Dashboard Ventes — Cafe 2023")
st.caption(f"{len(df_f):,} transactions filtrées sur {len(df):,}")
st.markdown("---")

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("CA Reel",       f"{ca:,.0f} £")
c2.metric("CA Estime",     f"{ca_est:,.0f} £", delta=f"+{n_manq*pm:.0f}£ estimes")
c3.metric("Panier moyen",  f"{pm:.2f} £")
c4.metric("Transactions",  f"{n_tx:,}")
c5.metric("Produit star",  top_p)
c6.metric("CA non attribue", f"{(ca_nr_lieu + ca_nr_paie + ca_nr_item):,.0f} £",
          delta=f"{(ca_nr_lieu + ca_nr_paie + ca_nr_item)/ca*100:.0f}% info manquante", delta_color="inverse")

st.markdown("---")

# ── ONGLETS ───────────────────────────────────────────────────────────────────
tabs = st.tabs(["📦 Produits","📅 Temps","🌡 Saisonnalite","📊 S1 vs S2",
                "📍 Lieu & Paiement","🎛 Analyse libre","⚖ Comparateur",
                "🔭 Exploration","⚠ Qualite"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRODUITS  (bubble chart + treemap + funnel)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Analyse par produit")
    if ca_nr_item > 0:
        st.warning(f"CA non attribue a un produit : {ca_nr_item:,.0f} £ ({ca_nr_item/ca*100:.1f}% du CA)")

    recap = df_f.dropna(subset=["item"]).groupby("item").agg(
        CA=("total_spent","sum"), Ventes=("total_spent","count"),
        Panier=("total_spent","mean"), Qte=("quantity","sum")
    ).round(2).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        # Bubble chart CA vs Panier moyen, taille = volume
        fig = px.scatter(recap, x="Panier", y="CA", size="Qte", color="item",
                         text="item", size_max=60,
                         title="CA vs Panier moyen (taille = volume vendu)",
                         labels={"Panier":"Panier moyen (£)","CA":"CA total (£)","item":"Produit"},
                         color_discrete_sequence=PALETTE)
        fig.update_traces(textposition="top center")
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Salad : fort CA ET fort panier — le produit ideal. Coffee : fort volume mais faible panier.")

    with col2:
        # Treemap
        fig = px.treemap(recap, path=["item"], values="CA", color="Panier",
                         color_continuous_scale="RdYlGn",
                         title="Treemap CA par produit (couleur = panier moyen)",
                         labels={"CA":"CA (£)","Panier":"Panier moyen"})
        fig.update_traces(textinfo="label+value+percent root")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Plus le carre est grand et vert, plus le produit est strategique.")

    col3, col4 = st.columns(2)
    with col3:
        # Funnel CA -> Ventes -> Volume
        recap_sort = recap.sort_values("CA", ascending=False)
        fig = go.Figure(go.Funnel(
            y=recap_sort["item"],
            x=recap_sort["CA"],
            textinfo="value+percent total",
            marker=dict(color=PALETTE[:len(recap_sort)])
        ))
        fig.update_layout(title="Funnel CA par produit")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Visualisation de la concentration du CA — Salad seule represente 21% du total.")

    with col4:
        # Bar chart empile CA + Panier sur meme graphique
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=recap_sort["item"], y=recap_sort["CA"],
                             name="CA total", marker_color=PALETTE[0]), secondary_y=False)
        fig.add_trace(go.Scatter(x=recap_sort["item"], y=recap_sort["Panier"],
                                 name="Panier moyen", mode="lines+markers",
                                 marker=dict(size=10, color=PALETTE[4]),
                                 line=dict(width=3, color=PALETTE[4])), secondary_y=True)
        fig.update_layout(title="CA total + Panier moyen par produit",
                          plot_bgcolor="rgba(0,0,0,0)")
        fig.update_yaxes(title_text="CA (£)", secondary_y=False)
        fig.update_yaxes(title_text="Panier moyen (£)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Le paradoxe Coffee : 1er en ventes, 6eme en CA — le panier moyen explique tout.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TEMPS  (area chart + heatmap jours/mois + tendance)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Analyse temporelle")

    ca_mois = df_f.groupby("mois")["total_spent"].sum().reset_index()
    ca_mois.columns = ["Mois","CA"]
    coef = np.polyfit(ca_mois["Mois"], ca_mois["CA"], 1)
    ca_mois["Tendance"] = np.polyval(coef, ca_mois["Mois"])

    col1, col2 = st.columns(2)
    with col1:
        # Area chart avec tendance
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=ca_mois["CA"],
                                  fill="tozeroy", mode="lines+markers",
                                  name="CA reel", line=dict(color=PALETTE[0], width=2),
                                  marker=dict(size=8),
                                  fillcolor=f"rgba(124,58,237,0.15)"))
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=ca_mois["Tendance"],
                                  mode="lines", name=f"Tendance +{coef[0]:.0f}£/mois",
                                  line=dict(color="#ef4444", dash="dash", width=2)))
        fig.update_layout(title="Evolution du CA mensuel + tendance",
                          xaxis=dict(tickvals=list(range(1,13)), ticktext=MOIS_FR),
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Croissance de +{coef[0]:.0f}£/mois — stable mais peu dynamique (+0.7% sur l'annee).")

    with col2:
        # Heatmap transactions par jour et mois
        df_dates = df_f.dropna(subset=["transaction_date"])
        df_dates["jour_num"] = df_dates["transaction_date"].dt.dayofweek
        heat = df_dates.groupby(["mois","jour_num"])["total_spent"].sum().reset_index()
        heat_pivot = heat.pivot(index="jour_num", columns="mois", values="total_spent").fillna(0)
        fig = px.imshow(heat_pivot,
                        labels=dict(x="Mois", y="Jour", color="CA (£)"),
                        x=MOIS_FR, y=JOURS_FR,
                        color_continuous_scale="Purples",
                        title="Heatmap CA : Jour x Mois")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Aucun carre rouge dominant — confirme la regularite 7j/7 et 12 mois/12.")

    col3, col4 = st.columns(2)
    with col3:
        # Violin plot distribution CA par jour
        df_jour = df_f.dropna(subset=["jour_semaine","total_spent"]).copy()
        df_jour["Jour"] = df_jour["jour_semaine"].map(dict(zip(ORDRE_JOURS, JOURS_FR)))
        fig = px.violin(df_jour, x="Jour", y="total_spent", color="Jour",
                        box=True, points=False,
                        category_orders={"Jour": JOURS_FR},
                        title="Distribution du CA par jour de la semaine",
                        labels={"total_spent":"CA (£)"},
                        color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Les violons sont quasi identiques — aucun jour ne se distingue des autres.")

    with col4:
        # Bar chart transactions par mois + CA
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        vol_mois = df_f.groupby("mois")["transaction_id"].count().reset_index()
        fig.add_trace(go.Bar(x=vol_mois["mois"], y=vol_mois["transaction_id"],
                             name="Nb transactions", marker_color=PALETTE[1],
                             opacity=0.7), secondary_y=False)
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=ca_mois["CA"],
                                  name="CA", mode="lines+markers",
                                  line=dict(color=PALETTE[0], width=3),
                                  marker=dict(size=8)), secondary_y=True)
        fig.update_layout(title="Volume transactions vs CA par mois",
                          xaxis=dict(tickvals=list(range(1,13)), ticktext=MOIS_FR),
                          plot_bgcolor="rgba(0,0,0,0)")
        fig.update_yaxes(title_text="Nb transactions", secondary_y=False)
        fig.update_yaxes(title_text="CA (£)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Volume et CA evoluent de concert — pas de mois avec beaucoup de transactions mais peu de CA.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SAISONNALITE  (heatmap normalisee + line chart + bar amplitude)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Saisonnalite par produit")

    ca_pm = df_f.dropna(subset=["item"]).groupby(["mois","item"])["total_spent"].sum().unstack().fillna(0)
    ca_norm = ca_pm.div(ca_pm.mean()).round(2)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.imshow(ca_norm.T,
                        labels=dict(x="Mois", y="Produit", color="Index (1=moy)"),
                        x=MOIS_FR, color_continuous_scale="RdYlGn",
                        title="Saisonnalite normalisee (1.0 = moyenne annuelle)",
                        zmin=0.6, zmax=1.4)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Vert = au-dessus de la moyenne, Rouge = en dessous. Sandwich fort en hiver, Smoothie fort en ete.")

    with col2:
        fig = px.line(ca_pm.reset_index().melt(id_vars="mois", var_name="Produit", value_name="CA"),
                      x="mois", y="CA", color="Produit", markers=True,
                      title="CA mensuel par produit",
                      labels={"CA":"CA (£)","mois":"Mois"},
                      color_discrete_sequence=PALETTE)
        fig.update_xaxes(tickvals=list(range(1,13)), ticktext=MOIS_FR)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Cliquez sur un produit dans la legende pour l'isoler.")

    # Amplitude saisonnalite
    variation = (ca_norm.max() - ca_norm.min()).round(2).reset_index()
    variation.columns = ["Produit","Amplitude"]
    variation = variation.sort_values("Amplitude", ascending=True)

    fig = go.Figure(go.Bar(
        y=variation["Produit"], x=variation["Amplitude"],
        orientation="h",
        marker=dict(color=variation["Amplitude"], colorscale="RdYlGn_r",
                    showscale=True, colorbar=dict(title="Amplitude"))
    ))
    fig.update_layout(title="Amplitude saisonniere par produit (plus c'est rouge = plus saisonnier)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Sandwich et Smoothie : les deux produits les plus saisonniers (0.40). Cookie : le plus stable (0.27).")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — S1 vs S2
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Comparaison S1 vs S2")

    s1 = df_f[df_f["mois"] <= 6]
    s2 = df_f[df_f["mois"] > 6]

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("CA S1", f"{s1['total_spent'].sum():,.0f} £")
    c2.metric("CA S2", f"{s2['total_spent'].sum():,.0f} £",
              delta=f"{s2['total_spent'].sum()-s1['total_spent'].sum():,.0f} £ vs S1")
    c3.metric("Panier S1", f"{s1['total_spent'].mean():.2f} £")
    c4.metric("Panier S2", f"{s2['total_spent'].mean():.2f} £",
              delta=f"{s2['total_spent'].mean()-s1['total_spent'].mean():.2f} £ vs S1")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        ca_sem = df_f.dropna(subset=["item"]).groupby(["semestre","item"])["total_spent"].sum().reset_index()
        fig = px.bar(ca_sem, x="item", y="total_spent", color="semestre",
                     barmode="group", title="CA par produit S1 vs S2",
                     labels={"total_spent":"CA (£)","item":"Produit","semestre":"Semestre"},
                     color_discrete_sequence=[PALETTE[0], PALETTE[4]])
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Sandwich domine en S1, Salad prend le relais en S2.")

    with col2:
        panier_s1 = s1.groupby("item")["total_spent"].mean()
        panier_s2 = s2.groupby("item")["total_spent"].mean()
        diff = (panier_s2 - panier_s1).round(2).reset_index()
        diff.columns = ["Produit","Delta"]
        diff = diff.sort_values("Delta")
        diff["Couleur"] = diff["Delta"].apply(lambda x: "#10b981" if x >= 0 else "#ef4444")
        fig = go.Figure(go.Bar(
            x=diff["Produit"], y=diff["Delta"],
            marker_color=diff["Couleur"],
            text=diff["Delta"].apply(lambda x: f"+{x:.2f}£" if x >= 0 else f"{x:.2f}£"),
            textposition="outside"
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
        fig.update_layout(title="Variation panier moyen S1 -> S2 (£)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Sandwich -0.54£ en S2, Salad +0.54£ en S2 — compensation parfaite entre les deux produits stars.")

    st.info("Opportunite : une version estivale du Sandwich maintiendrait le panier en S2 sans cannibaliser la Salad.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — LIEU & PAIEMENT  (sunburst + waterfall)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("Lieu & Mode de paiement")

    col1, col2 = st.columns(2)
    with col1:
        # Sunburst lieu > item
        df_sun = df_f.dropna(subset=["item"]).copy()
        df_sun_agg = df_sun.groupby(["location","item"])["total_spent"].sum().reset_index()
        fig = px.sunburst(df_sun_agg, path=["location","item"], values="total_spent",
                          color="total_spent", color_continuous_scale="Blues",
                          title="Sunburst CA : Lieu > Produit",
                          labels={"total_spent":"CA (£)"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Cliquez sur un lieu pour zoomer sur ses produits. Non renseigne = 40% du CA sans lieu connu.")

    with col2:
        # Sunburst paiement > item
        df_sun2 = df_f.dropna(subset=["item"]).copy()
        df_sun2_agg = df_sun2.groupby(["payment_method","item"])["total_spent"].sum().reset_index()
        fig = px.sunburst(df_sun2_agg, path=["payment_method","item"], values="total_spent",
                          color="total_spent", color_continuous_scale="Oranges",
                          title="Sunburst CA : Paiement > Produit",
                          labels={"total_spent":"CA (£)"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Repartition parfaitement uniforme entre les 3 modes de paiement.")

    col3, col4 = st.columns(2)
    with col3:
        # Waterfall CA par lieu
        df_lieu = df_f[df_f["location"] != "Non renseigne"]
        ca_lieu = df_lieu.groupby("location")["total_spent"].sum().reset_index()
        fig = go.Figure(go.Waterfall(
            x=ca_lieu["location"].tolist() + ["Non renseigne","Total"],
            y=ca_lieu["total_spent"].tolist() + [ca_nr_lieu, 0],
            measure=["relative"] * len(ca_lieu) + ["relative","total"],
            connector={"line":{"color":"rgb(63,63,63)"}},
            increasing={"marker":{"color":PALETTE[0]}},
            totals={"marker":{"color":PALETTE[2]}}
        ))
        fig.update_layout(title="Waterfall CA par lieu",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Le Non renseigne pese autant que In-store et Takeaway reunis.")

    with col4:
        # Panier moyen par paiement avec error bars
        df_paie = df_f[df_f["payment_method"] != "Non renseigne"]
        panier_paie = df_paie.groupby("payment_method")["total_spent"].agg(["mean","std"]).reset_index()
        fig = go.Figure()
        for i, row in panier_paie.iterrows():
            fig.add_trace(go.Bar(
                x=[row["payment_method"]], y=[row["mean"]],
                error_y=dict(type="data", array=[row["std"]], visible=True),
                name=row["payment_method"],
                marker_color=PALETTE[i]
            ))
        fig.update_layout(title="Panier moyen par paiement (avec ecart-type)",
                          showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          yaxis_title="£ par transaction")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Ecart-type similaire sur les 3 modes — comportement d'achat identique quel que soit le paiement.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ANALYSE LIBRE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("Construis ton propre graphique")

    AXES = {"Produit":"item","Lieu":"location","Paiement":"payment_method",
            "Mois":"mois","Jour":"jour_semaine","Trimestre":"trimestre","Semestre":"semestre"}
    METRIQUES = {"CA total":"sum","Panier moyen":"mean",
                 "Nb transactions":"count","Quantite vendue":"sum_qty"}
    TYPES = ["Barres","Barres horizontales","Ligne","Area","Scatter","Camembert","Treemap","Funnel"]

    c1,c2,c3,c4 = st.columns(4)
    axe   = c1.selectbox("Grouper par", list(AXES.keys()))
    metr  = c2.selectbox("Mesurer",     list(METRIQUES.keys()))
    coul  = c3.selectbox("Couleur",     ["Auto"] + list(AXES.keys()))
    tgraf = c4.selectbox("Type",        TYPES)

    col_x = AXES[axe]
    agg   = METRIQUES[metr]
    if agg == "sum_qty":
        dg = df_f.groupby(col_x)["quantity"].sum().reset_index()
        dg.columns = [col_x,"v"]
    elif agg == "sum":
        dg = df_f.groupby(col_x)["total_spent"].sum().reset_index()
        dg.columns = [col_x,"v"]
    elif agg == "mean":
        dg = df_f.groupby(col_x)["total_spent"].mean().reset_index()
        dg.columns = [col_x,"v"]
    else:
        dg = df_f.groupby(col_x)["total_spent"].count().reset_index()
        dg.columns = [col_x,"v"]
    dg["v"] = dg["v"].round(2)
    cc = col_x if coul == "Auto" else AXES[coul]

    kw = dict(title=f"{metr} par {axe}", labels={"v":metr, col_x:axe},
              color_discrete_sequence=PALETTE)
    if tgraf == "Barres":
        fig = px.bar(dg, x=col_x, y="v", color=col_x, **kw)
    elif tgraf == "Barres horizontales":
        fig = px.bar(dg.sort_values("v"), x="v", y=col_x, orientation="h", color=col_x, **kw)
    elif tgraf == "Ligne":
        fig = px.line(dg, x=col_x, y="v", markers=True, **kw)
    elif tgraf == "Area":
        fig = px.area(dg, x=col_x, y="v", **kw)
    elif tgraf == "Scatter":
        fig = px.scatter(dg, x=col_x, y="v", size="v", color=col_x, **kw)
    elif tgraf == "Camembert":
        fig = px.pie(dg, values="v", names=col_x, **kw)
    elif tgraf == "Treemap":
        fig = px.treemap(dg, path=[col_x], values="v", **kw)
    else:
        fig = go.Figure(go.Funnel(y=dg.sort_values("v",ascending=False)[col_x],
                                   x=dg.sort_values("v",ascending=False)["v"]))
        fig.update_layout(title=f"{metr} par {axe}")

    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(dg.sort_values("v", ascending=False), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — COMPARATEUR
# ══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("Comparateur de produits")
    plist = sorted(df_f["item"].dropna().unique())
    col_a, col_b = st.columns(2)
    p1 = col_a.selectbox("Produit A", plist, index=0)
    p2 = col_b.selectbox("Produit B", plist, index=1)

    if p1 != p2:
        def stats(p):
            d = df_f[df_f["item"]==p]
            return {"CA total (£)": round(d["total_spent"].sum(),2),
                    "Panier moyen (£)": round(d["total_spent"].mean(),2),
                    "Nb ventes": d["total_spent"].count(),
                    "Qte vendue": round(d["quantity"].sum(),0),
                    "Prix unitaire (£)": round(d["price_per_unit"].mean(),2)}

        s1, s2 = stats(p1), stats(p2)
        cols = st.columns(len(s1))
        for i,(k,v1) in enumerate(s1.items()):
            cols[i].metric(k, f"{v1}", delta=f"{round(v1-s2[k],2)} vs {p2}")

        cats = list(s1.keys())
        mx = {k: max(s1[k],s2[k]) for k in cats}
        n1 = [s1[k]/mx[k]*100 if mx[k]>0 else 0 for k in cats]
        n2 = [s2[k]/mx[k]*100 if mx[k]>0 else 0 for k in cats]

        col1, col2 = st.columns(2)
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=n1+[n1[0]], theta=cats+[cats[0]],
                                          fill="toself", name=p1, line_color=PALETTE[0]))
            fig.add_trace(go.Scatterpolar(r=n2+[n2[0]], theta=cats+[cats[0]],
                                          fill="toself", name=p2, line_color=PALETTE[4]))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),
                              title=f"{p1} vs {p2} — Radar")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            df_c = df_f[df_f["item"].isin([p1,p2])]
            ca_c = df_c.groupby(["mois","item"])["total_spent"].sum().reset_index()
            fig = px.line(ca_c, x="mois", y="total_spent", color="item", markers=True,
                          title="Evolution CA mensuel",
                          labels={"total_spent":"CA (£)","mois":"Mois","item":"Produit"},
                          color_discrete_sequence=[PALETTE[0],PALETTE[4]])
            fig.update_xaxes(tickvals=list(range(1,13)), ticktext=MOIS_FR)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        # Violin distributions
        df_v = df_f[df_f["item"].isin([p1,p2])].dropna(subset=["total_spent"])
        fig = px.violin(df_v, x="item", y="total_spent", color="item", box=True, points="outliers",
                        title="Distribution des transactions",
                        labels={"total_spent":"CA (£)","item":"Produit"},
                        color_discrete_sequence=[PALETTE[0],PALETTE[4]])
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — PYGWALKER
# ══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("Exploration libre — comme Tableau")
    st.markdown("Glisse-depose n'importe quelle colonne pour construire ton propre graphique.")
    try:
        import pygwalker as pyg
        from pygwalker.api.streamlit import StreamlitRenderer
        renderer = StreamlitRenderer(df_f, spec="./gw_config.json", spec_io_mode="rw")
        renderer.explorer()
    except ImportError:
        st.error("Pygwalker non installe — ajoute 'pygwalker' dans requirements.txt")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 — QUALITE DES DONNEES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[8]:
    st.subheader("Qualite des donnees")
    st.error("Probleme structurel : 25 a 28% d'erreurs systeme par mois sur toute l'annee 2023.")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("CA reel",         f"{ca:,.0f} £")
    c2.metric("CA perdu",        f"{n_manq*pm:.0f} £",  delta="-0.4%", delta_color="inverse")
    c3.metric("CA sans produit", f"{ca_nr_item:,.0f} £", delta=f"-{ca_nr_item/ca*100:.1f}%", delta_color="inverse")
    c4.metric("CA sans lieu",    f"{ca_nr_lieu:,.0f} £", delta=f"-{ca_nr_lieu/ca*100:.1f}%", delta_color="inverse")
    c5.metric("CA sans paiement",f"{ca_nr_paie:,.0f} £", delta=f"-{ca_nr_paie/ca*100:.1f}%", delta_color="inverse")

    st.markdown("---")
    st.markdown("""
    **Le vrai probleme : pas le CA perdu (357£ = 0.4%) mais l'INFORMATION perdue**
    - **39.7% du CA** : on ne sait pas si c'etait In-store ou Takeaway
    - **31.2% du CA** : on ne sait pas comment c'etait paye
    - **5.8% du CA** : on ne sait pas quel produit a ete vendu

    Toutes les decisions strategiques sont donc basees sur 60% des donnees seulement.
    """)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        # Gauge qualite globale
        pct_complet = 9048 / 10000 * 100
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=pct_complet,
            delta={"reference": 100, "valueformat": ".1f"},
            title={"text": "Taux de completude des donnees (%)"},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": "#7c3aed"},
                   "steps": [{"range":[0,50],"color":"#ef4444"},
                              {"range":[50,75],"color":"#d97706"},
                              {"range":[75,100],"color":"#059669"}],
                   "threshold":{"line":{"color":"red","width":4},"value":90}}
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        taux_err = {1:27.5,2:26.5,3:27.2,4:28.0,5:25.7,6:24.8,
                    7:25.8,8:25.4,9:26.5,10:26.4,11:24.9,12:25.9}
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(taux_err.keys()), y=list(taux_err.values()),
                                  fill="tozeroy", mode="lines+markers",
                                  line=dict(color="#ef4444", width=2),
                                  fillcolor="rgba(239,68,68,0.15)",
                                  name="Taux erreur"))
        fig.add_hline(y=26.3, line_dash="dash", line_color="white",
                      annotation_text="Moyenne 26.3%", opacity=0.7)
        fig.update_layout(title="Taux d'erreur par mois (%)",
                          xaxis=dict(tickvals=list(range(1,13)), ticktext=MOIS_FR),
                          plot_bgcolor="rgba(0,0,0,0)",
                          yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        statut = {"Complet":9048,"Produit manquant":453,"Date manquante":435,
                  "CA manquant":40,"Produit+Date manquants":24}
        fig = px.pie(values=list(statut.values()), names=list(statut.keys()),
                     title="Categorisation des 10 000 transactions",
                     color_discrete_map={"Complet":"#059669","Produit manquant":"#d97706",
                                          "Date manquante":"#2563eb","CA manquant":"#ef4444",
                                          "Produit+Date manquants":"#7c3aed"},
                     hole=0.4)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.markdown("### Actions prioritaires")
        st.markdown("""
        1. **Rendre location et payment_method obligatoires**
           → recuperer 35 337£ de CA attribuable a un lieu
        2. **Horodatage automatique**
           → eliminer les 460 dates manquantes
        3. **Alerte caisse > 5% erreurs/jour**
           → intervention technique immediate
        4. **Validation total = qty x prix**
           → bloquer les transactions incoherentes

        **Impact total si tout corrige : +26% de donnees exploitables**
        """)

    st.markdown("---")
    st.subheader("Donnees brutes")
    st.dataframe(df_f, use_container_width=True)
    st.download_button("Telecharger CSV", df_f.to_csv(index=False).encode("utf-8"),
                       "cafe_filtree.csv", "text/csv")
    
