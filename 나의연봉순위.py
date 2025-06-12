import streamlit as st
import pandas as pd
import re
import numpy as np
import plotly.graph_objects as go
from scipy import stats

st.set_page_config(
    page_title="나의 근로소득 순위 분석",
    page_icon="📊",
    layout="centered"
)

@st.cache_data
def load_data():
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna()
    df["인원"] = df["인원"].astype(float)
    df["근로소득금액"] = df["근로소득금액"].astype(float)

    df['근로소득금액_1인당_억원'] = df.apply(
        lambda row: row['근로소득금액'] / row['인원'] if row['인원'] > 0 else 0,
        axis=1
    )

    df['근로소득금액_1인당_만원'] = df['근로소득금액_1인당_억원'] * 1e4

    def get_percentile_rank(s):
        match = re.search(r'(\d+\.?\d*)', s)
        if match:
            value = float(match.group(1))
            if '상위' in s:
                return 100 - value
            elif '하위' in s:
                return value
            else:
                return value / 1000 * 100
        return -1

    df['percentile_rank'] = df['구분'].apply(get_percentile_rank)

    df_sorted = df.sort_values(
        by=["근로소득금액_1인당_만원", 'percentile_rank'],
        ascending=True
    ).reset_index(drop=True)

    return df_sorted

df = load_data()

st.title("📊 나의 근로소득 순위는?")
st.markdown("국세청 [근로소득 백분위(천분위)] 통계 기준이며, **1인당 근로소득금액**을 기준으로 순위를 계산합니다.")
st.markdown("---")

with st.sidebar:
    st.header("입력하기 ✍️")
    st.markdown("당신의 연간 **근로소득금액**을 입력해 주세요.")
    user_income = st.number_input(
        "근로소득금액 (만원)",
        min_value=0,
        value=None,  # 초기값 None → 빈칸으로 표시됨
        step=100,
        help="세금 및 공제 전의 총 급여가 아닌, 근로소득공제 등을 마친 후의 근로소득금액을 입력하세요."
    )
    st.markdown("---")
    st.caption("본 앱은 국세청 공개 통계 자료를 바탕으로 만들어졌습니다.")

if user_income is not None and user_income > 0:
    user_income_mw = user_income

    min_income_data = df["근로소득금액_1인당_만원"].min()
    max_income_data = df["근로소득금액_1인당_만원"].max()

    st.subheader("⭐ 당신의 소득 순위 결과")
    st.metric(label="✅ 당신의 근로소득금액", value=f"{user_income_mw:,.0f} 만원")

    if user_income_mw < min_income_data:
        st.info(
            f"📉 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 낮은 구간인 "
            f"**{df['구분'].iloc[0]}** 의 1인당 근로소득금액({min_income_data:,.0f} 만원)보다도 낮습니다."
        )
        user_percentile_estimate = 0.0
    elif user_income_mw > max_income_data:
        st.info(
            f"📈 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 높은 구간인 "
            f"**{df['구분'].iloc[-1]}** 의 1인당 근로소득금액({max_income_data:,.0f} 만원)보다도 높습니다. 당신은 통계상 최상위권에 속합니다!"
        )
        user_percentile_estimate = 100.0
    else:
        upper_bound_indices = df[df["근로소득금액_1인당_만원"] >= user_income_mw].index
        upper_bound_row = df.loc[upper_bound_indices[0]]
        lower_bound_indices = df[df["근로소득금액_1인당_만원"] < user_income_mw].index

        if not lower_bound_indices.empty:
            lower_bound_row = df.loc[lower_bound_indices[-1]]

            # 문구 수정: 별표 없이 bold 처리만 (Streamlit markdown에서 **로 bold)
            st.success(
                f"🎉 국세청 통계 기준, 당신의 근로소득금액은 **{lower_bound_row['구분']}** 의 1인당 근로소득금액과 **{upper_bound_row['구분']}** 의 1인당 근로소득금액 사이에 해당합니다!"
            )
            st.write(f"이는 당신이 적어도 **{lower_bound_row['구분']}** 에 해당하는 1인당 근로소득금액보다는 더 많은 수입을 올리고 있음을 의미합니다.")

            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"⬇️ {lower_bound_row['구분']} (하한)", value=f"{lower_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")
            with col2:
                st.metric(label=f"⬆️ {upper_bound_row['구분']} (상한)", value=f"{upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")

            income_values = df['근로소득금액_1인당_만원'].values
            percentile_ranks = df['percentile_rank'].values

            user_percentile_estimate = np.interp(user_income_mw, income_values, percentile_ranks)
            user_percentile_estimate = max(0.0, min(100.0, user_percentile_estimate))

            st.write(f"당신은 통계적으로 약 **상위 {100 - user_percentile_estimate:.1f}%** (또는 **하위 {user_percentile_estimate:.1f}%**)에 해당합니다.")
        else:
            st.success(
                f"🎉 당신의 근로소득금액은 국세청 통계 기준 "
                f"**{upper_bound_row['구분']}** 의 1인당 근로소득금액({upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원)에 해당하거나 그보다 낮습니다."
            )
            st.metric(label=f"⬆️ {upper_bound_row['구분']} (상한)", value=f"{upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")
            user_percentile_estimate = np.interp(user_income_mw, df['근로소득금액_1인당_만원'].values, df['percentile_rank'].values)
            user_percentile_estimate = max(0.0, min(100.0, user_percentile_estimate))
            st.write(f"당신은 통계적으로 약 **상위 {100 - user_percentile_estimate:.1f}%** (또는 **하위 {user_percentile_estimate:.1f}%**)에 해당합니다.")

    st.markdown("---")
    st.subheader("📊 근로소득금액 분포 그래프")

    # KDE 그래프용 데이터, 1인당 근로소득금액 > 0
    data_for_kde = df['근로소득금액_1인당_만원'][df['근로소득금액_1인당_만원'] > 0].values
    population_for_kde = df['인원'][df['근로소득금액_1인당_만원'] > 0].values

    if len(data_for_kde) > 1:
        kde = stats.gaussian_kde(data_for_kde, weights=population_for_kde)  # 가중치: 인원수

        # 가로축: 억원 단위 (만원/1만 = 억원)
        min_income_억 = min_income_data / 1e4
        max_income_억 = max_income_data / 1e4 * 1.05

        x_kde_만원 = np.linspace(min_income_data, max_income_data * 1.05, 500)
        x_kde_억 = x_kde_만원 / 1e4

        y_kde_density = kde(x_kde_만원)

        # 세로축 밀도 → 인구수(만명 단위)
        # 인구수 = 밀도 * 총 인원 (근사)
        total_population = df['인원'].sum()
        y_kde_population = y_kde_density * total_population / 1e4  # 만명 단위

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x_kde_억
