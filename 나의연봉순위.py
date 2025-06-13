import streamlit as st
import pandas as pd
import re
import numpy as np  # For numerical operations, especially interpolation
import plotly.graph_objects as go  # Plotly Graph Objects for more control
from scipy import stats  # For Kernel Density Estimation (KDE)

# Streamlit page configuration: sets browser tab title and icon.
st.set_page_config(
    page_title="나의 근로소득 순위 분석",
    page_icon="📊",
    layout="centered"  # Set page layout to centered (can choose 'centered' or 'wide')
)

# Function to load and preprocess data
@st.cache_data
def load_data():
    # Load CSV file with cp949 encoding.
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna()  # Remove rows with missing values.

    # Convert necessary columns to float type.
    df["인원"] = df["인원"].astype(float)
    df["근로소득금액"] = df["근로소득금액"].astype(float)

    # Calculate 'income per person' by dividing 'income amount (billion KRW)' by 'number of people'.
    # Handle ZeroDivisionError if 'number of people' is 0.
    df['근로소득금액_1인당_억원'] = df.apply(
        lambda row: row['근로소득금액'] / row['인원'] if row['인원'] > 0 else 0,
        axis=1
    )
    # Convert 'income per person' from 'billion KRW' to 'ten thousand KRW'. (1 billion KRW = 10,000 ten thousand KRW)
    df['근로소득금액_1인당_만원'] = df['근로소득금액_1인당_억원'] * 1e4

    # Function to get percentile rank (0-100 scale) for sorting and comparison.
    # 0 represents the lowest income, 100 represents the highest income percentile.
    def get_percentile_rank(s):
        match = re.search(r'(\d+\.?\d*)', s)  # Extract numerical part from string
        if match:
            value = float(match.group(1))
            if '상위' in s:
                # 'Top 1%' means 99th percentile (higher than 99% of total)
                # 'Top 100%' means 0th percentile (lowest income)
                return 100 - value
            elif '하위' in s:
                # 'Bottom 5%' means 5th percentile
                return value
            else:
                # For "100분위" (based on thousand-percentile data), it means 100/1000 = 10th percentile
                # e.g., '100분위' means income at the 10% mark.
                return value / 1000 * 100
        return -1  # Return -1 if no valid number (should not happen with valid data)

    df['percentile_rank'] = df['구분'].apply(get_percentile_rank)

    # Sort DataFrame by 'income per person (ten thousand KRW)' in ascending order,
    # then by 'percentile_rank' in ascending order for ties.
    # (Ascending income = from lower percentile to higher percentile)
    df_sorted = df.sort_values(
        by=["근로소득금액_1인당_만원", 'percentile_rank'],
        ascending=True
    ).reset_index(drop=True)

    return df_sorted


# Call data loading function to load the data.
df = load_data()

# --- App UI Start ---

# Main title and description
st.title("📊 나의 근로소득 순위는?")
st.markdown("국세청 [근로소득 백분위(천분위)] 통계 기준이며, **1인당 근로소득금액**을 기준으로 순위를 계산합니다.")
st.markdown("---")  # Visual separator

# User input: moved to sidebar
with st.sidebar:
    st.header("입력하기 ✍️")
    st.markdown("당신의 연간 **근로소득금액**을 입력해 주세요.")
user_income_str = st.text_input(
    "근로소득금액 (만원)",
    value="",
    placeholder="예: 5000",
    help="세금 및 공제 전의 총 급여가 아닌, 근로소득공제 등을 마친 후의 근로소득금액을 입력하세요."
)

# 입력값이 숫자인지 확인
try:
    user_income = float(user_income_str.replace(",", ""))
except ValueError:
    user_income = 0  # 유효하지 않은 입력은 0으로 처리
    st.markdown("---")
    st.caption("본 앱은 국세청 공개 통계 자료를 바탕으로 만들어졌습니다.")

