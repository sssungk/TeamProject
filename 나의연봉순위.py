import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats

# 1. 사용자 입력 받기 (빈칸 기본값으로 설정)
income_input = st.text_input("근로소득금액 (만원)", value="", placeholder="예: 4500")

# 숫자 유효성 검사
try:
    income = int(income_input)
    valid_input = True
except:
    valid_input = False

# 샘플 데이터 생성 (예시용)
np.random.seed(0)
sample_data = np.random.normal(loc=5000, scale=2000, size=10000)
sample_data = sample_data[sample_data > 0]  # 음수 제거

# 커널 밀도 추정
kde = stats.gaussian_kde(sample_data)
x_vals = np.linspace(0, max(sample_data) * 1.1, 1000)
density = kde(x_vals)
population_density = density * len(sample_data) / 10000  # 인구수를 만명 단위로

# 소득 퍼센타일 계산
percentile = 100 - stats.percentileofscore(sample_data, income) if valid_input else None
percentile_floor = int(percentile)
percentile_ceil = int(percentile) - 1

# 2. 문구 출력 (굵은 텍스트로 표시)
if valid_input:
    st.markdown(
        f"🎉 국세청 통계 기준, 당신의 근로소득금액은 **상위 {percentile_floor}%** 의 1인당 근로소득금액과 "
        f"**상위 {percentile_ceil}%** 의 1인당 근로소득금액 사이에 해당합니다!"
    )

# 3. 그래프 출력 (세로축: 인구수 / 가로축: 억 단위 표기)
fig = go.Figure()

# 밀도 곡선 (인구수 단위)
fig.add_trace(go.Scatter(
    x=x_vals,
    y=population_density,
    mode="lines",
    name="근로소득 분포",
    fill="tozeroy"
))

# 사용자 입력 위치 표시
if valid_input:
    fig.add_trace(go.Scatter(
        x=[income],
        y=[kde(income) * len(sample_data) / 10000],
        mode="markers+text",
        name="당신의 위치",
        text=["나"],
        textposition="top center",
        marker=dict(size=10, color="red")
    ))

# 축 설정
fig.update_layout(
    title="근로소득금액 분포 (전국)",
    xaxis_title="1인당 근로소득 금액 (억원)",
    yaxis_title="인구수 (만 명)",
    xaxis=dict(
        tickmode="array",
        tickvals=[i for i in range(0, 20001, 2000)],
        ticktext=[f"{v//10000}억원" for v in range(0, 20001, 2000)],
    ),
    yaxis=dict(tickformat=".1f"),
)

st.plotly_chart(fig)
