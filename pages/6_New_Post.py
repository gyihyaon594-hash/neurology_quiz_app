import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

st.set_page_config(page_title="컨퍼런스 관리", page_icon="✍️")

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

def upload_image_to_imgbb(image_file):
    try:
        api_key = st.secrets.get("imgbb", {}).get("api_key", "")
        if not api_key:
            st.error("imgBB API 키가 설정되지 않았습니다.")
            return None
        
        image_file.seek(0)
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": api_key, "image": image_data, "name": image_file.name},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result['data']['url']
        return None
    except Exception as e:
        st.error(f"이미지 업로드 오류: {e}")
        return None

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

def add_post(author, content, image_urls="", video_url=""):
    sheet = get_conference_sheet()
    post_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([post_id, author, content, created_at, image_urls, video_url])
    return post_id

def get_all_posts():
    sheet = get_conference_sheet()
    return sheet.get_all_records()

def delete_post(post_id):
    sheet = get_conference_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(post_id):
            sheet.delete_rows(idx + 1)
            return True
    return False

def update_post(post_id, content, image_urls="", video_url=""):
    sheet = get_conference_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(post_id):
            sheet.update_cell(idx + 1, 3, content)
            sheet.update_cell(idx + 1, 5, image_urls)
            sheet.update_cell(idx + 1, 6, video_url)
            return True
    return False

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

def join_image_urls(urls_list):
    valid_urls = [url for url in urls_list if is_valid_url(url)]
    return ','.join(valid_urls)

# ============ UI ============
st.title("✍️ 컨퍼런스 관리")
st.write("Morning Conference에 새 컨퍼런스 내용을 등록합니다.")

