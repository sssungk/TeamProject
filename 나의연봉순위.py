import streamlit as st
import pandas as pd

# 데이터 로딩
@st.cache_data
def load_data():
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna()
    df["총급여"] = df["총급여"].astype(float) * 1e8  # 억 원 → 원
    return df

df = load_data()

st.title("나의 근로소득 순위는?")
st.write("국세청 근로소득 분위(천분위) 자료 기준")

# 사용자 연봉 입력
user_income = st.number_input("당신의 연간 총급여(연봉)를 입력하세요 (원)", min_value=0)

if user_income > 0:
    # 내림차순으로 정렬 (상위 순위부터)
    df_sorted = df.sort_values(by="총급여", ascending=False).reset_index(drop=True)
    
    # 몇 퍼센트인지 계산
    for idx, row in df_sorted.iterrows():
        if user_income >= row["총급여"]:
            st.success(f"🎉 당신은 **{row['구분']}** 에 해당합니다!")
            break
    else:
        st.info("입력하신 연봉은 통계 범위 밖에 있습니다.")
