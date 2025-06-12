import streamlit as st
import pandas as pd
import re
import numpy as np # For numerical operations, especially interpolation
import plotly.graph_objects as go # Plotly Graph Objects for more control
from scipy import stats # For Kernel Density Estimation (KDE)

# Streamlit page configuration: sets browser tab title and icon.
st.set_page_config(
    page_title="나의 근로소득 순위 분석",
    page_icon="📊",
    layout="centered" # Set page layout to centered (can choose 'centered' or 'wide')
)

# Function to load and preprocess data
@st.cache_data
def load_data():
    # Load CSV file with cp949 encoding.
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna() # Remove rows with missing values.

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
        match = re.search(r'(\d+\.?\d*)', s) # Extract numerical part from string
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
        return -1 # Return -1 if no valid number (should not happen with valid data)

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
st.markdown("---") # Visual separator

# User input: moved to sidebar
with st.sidebar:
    st.header("입력하기 ✍️")
    st.markdown("당신의 연간 **근로소득금액**을 입력해 주세요.")
    user_income = st.number_input(
        "근로소득금액 (만원)", # Input field label
        min_value=0, # Minimum value 0
        value=0, # Initial value 0
        step=100, # Step by 100 (ten thousand KRW)
        help="세금 및 공제 전의 총 급여가 아닌, 근로소득공제 등을 마친 후의 근로소득금액을 입력하세요."
    )
    st.markdown("---")
    st.caption("본 앱은 국세청 공개 통계 자료를 바탕으로 만들어졌습니다.")

# Main content area
if user_income > 0:
    user_income_mw = user_income # User input is already in 'ten thousand KRW' units.

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
        user_percentile_estimate = 0.0 # Estimated percentile for plotting
    elif user_income_mw > max_income_data:
        st.info(
            f"📈 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 높은 구간인 "
            f"**{df['구분'].iloc[-1]}** 의 1인당 근로소득금액({max_income_data:,.0f} 만원)보다도 높습니다. 당신은 통계상 최상위권에 속합니다!"
        )
        user_percentile_estimate = 100.0 # Estimated percentile for plotting
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
            st.write(f"이는 당신이 적어도 **{lower_bound_row['구분']}** 에 해당하는 1인당 근로소득금액보다는 더 많은 수입을 올리고 있음을 의미합니다.")

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

            st.write(f"당신은 통계적으로 약 **상위 {100 - user_percentile_estimate:.1f}%** (또는 **하위 {user_percentile_estimate:.1f}%**)에 해당합니다.")

        else:
            # Case where user's income falls within the first percentile group or slightly above it
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
    
    # --- Plotly Graph Objects for KDE Plot ---
    # Filter out zero incomes for KDE calculation to avoid skewing the distribution
    data_for_kde = df['근로소득금액_1인당_만원'][df['근로소득금액_1인당_만원'] > 0].values

    if len(data_for_kde) > 1: # KDE requires at least 2 data points
        # Calculate KDE
        kde = stats.gaussian_kde(data_for_kde)
        
        # Create x-values for the KDE curve (range from min to max income)
        x_kde = np.linspace(min_income_data, max_income_data * 1.05, 500) # Extend slightly beyond max income
        y_kde = kde(x_kde)

        # Create Plotly figure
        fig = go.Figure()

        # Add KDE trace (filled area)
        fig.add_trace(go.Scatter(
            x=x_kde,
            y=y_kde,
            mode='lines',
            fill='tozeroy', # Fills the area under the curve
            name='근로소득금액 분포 (KDE)',
            line=dict(color='skyblue', width=2)
        ))
        
        # Add a vertical line for user's income
        fig.add_vline(x=user_income_mw, line_dash="dot", line_color="red", line_width=2,
                      annotation_text=f"내 근로소득 ({user_income_mw:,.0f}만원)",
                      annotation_position="top right",
                      annotation_font_color="red")
        
        # Add annotation for user's percentile rank
        # Position annotation at the peak of the KDE curve's height for better visibility
        # Find the density value at user_income_mw for positioning
        user_density_at_x = kde(np.array([user_income_mw]))[0]

        fig.add_annotation(
            x=user_income_mw,
            y=user_density_at_x * 1.1, # Position slightly above the KDE curve at user's income
            text=f'당신은 약 상위 {100 - user_percentile_estimate:.1f}%',
            showarrow=True, # Show arrow pointing to the line
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor="red",
            ax=user_income_mw, # arrow's head x
            ay=user_density_at_x * 1.05, # arrow's head y
            font=dict(color="red"),
            bgcolor="white",
            opacity=0.7,
            borderpad=4,
            borderwidth=0,
            xanchor='left' # Text starts to the right of the line
        )

        # Update layout for title and axis labels
        fig.update_layout(
            title={
                'text': '근로소득금액 분포 및 당신의 위치',
                'yanchor': 'top',
                'xanchor': 'center',
                'x': 0.5
            },
            xaxis_title='1인당 근로소득금액 (만원)',
            yaxis_title='밀도',
            hovermode="x unified", # Display information on hover
            height=500 # Set a fixed height for the graph
        )
        
        st.plotly_chart(fig, use_container_width=True) # Display Plotly graph in Streamlit
    else:
        st.warning("데이터 포인트가 부족하여 근로소득 분포 그래프를 그릴 수 없습니다. (2개 이상의 유효한 소득 데이터 필요)")
    # --- Plotly Graph Objects for KDE Plot End ---

