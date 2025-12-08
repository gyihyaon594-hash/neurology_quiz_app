import streamlit as st

st.set_page_config(page_title="질의응답", page_icon="💬")

# 로그인 확인
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("홈에서 먼저 등록해주세요.")
    st.stop()

st.title("💬 질의응답 (Agora)")

# 질문 입력
question = st.text_area("질문을 입력하세요", height=150)

if st.button("질문 제출"):
    if question:
        st.success("질문이 등록되었습니다!")
        # 여기에 질문 저장 로직 추가 가능
    else:
        st.warning("질문을 입력해주세요.")

# 기존 질문 목록 (예시)
st.subheader("📋 질문 목록")
st.info("아직 등록된 질문이 없습니다.")
