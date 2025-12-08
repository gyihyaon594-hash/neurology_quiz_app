import streamlit as st
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="질의응답", page_icon="💬")

# 로그인 확인
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("홈에서 먼저 등록해주세요.")
    st.stop()

# Google Sheets 연결
@st.cache_resource
def get_google_sheet():
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
    sheet = client.open_by_url(sheet_url).sheet1
    return sheet

sheet = get_google_sheet()

st.title("💬 질의응답 (Agora)")

# 질문 입력
question = st.text_area("질문을 입력하세요", height=150)

if st.button("질문 제출"):
    if question:
        sheet.append_row([
            st.session_state.user_id,
            question,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])
        st.success("질문이 등록되었습니다!")
        st.rerun()
    else:
        st.warning("질문을 입력해주세요.")

# 질문 목록 표시
st.subheader("📋 질문 목록")

data = sheet.get_all_records()

if data:
    for q in reversed(data):
        st.markdown(f"**{q['user']}** ({q['time']})")
        st.write(q['question'])
        st.divider()
else:
    st.info("아직 등록된 질문이 없습니다.")