# If user input is 0 or not yet entered, display introductory message
else:
    st.info("👈 왼쪽 사이드바에 연간 근로소득금액을 입력하여 당신의 순위를 확인해 보세요! (예: 5000)")

st.markdown("---")

# Detailed statistical data view: wrapped in st.expander for cleanliness
with st.expander("📊 통계 데이터 상세 보기 (클릭하여 펼치기/접기)"):
    st.markdown("국세청에서 제공하는 1인당 근로소득금액의 백분위별 주요 통계 자료입니다.")

    # Generate summary DataFrame for key percentiles (e.g., 5% intervals)
    # Includes 0.1%, 0.5%, 1%, 5%, 10% ... 95%, 99%, 99.5%, 99.9%
    
    # Target percentile ranks (0-100 scale, from lowest to highest income)
    target_ranks = [0.0, 0.1, 0.5, 1.0] + list(range(5, 100, 5)) + [99.0, 99.5, 99.9, 100.0]
    target_ranks = sorted(list(set(target_ranks))) # Remove duplicates and sort

    summary_rows = []
    seen_percentile_ranks = set() # Prevent duplicate additions for rows with same percentile rank

    for target_rank in target_ranks:
        # Find the row in df closest to the target_rank
        closest_row_idx = (df['percentile_rank'] - target_rank).abs().idxmin()
        row = df.loc[closest_row_idx].copy() # Use copy() to prevent SettingWithCopyWarning

        # Update '구분' (category) column based on 'percentile_rank' for better clarity.
        if row['percentile_rank'] >= 99.9:
            row['구분'] = f"상위 {100 - row['percentile_rank']:.1f}%"
        elif row['percentile_rank'] >= 99:
             row['구분'] = f"상위 {100 - row['percentile_rank']:.0f}%"
        elif row['percentile_rank'] <= 0.1:
            row['구분'] = f"하위 {row['percentile_rank']:.1f}%"
        elif row['percentile_rank'] <= 1:
            row['구분'] = f"하위 {row['percentile_rank']:.0f}%"
        else:
            row['구분'] = f"하위 {row['percentile_rank']:.0f}% (약 {row['percentile_rank']:.0f}분위)"


        # Add row only if percentile rank not seen or if it's a specific boundary value
        if row['percentile_rank'] not in seen_percentile_ranks or \
           target_rank in [0.0, 0.1, 99.9, 100.0]: # Always include specific boundary values
            summary_rows.append(row)
            seen_percentile_ranks.add(row['percentile_rank'])
            
    # Create summary DataFrame and sort by percentile rank
    summary_df = pd.DataFrame(summary_rows).sort_values(by='percentile_rank', ascending=True)
    summary_df = summary_df.drop_duplicates(subset=['percentile_rank']) # Final duplicate removal

    # Display summary DataFrame (only relevant columns, rounded to 2 decimal places)
    st.dataframe(summary_df[['구분', '인원', '근로소득금액_1인당_만원', 'percentile_rank']].round(2),
                 height=300) # Set height to make it scrollable

    st.markdown("---")
    st.markdown("전체 통계 데이터 (정렬 기준: 1인당 근로소득금액):")
    # Display full DataFrame (relevant columns, rounded to 2 decimal places)
    st.dataframe(df[['구분', '인원', '근로소득금액', '근로소득금액_1인당_만원', 'percentile_rank']].round(2))

st.markdown("---")
st.caption("© 2025 근로소득 순위 분석기. 데이터 출처: 국세청.")
