import streamlit as st
import pandas as pd
import re
import numpy as np # For numerical operations, especially interpolation
import plotly.express as px # Plotly Express for easy plotting
import plotly.graph_objects as go # Plotly Graph Objects for more control (e.g., adding lines)

# Streamlit 페이지 설정: 브라우저 탭 제목과 아이콘을 설정합니다.
st.set_page_config(
    page_title="나의 근로소득 순위 분석",
    page_icon="�",
    layout="centered" # 페이지 레이아웃을 중앙 정렬로 설정 (기본값은 'centered' 또는 'wide' 선택 가능)
)

# 데이터 불러오기 및 전처리 함수
@st.cache_data
def load_data():
    # CSV 파일을 cp949 인코딩으로 불러옵니다.
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna() # 결측값이 있는 행은 제거합니다.

    # 필요한 컬럼들을 float 타입으로 변환합니다.
    df["인원"] = df["인원"].astype(float)
    df["근로소득금액"] = df["근로소득금액"].astype(float)

    # '근로소득금액(억 원)'을 '인원(명)'으로 나누어 '1인당 근로소득금액'을 계산합니다.
    # 인원이 0인 경우 발생할 수 있는 ZeroDivisionError를 방지하기 위해 처리합니다.
    df['근로소득금액_1인당_억원'] = df.apply(
        lambda row: row['근로소득금액'] / row['인원'] if row['인원'] > 0 else 0,
        axis=1
    )
    # '1인당 근로소득금액'을 사용자 입력 단위인 '만원'으로 변환합니다. (1억 원 = 10,000만원)
    df['근로소득금액_1인당_만원'] = df['근로소득금액_1인당_억원'] * 1e4

    # '구분' 컬럼을 정렬 및 백분위 변환을 위한 함수 (0-100 스케일)
    # 0은 최하위 소득, 100은 최상위 소득을 의미하는 백분위 랭크를 반환합니다.
    def get_percentile_rank(s):
        match = re.search(r'(\d+\.?\d*)', s) # 문자열에서 숫자 부분 추출
        if match:
            value = float(match.group(1))
            if '상위' in s:
                # '상위 1%'는 99th percentile (전체 중 99%보다 높다는 의미)
                # '상위 100%'는 0th percentile (가장 낮은 소득)
                return 100 - value
            elif '하위' in s:
                # '하위 5%'는 5th percentile
                return value
            else:
                # "100분위" (천분위 자료 기준)는 100/1000 = 10th percentile
                # 즉, '구분'이 '100분위'이면 100/1000 * 100 = 10% 지점의 소득을 의미합니다.
                return value / 1000 * 100
        return -1 # 유효한 값이 아닐 경우 -1 반환 (실제 데이터에서는 발생하지 않아야 함)

    df['percentile_rank'] = df['구분'].apply(get_percentile_rank)

    # '1인당 근로소득금액_만원'을 주 기준으로 오름차순 정렬하고,
    # 동일한 값 내에서는 'percentile_rank'를 기준으로 오름차순 정렬합니다.
    # (오름차순 소득 = 낮은 백분위부터 높은 백분위 순)
    df_sorted = df.sort_values(
        by=["근로소득금액_1인당_만원", 'percentile_rank'],
        ascending=True
    ).reset_index(drop=True)

    return df_sorted

# 데이터 로딩 함수를 호출하여 데이터를 불러옵니다.
df = load_data()

# --- 앱 UI 시작 ---

# 메인 제목 및 설명
st.title("📊 나의 근로소득 순위는?")
st.markdown("국세청 [근로소득 백분위(천분위)] 통계 기준이며, **1인당 근로소득금액**을 기준으로 순위를 계산합니다.")
st.markdown("---") # 시각적 구분선

# 사용자 입력: 사이드바로 이동
with st.sidebar:
    st.header("입력하기 ✍️")
    st.markdown("당신의 연간 **근로소득금액**을 입력해 주세요.")
    user_income = st.number_input(
        "근로소득금액 (만원)", # 입력 필드 레이블
        min_value=0, # 최소값 0
        value=0, # 초기값 0
        step=100, # 100만원 단위로 조절 가능
        help="세금 및 공제 전의 총 급여가 아닌, 근로소득공제 등을 마친 후의 근로소득금액을 입력하세요."
    )
    st.markdown("---")
    st.caption("본 앱은 국세청 공개 통계 자료를 바탕으로 만들어졌습니다.")