# Main content area
if user_income > 0:
    user_income_mw = user_income  # User input is already in 'ten thousand KRW' units.

    min_income_data = df["근로소득금액_1인당_만원"].min()
    max_income_data = df["근로소득금액_1인당_만원"].max()

    # Display results message
    st.subheader("⭐ 당신의 소득 순위 결과")

    # Emphasize user income using st.metric
    st.metric(label="✅ 당신의 근로소득금액", value=f"{user_income_mw:,.0f} 만원")

    # Handle cases outside the statistical range
    if user_income_mw < min_income_data:
        st.info(
            f"📉 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 낮은 구간인 "
            f"**{df['구분'].iloc[0]}** 의 1인당 근로소득금액({min_income_data:,.0f} 만원)보다도 낮습니다."
        )
        user_percentile_estimate = 0.0  # Estimated percentile for plotting
    elif user_income_mw > max_income_data:
        st.info(
            f"📈 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 높은 구간인 "
            f"**{df['구분'].iloc[-1]}** 의 1인당 근로소득금액({max_income_data:,.0f} 만원)보다도 높습니다. 당신은 통계상 최상위권에 속합니다!"
        )
        user_percentile_estimate = 100.0  # Estimated percentile for plotting
    else:
        # Handle cases within the statistical range
        # Find the row with the smallest 'income per person' greater than or equal to user's income (upper bound)
        upper_bound_indices = df[df["근로소득금액_1인당_만원"] >= user_income_mw].index
        upper_bound_row = df.loc[upper_bound_indices[0]]

        # Find the row with the largest 'income per person' less than user's income (lower bound)
        lower_bound_indices = df[df["근로소득금액_1인당_만원"] < user_income_mw].index

        if not lower_bound_indices.empty:
            lower_bound_row = df.loc[lower_bound_indices[-1]]

            st.success(
                f"🎉 국세청 통계 기준, 당신의 근로소득금액은 "
                f"**{lower_bound_row['구분']}** 의 1인당 근로소득금액과 **{upper_bound_row['구분']}** 의 1인당 근로소득금액 사이에 해당합니다!"
            )
            st.write(
                f"이는 당신이 적어도 **{lower_bound_row['구분']}** 에 해당하는 1인당 근로소득금액보다는 더 많은 수입을 올리고 있음을 의미합니다."
            )

            # Display income range metrics side-by-side using st.columns
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"⬇️ {lower_bound_row['구분']} (하한)", value=f"{lower_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")
            with col2:
                st.metric(label=f"⬆️ {upper_bound_row['구분']} (상한)", value=f"{upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")

            # Estimate user's percentile rank using linear interpolation
            income_values = df['근로소득금액_1인당_만원'].values
            percentile_ranks = df['percentile_rank'].values

            user_percentile_estimate = np.interp(user_income_mw, income_values, percentile_ranks)
            # Clip percentile estimate to be within 0-100 range
            user_percentile_estimate = max(0.0, min(100.0, user_percentile_estimate))

            st.write(
                f"당신은 통계적으로 약 :bold[상위 {100 - user_percentile_estimate:.1f}%] (또는 :bold[하위 {user_percentile_estimate:.1f}%])에 해당합니다."
            )

        else:
            # Case where user's income falls within the first percentile group or slightly above it
            st.warning("입력한 근로소득금액이 통계 데이터 범위 내 최하위 구간입니다.")
            user_percentile_estimate = 0.0

    # --- Plotting the KDE distribution chart ---
    # Extract income data for KDE
    income_data = df["근로소득금액_1인당_만원"].values

    # Calculate Kernel Density Estimate (KDE) using scipy.stats.gaussian_kde
    kde = stats.gaussian_kde(income_data)
    income_min = min(income_data)
    income_max = max(income_data)
    income_range = np.linspace(income_min, income_max, 500)
    kde_values = kde(income_range)

    # Plotly figure
    fig = go.Figure()

    # Add KDE curve line
    fig.add_trace(go.Scatter(
        x=income_range,
        y=kde_values,
        mode='lines',
        name='근로소득 KDE',
        line=dict(color='blue')
    ))

    # Add vertical line for user's income
    fig.add_vline(x=user_income_mw, line_dash="dash", line_color="red", annotation_text="내 소득", annotation_position="top right")

    # Set layout details
    fig.update_layout(
        title="근로소득금액 KDE 분포",
        xaxis_title="근로소득금액 (만원)",
        yaxis_title="밀도",
        template="plotly_white",
        height=450,
        width=700,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("연간 근로소득금액(만원)을 입력해 주세요.")

st.markdown("---")
st.caption("본 앱은 국세청 공개 통계 자료를 바탕으로 만들어졌습니다.")
