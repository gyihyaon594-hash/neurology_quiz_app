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
        worksheet.append_row(["id", "author", "content", "created_at", "image_urls", "video_url"])
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
    sheet = get_conference_sheet()
    data = sheet.get_all_records()
    return data

def get_replies(post_id):
    sheet = get_replies_sheet()
    data = sheet.get_all_records()
    return [r for r in data if str(r['post_id']) == str(post_id)]

def add_reply(post_id, author, content):
    sheet = get_replies_sheet()
    reply_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([reply_id, post_id, author, content, created_at])

def is_valid_url(url):
    if not url:
        return False
    url = str(url).strip()
    if url in ['', 'nan', 'None']:
        return False
    return url.startswith('http://') or url.startswith('https://')

def parse_image_urls(image_urls_str):
    if not image_urls_str:
        return []
    urls = str(image_urls_str).split(',')
    return [url.strip() for url in urls if is_valid_url(url.strip())]

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
    posts = sorted(posts, key=lambda x: x['id'], reverse=True)
    
    for post in posts:
        with st.container():
            st.caption(f"{post.get('author', '')} · {post.get('created_at', '')}")
            
            content = post.get('content', '') or post.get('content_above', '') or ''
            if content:
                st.markdown(f"## {content}")
            
            # ⭐ 이미지 표시 (st.image 사용, 반응형)
            image_urls_str = str(post.get('image_urls', '') or post.get('image_url', '') or post.get('image_name', '') or '')
            image_urls = parse_image_urls(image_urls_str)
            
            if image_urls:
                if len(image_urls) == 1:
                    # 단일 이미지: 중앙 정렬
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        try:
                            st.image(image_urls[0], use_container_width=True)
                        except:
                            st.warning("이미지를 불러올 수 없습니다.")
                else:
                    # 여러 이미지: 2열 또는 3열 그리드
                    num_cols = min(len(image_urls), 2)  # 최대 2열
                    
                    # 중앙 정렬을 위한 외부 컬럼
                    outer_col1, outer_col2, outer_col3 = st.columns([1, 4, 1])
                    with outer_col2:
                        # 이미지들을 행별로 표시
                        for i in range(0, len(image_urls), num_cols):
                            cols = st.columns(num_cols)
                            for j in range(num_cols):
                                if i + j < len(image_urls):
                                    with cols[j]:
                                        try:
                                            st.image(image_urls[i + j], use_container_width=True)
                                            st.caption(f"이미지 {i + j + 1}/{len(image_urls)}")
                                        except:
                                            st.warning(f"이미지 {i + j + 1} 로드 실패")
            
            # 동영상 표시
            video_url = str(post.get('video_url', '') or '').strip()
            if is_valid_url(video_url):
                col1, col2, col3 = st.columns([1, 3, 1])
                with col2:
                    try:
                        st.video(video_url)
                    except:
                        st.warning("동영상을 불러올 수 없습니다.")
            
            content_below = post.get('content_below', '')
            if content_below:
                st.markdown(f"**{content_below}**")
            
            # 댓글 섹션
            st.markdown("---")
            st.markdown("**💬 의견**")
            
            replies = get_replies(post['id'])
            if replies:
                for reply in replies:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**{reply['author']}** · {reply['created_at']}")
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{reply['content']}")
                    st.markdown("")
            
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