# 메인 콘텐츠 영역
if user_income > 0:
    user_income_mw = user_income # 사용자 입력값은 이미 만원 단위입니다.

    min_income_data = df["근로소득금액_1인당_만원"].min()
    max_income_data = df["근로소득금액_1인당_만원"].max()

    # 결과 메시지 표시
    st.subheader("⭐ 당신의 소득 순위 결과")

    # st.metric을 사용하여 사용자 소득을 시각적으로 강조
    st.metric(label="✅ 당신의 근로소득금액", value=f"{user_income_mw:,.0f} 만원")

    # 통계 범위 밖의 경우 처리
    if user_income_mw < min_income_data:
        st.info(
            f"📉 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 낮은 구간인 "
            f"**{df['구분'].iloc[0]}** 의 1인당 근로소득금액({min_income_data:,.0f} 만원)보다도 낮습니다."
        )
        user_percentile_estimate = 0.0 # 추정 백분위 0 (플로팅용)
    elif user_income_mw > max_income_data:
        st.info(
            f"📈 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 높은 구간인 "
            f"**{df['구분'].iloc[-1]}** 의 1인당 근로소득금액({max_income_data:,.0f} 만원)보다도 높습니다. 당신은 통계상 최상위권에 속합니다!"
        )
        user_percentile_estimate = 100.0 # 추정 백분위 100 (플로팅용)
    else:
        # 통계 범위 내의 경우 처리
        # 사용자의 소득보다 크거나 같은 '1인당 근로소득금액' 중 가장 작은 값을 가진 행 (상위 구간)
        upper_bound_indices = df[df["근로소득금액_1인당_만원"] >= user_income_mw].index
        upper_bound_row = df.loc[upper_bound_indices[0]]

        # 사용자의 소득보다 작은 '1인당 근로소득금액' 중 가장 큰 값을 가진 행 (하위 구간)
        lower_bound_indices = df[df["근로소득금액_1인당_만원"] < user_income_mw].index
        
        if not lower_bound_indices.empty:
            lower_bound_row = df.loc[lower_bound_indices[-1]]
            
            st.success(
                f"🎉 국세청 통계 기준, 당신의 근로소득금액은 "
                f"**{lower_bound_row['구분']}** 의 1인당 근로소득금액과 **{upper_bound_row['구분']}** 의 1인당 근로소득금액 사이에 해당합니다!"
            )
            st.write(f"이는 당신이 적어도 **{lower_bound_row['구분']}** 에 해당하는 1인당 근로소득금액보다는 더 많은 수입을 올리고 있음을 의미합니다.")

            # 관련 소득 구간 정보st.columns로 배치하여 시각적으로 정돈
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"⬇️ {lower_bound_row['구분']} (하한)", value=f"{lower_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")
            with col2:
                st.metric(label=f"⬆️ {upper_bound_row['구분']} (상한)", value=f"{upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")
            
            # 사용자 백분위 랭크 추정 (선형 보간 사용)
            income_values = df['근로소득금액_1인당_만원'].values
            percentile_ranks = df['percentile_rank'].values

            user_percentile_estimate = np.interp(user_income_mw, income_values, percentile_ranks)
            # 백분위 추정치를 0-100 범위로 클리핑
            user_percentile_estimate = max(0.0, min(100.0, user_percentile_estimate))

            st.write(f"당신은 통계적으로 약 **상위 {100 - user_percentile_estimate:.1f}%** (또는 **하위 {user_percentile_estimate:.1f}%**)에 해당합니다.")

        else:
            # 사용자의 연봉이 통계 데이터의 첫 번째 구간에 속하거나 그보다 약간 높은 경우
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
    
    # --- Plotly 그래프 그리기 설정 ---
    # KDE (커널 밀도 추정) 플롯으로 소득 분포의 부드러운 곡선을 그립니다.
    # Plotly Express의 density_kde를 사용하여 KDE 플롯을 생성합니다.
    fig = px.density_kde(df, x='근로소득금액_1인당_만원', color_discrete_sequence=['skyblue'])
    
    # 사용자의 근로소득금액 위치를 빨간색 점선으로 표시합니다.
    fig.add_vline(x=user_income_mw, line_dash="dot", line_color="red", line_width=2,
                  annotation_text=f"내 근로소득 ({user_income_mw:,.0f}만원)",
                  annotation_position="top right",
                  annotation_font_color="red")
    
    # 그래프 레이아웃 설정
    fig.update_layout(
        title={
            'text': '근로소득금액 분포 및 당신의 위치',
            'yanchor': 'top',
            'xanchor': 'center',
            'x': 0.5
        },
        xaxis_title='1인당 근로소득금액 (만원)',
        yaxis_title='밀도',
        hovermode="x unified" # 마우스 오버 시 정보 표시 방식 설정
    )

    # 사용자 위치에 백분위 텍스트 라벨 추가 (annotations 사용)
    # KDE 플롯의 y축 범위는 데이터에 따라 달라지므로, 동적으로 y 위치를 조정
    # Plotly는 Matplotlib처럼 ax.get_ylim()을 직접 제공하지 않으므로, 데이터의 밀도 최대치를 추정하여 Y위치 조정
    # 간단하게 그래프의 Y축 최대치의 일정 비율을 사용하거나, 더 정교하게는 KDE 데이터 자체를 활용할 수 있습니다.
    # 여기서는 대략적으로 그래프 높이의 80% 지점에 위치하도록 설정합니다.
    
    # 임시적인 KDE 데이터 계산 (Plotly는 내부적으로 계산하지만, 주석 위치를 위해 수동 계산 필요)
    # 실제로는 Plotly의 내부 KDE 계산 결과에 접근하는 것이 가장 정확하지만, 간단한 추정을 위해 다음과 같이 진행
    hist_data, edges = np.histogram(df['근로소득금액_1인당_만원'], bins=50, density=True)
    max_density = hist_data.max() if len(hist_data) > 0 else 0.01 # Max density for y-axis

    fig.add_annotation(
        x=user_income_mw,
        y=max_density * 0.9, # Y축 최대 밀도의 90% 지점에 위치
        text=f'당신은 약 상위 {100 - user_percentile_estimate:.1f}%',
        showarrow=False,
        font=dict(color="red"),
        bgcolor="white",
        opacity=0.7,
        borderpad=4,
        borderwidth=0,
        xanchor='left' # 텍스트가 시작되는 위치를 사용자 소득 선의 오른쪽으로 설정
    )
    
    st.plotly_chart(fig, use_container_width=True) # Streamlit에 Plotly 그래프 표시
    # --- Plotly 그래프 설정 끝 ---

