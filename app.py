import streamlit as st
from database_utils import register_user
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# 페이지 설정
st.set_page_config(
    page_title="신경과 5년차",
    page_icon="🧠"
)

# Google Sheets 연결
@st.cache_resource
def get_progress_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("progress")
    except:
        return None

# 진행 상태 불러오기 (10분 이내만)
def load_progress(user_id):
    sheet = get_progress_sheet()
    if sheet is None:
        return None
    try:
        cell = sheet.find(user_id)
        row = sheet.row_values(cell.row)
        qid = int(row[1])
        last_access = datetime.strptime(row[2], "%Y-%m-%d %H:%M")
        if (datetime.now() - last_access).total_seconds() < 600:
            return qid
        return None
    except:
        return None

# 허용된 사용자 목록
ALLOWED_USERS = {
    "윤지환": "8664",
    "윤현수": "4120",
    "송배섭": "1525",
    "손선우": "3461",
    "김동규": "9440",
}

# 세션 상태 초기화
if 'user_id' not in st.session_state:
    st.session_state.user_id = ''

# 페이지 제목
st.title("신경과 5년차 ver1")
st.markdown("신경과 퀴즈에 오신 것을 환영합니다! '학습 시작' 버튼을 클릭하면 신경과 문제가 제시됩니다. 각 질문에 가장 적합한 답을 골라 선택하세요. 본 신경학 퀴즈가 당신의 트레이닝에 도움이 되기를 바랍니다!")

with st.form("register"):
    st.write("학습자 등록")
    user = st.text_input("이름", key="user")
    phone = st.text_input("휴대폰 뒤 4자리 숫자", key="phone")
    submitted = st.form_submit_button("등록")
    if submitted:
        if user in ALLOWED_USERS and ALLOWED_USERS[user] == phone:
            register_user(user_id=user, phone=phone)
            st.success("등록 성공!")
            st.session_state.user_id = user
            
            # 기존 진행 상태 불러오기
            saved_qid = load_progress(user)
            if saved_qid and saved_qid > 1:
                st.session_state.qid = saved_qid
                st.info(f"이전 진행 상태를 불러왔습니다. ({saved_qid}번 문제부터 계속)")
        else:
            st.error("접근 권한이 없습니다. 이름과 휴대폰 번호를 확인해주세요.")

if st.session_state.user_id:
    st.page_link("pages/1_Quiz.py", label="🚀 학습 시작", use_container_width=True)
else:
    if st.button("학습 시작"):
        st.warning("먼저 등록해주세요.")








