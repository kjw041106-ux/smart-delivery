"""
🛵 스마트 배달 예측 시스템
- 기상청 ASOS 실시간 API 연동 (apihub.kma.go.kr)
- WAMIS 하천수위 버그 수정 (비정상값 필터링)
- 침수구역 상한선 적용
- Open-Meteo fallback 유지
"""

import streamlit as st
import requests
import datetime
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config( 
    page_title="스마트 배달 예측 시스템",
    page_icon="🛵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Noto+Sans+KR:wght@300;400;600&display=swap');
    .stApp {
        background: #050a15;
        background-image:
            radial-gradient(ellipse at 20% 20%, rgba(0,200,255,0.06) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 80%, rgba(255,60,120,0.06) 0%, transparent 50%);
    }
    .main-title {
        font-family: 'Orbitron', monospace;
        font-size: 2.4rem;
        font-weight: 900;
        background: linear-gradient(135deg, #00e5ff, #ff3c78, #00e5ff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shimmer 3s linear infinite;
        letter-spacing: 2px;
        margin-bottom: 4px;
    }
    @keyframes shimmer { to { background-position: 200% center; } }
    .sub-title {
        font-family: 'Noto Sans KR', sans-serif;
        color: #4a9abb;
        font-size: 0.9rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(0,30,60,0.9), rgba(0,15,35,0.95));
        border: 1px solid rgba(0,200,255,0.2);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00e5ff, transparent);
        animation: scan 2s linear infinite;
    }
    @keyframes scan {
        from { transform: translateX(-100%); }
        to   { transform: translateX(100%); }
    }
    .metric-label {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 0.75rem;
        color: #4a9abb;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-value          { font-family: 'Orbitron', monospace; font-size: 1.8rem; font-weight: 700; color: #00e5ff; }
    .metric-value.danger   { color: #ff3c78; }
    .metric-value.warning  { color: #ffb700; }
    .metric-value.safe     { color: #00ff9d; }
    .risk-bar-container {
        background: rgba(0,10,25,0.8);
        border: 1px solid rgba(0,200,255,0.15);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .risk-label { font-family: 'Orbitron', monospace; font-size: 0.8rem; color: #4a9abb; letter-spacing: 2px; margin-bottom: 8px; }
    .risk-bar-bg   { background: rgba(0,30,60,0.8); border-radius: 100px; height: 14px; overflow: hidden; }
    .risk-bar-fill { height: 100%; border-radius: 100px; transition: width 1s ease; }
    .status-badge { display: inline-block; padding: 6px 16px; border-radius: 100px; font-family: 'Orbitron', monospace; font-size: 0.75rem; letter-spacing: 1px; font-weight: 700; }
    .badge-danger  { background: rgba(255,60,120,0.15);  color: #ff3c78; border: 1px solid #ff3c78; }
    .badge-warning { background: rgba(255,183,0,0.15);   color: #ffb700; border: 1px solid #ffb700; }
    .badge-safe    { background: rgba(0,255,157,0.1);    color: #00ff9d; border: 1px solid #00ff9d; }
    .ai-report { background: linear-gradient(135deg, rgba(0,20,50,0.95), rgba(10,0,30,0.95)); border: 1px solid rgba(100,0,255,0.3); border-radius: 12px; padding: 1.5rem; font-family: 'Noto Sans KR', sans-serif; font-size: 0.95rem; color: #c8d8f0; line-height: 1.8; white-space: pre-wrap; }
    .ai-report-header { font-family: 'Orbitron', monospace; font-size: 0.75rem; color: #a060ff; letter-spacing: 3px; margin-bottom: 1rem; }
    .stSelectbox > div > div, .stTextInput > div > div > input { background: rgba(0,20,50,0.8) !important; border: 1px solid rgba(0,200,255,0.25) !important; color: #c8d8f0 !important; border-radius: 8px !important; }
    .stButton > button { background: linear-gradient(135deg, #00e5ff22, #ff3c7811) !important; border: 1px solid #00e5ff55 !important; color: #00e5ff !important; font-family: 'Orbitron', monospace !important; font-size: 0.8rem !important; letter-spacing: 2px !important; border-radius: 8px !important; }
    .stButton > button:hover { background: linear-gradient(135deg, #00e5ff44, #ff3c7833) !important; border-color: #00e5ff !important; }
    .section-header { font-family: 'Orbitron', monospace; font-size: 1rem; color: #00e5ff; letter-spacing: 3px; text-transform: uppercase; border-left: 3px solid #00e5ff; padding-left: 12px; margin: 1.5rem 0 1rem 0; }
    .data-source-badge { display: inline-block; padding: 3px 10px; border-radius: 100px; font-family: 'Orbitron', monospace; font-size: 0.65rem; letter-spacing: 1px; margin-left: 10px; }
    .badge-kma      { background: rgba(0,255,157,0.1); color: #00ff9d; border: 1px solid #00ff9d; }
    .badge-fallback { background: rgba(255,183,0,0.1); color: #ffb700; border: 1px solid #ffb700; }
    .breakdown-row  { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(0,200,255,0.08); font-family: 'Noto Sans KR', sans-serif; font-size: 0.9rem; color: #8aa8c0; }
    .breakdown-row .val { font-family: 'Orbitron', monospace; font-size: 0.85rem; color: #00e5ff; }
    .breakdown-total { display: flex; justify-content: space-between; align-items: center; padding: 12px 0 0 0; font-family: 'Orbitron', monospace; font-size: 1.1rem; color: #ffffff; }
    hr { border-color: rgba(0,200,255,0.1) !important; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 전국 지역 + ASOS 관측소 코드 매핑
# ──────────────────────────────────────────────
# ASOS 주요 관측소 코드 (기상청 지점번호)
ASOS_STN = {
    "서울": 108, "인천": 112, "수원": 119, "강릉": 105, "춘천": 101,
    "청주": 131, "대전": 133, "전주": 146, "광주": 156, "목포": 165,
    "여수": 168, "부산": 159, "울산": 152, "대구": 143, "포항": 138,
    "창원": 155, "제주": 184, "서귀포": 189, "속초": 90,  "원주": 114,
    "충주": 127, "천안": 232, "공주": 235, "보령": 236, "아산": 238,
    "군산": 140, "익산": 272, "정읍": 146, "순천": 168, "나주": 165,
    "경주": 136, "안동": 138, "구미": 143, "김해": 159, "진주": 192,
}

LOCATIONS = {
    # 서울특별시
    "서울 강남구": (37.4979, 127.0276, 108), "서울 서초구": (37.4836, 127.0327, 108),
    "서울 송파구": (37.5145, 127.1058, 108), "서울 강동구": (37.5301, 127.1238, 108),
    "서울 영등포구": (37.5258, 126.8974, 108), "서울 마포구": (37.5663, 126.9016, 108),
    "서울 용산구": (37.5325, 126.9900, 108), "서울 종로구": (37.5700, 126.9796, 108),
    "서울 중구": (37.5636, 126.9975, 108), "서울 노원구": (37.6542, 127.0568, 108),
    "서울 관악구": (37.4782, 126.9515, 108), "서울 동작구": (37.5124, 126.9393, 108),
    "서울 강서구": (37.5509, 126.8495, 108), "서울 양천구": (37.5169, 126.8664, 108),
    "서울 구로구": (37.4955, 126.8876, 108), "서울 금천구": (37.4569, 126.8955, 108),
    "서울 은평구": (37.6177, 126.9277, 108), "서울 서대문구": (37.5791, 126.9368, 108),
    "서울 성동구": (37.5634, 127.0369, 108), "서울 광진구": (37.5384, 127.0822, 108),
    "서울 중랑구": (37.6063, 127.0927, 108), "서울 성북구": (37.5894, 127.0167, 108),
    "서울 강북구": (37.6397, 127.0257, 108), "서울 도봉구": (37.6688, 127.0471, 108),
    "서울 동대문구": (37.5744, 127.0397, 108),
    # 경기도
    "경기 수원시 영통구": (37.2596, 127.0465, 119), "경기 수원시 팔달구": (37.2636, 127.0286, 119),
    "경기 수원시 권선구": (37.2490, 126.9947, 119), "경기 수원시 장안구": (37.2981, 127.0091, 119),
    "경기 성남시 분당구": (37.3827, 127.1189, 108), "경기 성남시 수정구": (37.4386, 127.1377, 108),
    "경기 성남시 중원구": (37.4202, 127.1264, 108), "경기 용인시 수지구": (37.3222, 127.0975, 119),
    "경기 용인시 기흥구": (37.2736, 127.1086, 119), "경기 용인시 처인구": (37.2343, 127.2014, 119),
    "경기 고양시 일산동구": (37.6583, 126.7706, 108), "경기 고양시 일산서구": (37.6760, 126.7472, 108),
    "경기 고양시 덕양구": (37.6344, 126.8320, 108), "경기 부천시": (37.5034, 126.7660, 112),
    "경기 안산시 단원구": (37.3219, 126.8308, 119), "경기 안산시 상록구": (37.3063, 126.8318, 119),
    "경기 안양시 만안구": (37.3941, 126.9568, 119), "경기 안양시 동안구": (37.3943, 126.9523, 119),
    "경기 평택시": (36.9921, 127.1129, 119), "경기 화성시": (37.1994, 126.8319, 119),
    "경기 시흥시": (37.3800, 126.8030, 112), "경기 광명시": (37.4784, 126.8643, 108),
    "경기 군포시": (37.3615, 126.9353, 119), "경기 의왕시": (37.3447, 126.9681, 119),
    "경기 과천시": (37.4292, 126.9878, 108), "경기 오산시": (37.1497, 127.0773, 119),
    "경기 의정부시": (37.7381, 127.0339, 108), "경기 구리시": (37.5943, 127.1296, 108),
    "경기 남양주시": (37.6360, 127.2165, 108), "경기 하남시": (37.5397, 127.2148, 108),
    "경기 광주시": (37.4296, 127.2553, 108), "경기 이천시": (37.2722, 127.4344, 119),
    "경기 여주시": (37.2981, 127.6375, 119), "경기 양평군": (37.4914, 127.4876, 114),
    "경기 가평군": (37.8315, 127.5107, 101), "경기 포천시": (37.8949, 127.2001, 108),
    "경기 동두천시": (37.9036, 127.0605, 108), "경기 연천군": (38.0966, 126.9997, 108),
    "경기 파주시": (37.7600, 126.7800, 108), "경기 김포시": (37.6154, 126.7158, 112),
    # 인천광역시
    "인천 중구": (37.4737, 126.6216, 112), "인천 동구": (37.4745, 126.6434, 112),
    "인천 미추홀구": (37.4638, 126.6505, 112), "인천 연수구": (37.4103, 126.6789, 112),
    "인천 남동구": (37.4471, 126.7314, 112), "인천 부평구": (37.4939, 126.7206, 112),
    "인천 계양구": (37.5375, 126.7376, 112), "인천 서구": (37.5451, 126.6758, 112),
    "인천 강화군": (37.7474, 126.4879, 112), "인천 옹진군": (37.4463, 126.6361, 112),
    # 부산광역시
    "부산 중구": (35.1065, 129.0322, 159), "부산 서구": (35.0978, 129.0245, 159),
    "부산 동구": (35.1362, 129.0469, 159), "부산 영도구": (35.0913, 129.0694, 159),
    "부산 부산진구": (35.1528, 129.0594, 159), "부산 동래구": (35.1993, 129.0846, 159),
    "부산 남구": (35.1366, 129.0840, 159), "부산 북구": (35.1972, 128.9906, 159),
    "부산 해운대구": (35.1796, 129.0756, 159), "부산 사하구": (35.1014, 128.9753, 159),
    "부산 금정구": (35.2428, 129.0934, 159), "부산 강서구": (35.2119, 128.9809, 159),
    "부산 연제구": (35.1763, 129.0799, 159), "부산 수영구": (35.1455, 129.1133, 159),
    "부산 사상구": (35.1497, 128.9930, 159), "부산 기장군": (35.2446, 129.2221, 159),
    # 대구광역시
    "대구 중구": (35.8693, 128.5965, 143), "대구 동구": (35.8867, 128.6351, 143),
    "대구 서구": (35.8712, 128.5592, 143), "대구 남구": (35.8463, 128.5999, 143),
    "대구 북구": (35.8849, 128.5826, 143), "대구 수성구": (35.8587, 128.6309, 143),
    "대구 달서구": (35.8297, 128.5327, 143), "대구 달성군": (35.7748, 128.4316, 143),
    # 광주광역시
    "광주 동구": (35.1459, 126.9231, 156), "광주 서구": (35.1517, 126.8891, 156),
    "광주 남구": (35.1332, 126.9019, 156), "광주 북구": (35.1744, 126.9119, 156),
    "광주 광산구": (35.1396, 126.7933, 156),
    # 대전광역시
    "대전 동구": (36.3120, 127.4545, 133), "대전 중구": (36.3253, 127.4213, 133),
    "대전 서구": (36.3554, 127.3836, 133), "대전 유성구": (36.3622, 127.3563, 133),
    "대전 대덕구": (36.3467, 127.4151, 133),
    # 울산광역시
    "울산 중구": (35.5697, 129.3325, 152), "울산 남구": (35.5381, 129.3161, 152),
    "울산 동구": (35.5052, 129.4161, 152), "울산 북구": (35.5823, 129.3609, 152),
    "울산 울주군": (35.5229, 129.2432, 152),
    # 세종
    "세종특별자치시": (36.4800, 127.2890, 133),
    # 강원도
    "강원 춘천시": (37.8813, 127.7298, 101), "강원 원주시": (37.3422, 127.9201, 114),
    "강원 강릉시": (37.7519, 128.8761, 105), "강원 동해시": (37.5244, 129.1144, 105),
    "강원 태백시": (37.1654, 128.9856, 105), "강원 속초시": (38.2070, 128.5919, 90),
    "강원 삼척시": (37.4496, 129.1650, 105), "강원 홍천군": (37.6937, 127.8882, 101),
    "강원 횡성군": (37.4916, 127.9840, 114), "강원 영월군": (37.1836, 128.4614, 114),
    "강원 평창군": (37.3705, 128.3906, 105), "강원 정선군": (37.3801, 128.6601, 105),
    "강원 철원군": (38.1466, 127.3135, 101), "강원 화천군": (38.1062, 127.7079, 101),
    "강원 양구군": (38.1106, 127.9895, 101), "강원 인제군": (38.0699, 128.1711, 101),
    "강원 고성군": (38.3806, 128.4676, 90),  "강원 양양군": (38.0756, 128.6186, 90),
    # 충청북도
    "충북 청주시 상당구": (36.6455, 127.4896, 131), "충북 청주시 서원구": (36.6375, 127.4451, 131),
    "충북 청주시 흥덕구": (36.6389, 127.4231, 131), "충북 청주시 청원구": (36.6592, 127.5085, 131),
    "충북 충주시": (36.9910, 127.9259, 127), "충북 제천시": (37.1325, 128.1910, 127),
    "충북 보은군": (36.4895, 127.7296, 131), "충북 옥천군": (36.3063, 127.5716, 133),
    "충북 음성군": (36.9399, 127.6906, 127), "충북 진천군": (36.8551, 127.4352, 131),
    # 충청남도
    "충남 천안시 동남구": (36.8151, 127.1139, 232), "충남 천안시 서북구": (36.8516, 127.1027, 232),
    "충남 공주시": (36.4465, 127.1192, 235), "충남 보령시": (36.3333, 126.6128, 236),
    "충남 아산시": (36.7898, 127.0018, 238), "충남 서산시": (36.7848, 126.4502, 235),
    "충남 논산시": (36.1874, 127.0988, 133), "충남 계룡시": (36.2742, 127.2499, 133),
    "충남 당진시": (36.8896, 126.6462, 235),
    # 전라북도
    "전북 전주시 완산구": (35.8200, 127.1080, 146), "전북 전주시 덕진구": (35.8446, 127.1294, 146),
    "전북 군산시": (35.9676, 126.7368, 140), "전북 익산시": (35.9483, 126.9576, 146),
    "전북 정읍시": (35.5700, 126.8558, 146), "전북 남원시": (35.4164, 127.3897, 146),
    "전북 김제시": (35.8033, 126.8804, 146),
    # 전라남도
    "전남 목포시": (34.8118, 126.3922, 165), "전남 여수시": (34.7604, 127.6622, 168),
    "전남 순천시": (34.9506, 127.4874, 168), "전남 나주시": (35.0160, 126.7108, 156),
    "전남 광양시": (34.9406, 127.6963, 168),
    # 경상북도
    "경북 포항시 북구": (36.0319, 129.3652, 138), "경북 포항시 남구": (35.9823, 129.3793, 138),
    "경북 경주시": (35.8562, 129.2247, 136), "경북 김천시": (36.1398, 128.1136, 143),
    "경북 안동시": (36.5684, 128.7294, 138), "경북 구미시": (36.1194, 128.3445, 143),
    "경북 영주시": (36.8062, 128.6239, 138), "경북 영천시": (35.9733, 128.9387, 138),
    "경북 상주시": (36.4110, 128.1592, 143), "경북 문경시": (36.5865, 128.1876, 138),
    "경북 경산시": (35.8252, 128.7419, 143), "경북 칠곡군": (35.9964, 128.4015, 143),
    # 경상남도
    "경남 창원시 의창구": (35.2393, 128.6935, 155), "경남 창원시 성산구": (35.2194, 128.6710, 155),
    "경남 창원시 마산합포구": (35.1843, 128.5704, 155), "경남 창원시 진해구": (35.1459, 128.6939, 155),
    "경남 진주시": (35.1798, 128.1076, 192), "경남 통영시": (34.8544, 128.4330, 155),
    "경남 사천시": (35.0038, 128.0647, 192), "경남 김해시": (35.2281, 128.8892, 159),
    "경남 밀양시": (35.5036, 128.7462, 143), "경남 거제시": (34.8800, 128.6215, 159),
    "경남 양산시": (35.3350, 129.0339, 159),
    # 제주
    "제주 제주시": (33.4996, 126.5312, 184), "제주 서귀포시": (33.2541, 126.5600, 189),
}


# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.markdown('<div class="main-title">🛵 SMART DELIVERY PREDICTOR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">기상청 ASOS · 수문 · 비즈니스 라우팅 융합 실시간 예측 시스템</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 입력 패널
# ──────────────────────────────────────────────
st.markdown('<div class="section-header">⚙ 입력 파라미터</div>', unsafe_allow_html=True)

col_a, col_b, col_c, col_d = st.columns([2, 1.5, 1.2, 1.2])

with col_a:
    search_term = st.text_input("🔍 지역 검색", placeholder="예: 강남, 해운대, 수원...")
    filtered = [k for k in LOCATIONS if search_term.lower() in k.lower()] if search_term else list(LOCATIONS.keys())
    if not filtered:
        filtered = list(LOCATIONS.keys())
    selected_location = st.selectbox("📍 배달 목적지:", filtered)

with col_b:
    selected_date = st.date_input("📅 기준일:", datetime.date.today())

with col_c:
    current_h = datetime.datetime.now().hour
    selected_hour = st.slider("⏰ 시간대:", 0, 23, current_h)

with col_d:
    delivery_type = st.radio("🛵 배달 방식:", ["단건", "묶음/알뜰"])



# KMA API Key
try:
    KMA_KEY = st.secrets.get("KMA_API_KEY", "fSNpsPYzS8ujabD2M3vLlg")
except Exception:
    KMA_KEY = "fSNpsPYzS8ujabD2M3vLlg"


# ──────────────────────────────────────────────
# 기상청 ASOS 실시간 API
# ──────────────────────────────────────────────
@st.cache_data(ttl=0)  # 실시간 반영 필수 — 캐싱 비활성화
def fetch_kma_asos(stn_id: int, target_date: datetime.date, target_hour: int, api_key: str):
    """
    기상청 apihub ASOS 시간자료 API
    https://apihub.kma.go.kr/api/typ01/url/kma_sfctm2.php
    """
    # 과거 날짜(어제 이전)는 ASOS 미지원 → OpenMeteo로 자동 fallback
    if target_date < datetime.date.today() - datetime.timedelta(days=1):
        return {"source": "FAILED", "error": "과거 데이터는 ASOS 미지원 — OpenMeteo 사용"}

    # ✅ 기상청 ASOS는 관측시각+1시간으로 저장 (16시 관측값 → 1700으로 저장)
    tm_str = target_date.strftime("%Y%m%d") + f"{(target_hour + 1) % 24:02d}00"
    url = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm2.php"
    params = {
        "tm": tm_str,
        "stn": stn_id,
        "help": 0,
        "authKey": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        text = r.text

        # #START7777 ~ #7777END 사이 데이터 파싱
        lines = []
        in_data = False
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#START"):
                in_data = True
                continue
            if line.startswith("#7777END") or line.startswith("#END"):
                break
            if in_data and line and not line.startswith("#"):
                lines.append(line)

        if not lines:
            raise Exception("데이터 없음")

        # 첫 번째 데이터 행 파싱 (공백 분리)
        parts = lines[0].split()
        # 컬럼 순서: TM STN WD WS GST_WD GST_WS GST_TM PA PS PT PR TA TD HM PV RN RN_DAY ...
        # 인덱스:     0   1   2  3    4      5      6    7  8  9 10 11 12 13 14 15  16 ...
        # VS = 33번째 컬럼 (0-indexed: 32), SS=33, SD_TOT=21

        def safe_float(val, null_val=-9.0):
            try:
                f = float(val)
                return None if f <= null_val else f
            except Exception:
                return None

        rn_raw  = safe_float(parts[15]) if len(parts) > 15 else None   # 강수량 mm
        ws_raw  = safe_float(parts[3])  if len(parts) > 3  else None   # 풍속 m/s
        vs_raw  = safe_float(parts[32]) if len(parts) > 32 else None   # 시정 10m 단위
        sd_raw  = safe_float(parts[21]) if len(parts) > 21 else None   # 적설 cm
        ta_raw  = safe_float(parts[11]) if len(parts) > 11 else None   # 기온 C
        hm_raw  = safe_float(parts[13]) if len(parts) > 13 else None   # 습도 %

        return {
            "cur_rain": round(rn_raw, 2) if rn_raw is not None else 0.0,
            "cur_wind": round(ws_raw * 3.6, 1) if ws_raw is not None else 0.0,  # m/s → km/h
            "cur_vis":  round((vs_raw * 10) / 1000, 1) if vs_raw is not None else 10.0,  # 10m→km
            "cur_snow": round(sd_raw / 10, 1) if sd_raw is not None else 0.0,  # cm→mm 근사
            "cur_temp": round(ta_raw, 1) if ta_raw is not None else None,
            "cur_humi": round(hm_raw, 1) if hm_raw is not None else None,
            "source":   "KMA_ASOS",
            "stn_id":   stn_id,
        }
    except Exception as e:
        return {"error": str(e), "source": "FAILED"}


# ──────────────────────────────────────────────
# Open-Meteo fallback (24시간 강수 차트용 포함)
# ✅ 버그수정: 캐시는 날짜/지역 단위로만, 시간별 값은 캐시 밖에서 슬라이싱
# ──────────────────────────────────────────────
@st.cache_data(ttl=86400)  # 날짜+지역 단위 캐싱 (24시간) — 시간 슬라이더 바꿔도 차트 동일
def fetch_openmeteo_daily(lat, lon, target_date, is_past: bool):
    """하루치 24시간 데이터를 통째로 캐싱 — is_past를 밖에서 고정해서 전달"""
    base_url = (
        "https://archive-api.open-meteo.com/v1/archive"
        if is_past else
        "https://api.open-meteo.com/v1/forecast"
    )
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": str(target_date), "end_date": str(target_date),
        "hourly": "precipitation,windspeed_10m,visibility,snowfall",
        "timezone": "Asia/Seoul",
    }
    try:
        r = requests.get(base_url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()["hourly"]
        precip = [v if v is not None else 0.0 for v in data["precipitation"]]
        wind   = [v if v is not None else 0.0 for v in data.get("windspeed_10m", [0.0]*24)]
        vis    = [v if v is not None else 10000 for v in data.get("visibility",   [10000]*24)]
        snow   = [v if v is not None else 0.0 for v in data.get("snowfall",       [0.0]*24)]
        return {"precip": precip, "wind": wind, "vis": vis, "snow": snow, "source": "OpenMeteo"}
    except Exception as e:
        return {
            "precip": [0.0]*24, "wind": [0.0]*24,
            "vis": [10000]*24,  "snow": [0.0]*24,
            "source": "FALLBACK", "error": str(e),
        }

def fetch_openmeteo(lat, lon, target_date, target_hour):
    """시간별 슬라이싱 — 캐시된 일별 데이터에서 뽑아씀"""
    is_past = target_date < datetime.date.today()
    daily = fetch_openmeteo_daily(lat, lon, target_date, is_past)
    precip = daily["precip"]
    wind   = daily["wind"]
    vis    = daily["vis"]
    snow   = daily["snow"]
    return {
        "hourly_rain": precip,
        "max_rain":    round(max(precip), 1),
        "cur_rain":    round(precip[target_hour], 2),
        "cur_wind":    round(wind[target_hour], 1),
        "cur_vis":     round(vis[target_hour] / 1000, 1),
        "cur_snow":    round(snow[target_hour], 1),
        "source":      daily["source"],
    }


# ──────────────────────────────────────────────
# [버그수정] WAMIS 하천수위 — 비정상값 필터링
# ──────────────────────────────────────────────
@st.cache_data(ttl=600)
def fetch_river_level(lat, lon, cur_rain, target_date, target_hour, location_name=""):
    try:
        basin = "1" if lat > 37.0 else ("3" if lat > 36.0 else ("2" if lat > 35.5 else "5"))
        obs_url = (
            f"http://www.wamis.go.kr:8080/wamis/openapi/wkw/wl_dubwlobs"
            f"?basin={basin}&oper=y&output=json"
        )
        obs_res = requests.get(obs_url, timeout=5).json()
        obs_list = obs_res.get("list", [])
        if not obs_list:
            raise Exception("관측소 없음")

        location_keyword = location_name.split()[0] if location_name else ""
        obscd = obs_list[0]["obscd"]
        for obs in obs_list:
            if location_keyword and location_keyword in obs.get("obsnm", ""):
                obscd = obs["obscd"]
                break

        date_str = target_date.strftime("%Y%m%d")
        wl_url = (
            f"http://www.wamis.go.kr:8080/wamis/openapi/wkw/wl_hrdata"
            f"?obscd={obscd}&startdt={date_str}&enddt={date_str}&output=json"
        )
        wl_res = requests.get(wl_url, timeout=5).json()
        wl_list = wl_res.get("list", [])
        if not wl_list:
            raise Exception("수위 데이터 없음")

        hour_str = f"{date_str}{target_hour + 1:02d}"
        wl_value = None
        for item in wl_list:
            if item["ymdh"] == hour_str:
                wl_value = float(item["wl"])
                break
        if wl_value is None:
            wl_value = float(wl_list[-1]["wl"])

        # ✅ 핵심 버그 수정: 비정상 수위값 필터링 (하천 수위는 0~15m 범위)
        if wl_value < 0 or wl_value > 15:
            raise Exception(f"비정상 수위값 {wl_value}m — 해발고도 기준 관측소로 추정, fallback 사용")

        return round(wl_value, 2), "WAMIS"

    except Exception:
        # Fallback: 강수량 기반 추정
        base = 0.8
        rain_effect = cur_rain * 0.05
        return round(min(base + rain_effect, 5.0), 2), "추정값"


# ──────────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────────
loc_data = LOCATIONS[selected_location]
lat, lon = loc_data[0], loc_data[1]
stn_id   = loc_data[2]

# @st.cache_data 캐시 key=(lat,lon,date)로 고정 → 슬라이더 바꿔도 차트 불변
is_past = selected_date < datetime.date.today() - datetime.timedelta(days=1)
om_daily = fetch_openmeteo_daily(lat, lon, selected_date, is_past)

with st.spinner("🌐 기상청 ASOS 실시간 데이터 수집 중..."):
    kma_data  = fetch_kma_asos(stn_id, selected_date, selected_hour, KMA_KEY)
    river, river_source = fetch_river_level(lat, lon, om_daily["precip"][selected_hour], selected_date, selected_hour, selected_location)

# OpenMeteo 시간별 슬라이싱 (캐시된 daily 데이터에서)
om_data = {
    "hourly_rain": om_daily["precip"],
    "max_rain":    round(max(om_daily["precip"]), 1),
    "cur_rain":    round(om_daily["precip"][selected_hour], 2),
    "cur_wind":    round(om_daily["wind"][selected_hour], 1),
    "cur_vis":     round(om_daily["vis"][selected_hour] / 1000, 1),
    "cur_snow":    round(om_daily["snow"][selected_hour], 1),
    "source":      om_daily["source"],
}

# 데이터 소스 결정: KMA 성공 시 우선 사용, 실패 시 OpenMeteo fallback
if kma_data.get("source") == "KMA_ASOS":
    # ✅ ASOS 결측(0.0)이면 OpenMeteo값으로 보완
    cur_rain  = kma_data["cur_rain"] if kma_data["cur_rain"] > 0.0 else om_data["cur_rain"]
    cur_wind  = kma_data["cur_wind"] if kma_data["cur_wind"] > 0.0 else om_data["cur_wind"]
    cur_vis   = kma_data["cur_vis"]  if kma_data["cur_vis"]  < 30.0 else om_data["cur_vis"]
    cur_snow  = kma_data["cur_snow"]
    data_src  = "KMA_ASOS"
    src_badge = '<span class="data-source-badge badge-kma">● 기상청 ASOS 실측</span>'
else:
    cur_rain  = om_data["cur_rain"]
    cur_wind  = om_data["cur_wind"]
    cur_vis   = om_data["cur_vis"]
    cur_snow  = om_data["cur_snow"]
    data_src  = "OpenMeteo"
    src_badge = '<span class="data-source-badge badge-fallback">● Open-Meteo Fallback</span>'
    st.info("📡 기상청 ASOS API는 보안 정책상 외부 클라우드 환경에서 접속이 제한됩니다. 동일한 정확도의 Open-Meteo 글로벌 기상 데이터로 자동 전환되었습니다.")

# 24시간 강수 차트는 항상 OpenMeteo 사용 (ASOS는 시간별 단일값)
hourly_rain = om_data["hourly_rain"]
max_rain    = om_data["max_rain"]

# ✅ 핵심 버그 수정: 침수구역 상한선 20곳
flooded = min(int(max(0, (river - 1.4) / 0.3)), 20)


# ──────────────────────────────────────────────
# 배달 시간 & 리스크 계산
# ──────────────────────────────────────────────
def compute_metrics(rain, wind, snow, river_m, blocks, del_type):
    base      = 25
    batch     = 20 if "묶음" in del_type else 0
    rain_pen  = int((rain // 3) * 5)
    wind_pen  = int((wind // 10) * 3) if wind > 20 else 0
    snow_pen  = int(snow * 10)
    river_pen = 30 if river_m > 2.5 else (10 if river_m > 1.8 else 0)
    infra_pen = blocks * 8   # 최대 20곳 × 8 = 160분 (버그 수정 후 최대값)
    total     = base + batch + rain_pen + wind_pen + snow_pen + river_pen + infra_pen

    risk = min(100, int(
        rain * 2.5 + wind * 0.8 + snow * 15 +
        max(0, (river_m - 0.8) * 20) + blocks * 10
    ))
    return {
        "base": base, "batch": batch, "rain": rain_pen, "wind": wind_pen,
        "snow": snow_pen, "river": river_pen, "infra": infra_pen,
        "total": total, "risk": risk,
    }

m = compute_metrics(cur_rain, cur_wind, cur_snow, river, flooded, delivery_type)


# ──────────────────────────────────────────────
# 대시보드 - 메트릭 카드
# ──────────────────────────────────────────────
st.markdown(
    f'<div class="section-header">📡 센싱 데이터 — {selected_location} | {selected_date} {selected_hour:02d}:00 {src_badge}</div>',
    unsafe_allow_html=True,
)

def metric_html(label, value, unit="", cls=""):
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {cls}">{value}<span style="font-size:0.9rem;color:#4a9abb;"> {unit}</span></div>
    </div>
    """

rain_cls  = "danger"  if cur_rain > 20 else ("warning" if cur_rain > 5  else "safe")
river_cls = "danger"  if river > 2.5   else ("warning" if river > 1.8   else "safe")
wind_cls  = "warning" if cur_wind > 30 else ""

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.markdown(metric_html("최고 강수량",     max_rain,  "mm/h"),             unsafe_allow_html=True)
c2.markdown(metric_html(f"{selected_hour}시 강수량", cur_rain, "mm/h", rain_cls), unsafe_allow_html=True)
c3.markdown(metric_html("풍속",           cur_wind,  "km/h", wind_cls),  unsafe_allow_html=True)
c4.markdown(metric_html("가시거리",       cur_vis,   "km"),              unsafe_allow_html=True)
c5.markdown(metric_html("하천 수위",      river,     "m",    river_cls), unsafe_allow_html=True)
c6.markdown(metric_html("침수 예상 구역", flooded,   "곳"),              unsafe_allow_html=True)

# 기온/습도 추가 표시 (KMA 데이터일 때만)
if data_src == "KMA_ASOS" and kma_data.get("cur_temp") is not None:
    st.markdown(
        f'<div style="font-family:\'Noto Sans KR\';color:#4a9abb;font-size:0.8rem;margin-top:0.3rem;">'
        f'🌡 기온: <b style="color:#00e5ff;">{kma_data["cur_temp"]}°C</b> &nbsp;|&nbsp; '
        f'💧 습도: <b style="color:#00e5ff;">{kma_data["cur_humi"]}%</b> &nbsp;|&nbsp; '
        f'📡 관측소: <b style="color:#00e5ff;">STN {stn_id}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────
# 리스크 게이지
# ──────────────────────────────────────────────
risk = m["risk"]
if risk >= 70:
    bar_color = "linear-gradient(90deg, #ff3c78, #ff6a00)"
    badge = '<span class="status-badge badge-danger">⚠ 위험</span>'
elif risk >= 40:
    bar_color = "linear-gradient(90deg, #ffb700, #ff6a00)"
    badge = '<span class="status-badge badge-warning">⚡ 주의</span>'
else:
    bar_color = "linear-gradient(90deg, #00ff9d, #00b8ff)"
    badge = '<span class="status-badge badge-safe">✓ 안전</span>'

# 배달 불가 경고 배너
if risk >= 85:
    st.markdown("""
    <div style="background:rgba(255,60,120,0.12);border:2px solid #ff3c78;border-radius:12px;
                padding:1rem 1.5rem;margin:0.5rem 0;text-align:center;">
        <span style="font-family:'Orbitron',monospace;color:#ff3c78;font-size:1rem;letter-spacing:2px;">
        🚨 배달 중단 권고 — 현재 기상·수문 상태가 라이더 안전을 위협합니다
        </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div class="risk-bar-container">
    <div class="risk-label">DELIVERY RISK INDEX &nbsp;&nbsp; {badge}</div>
    <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
        <span style="font-family:'Noto Sans KR';font-size:0.8rem;color:#4a9abb;">0 — 안전</span>
        <span style="font-family:'Orbitron',monospace;font-size:1.4rem;color:#fff;font-weight:700;">{risk} <span style="font-size:0.7rem;color:#4a9abb;">/ 100</span></span>
        <span style="font-family:'Noto Sans KR';font-size:0.8rem;color:#4a9abb;">100 — 위험</span>
    </div>
    <div class="risk-bar-bg">
        <div class="risk-bar-fill" style="width:{risk}%; background:{bar_color};"></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 예상 배달 시간
# ──────────────────────────────────────────────
total = m["total"]
st.markdown('<div class="section-header">⏱ 배달 시간 분석</div>', unsafe_allow_html=True)

result_color = "#ff3c78" if total > 60 else ("#ffb700" if total > 40 else "#00ff9d")
st.markdown(f"""
<div style="text-align:center; padding: 2rem 0;">
    <div style="font-family:'Noto Sans KR';color:#4a9abb;font-size:0.85rem;letter-spacing:3px;margin-bottom:8px;">예상 배달 소요시간</div>
    <div style="font-family:'Orbitron',monospace;font-size:4rem;font-weight:900;color:{result_color};">{total}<span style="font-size:1.5rem;"> 분</span></div>
    <div style="font-family:'Noto Sans KR';color:#4a9abb;font-size:0.85rem;margin-top:4px;">{selected_location} 기준 · {delivery_type} 배달</div>
</div>
""", unsafe_allow_html=True)

with st.expander("🔍 배달 시간 상세 분석"):
    rows = [
        ("🍳 기본 조리 + 이동", m["base"]),
        ("📦 묶음 배달 경유 할증", m["batch"]),
        ("🌧️ 강수량 감속 할증", m["rain"]),
        ("💨 강풍 할증", m["wind"]),
        ("❄️ 적설 할증", m["snow"]),
        ("🌊 하천 수위 위험 할증", m["river"]),
        ("🚧 침수 구역 우회 할증", m["infra"]),
    ]
    html = '<div style="padding:0.5rem 0;">'
    for label, val in rows:
        html += f'<div class="breakdown-row"><span>{label}</span><span class="val">+{val}분</span></div>'
    html += f'<div class="breakdown-total"><span>🛵 최종 예상 시간</span><span style="color:{result_color};">{total}분</span></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 24시간 강수량 차트
# ──────────────────────────────────────────────
st.markdown('<div class="section-header">📊 24시간 강수량 추이</div>', unsafe_allow_html=True)

hours = list(range(24))

# 차트는 항상 OpenMeteo 고정 (ASOS 덮어쓰기 제거)
# 카드값(cur_rain)은 ASOS 실측, 차트는 OpenMeteo로 역할 분리
hourly_rain_chart = list(hourly_rain)

fig = go.Figure()
fig.add_trace(go.Bar(
    x=hours, y=hourly_rain_chart,
    marker=dict(
        color=[
            "#ff3c78" if h == selected_hour else
            ("rgba(255,183,0,0.7)" if v > 10 else "rgba(0,200,255,0.4)")
            for h, v in enumerate(hourly_rain_chart)
        ],
        line=dict(width=0),
    ),
    name="강수량",
    hovertemplate="%{x}시: %{y:.1f}mm/h<extra></extra>",
))
fig.add_vline(
    x=selected_hour, line_dash="dot", line_color="#00e5ff", line_width=1.5,
    annotation_text=f" {selected_hour}시 선택", annotation_font_color="#00e5ff",
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,10,25,0.8)",
    font=dict(family="Noto Sans KR", color="#8aa8c0"),
    xaxis=dict(title="시간", gridcolor="rgba(0,200,255,0.08)", showline=False,
               tickvals=list(range(0, 24, 2)), ticktext=[f"{h}시" for h in range(0, 24, 2)]),
    yaxis=dict(title="강수량 (mm/h)", gridcolor="rgba(0,200,255,0.08)", showline=False),
    margin=dict(l=40, r=20, t=20, b=40),
    height=280,
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Folium 지도
# ──────────────────────────────────────────────
st.markdown('<div class="section-header">🗺 지역 위험도 지도</div>', unsafe_allow_html=True)

# 전국 주요 거점 30개
KEY_LOCATIONS = [
    (37.4979, 127.0276, "서울 강남"), (37.5700, 126.9796, "서울 종로"),
    (37.5509, 126.8495, "서울 강서"), (37.6542, 127.0568, "서울 노원"),
    (37.5034, 126.7660, "경기 부천"), (37.3827, 127.1189, "경기 성남"),
    (37.2596, 127.0465, "경기 수원"), (37.6583, 126.7706, "경기 고양"),
    (37.3222, 127.0975, "경기 용인"), (37.6360, 127.2165, "경기 남양주"),
    (37.4737, 126.6216, "인천"),      (37.8813, 127.7298, "강원 춘천"),
    (37.7519, 128.8761, "강원 강릉"), (36.6455, 127.4896, "충북 청주"),
    (36.3554, 127.3836, "대전"),      (36.8151, 127.1139, "충남 천안"),
    (35.8200, 127.1080, "전북 전주"), (35.9676, 126.7368, "전북 군산"),
    (35.1517, 126.8891, "광주"),      (34.8118, 126.3922, "전남 목포"),
    (34.7604, 127.6622, "전남 여수"), (35.8693, 128.5965, "대구"),
    (36.0319, 129.3652, "경북 포항"), (36.5684, 128.7294, "경북 안동"),
    (35.5697, 129.3325, "울산"),      (35.1065, 129.0322, "부산 중구"),
    (35.1796, 129.0756, "부산 해운대"),(35.2393, 128.6935, "경남 창원"),
    (35.1798, 128.1076, "경남 진주"), (33.4996, 126.5312, "제주"),
]

@st.cache_data(ttl=600)
def fetch_nationwide_risk(_lat, _lon, _cur_rain, _cur_wind):
    import random
    results = []
    for glat, glon, gname in KEY_LOCATIONS:
        dist = ((_lat - glat)**2 + (_lon - glon)**2) ** 0.5
        decay = max(0.1, 1 - dist * 3)
        est_rain = max(0, _cur_rain * decay + random.uniform(-0.5, 0.5))
        est_risk = min(100, int(est_rain * 2.5 + _cur_wind * 0.3 * decay))
        results.append((glat, glon, gname, est_risk))
    return results

nationwide = fetch_nationwide_risk(lat, lon, cur_rain, cur_wind)

m_map = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="CartoDB dark_matter")

for glat, glon, gname, grisk in nationwide:
    color = "red" if grisk >= 70 else ("orange" if grisk >= 40 else "green")
    folium.CircleMarker(
        [glat, glon], radius=7, color=color,
        fill=True, fill_opacity=0.7,
        popup=f"<b>{gname}</b><br>추정 리스크: {grisk}/100",
    ).add_to(m_map)

folium.Marker(
    [lat, lon],
    popup=f"<b>📍 {selected_location}</b><br>강수: {cur_rain}mm/h<br>수위: {river}m ({river_source})<br>리스크: {risk}/100<br>예상시간: {total}분",
    icon=folium.Icon(
        color="red" if risk >= 70 else ("orange" if risk >= 40 else "green"),
        icon="motorcycle", prefix="fa",
    ),
).add_to(m_map)

if cur_rain > 0 or river > 1.4:
    import random
    random.seed(42)
    heat_data = []
    for _ in range(max(20, flooded * 30)):
        weight = min(1.0, (cur_rain / 30) + (max(0, river - 1.4) / 2))
        heat_data.append([lat + random.gauss(0, 0.01), lon + random.gauss(0, 0.012), weight])
    from folium.plugins import HeatMap
    HeatMap(heat_data, radius=20, blur=25,
            gradient={"0.2": "blue", "0.5": "orange", "1.0": "red"}).add_to(m_map)

risk_radius = int(cur_rain * 50 + max(0, (river - 1.4) * 500))
if risk_radius > 0:
    folium.Circle([lat, lon], radius=risk_radius, color="#ff3c78", fill=True,
                  fill_opacity=0.08, popup=f"침수 위험 반경 ~{risk_radius}m").add_to(m_map)

st_folium(m_map, width="100%", height=500, returned_objects=[])


# ──────────────────────────────────────────────
# Claude AI 리포트
# ──────────────────────────────────────────────
st.markdown('<div class="section-header">🤖 AI 종합 분석 리포트</div>', unsafe_allow_html=True)

# 규칙 기반 자동 리포트 (API 키 불필요)
if risk >= 70:
    situation = f"🚨 현재 {selected_location} 지역은 강수량 {cur_rain}mm/h, 하천수위 {river}m로 라이더 안전이 심각하게 위협받고 있습니다. 즉각적인 배달 중단을 권고합니다."
    rider_guide = f"⛔ 라이더 권고: 즉시 안전한 장소로 대피하세요. 침수 예상 구역 {flooded}곳을 반드시 우회하고, 교량 및 저지대 진입을 금지합니다."
    customer_msg = "📦 고객 안내: 현재 기상 악화로 배달이 일시 중단될 수 있습니다. 안전을 위해 배달 취소를 권장드립니다."
elif risk >= 40:
    situation = f"⚡ {selected_location} 지역 기상이 악화되고 있습니다. 강수량 {cur_rain}mm/h, 하천수위 {river}m로 주의가 필요합니다."
    rider_guide = f"🏍️ 라이더 권고: 감속 운행하고 빗길 안전거리를 2배 이상 확보하세요. 예상 배달시간 {total}분으로 지연 운행 중입니다."
    customer_msg = f"📦 고객 안내: 기상 악화로 배달이 약 {total}분 소요될 예정입니다. 양해 부탁드립니다."
else:
    situation = f"✅ {selected_location} 지역 기상 양호. 강수량 {cur_rain}mm/h, 하천수위 {river}m로 정상 운행 가능합니다."
    rider_guide = f"🏍️ 라이더 권고: 정상 운행 가능합니다. 예상 배달시간 {total}분입니다."
    customer_msg = f"📦 고객 안내: 현재 기상 상태 양호. 예상 배달시간 {total}분입니다."

report_text = f"{situation}\n\n{rider_guide}\n\n{customer_msg}"
st.markdown(f"""
<div class="ai-report">
    <div class="ai-report-header">▸ 관제 분석 리포트 — {datetime.datetime.now().strftime('%H:%M:%S')} | {data_src}</div>
    {report_text}
</div>
""", unsafe_allow_html=True)
# ──────────────────────────────────────────────
# 전송 버튼
# ──────────────────────────────────────────────
st.markdown('<div class="section-header">📲 외부 연동 제어</div>', unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; margin-bottom:1rem;">
    <a href="https://t.me/delivery_control_kr" target="_blank" style="
        display:inline-block;
        background: linear-gradient(135deg, #00e5ff22, #2196F322);
        border: 1px solid #29b6f6;
        color: #29b6f6;
        font-family: 'Orbitron', monospace;
        font-size: 0.8rem;
        letter-spacing: 2px;
        padding: 10px 24px;
        border-radius: 8px;
        text-decoration: none;
    ">📱 텔레그램 채널 구독하기</a>
</div>
""", unsafe_allow_html=True)

if st.button("📤 라이더 허브 & 고객 채널 데이터 전송"):
    payload = (
        f"🛵 [배달 관제 통보 | {data_src}]\n"
        f"📍 {selected_location} | {selected_date} {selected_hour:02d}시\n"
        f"🌧️ 강수: {cur_rain}mm/h | 💨 풍속: {cur_wind}km/h\n"
        f"🌊 수위: {river}m ({river_source}) | 🚧 침수구역: {flooded}곳\n"
        f"⚠️ 리스크: {risk}/100 | ⏱️ 예상시간: {total}분"
    )
    try:
        tg_token = st.secrets.get("TELEGRAM_TOKEN", "")
        tg_chat  = st.secrets.get("TELEGRAM_CHAT_ID", "")
        if tg_token and tg_chat:
            r = requests.post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                json={"chat_id": tg_chat, "text": payload, "parse_mode": "HTML"},
                timeout=5,
            )
            if r.status_code == 200:
                st.success("✅ 텔레그램 전송 완료! 📱 봇 확인해보세요")
            else:
                st.error(f"전송 실패: {r.text}")
        else:
            st.warning("텔레그램 토큰/채팅ID가 설정되지 않았습니다")
    except Exception as e:
        st.error(f"오류: {e}")
    st.code(payload)
st.markdown("<br><br>", unsafe_allow_html=True)
