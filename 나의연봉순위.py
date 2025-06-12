import streamlit as st
import pandas as pd
import re # '구분' 컬럼에서 숫자 추출을 위해 정규표현식 모듈 추가

# 데이터 불러오기 및 전처리
# st.cache_data를 사용하여 데이터를 한 번만 로드하고 캐시하여 성능을 최적화합니다.
@st.cache_data
def load_data():
    # CSV 파일을 cp949 인코딩으로 불러옵니다.
    df = pd.read_csv("국세청_근로소득 백분위(천분위) 자료_20241231.csv", encoding='cp949')
    df = df.dropna() # 결측값이 있는 행은 제거합니다.

    # --- 변경된 부분 시작 ---
    # '총급여' 컬럼을 float 타입으로 변환합니다.
    # 사용자님의 피드백에 따라, 원본 CSV의 '총급여'가 이미 '만원' 단위라고 가정하여
    # 기존에 '억 원'을 '만원'으로 변환하던 '* 1e4' 부분을 제거했습니다.
    df["총급여"] = df["총급여"].astype(float)
    # --- 변경된 부분 끝 ---

    # '구분' 컬럼을 정렬하기 위한 임시 숫자 컬럼을 생성합니다.
    # '상위 1%'와 같은 문자열을 백분위 관점의 숫자로 변환하여 정확한 순서로 정렬되도록 합니다.
    # 예: "상위 1%"는 99.0, "하위 5%"는 5.0, "100분위"는 10.0으로 변환합니다.
    def get_percentile_value(s):
        # 문자열에서 숫자 부분(정수 또는 소수)을 추출합니다.
        match = re.search(r'(\d+\.?\d*)', s)
        if match:
            value = float(match.group(1))
            if '상위' in s:
                # '상위' 키워드가 있는 경우, 백분위 값을 100에서 뺀 값으로 변환합니다.
                # 예를 들어, '상위 1%'는 전체의 99%보다 더 많은 소득을 의미하므로 99.0으로 변환합니다.
                return 100 - value
            elif '하위' in s:
                # '하위' 키워드가 있는 경우, 해당 백분위 값을 그대로 사용합니다.
                # 예를 들어, '하위 5%'는 5.0으로 변환합니다.
                return value
            else:
                # '100분위', '1000분위' 등 숫자로만 구성된 '구분'을 처리합니다.
                # 파일 이름에 '천분위'가 언급되어 있으므로, 천분위를 백분위 기준으로 스케일링합니다.
                # (1000으로 나누고 100을 곱하여 백분율로 변환)
                return value / 1000 * 100
        return -1 # 유효한 숫자가 없는 경우 기본값 (-1) 반환

    # 임시 정렬 컬럼 '_sort_order'를 DataFrame에 추가합니다.
    df['_sort_order'] = df['구분'].apply(get_percentile_value)

    # '총급여'를 주 기준으로 오름차순 정렬하고,
    # 동일한 '총급여' 내에서는 '_sort_order' (백분위 값)를 기준으로 오름차순 정렬합니다.
    df_sorted = df.sort_values(by=["총급여", '_sort_order'], ascending=True).reset_index(drop=True)

    # 정렬에 사용한 임시 컬럼은 더 이상 필요 없으므로 제거합니다.
    df_sorted = df_sorted.drop(columns=['_sort_order'])
    return df_sorted

# 데이터 로딩 함수를 호출하여 데이터를 불러옵니다.
df = load_data()

# Streamlit 애플리케이션의 UI 제목을 설정합니다.
st.title("📊 나의 근로소득 순위는?")
# 통계 데이터의 출처와 데이터가 일부만 표시됨을 안내합니다.
st.write("국세청 [근로소득 백분위(천분위)] 통계 기준입니다. 통계 데이터는 일부만 표시됩니다.")
st.write("---") # 시각적인 구분선을 추가합니다.

# 사용자로부터 연간 총급여(연봉)를 만원 단위로 입력받습니다.
# min_value를 0으로 설정하고, value를 0으로 초기화, step을 100으로 설정하여 편리하게 입력 가능하도록 합니다.
user_income = st.number_input("당신의 연간 총급여(연봉)를 입력하세요 (만원)", min_value=0, value=0, step=100)

