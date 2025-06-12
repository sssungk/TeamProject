import streamlit as st
import pandas as pd
import re

# Streamlit 페이지 설정: 브라우저 탭 제목과 아이콘을 설정합니다.
st.set_page_config(
    page_title="나의 근로소득 순위 분석",
    page_icon="📊",
    layout="centered" # 페이지 레이아웃을 중앙 정렬로 설정 (기본값은 'centered' 또는 'wide' 선택 가능)
)

# 데이터 불러오기 및 전처리 함수
@st.cache_data
def load_data():
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna()

    df["인원"] = df["인원"].astype(float)
    df["근로소득금액"] = df["근로소득금액"].astype(float)

    # 1인당 근로소득금액 계산 (억 원 -> 만원)
    df['근로소득금액_1인당_억원'] = df.apply(
        lambda row: row['근로소득금액'] / row['인원'] if row['인원'] > 0 else 0,
        axis=1
    )
    df['근로소득금액_1인당_만원'] = df['근로소득금액_1인당_억원'] * 1e4

    # '구분' 컬럼 정렬을 위한 임시 숫자 컬럼 생성
    def get_percentile_value(s):
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

    df['_sort_order'] = df['구분'].apply(get_percentile_value)

    # '1인당 근로소득금액_만원' 및 백분위 순서로 정렬
    df_sorted = df.sort_values(
        by=["근로소득금액_1인당_만원", '_sort_order'],
        ascending=True
    ).reset_index(drop=True)

    df_sorted = df_sorted.drop(columns=['_sort_order'])
    return df_sorted

# 데이터 로딩
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
        "근로소득금액 (만원)",
        min_value=0,
        value=0,
        step=100,
        help="세금 및 공제 전의 총 급여가 아닌, 근로소득공제 등을 마친 후의 근로소득금액을 입력하세요."
    )
    st.markdown("---")
    st.caption("본 앱은 국세청 공개 통계 자료를 바탕으로 만들어졌습니다.")

# 메인 콘텐츠 영역
if user_income > 0:
    user_income_mw = user_income

    min_income_data = df["근로소득금액_1인당_만원"].min()
    max_income_data = df["근로소득금액_1인당_만원"].max()

    # 결과 메시지 표시
    st.subheader("⭐ 당신의 소득 순위 결과")

    # st.metric을 사용하여 사용자 소득 강조
    st.metric(label="✅ 당신의 근로소득금액", value=f"{user_income_mw:,.0f} 만원")

    # 통계 범위 밖의 경우
    if user_income_mw < min_income_data:
        st.info(
            f"📉 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 낮은 구간인 "
            f"**{df['구분'].iloc[0]}** 의 1인당 근로소득금액({min_income_data:,.0f} 만원)보다도 낮습니다."
        )
    elif user_income_mw > max_income_data:
        st.info(
            f"📈 당신의 근로소득금액({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 높은 구간인 "
            f"**{df['구분'].iloc[-1]}** 의 1인당 근로소득금액({max_income_data:,.0f} 만원)보다도 높습니다. 당신은 통계상 최상위권에 속합니다!"
        )
    else:
        # 통계 범위 내의 경우
        upper_bound_indices = df[df["근로소득금액_1인당_만원"] >= user_income_mw].index
        upper_bound_row = df.loc[upper_bound_indices[0]]

        lower_bound_indices = df[df["근로소득금액_1인당_만원"] < user_income_mw].index
        
        if not lower_bound_indices.empty:
            lower_bound_row = df.loc[lower_bound_indices[-1]]
            
            st.success(
                f"🎉 국세청 통계 기준, 당신의 근로소득금액은 "
                f"**{lower_bound_row['구분']}** 의 소득과 **{upper_bound_row['구분']}** 의 소득 사이에 해당합니다!"
            )
            st.write(f"이는 당신이 적어도 **{lower_bound_row['구분']}** 에 해당하는 1인당 근로소득금액보다는 더 많은 수입을 올리고 있음을 의미합니다.")

            # 관련 소득 구간 정보st.columns로 배치
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"⬇️ {lower_bound_row['구분']} (하한)", value=f"{lower_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")
            with col2:
                st.metric(label=f"⬆️ {upper_bound_row['구분']} (상한)", value=f"{upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")
            
        else:
            # 사용자의 연봉이 통계 데이터의 첫 번째 구간에 속하거나 그보다 약간 높은 경우
            st.success(
                f"🎉 당신의 근로소득금액은 국세청 통계 기준 "
                f"**{upper_bound_row['구분']}** 의 1인당 근로소득금액({upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원)에 해당하거나 그보다 낮습니다."
            )
            st.metric(label=f"⬆️ {upper_bound_row['구분']} (상한)", value=f"{upper_bound_row['근로소득금액_1인당_만원']:,.0f} 만원")

# 사용자 입력이 0이거나 아직 입력하지 않은 경우 안내 메시지
else:
    st.info("👈 왼쪽 사이드바에 연간 근로소득금액을 입력하여 당신의 순위를 확인해 보세요! (예: 5000)")

st.markdown("---")

# 통계 데이터 미리보기: st.expander로 감싸 깔끔하게 정리
with st.expander("📊 통계 데이터 미리보기 (클릭하여 펼치기/접기)"):
    st.markdown("국세청에서 제공하는 원본 데이터의 일부입니다. '근로소득금액_1인당_만원' 컬럼을 참고하세요.")
    st.dataframe(df[['구분', '인원', '근로소득금액', '근로소득금액_1인당_만원']].head(20)) # 더 많은 행을 보여줄 수 있도록 head(20)으로 변경

st.markdown("---")
st.caption("© 2025 근로소득 순위 분석기. 데이터 출처: 국세청.")
