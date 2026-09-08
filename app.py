import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Portfolio Rebalance", layout="wide", page_icon="📈"
)

# แต่งสไตล์ CSS ให้เหมือนแอปมือถือ
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
    }
    div.stButton > button:first-child {
        background-color: #00D26A;
        color: #0E1117;
        font-weight: bold;
        border-radius: 12px;
        height: 50px;
        font-size: 18px;
        border: none;
        box-shadow: 0px 4px 10px rgba(0, 210, 106, 0.3);
    }
    div.stButton > button:first-child:hover {
        background-color: #00FF80;
        color: #0E1117;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("🤖 แอป Rebalance พอร์ตส่วนตัว (พร้อมชาร์ทวิเคราะห์)")

# 1. ข้อมูลตั้งต้นพร้อมหมวดหมู่ (Category)
default_data = [
    {"Category": "PHYSICAL", "Ticker": "PHYS", "Shares": 590, "Target %": 24.0, "Lock": False},
    {"Category": "PHYSICAL", "Ticker": "PSLV", "Shares": 557, "Target %": 16.0, "Lock": False},
    {"Category": "MINERS", "Ticker": "AGI", "Shares": 326, "Target %": 12.0, "Lock": False},
    {"Category": "MINERS", "Ticker": "AEM", "Shares": 0, "Target %": 9.0, "Lock": False},
    {"Category": "MINERS", "Ticker": "GDX", "Shares": 0, "Target %": 9.0, "Lock": False},
    {"Category": "ROYALTY", "Ticker": "FNV", "Shares": 0, "Target %": 8.0, "Lock": False},
    {"Category": "ROYALTY", "Ticker": "WPM", "Shares": 0, "Target %": 7.0, "Lock": False},
    {"Category": "ROYALTY", "Ticker": "RGLD", "Shares": 0, "Target %": 5.0, "Lock": False},
    {"Category": "CRYPTO", "Ticker": "COIN", "Shares": 35, "Target %": 10.0, "Lock": True},
    {"Category": "OTHERS", "Ticker": "BKR", "Shares": 15, "Target %": 0.0, "Lock": False},
    {"Category": "OTHERS", "Ticker": "SQM", "Shares": 12, "Target %": 0.0, "Lock": False},
    {"Category": "OTHERS", "Ticker": "NPKI", "Shares": 32, "Target %": 0.0, "Lock": False},
]

st.sidebar.header("⚙️ ตั้งค่าเงินสด")
cash_input = st.sidebar.number_input("เงินสดคงเหลือ ($)", value=0.0, step=100.0)

st.subheader("📌 Portfolio ")
df_input = pd.DataFrame(default_data)

edited_df = st.data_editor(
    df_input,
    num_rows="dynamic",
    column_config={
        "Category": st.column_config.TextColumn("หมวดหมู่ (Category)", required=True),
        "Ticker": st.column_config.TextColumn("ชื่อหุ้น (Ticker)", required=True),
        "Shares": st.column_config.NumberColumn("จำนวนหุ้น", min_value=0),
        "Target %": st.column_config.NumberColumn("Target %", min_value=0.0),
        "Lock": st.column_config.CheckboxColumn("🔒 Lock (ไม่ขาย)", default=False),
    },
    use_container_width=True,
)

# กดปุ่มเพื่อคำนวณ
if st.button("🔄 ดึงราคา Real-time & คำนวณ Rebalance", type="primary"):
    with st.spinner("กำลังดึงราคาล่าสุดจาก Yahoo Finance..."):
        edited_df["Ticker"] = edited_df["Ticker"].str.strip().str.upper()
        tickers = edited_df["Ticker"].unique().tolist()
        tickers_to_fetch = tickers + ["THB=X"]

        prices = {}
        
        # วนดึงทีละตัว ป้องกันปัญหา DataFrame ตีกัน
        for t in tickers_to_fetch:
            try:
                ticker_obj = yf.Ticker(t)
                hist = ticker_obj.history(period="1d")
                if not hist.empty and "Close" in hist.columns:
                    val = hist["Close"].iloc[-1]
                    prices[t] = float(val) if pd.notna(val) else 0.0
                else:
                    prices[t] = 0.0
            except Exception:
                prices[t] = 0.0

        # ดึงเรทเงินบาท
        raw_rate = prices.get("THB=X", 34.5)
        usd_thb = float(raw_rate) if (pd.notna(raw_rate) and raw_rate > 0) else 34.5

        total_val = cash_input
        temp_data = []

        for _, row in edited_df.iterrows():
            cat = row["Category"]
            t = row["Ticker"]
            s = row["Shares"]
            tgt = row["Target %"]
            lock = row["Lock"]

            p = float(prices.get(t, 0.0))
            curr_v = s * p
            total_val += curr_v

            temp_data.append({
                "Category": cat,
                "Ticker": t,
                "Price": p,
                "Shares": s,
                "Target_Pct": tgt,
                "Curr_Val": curr_v,
                "Lock": lock,
            })

        results = []
        cat_summary = {}

        for item in temp_data:
            curr_pct = (item["Curr_Val"] / total_val * 100.0) if total_val > 0 else 0
            target_val = total_val * (item["Target_Pct"] / 100.0)

            if item["Lock"]:
                diff_s = 0
                action = "HOLD (0)"
            else:
                target_shares = round(target_val / item["Price"]) if item["Price"] > 0 else 0
                diff_s = target_shares - item["Shares"]
                if diff_s > 0:
                    action = f"BUY +{diff_s}"
                elif diff_s < 0:
                    action = f"SELL {diff_s}"
                else:
                    action = "HOLD (0)"

            diff_v = abs(diff_s * item["Price"])

            results.append({
                "Category": item["Category"],
                "Ticker": item["Ticker"],
                "Price ($)": f"${item['Price']:,.2f}",
                "Shares": item["Shares"],
                "Current Val ($)": f"${item['Curr_Val']:,.2f}",
                "Current_Pct_Num": curr_pct,
                "Current %": f"{curr_pct:.1f}%",
                "Target_Pct_Num": item["Target_Pct"],
                "Target %": f"{item['Target_Pct']:.1f}%",
                "Action": action,
                "Est Amount ($)": f"${diff_v:,.2f}",
            })

            cat = item["Category"]
            if cat not in cat_summary:
                cat_summary[cat] = {"Curr_Val": 0.0, "Target_Pct": 0.0}
            cat_summary[cat]["Curr_Val"] += item["Curr_Val"]
            cat_summary[cat]["Target_Pct"] += item["Target_Pct"]

        # บันทึกข้อมูลลง session_state
        st.session_state["df_res"] = pd.DataFrame(results)
        st.session_state["cat_summary"] = cat_summary
        st.session_state["total_val"] = total_val
        st.session_state["usd_thb"] = usd_thb
        st.session_state["cash_input"] = cash_input

# แสดงผลถ้ามีข้อมูลใน session_state แล้ว
if "df_res" in st.session_state:
    df_res = st.session_state["df_res"]
    cat_summary = st.session_state["cat_summary"]
    total_val = st.session_state["total_val"]
    usd_thb = st.session_state["usd_thb"]
    cash_in = st.session_state["cash_input"]

    st.divider()
    total_val_thb = total_val * usd_thb
    cash_thb = cash_in * usd_thb

    m1, m2, m3 = st.columns(3)
    m1.metric("💰 มูลค่าพอร์ตรวม", f"${total_val:,.2f}", f"≈ ฿{total_val_thb:,.0f} THB")
    m2.metric("💵 เงินสดในพอร์ต", f"${cash_in:,.2f}", f"≈ ฿{cash_thb:,.0f} THB")
    m3.metric("💱 อัตราแลกเปลี่ยน", f"฿{usd_thb:.2f} / $", f"สินทรัพย์ {len(df_res)} ตัว")

    st.subheader("📊 เปรียบเทียบสัดส่วนพอร์ต (Current vs Target)")
    tab1, tab2 = st.tabs(["สัดส่วนรายกลุ่ม (Category)", "สัดส่วนรายหุ้น (Tickers)"])

    with tab1:
        col1, col2 = st.columns(2)
        cat_rows = []
        for cat_name, c_data in cat_summary.items():
            c_pct = (c_data["Curr_Val"] / total_val * 100.0) if total_val > 0 else 0
            cat_rows.append({
                "Category": cat_name,
                "Current Val ($)": round(c_data["Curr_Val"], 2),
                "Current_Pct": c_pct,
                "Target_Pct": c_data["Target_Pct"],
            })
        df_cat = pd.DataFrame(cat_rows)

        with col1:
            fig_cat_curr = px.pie(
                df_cat, values="Current_Pct", names="Category",
                title="สัดส่วนปัจจุบัน (Current Category %)", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_cat_curr.update_traces(hovertemplate="<b>%{label}</b><br>สัดส่วนปัจจุบัน: %{value:.2f}%<extra></extra>")
            st.plotly_chart(fig_cat_curr, use_container_width=True)

        with col2:
            fig_cat_tgt = px.pie(
                df_cat, values="Target_Pct", names="Category",
                title="สัดส่วนเป้าหมาย (Target Category %)", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_cat_tgt.update_traces(hovertemplate="<b>%{label}</b><br>สัดส่วนเป้าหมาย: %{value:.2f}%<extra></extra>")
            st.plotly_chart(fig_cat_tgt, use_container_width=True)

    with tab2:
        col3, col4 = st.columns(2)
        with col3:
            fig_tk_curr = px.pie(
                df_res[df_res["Current_Pct_Num"] > 0], values="Current_Pct_Num", names="Ticker",
                title="สัดส่วนหุ้นปัจจุบัน (Current Tickers %)", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_tk_curr.update_traces(hovertemplate="<b>%{label}</b><br>สัดส่วนปัจจุบัน: %{value:.2f}%<extra></extra>")
            st.plotly_chart(fig_tk_curr, use_container_width=True)

        with col4:
            fig_tk_tgt = px.pie(
                df_res[df_res["Target_Pct_Num"] > 0], values="Target_Pct_Num", names="Ticker",
                title="สัดส่วนหุ้นเป้าหมาย (Target Tickers %)", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_tk_tgt.update_traces(hovertemplate="<b>%{label}</b><br>สัดส่วนเป้าหมาย: %{value:.2f}%<extra></extra>")
            st.plotly_chart(fig_tk_tgt, use_container_width=True)

    def highlight_action(val):
        if 'BUY' in str(val):
            return 'background-color: #0d3b24; color: #34d399; font-weight: bold;'
        elif 'SELL' in str(val):
            return 'background-color: #4c1d1d; color: #f87171; font-weight: bold;'
        return ''

    st.subheader("📋 แผนการ Rebalance รายหุ้น")
    st.dataframe(
        df_res.drop(columns=["Current_Pct_Num", "Target_Pct_Num"]).style.map(highlight_action, subset=['Action']),
        use_container_width=True
    )
