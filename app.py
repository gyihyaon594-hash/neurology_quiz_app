import streamlit as st
from database_utils import register_user

# 페이지 설정
st.set_page_config(
    page_title="영어 문법 학습",
    page_icon="🤖"
)


# 세션 상태 초기화
if 'user_id' not in st.session_state:
    st.session_state.user_id = ''

# 페이지 제목, 연구 내용
st.title("영어 문법 학습")
st.markdown("영어 문법 학습에 오신 것을 환영합니다! '학습 시작' 버튼을 클릭하면 빈칸에 알맞은 말을 선택하는 문법 문제가 제시됩니다. 각 빈칸에 가장 적합한 단어를 골라 선택하세요. 본 영어 문법 학습이 당신의 영어에 도움이 되기를 바랍니다!")


with st.form("register"):
    st.write("학습자 등록")
    user = st.text_input("아이디", key="user")
    phone = st.text_input("휴대폰 뒤 4자리 숫자", key="phone")
    submitted = st.form_submit_button("등록")
    if submitted:
        register_user(user_id = user, phone=phone)
        st.write("등록 성공!")
        st.session_state.user_id = user


if st.session_state.user_id:
    st.page_link("pages/question.py", label="🚀 학습 시작", use_container_width=True)
else:
    if st.button("학습 시작"):
        st.warning("먼저 아이디를 등록해주세요.")


