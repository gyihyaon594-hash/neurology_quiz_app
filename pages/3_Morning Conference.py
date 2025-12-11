import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Morning Conference", page_icon="🏥", layout="wide")

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

def get_all_comments():
    """모든 댓글 가져오기"""
    sheet = get_conference_sheet()
    data = sheet.get_all_records()
    return data

# ============ UI ============
st.title("🏥 Morning Conference")

st.divider()

# 글 목록
comments = get_all_comments()

if not comments:
    st.info("아직 등록된 글이 없습니다.")
else:
    # 최신순 정렬
    comments = sorted(comments, key=lambda x: x['id'], reverse=True)
    
    for comment in comments:
        with st.container():
            # 작성자, 시간
            st.caption(f"{comment['author']} · {comment['created_at']}")
            
            # 내용 (크게 표시)
            st.markdown(f"## {comment['content']}")
            
            # 이미지 표시 (반응형, 최대 800px)
            if comment['image_name']:
                try:
                    col1, col2, col3 = st.columns([1, 6, 1])
                    with col2:
                        st.image(f"image/{comment['image_name']}", use_container_width=True)
                except:
                    pass
            
            st.divider()