# 사용자 입력이 0이거나 아직 입력하지 않은 경우 안내 메시지
else:
    st.info("👈 왼쪽 사이드바에 연간 근로소득금액을 입력하여 당신의 순위를 확인해 보세요! (예: 5000)")

st.markdown("---")

# 통계 데이터 상세 보기: st.expander로 감싸 깔끔하게 정리
with st.expander("📊 통계 데이터 상세 보기 (클릭하여 펼치기/접기)"):
    st.markdown("국세청에서 제공하는 1인당 근로소득금액의 백분위별 주요 통계 자료입니다.")

    # 5% 단위 요약 데이터프레임 생성
    # 상위 100%부터 (하위 0%에 해당)
    # 5% 단위 (하위 5%, 10%, ..., 95%)
    # 그리고 상위 1%, 0.5%, 0.1% (최상위권)를 포함하여 사용자 요구 충족
    
    # 목표 백분위 랭크 (0-100 스케일, 낮은 소득부터 높은 소득까지)
    target_ranks = [0.0, 0.1, 0.5, 1.0] + list(range(5, 100, 5)) + [99.0, 99.5, 99.9, 100.0]
    target_ranks = sorted(list(set(target_ranks))) # 중복 제거 및 정렬

    summary_rows = []
    seen_percentile_ranks = set() # 동일한 백분위 랭크를 가진 행의 중복 추가 방지

    for target_rank in target_ranks:
        # df에서 target_rank와 percentile_rank가 가장 가까운 행을 찾습니다.
        closest_row_idx = (df['percentile_rank'] - target_rank).abs().idxmin()
        row = df.loc[closest_row_idx].copy() # SettingWithCopyWarning 방지를 위해 copy() 사용

        # '구분' 컬럼을 'percentile_rank'에 따라 업데이트하여 더 직관적으로 만듭니다.
        # 예: percentile_rank 99.9 -> 상위 0.1%
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


        # 중복 방지 로직: 이미 추가된 백분위 랭크가 아니거나, 매우 특정적인 최저/최고 랭크인 경우에만 추가
        if row['percentile_rank'] not in seen_percentile_ranks or \
           target_rank in [0.0, 0.1, 99.9, 100.0]: # 특정 경계값은 항상 포함
            summary_rows.append(row)
            seen_percentile_ranks.add(row['percentile_rank'])
            
    # 요약 데이터프레임 생성 및 백분위 랭크 기준으로 정렬
    summary_df = pd.DataFrame(summary_rows).sort_values(by='percentile_rank', ascending=True)
    summary_df = summary_df.drop_duplicates(subset=['percentile_rank']) # 최종 중복 제거

    # 요약 데이터프레임 표시 (관련 컬럼만, 소수점 2자리로 반올림)
    st.dataframe(summary_df[['구분', '인원', '근로소득금액_1인당_만원', 'percentile_rank']].round(2),
                 height=300) # 높이 지정하여 스크롤 가능하게

    st.markdown("---")
    st.markdown("전체 통계 데이터 (정렬 기준: 1인당 근로소득금액):")
    # 전체 데이터프레임 표시 (관련 컬럼만, 소수점 2자리로 반올림)
    st.dataframe(df[['구분', '인원', '근로소득금액', '근로소득금액_1인당_만원', 'percentile_rank']].round(2))

st.markdown("---")
st.caption("© 2025 근로소득 순위 분석기. 데이터 출처: 국세청.")
�
