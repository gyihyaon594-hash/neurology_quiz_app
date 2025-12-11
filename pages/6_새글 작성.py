import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="새글 작성", page_icon="✍️")

# 로그인 체크
def require_login():
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("등록이 필요합니다")
        time.sleep(3)
        st.switch_page("app.py")

require_login()

# Google Sheets 연결
def get_sheets_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(credentials)

def get_conference_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("conference")
    except:
        worksheet = spreadsheet.add_worksheet(title="conference", rows=1000, cols=5)
        worksheet.append_row(["id", "author", "content", "created_at", "image_name"])
        return worksheet

def add_comment(author, content, image_name=""):
    """댓글 추가"""
    sheet = get_conference_sheet()
    comment_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([comment_id, author, content, created_at, image_name])

# ============ UI ============
st.title("✍️ 새글 작성")
st.write("Morning Conference에 새 글을 등록합니다.")

st.divider()

# 인증 상태 확인
if 'write_authorized' not in st.session_state:
    st.session_state.write_authorized = False

# 인증되지 않은 경우
if not st.session_state.write_authorized:
    st.subheader("🔐 인증")
    st.write("글 작성 권한이 필요합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        input_name = st.text_input("이름", placeholder="이름을 입력하세요")
    with col2:
        input_code = st.text_input("인증코드", type="password", placeholder="인증코드 입력")
    
    if st.button("인증", type="primary"):
        if input_name == "윤지환" and input_code == "8664":
            st.session_state.write_authorized = True
            st.success("인증되었습니다!")
            st.rerun()
        else:
            st.error("인증 정보가 올바르지 않습니다.")

# 인증된 경우 - 글 작성 폼
else:
    st.success("✅ 인증됨: 윤지환")
    
    st.divider()
    
    # 이미지 업로드
    uploaded_image = st.file_uploader("이미지 업로드 (선택)", type=['png', 'jpg', 'jpeg'])
    
    # 내용 입력
    new_content = st.text_area(
        "내용",
        placeholder="질문이나 의견을 입력하세요...",
        height=150
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("등록", type="primary"):
            if new_content.strip():
                image_name = ""
                
                # 이미지 저장
                if uploaded_image:
                    image_name = f"conf_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_image.name}"
                    with open(f"image/{image_name}", "wb") as f:
                        f.write(uploaded_image.getbuffer())
                
                add_comment("윤지환", new_content, image_name)
                st.success("등록되었습니다!")
                time.sleep(1)
                st.switch_page("pages/3_Morning Conference.py")
            else:
                st.warning("내용을 입력해주세요.")
    
    with col2:
        if st.button("로그아웃"):
            st.session_state.write_authorized = False
            st.rerun()

