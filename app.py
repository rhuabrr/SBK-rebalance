import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Portfolio Rebalance", layout="wide")

st.title("🤖 แอป Rebalance พอร์ตส่วนตัว (Real-time)")

# ข้อมูลตั้งต้น
default_data = [
    {"Ticker": "PHYS", "Shares": 590, "Target %": 24.0, "Lock": False},
    {"Ticker": "PSLV", "Shares": 557, "Target %": 16.0, "Lock": False},
    {"Ticker": "AGI", "Shares": 326, "Target %": 12.0, "Lock": False},
    {"Ticker": "AEM", "Shares": 0, "Target %": 9.0, "Lock": False},
    {"Ticker": "GDX", "Shares": 0, "Target %": 9.0, "Lock": False},
    {"Ticker": "FNV", "Shares": 0, "Target %": 8.0, "Lock": False},
    {"Ticker": "WPM", "Shares": 0, "Target %": 7.0, "Lock": False},
    {"Ticker": "RGLD", "Shares": 0, "Target %": 5.0, "Lock": False},
    {"Ticker": "COIN", "Shares": 35, "Target %": 10.0, "Lock": True},
    {"Ticker": "BKR", "Shares": 15, "Target %": 0.0, "Lock": False},
    {"Ticker": "SQM", "Shares": 12, "Target %": 0.0, "Lock": False},
    {"Ticker": "NPKI", "Shares": 32, "Target %": 0.0, "Lock": False},
]

st.sidebar.header("⚙️ การตั้งค่าพอร์ต")
cash_input = st.sidebar.number_input("เงินสดคงเหลือ ($)", value=0.0, step=100.0)

# แสดงตารางให้ผู้ใช้แก้ไขจำนวนหุ้นและ Target % ได้จากหน้าเว็บ
st.subheader("📌 แก้ไขจำนวนหุ้น & Target % ได้ตรงนี้")
df_input = pd.DataFrame(default_data)
edited_df = st.data_editor(
    df_input,
    num_rows="dynamic",
    column_config={
        "Lock": st.column_config.CheckboxColumn("🔒 Lock (ไม่ขาย)", default=False)
    },
    use_container_width=True,
)

if st.button("🔄 ดึงราคา Real-time & คำนวณ Rebalance", type="primary"):
    with st.spinner("กำลังดึงราคาล่าสุดจาก Yahoo Finance..."):
        tickers = edited_df["Ticker"].tolist()
        try:
            prices = yf.download(tickers, period="1d")["Close"].iloc[-1]
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการดึงราคา: {e}")
            st.stop()

        total_val = cash_input
        temp_data = []

        for _, row in edited_df.iterrows():
            t = row["Ticker"]
            s = row["Shares"]
            tgt = row["Target %"]
            lock = row["Lock"]
            p = float(prices[t])
            curr_v = s * p
            total_val += curr_v

            temp_data.append(
                {
                    "Ticker": t,
                    "Price": p,
                    "Shares": s,
                    "Target_Pct": tgt,
                    "Curr_Val": curr_v,
                    "Lock": lock,
                }
            )

        results = []
        for item in temp_data:
            curr_pct = (item["Curr_Val"] / total_val * 100.0) if total_val > 0 else 0
            target_val = total_val * (item["Target_Pct"] / 100.0)

            if item["Lock"]:
                diff_s = 0
                action = "HOLD (0)"
            else:
                target_shares = round(target_val / item["Price"])
                diff_s = target_shares - item["Shares"]
                if diff_s > 0:
                    action = f"BUY +{diff_s}"
                elif diff_s < 0:
                    action = f"SELL {diff_s}"
                else:
                    action = "HOLD (0)"

            diff_v = abs(diff_s * item["Price"])

            results.append(
                {
                    "Ticker": item["Ticker"],
                    "Price ($)": round(item["Price"], 2),
                    "Shares": item["Shares"],
                    "Current Val ($)": round(item["Curr_Val"], 2),
                    "Current %": f"{curr_pct:.1f}%",
                    "Target %": f"{item['Target_Pct']:.1f}%",
                    "Action": action,
                    "Est Amount ($)": round(diff_v, 2),
                }
            )

        st.divider()
        st.metric("💰 มูลค่าพอร์ตรวมทั้งหมด", f"${total_val:,.2f}")
        st.subheader("📊 ผลลัพธ์แผน Rebalance")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
