import streamlit as st
import pandas as pd
import numpy as np

# 데이터 직접 포함
@st.cache_data
def load_income_data():
    data = {
        "income_bracket": [
            "1분위", "2분위", "3분위", "4분위", "5분위", 
            "6분위", "7분위", "8분위", "9분위", "10분위"
        ],
        "avg_income": [1200, 1600, 2000, 2500, 3000, 3600, 4500, 5500, 6700, 8000],
        "percentile_rank": [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
    }
    return pd.DataFrame(data)

# 수치 비교 및 포지션 분석
def interpret_income(user_income, df):
    percentiles = df["percentile_rank"]
    avg_incomes = df["avg_income"]

    idx = np.searchsorted(avg_incomes, user_income, side='right')
    if idx == 0:
        lower_pct = 0
        upper_pct = percentiles.iloc[0]
    elif idx == len(df):
        lower_pct = percentiles.iloc[-1]
        upper_pct = 100
    else:
        lower_pct = percentiles.iloc[idx - 1]
        upper_pct = percentiles.iloc[idx]

    lower_income = avg_incomes.iloc[idx - 1] if idx > 0 else 0
    upper_income = avg_incomes.iloc[idx] if idx < len(df) else user_income

    # 계량적 해석
    total_brackets = len(df)
    relative_position = (idx / total_brackets) * 100

    return lower_pct, upper_pct, lower_income, upper_income, relative_position

# --- UI 시작 ---
st.title("📊 나의 연봉 순위는?")

df = load_income_data()

# 입력창: 초기값 없이
income_input = st.text_input("연간 근로소득금액을 입력하세요 (단위: 만원)", value="", placeholder="예: 3200")

if income_input:
    try:
        user_income = float(income_input)
        lower_pct, upper_pct, lower_income, upper_income, relative_pos = interpret_income(user_income, df)

        st.success(f"🎉 국세청 통계 기준, 당신의 근로소득금액은 **상위 {lower_pct}%** 와 **상위 {upper_pct}%** 사이에 해당합니다!")

        st.markdown(
            f"""
            이는 당신이 적어도 **상위 {lower_pct}%** 수준의 1인당 근로소득자보다 더 높은 수입을 올리고 있음을 의미합니다.

            💡 **전문적 해석 예시**  
            - 귀하의 연간 근로소득은 **전국 근로소득자 중 상위 {100 - relative_pos:.1f}%** 수준에 위치합니다.  
            - 이는 통계적으로 약 **{relative_pos:.1f} 분위**에 해당하는 소득입니다.  
            - 비교 기준 범위: {lower_income:,}만원 ~ {upper_income:,}만원 구간
            """,
            unsafe_allow_html=True
        )

    except ValueError:
        st.error("숫자 형식으로 입력해 주세요. 예: 3200")