# ⭐ 반응형 이미지 CSS
st.markdown("""
<style>
    .thumb-img {
        max-width: 150px;
        max-height: 150px;
        object-fit: cover;
        border-radius: 8px;
        border: 2px solid #ddd;
    }
    .thumb-container {
        display: inline-block;
        margin: 5px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.divider()

if 'write_authorized' not in st.session_state:
    st.session_state.write_authorized = False
if 'edit_post_id' not in st.session_state:
    st.session_state.edit_post_id = None

if not st.session_state.write_authorized:
    st.subheader("🔐 인증")
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

else:
    st.success("✅ 인증됨: 윤지환")
    
    tab1, tab2 = st.tabs(["✍️ 새글 작성", "📝 글 관리"])
    
    # 탭 1: 새글 작성
    with tab1:
        st.divider()
        
        content = st.text_area("내용", placeholder="컨퍼런스 내용을 입력하세요...", height=150, key="new_content")
        
        st.markdown("---")
        st.markdown("### 🖼️ 이미지 첨부 (여러 개 가능)")
        
        image_option = st.radio(
            "이미지 추가 방법",
            ["없음", "파일 업로드 (imgBB 저장)", "URL 직접 입력"],
            horizontal=True,
            key="new_img_option"
        )
        
        image_urls_list = []
        uploaded_images = None
        
        if image_option == "파일 업로드 (imgBB 저장)":
            uploaded_images = st.file_uploader(
                "이미지 파일 선택 (여러 개 선택 가능)", 
                type=['png', 'jpg', 'jpeg', 'gif'],
                accept_multiple_files=True,
                key="new_img_upload"
            )
            if uploaded_images:
                st.markdown(f"**선택된 이미지: {len(uploaded_images)}개**")
                cols = st.columns(min(len(uploaded_images), 4))
                for idx, img in enumerate(uploaded_images):
                    with cols[idx % 4]:
                        st.image(img, caption=f"{idx+1}", width=150)
                st.info("💡 '등록' 버튼을 누르면 모든 이미지가 업로드됩니다.")
                
        elif image_option == "URL 직접 입력":
            url_input = st.text_area(
                "이미지 URL (여러 개는 줄바꿈으로 구분)",
                placeholder="https://example.com/image1.png\nhttps://example.com/image2.png",
                height=80,
                key="new_image_urls"
            )
            if url_input:
                urls = [u.strip() for u in url_input.strip().split('\n') if u.strip()]
                image_urls_list = [u for u in urls if is_valid_url(u)]
                if image_urls_list:
                    st.markdown(f"**입력된 이미지: {len(image_urls_list)}개**")
                    cols = st.columns(min(len(image_urls_list), 4))
                    for idx, url in enumerate(image_urls_list):
                        with cols[idx % 4]:
                            try:
                                st.image(url, caption=f"{idx+1}", width=150)
                            except:
                                st.warning(f"로드 실패")
        
        st.markdown("---")
        st.markdown("### 🎬 동영상 첨부")
        video_url = st.text_input("YouTube URL (선택)", placeholder="https://youtube.com/watch?v=...", key="new_video")
        if video_url and is_valid_url(video_url):
            try:
                st.video(video_url)
            except:
                st.warning("동영상을 불러올 수 없습니다.")
        
        st.markdown("---")
        
        if st.button("등록", type="primary"):
            if content.strip():
                final_image_urls = []
                
                if image_option == "파일 업로드 (imgBB 저장)" and uploaded_images:
                    progress = st.progress(0)
                    for idx, img_file in enumerate(uploaded_images):
                        uploaded_url = upload_image_to_imgbb(img_file)
                        if uploaded_url:
                            final_image_urls.append(uploaded_url)
                        progress.progress((idx + 1) / len(uploaded_images))
                    progress.empty()
                    st.success(f"이미지 {len(final_image_urls)}개 업로드 완료!")
                
                elif image_option == "URL 직접 입력":
                    final_image_urls = image_urls_list
                
                image_urls_str = join_image_urls(final_image_urls)
                post_id = add_post("윤지환", content, image_urls_str, video_url)
                st.success(f"등록되었습니다!")
                st.balloons()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.warning("내용을 입력해주세요.")
    
    # 탭 2: 글 관리
    with tab2:
        st.divider()
        
        if st.button("🔄 새로고침"):
            st.cache_data.clear()
            st.rerun()
        
        posts = get_all_posts()
        
        if not posts:
            st.info("등록된 글이 없습니다.")
        else:
            posts = sorted(posts, key=lambda x: x['id'], reverse=True)
            st.markdown(f"**총 {len(posts)}개의 글**")
            
            for post in posts:
                post_id = post['id']
                content = post.get('content', '') or post.get('content_above', '')
                is_editing = st.session_state.edit_post_id == post_id
                
                with st.container():
                    if is_editing:
                        st.markdown("### ✏️ 글 수정")
                        
                        edit_content = st.text_area("내용", value=content, height=150, key=f"edit_content_{post_id}")
                        
                        st.markdown("---")
                        st.markdown("### 🖼️ 이미지 수정")
                        
                        current_img_str = str(post.get('image_urls', '') or post.get('image_url', '') or post.get('image_name', '') or '')
                        current_images = parse_image_urls(current_img_str)
                        
                        # ⭐ 현재 이미지들 표시 (썸네일)
                        if current_images:
                            st.markdown(f"**현재 등록된 이미지: {len(current_images)}개**")
                            cols = st.columns(min(len(current_images), 4))
                            for idx, img_url in enumerate(current_images):
                                with cols[idx % 4]:
                                    try:
                                        st.image(img_url, caption=f"이미지 {idx+1}", width=150)
                                    except:
                                        st.warning(f"로드 실패")
                        else:
                            st.info("현재 등록된 이미지가 없습니다.")
                        
                        # ⭐ 수정 옵션 변경: 유지/전체교체/추가/URL수정/전체삭제
                        edit_img_option = st.radio(
                            "이미지 변경 방법",
                            ["유지", "전체 교체 (새로 업로드)", "기존에 추가", "URL 직접 수정", "전체 삭제"],
                            key=f"edit_img_opt_{post_id}"
                        )
                        
                        new_image_files = None
                        edit_image_urls = current_images.copy()
                        
                        if edit_img_option == "전체 교체 (새로 업로드)":
                            new_image_files = st.file_uploader(
                                "새 이미지 선택 (기존 이미지는 모두 삭제됩니다)",
                                type=['png', 'jpg', 'jpeg', 'gif'],
                                accept_multiple_files=True,
                                key=f"replace_img_{post_id}"
                            )
                            if new_image_files:
                                st.markdown(f"**새로 업로드할 이미지: {len(new_image_files)}개**")
                                cols = st.columns(min(len(new_image_files), 4))
                                for idx, img in enumerate(new_image_files):
                                    with cols[idx % 4]:
                                        st.image(img, caption=f"새 {idx+1}", width=150)
                                st.warning("⚠️ 저장 시 기존 이미지는 모두 삭제되고 새 이미지로 교체됩니다.")
                            edit_image_urls = []  # 기존 이미지 삭제
                        
                        elif edit_img_option == "기존에 추가":
                            new_image_files = st.file_uploader(
                                "추가할 이미지 선택",
                                type=['png', 'jpg', 'jpeg', 'gif'],
                                accept_multiple_files=True,
                                key=f"add_img_{post_id}"
                            )
                            if new_image_files:
                                st.markdown(f"**추가할 이미지: {len(new_image_files)}개**")
                                cols = st.columns(min(len(new_image_files), 4))
                                for idx, img in enumerate(new_image_files):
                                    with cols[idx % 4]:
                                        st.image(img, caption=f"추가 {idx+1}", width=150)
                                st.info(f"💡 저장 시 기존 {len(current_images)}개 + 새 {len(new_image_files)}개 = 총 {len(current_images) + len(new_image_files)}개")
                        
                        elif edit_img_option == "URL 직접 수정":
                            current_urls_text = '\n'.join(current_images)
                            edited_urls = st.text_area(
                                "이미지 URL (줄바꿈으로 구분, 삭제하려면 해당 줄 제거)",
                                value=current_urls_text,
                                height=100,
                                key=f"edit_urls_{post_id}"
                            )
                            if edited_urls:
                                urls = [u.strip() for u in edited_urls.strip().split('\n') if u.strip()]
                                edit_image_urls = [u for u in urls if is_valid_url(u)]
                                if edit_image_urls:
                                    st.markdown(f"**수정 후 이미지: {len(edit_image_urls)}개**")
                                    cols = st.columns(min(len(edit_image_urls), 4))
                                    for idx, url in enumerate(edit_image_urls):
                                        with cols[idx % 4]:
                                            try:
                                                st.image(url, caption=f"{idx+1}", width=150)
                                            except:
                                                st.warning("로드 실패")
                            else:
                                edit_image_urls = []
                        
                        elif edit_img_option == "전체 삭제":
                            edit_image_urls = []
                            st.warning("⚠️ 저장 시 모든 이미지가 삭제됩니다.")
                        
                        # 동영상 수정
                        st.markdown("---")
                        st.markdown("### 🎬 동영상 수정")
                        
                        current_video = str(post.get('video_url', '') or '').strip()
                        
                        if is_valid_url(current_video):
                            st.markdown("**현재 등록된 동영상:**")
                            try:
                                st.video(current_video)
                            except:
                                st.warning("동영상을 불러올 수 없습니다.")
                        else:
                            st.info("현재 등록된 동영상이 없습니다.")
                        
                        edit_video_url = st.text_input(
                            "YouTube URL (삭제하려면 비워두세요)", 
                            value=current_video if is_valid_url(current_video) else "",
                            key=f"edit_video_{post_id}"
                        )
                        
                        st.markdown("---")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{post_id}", type="primary"):
                                final_image_urls = edit_image_urls.copy()
                                
                                # 이미지 업로드 처리
                                if new_image_files:
                                    progress = st.progress(0)
                                    for idx, img_file in enumerate(new_image_files):
                                        uploaded_url = upload_image_to_imgbb(img_file)
                                        if uploaded_url:
                                            if edit_img_option == "전체 교체 (새로 업로드)":
                                                final_image_urls.append(uploaded_url)
                                            else:  # 기존에 추가
                                                final_image_urls.append(uploaded_url)
                                        progress.progress((idx + 1) / len(new_image_files))
                                    progress.empty()
                                
                                image_urls_str = join_image_urls(final_image_urls)
                                update_post(post_id, edit_content, image_urls_str, edit_video_url)
                                st.session_state.edit_post_id = None
                                st.success(f"수정되었습니다! (이미지: {len(final_image_urls)}개)")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                        with col2:
                            if st.button("❌ 취소", key=f"cancel_{post_id}"):
                                st.session_state.edit_post_id = None
                                st.rerun()
                    
                    else:
                        col1, col2, col3 = st.columns([5, 1, 1])
                        with col1:
                            media_icons = []
                            img_str = str(post.get('image_urls', '') or post.get('image_url', '') or post.get('image_name', '') or '')
                            img_count = len(parse_image_urls(img_str))
                            if img_count > 0:
                                media_icons.append(f"🖼️×{img_count}" if img_count > 1 else "🖼️")
                            if is_valid_url(post.get('video_url', '')):
                                media_icons.append("🎬")
                            media_str = " ".join(media_icons)
                            
                            st.markdown(f"**{content[:50]}{'...' if len(content) > 50 else ''}** {media_str}")
                            st.caption(f"{post['author']} · {post['created_at']}")
                        with col2:
                            if st.button("✏️", key=f"edit_{post_id}"):
                                st.session_state.edit_post_id = post_id
                                st.rerun()
                        with col3:
                            if st.button("🗑️", key=f"del_{post_id}"):
                                st.session_state[f"confirm_delete_{post_id}"] = True
                        
                        if st.session_state.get(f"confirm_delete_{post_id}", False):
                            st.warning("정말 삭제하시겠습니까?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ 예", key=f"yes_{post_id}"):
                                    delete_post(post_id)
                                    st.session_state[f"confirm_delete_{post_id}"] = False
                                    st.cache_data.clear()
                                    st.rerun()
                            with c2:
                                if st.button("❌ 아니오", key=f"no_{post_id}"):
                                    st.session_state[f"confirm_delete_{post_id}"] = False
                                    st.rerun()
                    
                    st.divider()
    
    st.divider()
    if st.button("로그아웃"):
        st.session_state.write_authorized = False
        st.session_state.edit_post_id = None
        st.rerun()
