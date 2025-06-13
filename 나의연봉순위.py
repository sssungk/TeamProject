import streamlit as st
import pandas as pd
import numpy as np

# 스타일 설정
st.set_page_config(page_title="근로소득 분위 분석기", layout="centered")

# 국세청 통계 데이터 로드
@st.cache_data
def load_income_data():
    df = pd.read_csv("income_data.csv")  # 컬럼: income_bracket, avg_income, percentile_rank
    df = df.sort_values(by="percentile_rank", ascending=True).reset_index(drop=True)
    return df

df = load_income_data()
total_people = 1000000  # 가상의 전체 근로소득자 수 (실제 통계가 있다면 그 수를 반영)

# 입력
st.title("📊 근로소득 분위 분석기")

with st.sidebar:
    st.header("입력하기 ✍️")
    st.markdown("당신의 연간 **근로소득금액**을 입력해 주세요 (단위: 만원).")
    
    income_input = st.text_input(
        "근로소득금액",
        value="",
        help="근로소득공제 등을 마친 후의 금액을 입력해 주세요 (단위: 만원)"
    )
    
    user_income = None
    if income_input.strip().isdigit():
        user_income = int(income_input.strip())

# 분석
if user_income is not None:
    # 사용자 소득이 속한 분위 추정
    user_percentile_estimate = np.interp(user_income, df["avg_income"], df["percentile_rank"])
    user_percentile_estimate = round(user_percentile_estimate, 1)

    # 상위 퍼센트 계산
    upper_percent = 100 - user_percentile_estimate

    # 인근 분위 구간 찾기
    lower_bound_row = df[df["avg_income"] <= user_income].iloc[-1]
    upper_bound_row = df[df["avg_income"] > user_income].iloc[0]

    lower_rank = 100 - lower_bound_row['percentile_rank']
    upper_rank = 100 - upper_bound_row['percentile_rank']

    st.success(
        f"🔍 귀하의 연간 근로소득은 통계적으로 **상위 {int(lower_rank)}% ~ {int(upper_rank)}% 구간**에 해당하며, "
        f"이는 전체 근로소득자 중 상위 20% 이내에 해당하는 수준입니다."
    )

    st.write(
        f"• 귀하의 소득은 근로소득자 {total_people:,}명 중 약 "
        f"**{int(total_people * user_percentile_estimate / 100):,}명보다 많습니다.**"
    )

    st.write(
        f"• 이는 전체 근로소득 분포에서 **천분위(P{int(user_percentile_estimate)})** 수준에 해당합니다."
    )

    st.caption(
        "※ 본 분석은 단순 평균 기준이며, 세부적인 소득 항목이나 세전/세후 여부에 따라 해석이 달라질 수 있습니다."
    )

else:
    st.info("좌측 입력창에 연간 근로소득금액(만원 단위)을 숫자로 입력해 주세요.")
