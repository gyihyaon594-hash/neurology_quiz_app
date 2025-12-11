import streamlit as st
import time
import os
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
        worksheet = spreadsheet.add_worksheet(title="conference", rows=1000, cols=6)
        worksheet.append_row(["id", "author", "content_above", "content_below", "created_at", "image_name"])
        return worksheet

def get_replies_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("replies")
    except:
        worksheet = spreadsheet.add_worksheet(title="replies", rows=1000, cols=5)
        worksheet.append_row(["reply_id", "post_id", "author", "content", "created_at"])
        return worksheet

def get_all_comments():
    """모든 글 가져오기"""
    sheet = get_conference_sheet()
    data = sheet.get_all_records()
    return data

def get_replies(post_id):
    """특정 글의 댓글 가져오기"""
    sheet = get_replies_sheet()
    data = sheet.get_all_records()
    return [r for r in data if str(r['post_id']) == str(post_id)]

def add_reply(post_id, author, content):
    """댓글 추가"""
    sheet = get_replies_sheet()
    reply_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([reply_id, post_id, author, content, created_at])

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
            
            # 이미지 위 내용
            content_above = comment.get('content_above') or comment.get('content', '')
            if content_above:
                st.markdown(f"## {content_above}")
            
            # 이미지 표시
            image_name = comment.get('image_name', '')
            if image_name and str(image_name).strip():
                image_path = f"image/{image_name}"
                
                # 파일 존재 여부 확인
                if os.path.exists(image_path):
                    col1, col2, col3 = st.columns([1, 6, 1])
                    with col2:
                        st.image(image_path, use_container_width=True)
                else:
                    st.warning(f"이미지 파일을 찾을 수 없습니다: {image_path}")
            
            # 이미지 아래 내용
            content_below = comment.get('content_below', '')
            if content_below:
                st.markdown(f"**{content_below}**")
            
            # 댓글 섹션
            st.markdown("---")
            st.markdown("**💬 의견**")
            
            # 기존 댓글 표시
            replies = get_replies(comment['id'])
            if replies:
                for reply in replies:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**{reply['author']}** · {reply['created_at']}")
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{reply['content']}")
                    st.markdown("")
            
            # 새 댓글 입력
            col1, col2 = st.columns([5, 1])
            with col1:
                new_reply = st.text_input(
                    "의견 입력",
                    placeholder="의견을 입력하세요...",
                    key=f"reply_{comment['id']}",
                    label_visibility="collapsed"
                )
            with col2:
                if st.button("등록", key=f"btn_{comment['id']}"):
                    if new_reply.strip():
                        add_reply(comment['id'], st.session_state.user_id, new_reply)
                        st.rerun()
                    else:
                        st.warning("내용을 입력해주세요.")
            
            st.divider()
