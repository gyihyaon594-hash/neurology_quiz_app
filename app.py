import streamlit as st
from database_utils import register_user
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials

# 페이지 설정
st.set_page_config(
    page_title="신경과 5년차",
    page_icon="🧠"
)

# 한국 시간대
KST = timezone(timedelta(hours=9))

# Google Sheets 연결
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
        
        now = datetime.utcnow()
        diff = (now - last_access).total_seconds()
        if diff < 600:
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

# 관리자 목록
ADMIN_USERS = {
    "윤지환": "8664"
}

# 세션 상태 초기화
if 'user_id' not in st.session_state:
    st.session_state.user_id = ''
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# 로그인된 경우 - 네비게이션 표시
if st.session_state.user_id:
    # 기본 페이지 (모든 사용자)
    pages = {
        "학습": [
            st.Page("pages/1_Quiz.py", title="Quiz", icon="🧠"),
            st.Page("pages/2_임신생검사 및 SNSB.py", title="임상신경생리검사 및 SNSB", icon="🔬"),
            st.Page("pages/3_Morning_Conference.py", title="Morning Conference", icon="🏥"),
            st.Page("pages/4_Dashboard.py", title="대쉬보드", icon="📊"),
            st.Page("pages/5_Question.py", title="질문", icon="❓"),
        ]
    }
    
    # 관리자 페이지 (관리자만)
    if st.session_state.is_admin:
        pages["관리자"] = [
            st.Page("pages/6_New_Post.py", title="컨퍼런스 관리", icon="✍️"),
            st.Page("pages/7_Quiz_Admin.py", title="문제 관리", icon="📝"),
            st.Page("pages/8_Test_Admin.py", title="검사자료 관리", icon="🔬"),
        ]
    
    # 사이드바에 사용자 정보 표시
    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.user_id}**")
        if st.session_state.is_admin:
            st.caption("👑 관리자")
        if st.button("로그아웃"):
            st.session_state.user_id = ''
            st.session_state.is_admin = False
            st.rerun()
    
    # 네비게이션 실행
    pg = st.navigation(pages)
    pg.run()

# 로그인 안 된 경우 - 등록 화면
else:
    st.title("신경과 5년차 ver1")
    st.markdown("신경과 퀴즈에 오신 것을 환영합니다! 등록 후 '학습 시작' 버튼을 클릭하세요.")

    with st.form("register"):
        st.write("학습자 등록")
        user = st.text_input("이름", key="user")
        phone = st.text_input("휴대폰 뒤 4자리 숫자", key="phone")
        submitted = st.form_submit_button("등록")
        
        if submitted:
            if user in ALLOWED_USERS and ALLOWED_USERS[user] == phone:
                register_user(user_id=user, phone=phone)
                st.session_state.user_id = user
                
                # 관리자 여부 확인
                if user in ADMIN_USERS and ADMIN_USERS[user] == phone:
                    st.session_state.is_admin = True
                else:
                    st.session_state.is_admin = False
                
                # 기존 진행 상태 불러오기
                saved_qid = load_progress(user)
                if saved_qid and saved_qid > 1:
                    st.session_state.qid = saved_qid
                    st.session_state.submitted = False
                    st.session_state.selected = None
                    st.success(f"등록 성공! {saved_qid}번 문제부터 계속합니다.")
                else:
                    st.success("등록 성공!")
                
                st.rerun()
            else:
                st.error("접근 권한이 없습니다.")













