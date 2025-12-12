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
        st.rerun()

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
        worksheet.append_row(["id", "author", "content", "created_at", "image_url", "video_url"])
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

@st.cache_data(ttl=300)
def get_all_posts():
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

def is_valid_url(url):
    """유효한 URL인지 확인"""
    if not url:
        return False
    url = str(url).strip()
    if url in ['', 'nan', 'None']:
        return False
    # URL 형식 확인 (http로 시작하는지)
    if url.startswith('http://') or url.startswith('https://'):
        return True
    return False

# ============ UI ============
st.title("🏥 Morning Conference")

# 새로고침 버튼
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# 글 목록
posts = get_all_posts()

if not posts:
    st.info("아직 등록된 글이 없습니다.")
else:
    # 최신순 정렬
    posts = sorted(posts, key=lambda x: x['id'], reverse=True)
    
    for post in posts:
        with st.container():
            # 작성자, 시간
            st.caption(f"{post.get('author', '')} · {post.get('created_at', '')}")
            
            # 내용 표시
            content = post.get('content', '') or post.get('content_above', '') or ''
            if content:
                st.markdown(f"## {content}")
            
            # ⭐ 이미지 표시 (URL 유효성 검사)
            image_url = str(post.get('image_url', '') or post.get('image_name', '') or '').strip()
            
            if is_valid_url(image_url):
                col1, col2, col3 = st.columns([1, 6, 1])
                with col2:
                    try:
                        st.image(image_url, use_container_width=True)
                    except Exception as e:
                        st.warning(f"이미지를 불러올 수 없습니다.")
            
            # ⭐ 동영상 표시
            video_url = str(post.get('video_url', '') or '').strip()
            
            if is_valid_url(video_url):
                col1, col2, col3 = st.columns([1, 6, 1])
                with col2:
                    try:
                        st.video(video_url)
                    except Exception as e:
                        st.warning(f"동영상을 불러올 수 없습니다.")
            
            # 이미지 아래 내용
            content_below = post.get('content_below', '')
            if content_below:
                st.markdown(f"**{content_below}**")
            
            # 댓글 섹션
            st.markdown("---")
            st.markdown("**💬 의견**")
            
            # 기존 댓글 표시
            replies = get_replies(post['id'])
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
                    key=f"reply_{post['id']}",
                    label_visibility="collapsed"
                )
            with col2:
                if st.button("등록", key=f"btn_{post['id']}"):
                    if new_reply.strip():
                        add_reply(post['id'], st.session_state.user_id, new_reply)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("내용을 입력해주세요.")
            
            st.divider()
