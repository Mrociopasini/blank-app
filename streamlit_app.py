import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Dashboard rápido", layout="wide")
st.title("Dashboard rápido con Streamlit (Cloud)")

st.sidebar.header("Controles")
uploaded = st.sidebar.file_uploader("Sube un CSV", type=["csv"])
sample_data = st.sidebar.checkbox("Usar datos de ejemplo (si no subes CSV)")

def load_sample():
    rng = pd.date_range("2023-01-01", periods=120, freq="D")
    df = pd.DataFrame({
        "fecha": rng,
        "valor_a": (np.arange(len(rng)) + np.random.randn(len(rng))*10).round(2),
        "valor_b": (np.arange(len(rng))[::-1] + np.random.randn(len(rng))*5).round(2),
        "categoria": np.random.choice(["A","B","C"], size=len(rng))
    })
    return df

if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)
        st.sidebar.success("CSV cargado correctamente")
    except Exception as e:
        st.sidebar.error(f"Error al leer CSV: {e}")
        st.stop()
elif sample_data:
    df = load_sample()
    st.sidebar.info("Usando datos de ejemplo")
else:
    st.info("Sube un CSV en la barra lateral o activa 'Usar datos de ejemplo'.")
    st.stop()

# Intentar parsear fechas simples
for col in df.columns:
    if df[col].dtype == object:
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().sum() >= max(3, len(df)*0.1):
            df[col] = parsed

numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

st.sidebar.write("Columnas detectadas:")
st.sidebar.write("Numéricas:", numeric_cols)
st.sidebar.write("Fechas:", date_cols)
st.sidebar.write("Categóricas:", cat_cols)

# Filtros
st.sidebar.subheader("Filtros")
filters = {}
for c in cat_cols:
    vals = df[c].dropna().unique().tolist()
    sel = st.sidebar.multiselect(f"Filtrar {c}", options=sorted(vals), default=sorted(vals))
    filters[c] = sel
for c in numeric_cols:
    lo = float(df[c].min())
    hi = float(df[c].max())
    rng = st.sidebar.slider(f"Rango {c}", lo, hi, (lo, hi))
    filters[c] = rng

df_filtered = df.copy()
for c, sel in filters.items():
    if c in cat_cols:
        df_filtered = df_filtered[df_filtered[c].isin(sel)]
    elif c in numeric_cols:
        lo, hi = sel
        df_filtered = df_filtered[(df_filtered[c] >= lo) & (df_filtered[c] <= hi)]

st.subheader("Vista previa de datos")
st.dataframe(df_filtered.head(200), use_container_width=True)

st.subheader("Estadísticas rápidas")
st.write(df_filtered.describe(include="all").T)

st.sidebar.subheader("Gráficas")
chart_type = st.sidebar.selectbox("Tipo", ["Scatter", "Histograma", "Serie temporal"])

if chart_type == "Scatter" and len(numeric_cols) >= 2:
    x = st.sidebar.selectbox("Eje X", numeric_cols, index=0)
    y = st.sidebar.selectbox("Eje Y", numeric_cols, index=1)
    color = st.sidebar.selectbox("Color (opcional)", [None] + cat_cols)
    chart = alt.Chart(df_filtered).mark_circle(size=60).encode(
        x=alt.X(x, type="quantitative"),
        y=alt.Y(y, type="quantitative"),
        color=color if color else alt.value("steelblue"),
        tooltip=list(df_filtered.columns)
    ).interactive()
    st.altair_chart(chart, use_container_width=True)
elif chart_type == "Histograma" and numeric_cols:
    col = st.sidebar.selectbox("Columna", numeric_cols)
    bins = st.sidebar.slider("Bins", 5, 100, 30)
    chart = alt.Chart(df_filtered).mark_bar().encode(
        alt.X(col, bin=alt.Bin(maxbins=bins)),
        y='count()'
    )
    st.altair_chart(chart, use_container_width=True)
elif chart_type == "Serie temporal" and date_cols and numeric_cols:
    date_col = st.sidebar.selectbox("Columna fecha", date_cols)
    val_col = st.sidebar.selectbox("Valor", numeric_cols)
    freq = st.sidebar.selectbox("Agrupar por", ["D", "W", "M"])
    agg = st.sidebar.selectbox("Agregación", ["mean", "sum", "median"])
    series = df_filtered.groupby(pd.Grouper(key=date_col, freq=freq))[val_col].agg(agg).reset_index()
    chart = alt.Chart(series).mark_line().encode(
        x=date_col,
        y=val_col,
        tooltip=[date_col, val_col]
    ).interactive()
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("Selecciona una combinación válida de columnas para la gráfica.")

@st.cache_data
def to_csv(dataframe):
    return dataframe.to_csv(index=False).encode("utf-8")

st.download_button("Descargar datos filtrados (CSV)", to_csv(df_filtered), file_name="filtrado.csv", mime="text/csv")
