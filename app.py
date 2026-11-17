import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Open Orders Inflow (Sample)", layout="wide")

TODAY = pd.Timestamp("2026-11-17")
BACKORDER_BUFFER_DAYS = 14
BLUE = "#2F5D8A"
ORANGE = "#D9822B"


@st.cache_data
def make_sample_orders(n=80, seed=11):
    """Made-up open orders. No real client data."""
    rng = np.random.default_rng(seed)
    customers = [f"Customer {c}" for c in "ABCDEFGHIJKL"]
    weights = np.array([9, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1, 1], dtype=float)
    df = pd.DataFrame({
        "Order": [f"SO-{2001 + i}" for i in range(n)],
        "Customer": rng.choice(customers, n, p=weights / weights.sum()),
        "Amount": rng.integers(1500, 60000, n).round(-1),
        "Terms (days)": rng.choice([0, 15, 30, 30, 30, 45], n),
        "Target date": TODAY + pd.to_timedelta((rng.beta(1.0, 2.0, n) * 520).astype(int) + 5, unit="D"),
        "Backordered": rng.random(n) < 0.25,
    })
    lag = df["Terms (days)"] + np.where(df["Backordered"], BACKORDER_BUFFER_DAYS, 0)
    df["Expected cash date"] = df["Target date"] + pd.to_timedelta(lag, unit="D")
    df["Days out"] = (df["Expected cash date"] - TODAY).dt.days
    return df


orders = make_sample_orders()

WINDOWS = [("2 weeks", 14), ("1 month", 30), ("3 months", 90), ("6 months", 180),
           ("9 months", 270), ("12 months", 365), ("18 months", 548)]

st.title("Open Orders: Expected Cash Inflow")
st.caption("Sample data for illustration. Not client data. As of Nov 17, 2026.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Open order value", f"${orders['Amount'].sum():,.0f}")
c2.metric("Open orders", f"{len(orders)}")
c3.metric("Backordered orders", f"{int(orders['Backordered'].sum())}")
c4.metric("Backordered value", f"${orders.loc[orders['Backordered'], 'Amount'].sum():,.0f}")

left, right = st.columns(2)

with left:
    st.subheader("Expected inflow by period")
    labels, in_stock, backordered = [], [], []
    for label, days in WINDOWS:
        w = orders[orders["Days out"] <= days]
        labels.append(label)
        in_stock.append(w.loc[~w["Backordered"], "Amount"].sum())
        backordered.append(w.loc[w["Backordered"], "Amount"].sum())
    fig = go.Figure()
    fig.add_bar(x=labels, y=in_stock, name="In stock", marker_color=BLUE)
    fig.add_bar(x=labels, y=backordered, name="Backordered", marker_color=ORANGE)
    fig.update_layout(barmode="stack", height=380, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis_title="Cumulative inflow ($)", legend=dict(orientation="h", y=1.1),
                      yaxis_tickformat="$,.0f")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top customers by open order value")
    top = (orders.groupby("Customer")["Amount"].sum().sort_values(ascending=True).tail(8))
    fig2 = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=BLUE))
    fig2.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_tickformat="$,.0f")
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Open orders")
view = orders.sort_values("Expected cash date")[
    ["Order", "Customer", "Amount", "Target date", "Expected cash date", "Backordered"]
].head(8).copy()
view["Target date"] = view["Target date"].dt.strftime("%b %d, %Y")
view["Expected cash date"] = view["Expected cash date"].dt.strftime("%b %d, %Y")
view["Amount"] = view["Amount"].map(lambda v: f"${v:,.0f}")
st.dataframe(view, hide_index=True, use_container_width=True)
