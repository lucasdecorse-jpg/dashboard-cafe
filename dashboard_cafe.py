import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Cafe Analytics 2023", page_icon="☕", layout="wide")

st.markdown("""
<style>
section[data-testid="stSidebar"] { background: #0f172a; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.kpi-box {
    background: #1e293b;
    border-radius: 10px;
    padding: 14px 18px;
    border-left: 3px solid #7c3aed;
    height: 100%;
}
.kpi-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.kpi-value { font-size: 26px; font-weight: 800; color: #f1f5f9; }
.kpi-delta { font-size: 12px; margin-top: 4px; }
.kpi-delta-pos { color: #10b981; }
.kpi-delta-neg { color: #f87171; }
.section-title { font-size: 20px; font-weight: 700; color: #f1f5f9; margin: 16px 0 4px 0; border-bottom: 1px solid #334155; padding-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

MOIS_FR     = ["Jan","Fev","Mar","Avr","Mai","Juin","Juil","Aou","Sep","Oct","Nov","Dec"]
ORDRE_JOURS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
JOURS_FR    = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
PALETTE     = ["#7c3aed","#2563eb","#0891b2","#059669","#d97706","#dc2626","#db2777","#65a30d"]

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
    df["location"]         = df["location"].fillna("Non renseigne")
    df["payment_method"]   = df["payment_method"].fillna("Non renseigne")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["mois"]         = df["transaction_date"].dt.month
    df["jour_semaine"] = df["transaction_date"].dt.day_name()
    df["trimestre"]    = df["transaction_date"].dt.quarter
    df["semestre"]     = df["mois"].apply(lambda x: "S1 Jan-Juin" if x <= 6 else "S2 Juil-Dec")
    return df.drop_duplicates()

df = load_data()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ☕ Navigation")
    page = st.selectbox("", [
        "🏠 Vue d'ensemble",
        "📦 Produits",
        "📅 Temps",
        "🌡 Saisonnalite",
        "📊 S1 vs S2",
        "📍 Lieu & Paiement",
        "🎛 Analyse libre",
        "⚖ Comparateur",
        "🔭 Exploration",
        "⚠ Qualite"
    ])
    st.markdown("---")
    st.markdown("## Filtres")

    st.markdown("<br>**🛒 Produits**", unsafe_allow_html=True)
    produits_dispo = sorted(df["item"].dropna().unique())
    produits_choix = [p for p in produits_dispo if st.checkbox(p, value=True, key=f"prod_{p}")]
    if not produits_choix:
        produits_choix = produits_dispo

    st.markdown("<br>**📍 Lieu**", unsafe_allow_html=True)
    lieux_dispo = [l for l in df["location"].unique() if l != "Non renseigne"]
    lieux_choix = [l for l in lieux_dispo if st.checkbox(l, value=True, key=f"lieu_{l}")]
    if not lieux_choix:
        lieux_choix = lieux_dispo

    st.markdown("<br>**💳 Mode de paiement**", unsafe_allow_html=True)
    paie_dispo = [p for p in df["payment_method"].unique() if p != "Non renseigne"]
    paie_choix = [p for p in paie_dispo if st.checkbox(p, value=True, key=f"paie_{p}")]
    if not paie_choix:
        paie_choix = paie_dispo

    st.markdown("<br>**📅 Periode**", unsafe_allow_html=True)
    mois_labels = ["Jan","Fev","Mar","Avr","Mai","Jun","Jul","Aou","Sep","Oct","Nov","Dec"]
    mois_selec = []
    cols_mois = st.columns(4)
    for i, m in enumerate(mois_labels):
        with cols_mois[i % 4]:
            if st.checkbox(m, value=True, key=f"mois_{i+1}"):
                mois_selec.append(i+1)
    if not mois_selec:
        mois_selec = list(range(1,13))
    mois_range = (min(mois_selec), max(mois_selec))
    st.markdown("---")
    st.caption("Cafe 2023 - 10 000 transactions")

# ── FILTRAGE ──────────────────────────────────────────────────────────────────
df_f = df[
    (df["item"].isin(produits_choix) | df["item"].isna()) &
    (df["location"].isin(lieux_choix + ["Non renseigne"])) &
    (df["payment_method"].isin(paie_choix + ["Non renseigne"])) &
    (df["mois"].isin(mois_selec) | df["mois"].isna())
]

ca_total   = df_f["total_spent"].sum()
pm_total   = df_f["total_spent"].mean()
n_tx       = df_f["total_spent"].notna().sum()
top_p      = df_f.groupby("item")["total_spent"].sum().idxmax() if df_f["item"].notna().any() else "-"
n_manq     = df_f["total_spent"].isna().sum()
ca_est     = ca_total + n_manq * pm_total
ca_nr_lieu = df_f[df_f["location"] == "Non renseigne"]["total_spent"].sum()
ca_nr_paie = df_f[df_f["payment_method"] == "Non renseigne"]["total_spent"].sum()
ca_nr_item = df_f[df_f["item"].isna()]["total_spent"].sum()

# ── HEADER ───────────────────────────────────────────────────────────────────
st.title("☕ Cafe Analytics - Vue dirigeant 2023")
st.markdown("Analyse complete des ventes sur 10 000 transactions - nettoyage, reconstruction et exploration des donnees.")
st.markdown("---")

# KPI avec HTML custom
kc = st.columns(6)
kpis = [
    ("CA Reel",        f"{ca_total:,.0f} £",    None,                               None),
    ("CA Estime",      f"{ca_est:,.0f} £",       f"+{n_manq*pm_total:.0f}£ estimes", "pos"),
    ("Panier moyen",   f"{pm_total:.2f} £",      None,                               None),
    ("Transactions",   f"{n_tx:,}",              None,                               None),
    ("Produit star",   top_p,                    "1er en CA et panier moyen",         "pos"),
    ("Info manquante", f"{(ca_nr_lieu+ca_nr_paie+ca_nr_item):,.0f} £",
                       f"{(ca_nr_lieu+ca_nr_paie+ca_nr_item)/ca_total*100:.0f}% sans contexte",
                       "neg"),
]
for i, (label, value, delta, dtype) in enumerate(kpis):
    delta_html = ""
    if delta:
        cls = "kpi-delta-pos" if dtype == "pos" else "kpi-delta-neg"
        delta_html = f'<div class="kpi-delta {cls}">{delta}</div>'
    kc[i].markdown(f"""
    <div class="kpi-box">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 - PRODUITS
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Vue d'ensemble":
    st.markdown("<div class='section-title'>Vue d'ensemble - Ce que les donnees nous disent</div>", unsafe_allow_html=True)
    st.caption("Synthese des 5 insights cles issus de l'analyse de 10 000 transactions sur l'annee 2023.")

    st.markdown("---")

    # Insight 1
    col1, col2 = st.columns([1,2])
    with col1:
        recap_ov = df_f.dropna(subset=["item"]).groupby("item")["total_spent"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(recap_ov, x="item", y="total_spent", color="total_spent",
                     color_continuous_scale="Blues",
                     labels={"total_spent":"CA (£)","item":""})
        fig.update_layout(showlegend=False, coloraxis_showscale=False,
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          margin=dict(t=10,b=10), height=200)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### 🥗 La Salad est le produit star")
        st.markdown("""
        Avec **19 070£ de CA** et un panier moyen de **15.03£**, la Salad est de loin le produit
        le plus rentable. Elle represente 21% du CA total a elle seule.
        Le Coffee, pourtant le plus commande, ne genere que 7 798£ - son prix bas (2£) plombe le CA
        malgre un volume record. **Recommandation : mettre la Salad en avant sur le menu.**
        """)

    st.markdown("---")

    # Insight 2
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("### 📅 Une regularite remarquable - mais peu de croissance")
        st.markdown("""
        Le cafe realise exactement **26 transactions par jour**, 365 jours sur 365, sans exception.
        Le CA mensuel varie de seulement **700£** entre le meilleur et le pire mois.
        La tendance est legerement positive (+4£/mois) mais la croissance annuelle est de **seulement 0.7%**.
        **Recommandation : creer des evenements ou promotions pour casser cette monotonie et creer des pics.**
        """)
    with col2:
        ca_ov = df_f.groupby("mois")["total_spent"].sum().reset_index()
        fig = px.line(ca_ov, x="mois", y="total_spent", markers=True,
                      labels={"total_spent":"","mois":""}, color_discrete_sequence=[PALETTE[0]])
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          margin=dict(t=10,b=10), height=200)
        fig.update_xaxes(tickvals=list(range(1,13)), ticktext=["J","F","M","A","M","J","J","A","S","O","N","D"])
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Insight 3
    col1, col2 = st.columns([1,2])
    with col1:
        ca_ov_s = df_f.dropna(subset=["item"]).groupby(["semestre","item"])["total_spent"].sum().reset_index()
        fig = px.bar(ca_ov_s, x="item", y="total_spent", color="semestre", barmode="group",
                     labels={"total_spent":"","item":"","semestre":""},
                     color_discrete_sequence=[PALETTE[0],PALETTE[4]])
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          margin=dict(t=10,b=10), height=200, showlegend=True,
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### 🔄 Sandwich et Salad se relaient selon la saison")
        st.markdown("""
        En hiver (S1), le **Sandwich domine** avec un panier 0.54£ plus eleve.
        En ete (S2), la **Salad prend le relais** avec exactement +0.54£ de plus.
        La compensation est parfaite - le CA global reste stable.
        **Recommandation : developper une version estivale du Sandwich
        pour maintenir son CA en S2 sans cannibaliser la Salad.**
        """)

    st.markdown("---")

    # Insight 4
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("### ⚖️ In-store et Takeaway sont parfaitement equilibres")
        st.markdown("""
        Les deux canaux font quasi le meme CA et le meme panier moyen (ecart de 0.23£).
        Aucun produit n'a de preference marquee pour un canal.
        Les 3 modes de paiement sont egalement equilibres a **33% chacun**.
        **Conclusion : le comportement d'achat est independant du lieu et du paiement.
        Les deux canaux et les 3 modes sont tous indispensables.**
        """)
    with col2:
        lieu_ov = df_f[df_f["location"] != "Non renseigne"].groupby("location")["total_spent"].sum().reset_index()
        fig = px.pie(lieu_ov, values="total_spent", names="location",
                     color_discrete_sequence=[PALETTE[0],PALETTE[4]])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=10,b=10), height=200)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Insight 5
    st.markdown("### ⚠️ Un probleme systeme urgent : vous analysez sur 60% de vos donnees")
    col1, col2, col3 = st.columns(3)
    col1.error("**35 337 £** de CA sans lieu identifie — vous ne savez pas si 40% de votre CA vient de ventes sur place ou a emporter.")
    col2.error("**27 775 £** de CA sans mode de paiement — vous ne savez pas comment 31% de votre CA a ete encaisse.")
    col3.warning("**Solution :** rendre ces champs obligatoires a la caisse + horodatage automatique des transactions.")

