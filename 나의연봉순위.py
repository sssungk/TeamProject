import streamlit as st
import pandas as pd

# 데이터 불러오기 및 전처리
@st.cache_data
def load_data():
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna()
    df["총급여"] = df["총급여"].astype(float) * 1e4  # 억 원 → 만 원
    return df

# 데이터 로딩
df = load_data()

# UI 제목
st.title("📊 나의 근로소득 순위는?")
st.write("국세청 [근로소득 백분위(천분위)] 통계 기준입니다.")

# 사용자 입력 (만원 단위)
user_income = st.number_input("당신의 연간 총급여(연봉)를 입력하세요 (만원)", min_value=0)

if user_income > 0:
    # 만원 단위로 변환
    user_income_mw = user_income * 1  # 입력값은 이미 만원 단위이므로 그대로 사용

    # 오름차순 정렬: 총급여 적은 순 → 많은 순 (하위 → 상위)
    df_sorted = df.sort_values(by="총급여", ascending=True).reset_index(drop=True)

    # 해당 분위 찾기
    for idx, row in df_sorted.iterrows():
        if user_income_mw <= row["총급여"]:
            st.success(f"🎉 당신은 **{row['구분']}** 에 해당합니다!")
            break
    else:
        st.info("입력하신 연봉은 통계 범위를 초과합니다.")