# 사용자 입력이 0보다 큰 경우에만 순위 계산 로직을 실행합니다.
if user_income > 0:
    user_income_mw = user_income # 사용자 입력값은 이미 만원 단위입니다.

    # 통계 데이터 내 최소 및 최대 '총급여' 값을 가져옵니다.
    min_income_data = df["총급여"].min()
    max_income_data = df["총급여"].max()

    # 사용자의 연봉이 통계 데이터의 최하위 소득보다 낮을 경우
    if user_income_mw < min_income_data:
        st.info(
            f"📉 당신의 연봉({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 낮은 소득 구간인 "
            f"**{df['구분'].iloc[0]}** 의 소득({min_income_data:,.0f} 만원)보다도 낮습니다."
        )
    # 사용자의 연봉이 통계 데이터의 최상위 소득보다 높을 경우
    elif user_income_mw > max_income_data:
        st.info(
            f"📈 당신의 연봉({user_income_mw:,.0f} 만원)은 통계 데이터 내 가장 높은 소득 구간인 "
            f"**{df['구분'].iloc[-1]}** 의 소득({max_income_data:,.0f} 만원)보다도 높습니다. 당신은 통계상 최상위권에 속합니다!"
        )
    else:
        # 사용자의 연봉이 통계 데이터 범위 내에 있을 경우
        # 1. 사용자의 소득보다 크거나 같은 '총급여' 중 가장 작은 값을 가진 행을 찾습니다. (상위 구간의 기준)
        # 이 행은 사용자의 소득이 포함되거나 그 이하인 백분위 그룹의 상한선을 나타냅니다.
        upper_bound_indices = df[df["총급여"] >= user_income_mw].index
        upper_bound_row = df.loc[upper_bound_indices[0]] # 가장 첫 번째(가장 가까운) 상위 구간 행을 가져옵니다.

        # 2. 사용자의 소득보다 작은 '총급여' 중 가장 큰 값을 가진 행을 찾습니다. (하위 구간의 기준)
        # 이 행은 사용자의 소득이 넘어서는 백분위 그룹의 하한선을 나타냅니다.
        lower_bound_indices = df[df["총급여"] < user_income_mw].index
        
        if not lower_bound_indices.empty:
            lower_bound_row = df.loc[lower_bound_indices[-1]] # 가장 마지막(가장 가까운) 하위 구간 행을 가져옵니다.
            st.success(
                f"🎉 당신의 연봉({user_income_mw:,.0f} 만원)은 국세청 통계 기준 "
                f"**{lower_bound_row['구분']}** 의 소득({lower_bound_row['총급여']:,.0f} 만원)과 "
                f"**{upper_bound_row['구분']}** 의 소득({upper_bound_row['총급여']:,.0f} 만원) 사이에 해당합니다."
            )
            st.write(f"이는 당신이 적어도 **{lower_bound_row['구분']}** 에 해당하는 소득자보다는 더 많은 수입을 올리고 있음을 의미합니다.")
        else:
            # 사용자의 연봉이 통계 데이터의 첫 번째 구간에 속하거나 그보다 약간 높은 경우
            # (즉, lower_bound_indices가 비어 있는 경우)
            st.success(
                f"🎉 당신의 연봉({user_income_mw:,.0f} 만원)은 국세청 통계 기준 "
                f"**{upper_bound_row['구분']}** 의 소득({upper_bound_row['총급여']:,.0f} 만원)에 해당하거나 그보다 낮습니다."
            )

# 사용자 입력이 0이거나 아직 입력하지 않은 경우 안내 메시지를 표시합니다.
else:
    st.info("연봉을 입력하면 당신의 순위를 확인할 수 있습니다. (예: 5000)")

st.write("---") # 시각적인 구분선을 추가합니다.
st.markdown("### 🔍 통계 데이터 미리보기")
# 데이터프레임의 상위 10개 행을 표시하여 사용자가 데이터 구조를 확인할 수 있도록 합니다.
st.dataframe(df.head(10))