elif page == "📦 Produits":
    st.markdown('<div class="section-title">Analyse par produit</div>', unsafe_allow_html=True)
    if ca_nr_item > 0:
        st.caption(f"ℹ️ {ca_nr_item:,.0f}£ de CA non attribue a un produit ({ca_nr_item/ca_total*100:.1f}%) - produit inconnu mais vente confirmee.")

    recap = df_f.dropna(subset=["item"]).groupby("item").agg(
        CA=("total_spent","sum"), Ventes=("total_spent","count"),
        Panier=("total_spent","mean"), Qte=("quantity","sum")
    ).round(2).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig = px.scatter(recap, x="Panier", y="CA", size="Qte", color="item",
                         text="item", size_max=60,
                         title="CA vs Panier moyen - taille = volume vendu",
                         labels={"Panier":"Panier moyen (£)","CA":"CA total (£)","item":"Produit"},
                         color_discrete_sequence=PALETTE)
        fig.update_traces(textposition="top center")
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Salad : fort CA ET fort panier - le produit ideal. Coffee : fort volume mais faible panier - opportunite d'upsell.")

    with col2:
        fig = px.treemap(recap, path=["item"], values="CA", color="Panier",
                         color_continuous_scale="RdYlGn",
                         title="Treemap CA - couleur = panier moyen",
                         labels={"CA":"CA (£)","Panier":"Panier moyen"})
        fig.update_traces(textinfo="label+value+percent root")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Plus le carre est grand et vert, plus le produit est strategique en CA et en valeur.")

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        recap_sort = recap.sort_values("CA", ascending=False)
        fig = go.Figure(go.Funnel(
            y=recap_sort["item"], x=recap_sort["CA"],
            textinfo="value+percent total",
            marker=dict(color=PALETTE[:len(recap_sort)])
        ))
        fig.update_layout(title="Funnel CA par produit",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Salad seule represente 21% du CA total - 3 produits font plus de 50%.")

    with col4:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=recap_sort["item"], y=recap_sort["CA"],
                             name="CA total", marker_color=PALETTE[0], opacity=0.85),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=recap_sort["item"], y=recap_sort["Panier"],
                                 name="Panier moyen", mode="lines+markers",
                                 marker=dict(size=10, color=PALETTE[4]),
                                 line=dict(width=3, color=PALETTE[4])),
                      secondary_y=True)
        fig.update_layout(title="CA total + Panier moyen superpose",
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        fig.update_yaxes(title_text="CA (£)", secondary_y=False)
        fig.update_yaxes(title_text="Panier moyen (£)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Le paradoxe Coffee : 1er en ventes, 6eme en CA - son prix bas plombe le CA malgre le volume.")

    st.markdown("---")
    st.markdown("**Tableau recapitulatif complet**")
    st.dataframe(recap.sort_values("CA", ascending=False), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 - TEMPS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Temps":
    st.markdown('<div class="section-title">Analyse temporelle</div>', unsafe_allow_html=True)
    st.caption("Le cafe est ouvert 365j/365 avec 26 transactions/jour en moyenne - aucune interruption detectee.")

    ca_mois = df_f.groupby("mois")["total_spent"].sum().reset_index()
    ca_mois.columns = ["Mois","CA"]
    coef = np.polyfit(ca_mois["Mois"], ca_mois["CA"], 1)
    ca_mois["Tendance"] = np.polyval(coef, ca_mois["Mois"])

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=ca_mois["CA"],
                                  fill="tozeroy", mode="lines+markers",
                                  name="CA reel", line=dict(color=PALETTE[0], width=2),
                                  marker=dict(size=8),
                                  fillcolor="rgba(124,58,237,0.15)"))
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=ca_mois["Tendance"],
                                  mode="lines", name=f"Tendance +{coef[0]:.0f}£/mois",
                                  line=dict(color="#ef4444", dash="dash", width=2)))
        fig.update_layout(title="Evolution CA mensuel + tendance lineaire",
                          xaxis=dict(tickvals=list(range(1,13)), ticktext=MOIS_FR),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"+{coef[0]:.0f}£/mois - croissance de 0.7% sur l'annee. Stable mais peu dynamique.")

    with col2:
        df_dates = df_f.dropna(subset=["transaction_date"]).copy()
        df_dates["jour_num"] = df_dates["transaction_date"].dt.dayofweek
        heat = df_dates.groupby(["mois","jour_num"])["total_spent"].sum().reset_index()
        heat_pivot = heat.pivot(index="jour_num", columns="mois", values="total_spent").fillna(0)
        fig = px.imshow(heat_pivot,
                        labels=dict(x="Mois", y="Jour", color="CA (£)"),
                        x=MOIS_FR, y=JOURS_FR,
                        color_continuous_scale="Purples",
                        title="Heatmap CA : Jour x Mois")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Intensite homogene - regularite absolue 7j/7 et 12 mois/12 confirmee.")

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        df_jour = df_f.dropna(subset=["jour_semaine","total_spent"]).copy()
        df_jour["Jour"] = df_jour["jour_semaine"].map(dict(zip(ORDRE_JOURS, JOURS_FR)))
        fig = px.violin(df_jour, x="Jour", y="total_spent", color="Jour",
                        box=True, points=False,
                        category_orders={"Jour": JOURS_FR},
                        title="Distribution du CA par jour de la semaine",
                        labels={"total_spent":"CA (£)"},
                        color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Violons identiques - aucun jour fort, aucun jour faible. Le cafe ne depend pas du weekend.")

    with col4:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        vol_mois = df_f.groupby("mois")["transaction_id"].count().reset_index()
        fig.add_trace(go.Bar(x=vol_mois["mois"], y=vol_mois["transaction_id"],
                             name="Nb transactions", marker_color=PALETTE[1], opacity=0.7),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=ca_mois["Mois"], y=ca_mois["CA"],
                                  name="CA", mode="lines+markers",
                                  line=dict(color=PALETTE[0], width=3), marker=dict(size=8)),
                      secondary_y=True)
        fig.update_layout(title="Volume transactions vs CA mensuel",
                          xaxis=dict(tickvals=list(range(1,13)), ticktext=MOIS_FR),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        fig.update_yaxes(title_text="Nb transactions", secondary_y=False)
        fig.update_yaxes(title_text="CA (£)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Volume et CA evoluent de concert - pas de mois avec beaucoup de clients mais peu de depenses.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 - SAISONNALITE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌡 Saisonnalite":
    st.markdown('<div class="section-title">Saisonnalite par produit</div>', unsafe_allow_html=True)
    st.caption("Le CA global est stable - mais certains produits ont une vraie saisonnalite cachee derriere la moyenne.")

    ca_pm   = df_f.dropna(subset=["item"]).groupby(["mois","item"])["total_spent"].sum().unstack().fillna(0)
    ca_norm = ca_pm.div(ca_pm.mean()).round(2)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.imshow(ca_norm.T,
                        labels=dict(x="Mois", y="Produit", color="Index (1=moy)"),
                        x=MOIS_FR, color_continuous_scale="RdYlGn",
                        title="Saisonnalite normalisee - 1.0 = moyenne annuelle",
                        zmin=0.6, zmax=1.4)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Vert = au-dessus de la moyenne. Sandwich fort en hiver, Smoothie fort en ete.")

    with col2:
        fig = px.line(ca_pm.reset_index().melt(id_vars="mois", var_name="Produit", value_name="CA"),
                      x="mois", y="CA", color="Produit", markers=True,
                      title="CA mensuel par produit - cliquez pour isoler",
                      labels={"CA":"CA (£)","mois":"Mois"},
                      color_discrete_sequence=PALETTE)
        fig.update_xaxes(tickvals=list(range(1,13)), ticktext=MOIS_FR)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Cliquez sur un produit dans la legende pour l'isoler et voir sa courbe en detail.")

    st.markdown("---")
    variation = (ca_norm.max() - ca_norm.min()).round(2).reset_index()
    variation.columns = ["Produit","Amplitude"]
    variation = variation.sort_values("Amplitude", ascending=True)
    fig = go.Figure(go.Bar(
        y=variation["Produit"], x=variation["Amplitude"], orientation="h",
        marker=dict(color=variation["Amplitude"], colorscale="RdYlGn_r",
                    showscale=True, colorbar=dict(title="Amplitude"))
    ))
    fig.update_layout(title="Amplitude saisonniere par produit - rouge = plus saisonnier",
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Sandwich et Smoothie : les plus saisonniers (0.40). Cookie : le plus stable toutes saisons (0.27).")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 - S1 vs S2
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 S1 vs S2":
    st.markdown('<div class="section-title">Comparaison S1 vs S2</div>', unsafe_allow_html=True)
    st.caption("Le CA global est quasi identique entre les deux semestres - mais les raisons sont differentes.")

    s1 = df_f[df_f["mois"] <= 6]
    s2 = df_f[df_f["mois"] > 6]

    sc1,sc2,sc3,sc4 = st.columns(4)
    sc1.metric("CA S1",     f"{s1['total_spent'].sum():,.0f} £")
    sc2.metric("CA S2",     f"{s2['total_spent'].sum():,.0f} £",
               delta=f"{s2['total_spent'].sum()-s1['total_spent'].sum():,.0f} £ vs S1")
    sc3.metric("Panier S1", f"{s1['total_spent'].mean():.2f} £")
    sc4.metric("Panier S2", f"{s2['total_spent'].mean():.2f} £",
               delta=f"{s2['total_spent'].mean()-s1['total_spent'].mean():.2f} £ vs S1")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        ca_sem = df_f.dropna(subset=["item"]).groupby(["semestre","item"])["total_spent"].sum().reset_index()
        fig = px.bar(ca_sem, x="item", y="total_spent", color="semestre", barmode="group",
                     title="CA par produit S1 vs S2",
                     labels={"total_spent":"CA (£)","item":"Produit","semestre":"Semestre"},
                     color_discrete_sequence=[PALETTE[0], PALETTE[4]])
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Sandwich domine en S1 (hiver), Salad prend le relais en S2 (ete).")

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
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Sandwich -0.54£ en S2, Salad +0.54£ - compensation parfaite entre les deux produits stars.")

    st.info("💡 Opportunite : developper une version estivale du Sandwich maintiendrait le panier en S2 sans cannibaliser la Salad.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 - LIEU & PAIEMENT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📍 Lieu & Paiement":
    st.markdown('<div class="section-title">Lieu & Mode de paiement</div>', unsafe_allow_html=True)
    st.caption("40% du CA n'a pas de lieu identifie - 31% n'a pas de mode de paiement. Ces analyses portent sur 60% des donnees.")

    col1, col2 = st.columns(2)
    with col1:
        df_sun_agg = df_f.dropna(subset=["item"]).groupby(["location","item"])["total_spent"].sum().reset_index()
        fig = px.sunburst(df_sun_agg, path=["location","item"], values="total_spent",
                          color="total_spent", color_continuous_scale="Blues",
                          title="Sunburst CA : Lieu > Produit",
                          labels={"total_spent":"CA (£)"})
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Cliquez sur un lieu pour zoomer sur ses produits.")

    with col2:
        df_sun2_agg = df_f.dropna(subset=["item"]).groupby(["payment_method","item"])["total_spent"].sum().reset_index()
        fig = px.sunburst(df_sun2_agg, path=["payment_method","item"], values="total_spent",
                          color="total_spent", color_continuous_scale="Oranges",
                          title="Sunburst CA : Paiement > Produit",
                          labels={"total_spent":"CA (£)"})
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Repartition parfaitement uniforme entre les 3 modes de paiement.")

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
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
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Le 'Non renseigne' pese autant que In-store et Takeaway reunis - probleme systeme prioritaire.")

    with col4:
        df_paie = df_f[df_f["payment_method"] != "Non renseigne"]
        panier_paie = df_paie.groupby("payment_method")["total_spent"].agg(["mean","std"]).reset_index()
        fig = go.Figure()
        for i, row in panier_paie.iterrows():
            fig.add_trace(go.Bar(
                x=[row["payment_method"]], y=[row["mean"]],
                error_y=dict(type="data", array=[row["std"]], visible=True),
                name=row["payment_method"], marker_color=PALETTE[i]
            ))
        fig.update_layout(title="Panier moyen par paiement avec ecart-type",
                          showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", yaxis_title="£ par transaction")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Ecart-type identique sur les 3 modes - le moyen de paiement n'influence pas le comportement d'achat.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 - ANALYSE LIBRE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎛 Analyse libre":
    st.markdown('<div class="section-title">Construis ton propre graphique</div>', unsafe_allow_html=True)
    st.caption("Choisis l'axe, la metrique et le type de visualisation - le graphique se genere en temps reel.")

    AXES     = {"Produit":"item","Lieu":"location","Paiement":"payment_method",
                "Mois":"mois","Jour":"jour_semaine","Trimestre":"trimestre","Semestre":"semestre"}
    METRIQUES = {"CA total":"sum","Panier moyen":"mean",
                 "Nb transactions":"count","Quantite vendue":"sum_qty"}
    TYPES    = ["Barres","Barres horizontales","Ligne","Area","Scatter","Camembert","Treemap","Funnel"]

    al1,al2,al3,al4 = st.columns(4)
    axe   = al1.selectbox("Grouper par", list(AXES.keys()))
    metr  = al2.selectbox("Mesurer",     list(METRIQUES.keys()))
    coul  = al3.selectbox("Couleur",     ["Auto"] + list(AXES.keys()))
    tgraf = al4.selectbox("Type",        TYPES)

    col_x = AXES[axe]
    agg   = METRIQUES[metr]
    if agg == "sum_qty":
        dg = df_f.groupby(col_x)["quantity"].sum().reset_index(); dg.columns=[col_x,"v"]
    elif agg == "sum":
        dg = df_f.groupby(col_x)["total_spent"].sum().reset_index(); dg.columns=[col_x,"v"]
    elif agg == "mean":
        dg = df_f.groupby(col_x)["total_spent"].mean().reset_index(); dg.columns=[col_x,"v"]
    else:
        dg = df_f.groupby(col_x)["total_spent"].count().reset_index(); dg.columns=[col_x,"v"]
    dg["v"] = dg["v"].round(2)

    kw = dict(title=f"{metr} par {axe}", labels={"v":metr,col_x:axe}, color_discrete_sequence=PALETTE)
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
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(dg.sort_values("v", ascending=False), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 - COMPARATEUR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚖ Comparateur":
    st.markdown('<div class="section-title">Comparateur de produits</div>', unsafe_allow_html=True)
    st.caption("Selectionne deux produits pour comparer leurs performances sur tous les criteres.")

    plist = sorted(df_f["item"].dropna().unique())
    col_a, col_b = st.columns(2)
    p1 = col_a.selectbox("Produit A", plist, index=0)
    p2 = col_b.selectbox("Produit B", plist, index=1)

    if p1 != p2:
        def stats(p):
            d = df_f[df_f["item"]==p]
            return {"CA total (£)":round(d["total_spent"].sum(),2),
                    "Panier moyen (£)":round(d["total_spent"].mean(),2),
                    "Nb ventes":d["total_spent"].count(),
                    "Qte vendue":round(d["quantity"].sum(),0),
                    "Prix unitaire (£)":round(d["price_per_unit"].mean(),2)}

        s1, s2 = stats(p1), stats(p2)
        scols = st.columns(len(s1))
        for i,(k,v1) in enumerate(s1.items()):
            scols[i].metric(k, f"{v1}", delta=f"{round(v1-s2[k],2)} vs {p2}")

        st.markdown("---")
        cats = list(s1.keys())
        mx   = {k: max(s1[k],s2[k]) for k in cats}
        n1   = [s1[k]/mx[k]*100 if mx[k]>0 else 0 for k in cats]
        n2   = [s2[k]/mx[k]*100 if mx[k]>0 else 0 for k in cats]

        col1, col2 = st.columns(2)
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=n1+[n1[0]], theta=cats+[cats[0]],
                                          fill="toself", name=p1, line_color=PALETTE[0]))
            fig.add_trace(go.Scatterpolar(r=n2+[n2[0]], theta=cats+[cats[0]],
                                          fill="toself", name=p2, line_color=PALETTE[4]))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),
                              title=f"Radar {p1} vs {p2}",
                              paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            df_c  = df_f[df_f["item"].isin([p1,p2])]
            ca_c  = df_c.groupby(["mois","item"])["total_spent"].sum().reset_index()
            fig   = px.line(ca_c, x="mois", y="total_spent", color="item", markers=True,
                            title="Evolution CA mensuel",
                            labels={"total_spent":"CA (£)","mois":"Mois","item":"Produit"},
                            color_discrete_sequence=[PALETTE[0],PALETTE[4]])
            fig.update_xaxes(tickvals=list(range(1,13)), ticktext=MOIS_FR)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        df_v = df_f[df_f["item"].isin([p1,p2])].dropna(subset=["total_spent"])
        fig  = px.violin(df_v, x="item", y="total_spent", color="item",
                         box=True, points="outliers",
                         title="Distribution des montants de transaction",
                         labels={"total_spent":"CA (£)","item":"Produit"},
                         color_discrete_sequence=[PALETTE[0],PALETTE[4]])
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Le violin montre la distribution complete des transactions - pas seulement la moyenne.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 - EXPLORATION PYGWALKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔭 Exploration":
    st.markdown('<div class="section-title">Exploration libre - comme Tableau</div>', unsafe_allow_html=True)
    st.caption("Glisse-depose n'importe quelle colonne pour construire ton propre graphique interactif.")
    st.markdown("### Croise n'importe quelles colonnes")
    exp_cols = ["item","location","payment_method","mois","jour_semaine","trimestre","semestre"]
    exp_metrics = {"CA total (£)":"sum","Panier moyen (£)":"mean","Nb transactions":"count","Quantite vendue":"sum_qty"}
    exp_types = ["Barres groupees","Barres empilees","Heatmap","Scatter","Ligne","Camembert","Treemap"]

    ex1,ex2,ex3,ex4,ex5 = st.columns(5)
    e_x     = ex1.selectbox("Axe X",    exp_cols, key="ex_x")
    e_color = ex2.selectbox("Couleur",  ["Aucune"] + exp_cols, key="ex_color")
    e_metr  = ex3.selectbox("Metrique", list(exp_metrics.keys()), key="ex_metr")
    e_type  = ex4.selectbox("Type",     exp_types, key="ex_type")
    e_top   = ex5.slider("Top N valeurs", 2, 20, 10, key="ex_top")

    agg = exp_metrics[e_metr]
    grp = [e_x] if e_color == "Aucune" else [e_x, e_color]

    if agg == "sum_qty":
        dg2 = df_f.groupby(grp)["quantity"].sum().reset_index()
        dg2.rename(columns={"quantity":"v"}, inplace=True)
    elif agg == "sum":
        dg2 = df_f.groupby(grp)["total_spent"].sum().reset_index()
        dg2.rename(columns={"total_spent":"v"}, inplace=True)
    elif agg == "mean":
        dg2 = df_f.groupby(grp)["total_spent"].mean().reset_index()
        dg2.rename(columns={"total_spent":"v"}, inplace=True)
    else:
        dg2 = df_f.groupby(grp)["total_spent"].count().reset_index()
        dg2.rename(columns={"total_spent":"v"}, inplace=True)

    dg2["v"] = dg2["v"].round(2)
    top_vals = dg2.groupby(e_x)["v"].sum().nlargest(e_top).index
    dg2 = dg2[dg2[e_x].isin(top_vals)]

    color_col = e_color if e_color != "Aucune" else None
    kw2 = dict(labels={"v":e_metr, e_x:e_x}, color_discrete_sequence=PALETTE)

    if e_type == "Barres groupees":
        fig = px.bar(dg2, x=e_x, y="v", color=color_col, barmode="group",
                     title=f"{e_metr} par {e_x}", **kw2)
    elif e_type == "Barres empilees":
        fig = px.bar(dg2, x=e_x, y="v", color=color_col, barmode="stack",
                     title=f"{e_metr} par {e_x}", **kw2)
    elif e_type == "Heatmap" and color_col:
        pivot = dg2.pivot_table(index=color_col, columns=e_x, values="v", aggfunc="sum").fillna(0)
        fig = px.imshow(pivot, color_continuous_scale="Blues",
                        title=f"Heatmap {e_metr} : {color_col} x {e_x}")
    elif e_type == "Scatter":
        fig = px.scatter(dg2, x=e_x, y="v", color=color_col, size="v",
                         title=f"{e_metr} par {e_x}", **kw2)
    elif e_type == "Ligne":
        fig = px.line(dg2, x=e_x, y="v", color=color_col, markers=True,
                      title=f"{e_metr} par {e_x}", **kw2)
    elif e_type == "Camembert":
        fig = px.pie(dg2, values="v", names=e_x,
                     title=f"{e_metr} par {e_x}", color_discrete_sequence=PALETTE)
    elif e_type == "Treemap":
        path = [e_x] if not color_col else [color_col, e_x]
        fig = px.treemap(dg2, path=path, values="v",
                         title=f"{e_metr} par {e_x}", color_discrete_sequence=PALETTE)
    else:
        fig = px.bar(dg2, x=e_x, y="v", color=color_col,
                     title=f"{e_metr} par {e_x}", **kw2)

    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("**Donnees brutes du graphique**")
    st.dataframe(dg2.sort_values("v", ascending=False), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9 - QUALITE DES DONNEES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚠ Qualite":
    st.markdown('<div class="section-title">Qualite des donnees</div>', unsafe_allow_html=True)
    st.error("⚠️ Vous analysez vos performances sur 60% de vos donnees seulement. Les 40% restants existent mais sont illisibles.")
    st.markdown("""
    > **Ce que ca signifie concretement :** vous prenez des decisions strategiques sur le lieu, le paiement et les produits
    > sans avoir la moitie du tableau. Pas parce que les ventes n'ont pas eu lieu - mais parce que votre systeme de caisse
    > ne les enregistre pas correctement.
    """)

    qc1,qc2,qc3,qc4,qc5 = st.columns(5)
    qc1.metric("CA total enregistre", f"{ca_total:,.0f} £", delta="100% des ventes")
    qc2.metric("CA analysable", f"{ca_total - ca_nr_lieu:,.0f} £",
               delta=f"-{ca_nr_lieu/ca_total*100:.0f}% sans contexte lieu", delta_color="inverse")
    qc3.metric("Ou ont-ils commande ?", f"{ca_nr_lieu:,.0f} £ inconnus",
               delta=f"{ca_nr_lieu/ca_total*100:.0f}% du CA sans lieu", delta_color="inverse")
    qc4.metric("Comment ont-ils paye ?", f"{ca_nr_paie:,.0f} £ inconnus",
               delta=f"{ca_nr_paie/ca_total*100:.0f}% du CA sans paiement", delta_color="inverse")
    qc5.metric("Qu'ont-ils commande ?", f"{ca_nr_item:,.0f} £ inconnus",
               delta=f"{ca_nr_item/ca_total*100:.0f}% du CA sans produit", delta_color="inverse")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
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
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("90.5% de completude - bon score mais le 9.5% manquant cache 40% d'info contextuelle perdue.")

    with col2:
        taux_err = {1:27.5,2:26.5,3:27.2,4:28.0,5:25.7,6:24.8,
                    7:25.8,8:25.4,9:26.5,10:26.4,11:24.9,12:25.9}
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(taux_err.keys()), y=list(taux_err.values()),
                                  fill="tozeroy", mode="lines+markers",
                                  line=dict(color="#ef4444", width=2),
                                  fillcolor="rgba(239,68,68,0.15)"))
        fig.add_hline(y=26.3, line_dash="dash", line_color="white",
                      annotation_text="Moyenne 26.3%", opacity=0.7)
        fig.update_layout(title="Taux d'erreur par mois (%)",
                          xaxis=dict(tickvals=list(range(1,13)), ticktext=MOIS_FR),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Stable toute l'annee - ce n'est pas une panne ponctuelle, c'est un probleme systeme permanent.")

    st.markdown("---")
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
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.markdown("### Actions prioritaires")
        st.markdown("""
        **1. Rendre location et payment_method obligatoires**
        → recuperer 35 337£ de CA attribuable a un lieu

        **2. Horodatage automatique des transactions**
        → eliminer les 460 dates manquantes

        **3. Alerte si une caisse depasse 5% d'erreurs/jour**
        → intervention technique immediate

        **4. Validation automatique : total = qty x prix**
        → bloquer les transactions incoherentes a la source
        """)
        st.success("Impact estime : **+26% de donnees exploitables** si tout corrige.")

    st.markdown("---")
    st.markdown("**Donnees brutes filtrees**")
    st.dataframe(df_f, use_container_width=True)
    st.download_button("⬇️ Telecharger CSV", df_f.to_csv(index=False).encode("utf-8"),
                       "cafe_filtree.csv", "text/csv")
