import streamlit as st
import pandas as pd
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="임상신경생리검사 및 SNSB", page_icon="🧠")

# 검사 카테고리 정의
NEURO_TESTS = {
    "NCS": "1. 신경전도검사",
    "EMG": "2. 침근전도검사",
    "EP": "3. 유발전위검사",
    "ANS": "4. 자율신경계기능검사",
    "EEG": "5. 뇌파",
    "TCD": "6. 뇌혈류초음파",
    "Carotid": "7. 경동맥초음파",
    "VOG_VNG": "8. VOG & VNG",
    "SNSB": "9. SNSB",
    "Gait": "10. 보행검사"
}

def require_login():
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("등록이 필요합니다")
        time.sleep(3)
        st.switch_page("app.py")

require_login()

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

def get_neurotest_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("neurotest")
    except:
        worksheet = spreadsheet.add_worksheet(title="neurotest", rows=1000, cols=10)
        worksheet.append_row([
            "id", "category", "title", "content", "image_url", 
            "video_url", "author", "created_at", "order", "type"
        ])
        return worksheet

@st.cache_data(ttl=300)
def load_all_materials():
    try:
        sheet = get_neurotest_sheet()
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def get_materials_by_category(df, category):
    if df.empty:
        return pd.DataFrame()
    filtered = df[df['category'] == category]
    if 'order' in filtered.columns:
        filtered = filtered.sort_values('order')
    return filtered.reset_index(drop=True)

def get_category_counts(df):
    if df.empty:
        return {cat: 0 for cat in NEURO_TESTS.keys()}
    counts = df['category'].value_counts().to_dict()
    return {cat: counts.get(cat, 0) for cat in NEURO_TESTS.keys()}

# 세션 상태 초기화
if "selected_neurotest" not in st.session_state:
    st.session_state.selected_neurotest = None
if "neurotest_item_idx" not in st.session_state:
    st.session_state.neurotest_item_idx = 0

# ============ UI ============
st.title("🧠 임상신경생리검사 및 SNSB")

all_materials_df = load_all_materials()

# 카테고리 미선택 시
if st.session_state.selected_neurotest is None:
    st.subheader("📋 검사 종류를 선택하세요")
    
    category_counts = get_category_counts(all_materials_df)
    
    # ⭐ 수정된 부분: 2개씩 묶어서 순서대로 표시
    items = list(NEURO_TESTS.items())
    
    for i in range(0, len(items), 2):
        col1, col2 = st.columns(2)
        
        # 왼쪽 버튼
        cat_en, cat_kr = items[i]
        with col1:
            count = category_counts.get(cat_en, 0)
            if st.button(
                f"📖 {cat_kr} 자료 {count}개", 
                key=f"neuro_{cat_en}",
                use_container_width=True
            ):
                st.session_state.selected_neurotest = cat_en
                st.session_state.neurotest_item_idx = 0
                st.rerun()
        
        # 오른쪽 버튼
        if i + 1 < len(items):
            cat_en, cat_kr = items[i + 1]
            with col2:
                count = category_counts.get(cat_en, 0)
                if st.button(
                    f"📖 {cat_kr} 자료 {count}개", 
                    key=f"neuro_{cat_en}",
                    use_container_width=True
                ):
                    st.session_state.selected_neurotest = cat_en
                    st.session_state.neurotest_item_idx = 0
                    st.rerun()
    
    st.divider()
    if st.button("🔄 자료 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 카테고리 선택됨
else:
    category = st.session_state.selected_neurotest
    df = get_materials_by_category(all_materials_df, category)
    
    with st.sidebar:
        st.markdown(f"**현재 검사:** {NEURO_TESTS.get(category, category)}")
        if st.button("🔙 검사 목록으로"):
            st.session_state.selected_neurotest = None
            st.session_state.neurotest_item_idx = 0
            st.rerun()
    
    st.subheader(f"📁 {NEURO_TESTS.get(category, category)}")
    
    if df.empty:
        st.info("아직 등록된 자료가 없습니다.")
        
        st.markdown("---")
        st.markdown(f"### {NEURO_TESTS.get(category, category)} 학습 자료")
        st.markdown("""
        이 섹션에서는 다음 내용을 학습할 수 있습니다:
        - 검사 원리 및 방법
        - 정상 소견
        - 이상 소견 해석
        - 임상 적용
        
        *자료는 '검사자료 관리' 페이지에서 등록할 수 있습니다.*
        """)
    else:
        total_items = len(df)
        current_idx = st.session_state.neurotest_item_idx
        
        if current_idx >= total_items:
            st.session_state.neurotest_item_idx = 0
            current_idx = 0
        
        item = df.iloc[current_idx]
        
        st.caption(f"자료 {current_idx + 1} / {total_items}")
        st.markdown(f"## {item.get('title', '제목 없음')}")
        
        image_url = item.get('image_url', '')
        if image_url and str(image_url).strip() and str(image_url).startswith('http'):
            col1, col2, col3 = st.columns([1, 4, 1])
            with col2:
                st.image(image_url, use_container_width=True)
        
        video_url = item.get('video_url', '')
        if video_url and str(video_url).strip() and str(video_url).startswith('http'):
            col1, col2, col3 = st.columns([1, 4, 1])
            with col2:
                st.video(video_url)
        
        content = item.get('content', '')
        if content:
            st.markdown(content)
        
        st.divider()
        
        if total_items > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if current_idx > 0:
                    if st.button("◀ 이전"):
                        st.session_state.neurotest_item_idx -= 1
                        st.rerun()
            with col2:
                titles = [f"{i+1}. {df.iloc[i].get('title', '제목 없음')[:20]}" for i in range(total_items)]
                selected_title = st.selectbox(
                    "자료 선택",
                    options=titles,
                    index=current_idx,
                    label_visibility="collapsed"
                )
                new_idx = titles.index(selected_title)
                if new_idx != current_idx:
                    st.session_state.neurotest_item_idx = new_idx
                    st.rerun()
            with col3:
                if current_idx < total_items - 1:
                    if st.button("다음 ▶"):
                        st.session_state.neurotest_item_idx += 1
                        st.rerun()
