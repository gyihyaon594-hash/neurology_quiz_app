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
    if url.startswith('http://') or url.startswith('https://'):
        return True
    return False

def parse_image_urls(image_urls_str):
    if not image_urls_str:
        return []
    urls = str(image_urls_str).split(',')
    return [url.strip() for url in urls if is_valid_url(url.strip())]

# ============ UI ============
st.title("🏥 Morning Conference")

# ⭐ 반응형 이미지 CSS
st.markdown("""
<style>
    .responsive-img {
        max-width: 100%;
        max-height: 500px;
        width: auto;
        height: auto;
        display: block;
        margin: 10px auto;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .image-gallery {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        justify-content: center;
        margin: 15px 0;
    }
    .gallery-item {
        flex: 1 1 300px;
        max-width: 400px;
    }
    .gallery-item img {
        width: 100%;
        height: auto;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    @media (max-width: 768px) {
        .gallery-item {
            flex: 1 1 100%;
            max-width: 100%;
        }
    }
</style>
""", unsafe_allow_html=True)

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
            
            # ⭐ 반응형 이미지 갤러리
            image_urls_str = str(post.get('image_urls', '') or post.get('image_url', '') or post.get('image_name', '') or '')
            image_urls = parse_image_urls(image_urls_str)
            
            if image_urls:
                if len(image_urls) == 1:
                    # 단일 이미지: 중앙 정렬, 최대 너비 제한
                    st.markdown(f"""
                    <div style="text-align: center;">
                        <img src="{image_urls[0]}" class="responsive-img" alt="이미지">
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # 여러 이미지: 갤러리 형태
                    gallery_html = '<div class="image-gallery">'
                    for idx, img_url in enumerate(image_urls):
                        gallery_html += f'''
                        <div class="gallery-item">
                            <img src="{img_url}" alt="이미지 {idx+1}">
                            <p style="text-align: center; font-size: 12px; color: #666;">이미지 {idx+1}/{len(image_urls)}</p>
                        </div>
                        '''
                    gallery_html += '</div>'
                    st.markdown(gallery_html, unsafe_allow_html=True)
            
            # 동영상 표시
            video_url = str(post.get('video_url', '') or '').strip()
            if is_valid_url(video_url):
                col1, col2, col3 = st.columns([1, 4, 1])
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
