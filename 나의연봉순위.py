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
    df["인원"] = pd.to_numeric(df["인원"], errors='coerce')
    df["근로소득금액"] = pd.to_numeric(df["근로소득금액"], errors='coerce')
    df = df.dropna(subset=["인원", "근로소득금액"])
    df = df[(df["인원"] > 0) & (df["근로소득금액"] > 0)]
    
    df['근로소득금액_1인당_만원'] = df['근로소득금액'] / df['인원']

    def get_percentile_rank(s):
        match = re.search(r'(\d+\.?\d*)', s)
        if match:
            val = float(match.group(1))
            if '상위' in s:
                return 100 - val / 1000 * 100  # 천분위 기준일 경우
            elif '하위' in s:
                return val / 1000 * 100
            else:
                # 단순 퍼센트
                return val
        return np.nan

    df['percentile_rank'] = df['구분'].apply(get_percentile_rank)
    df = df.dropna(subset=['percentile_rank'])

    df = df.sort_values(by=["근로소득금액_1인당_만원", "percentile_rank"], ascending=True).reset_index(drop=True)
    return df

df = load_data()

st.title("📊 나의 근로소득 순위는?")
st.markdown("국세청 [근로소득 백분위(천분위)] 통계 기준이며, **1인당 근로소득금액**을 기준으로 순위를 계산합니다.")
st.markdown("---")

with st.sidebar:
    st.header("입력하기 ✍️")
    user_income = st.number_input(
        "근로소득금액 (만원)",
        min_value=0,
        value=None,
        step=100,
        help="세금 및 공제 전이 아닌, 근로소득금액(만원)을 입력하세요."
    )
    st.markdown("---")
    st.caption("본 앱은 국세청 공개 통계 자료를 바탕으로 만들어졌습니다.")

if user_income is not None and user_income > 0:
    st.subheader("⭐ 당신의 소득 순위 결과")

    st.metric(label="✅ 당신의 근로소득금액", value=f"{user_income:,.0f} 만원")

    if user_income < df["근로소득금액_1인당_만원"].min():
        st.info(f"📉 입력하신 근로소득금액({user_income:,.0f} 만원)은 통계 내 가장 낮은 구간보다 낮습니다.")
        user_percentile = 0
    elif user_income > df["근로소득금액_1인당_만원"].max():
        st.info(f"📈 입력하신 근로소득금액({user_income:,.0f} 만원)은 통계 내 가장 높은 구간보다 높습니다.")
        user_percentile = 100
    else:
        # 근로소득금액 기준 인접 구간 찾기
        upper_idx = df[df["근로소득금액_1인당_만원"] >= user_income].index[0]
        lower_idx = upper_idx - 1 if upper_idx > 0 else 0

        lower_row = df.loc[lower_idx]
        upper_row = df.loc[upper_idx]

        st.success(
            f"🎉 국세청 통계 기준, 당신의 근로소득금액은 "
            f"**{lower_row['구분']}** 의 1인당 근로소득금액과 "
            f"**{upper_row['구분']}** 의 1인당 근로소득금액 사이에 해당합니다!"
        )

        st.write(f"이는 당신이 **{lower_row['구분']}** 보다는 높고 **{upper_row['구분']}** 보다는 낮은 근로소득임을 의미합니다.")

        st.metric(label=f"⬇️ {lower_row['구분']}", value=f"{lower_row['근로소득금액_1인당_만원']:,.0f} 만원")
        st.metric(label=f"⬆️ {upper_row['구분']}", value=f"{upper_row['근로소득금액_1인당_만원']:,.0f} 만원")

        # 퍼센트 계산 (선형보간)
        user_percentile = np.interp(user_income,
                                    df["근로소득금액_1인당_만원"],
                                    df["percentile_rank"])

        user_percentile = max(0, min(100, user_percentile))
        st.write(f"당신은 통계적으로 약 **상위 {100 - user_percentile:.1f}%** (또는 **하위 {user_percentile:.1f}%**)에 해당합니다.")

    # 분포 그래프
    st.markdown("---")
    st.subheader("📊 근로소득금액 분포 그래프")

    x_data = df["근로소득금액_1인당_만원"].values
    weights = df["인원"].values

    kde = stats.gaussian_kde(x_data, weights=weights)

    x_vals_만원 = np.linspace(x_data.min(), x_data.max()*1.05, 500)
    y_density = kde(x_vals_만원)

    total_pop = weights.sum()
    y_population_만명 = y_density * total_pop / 1e4  # 만명 단위

    x_vals_억 = x_vals_만원 / 1e4
    user_income_억 = user_income / 1e4

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals_억,
        y=y_population_만명,
        mode='lines',
        name='근로소득 분포 (인구수 만명 단위)'
    ))

    fig.add_trace(go.Scatter(
        x=[user_income_억, user_income_억],
        y=[0, max(y_population_만명)*1.1],
        mode="lines",
        line=dict(color="red", dash="dash"),
        name="당신의 근로소득"
    ))

    fig.update_layout(
        xaxis_title="1인당 근로소득금액 (억원 단위)",
        yaxis_title="인구수 (만명 단위)",
        margin=dict(l=40, r=40, t=40, b=40),
        height=400,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("좌측 입력창에서 근로소득금액을 입력해주세요.")
