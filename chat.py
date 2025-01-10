import streamlit as st
from llm import get_ai_response

# 페이지 config 작성
st.set_page_config(page_title="데이터센터 챗봇", page_icon="🤖")

# h1태그
st.title("🤖 Onion DataCenter Chatbot")

st.caption("데이터센터에 관련된 모든것을 답해드립니다!")




if 'message_list' not in st.session_state:
    st.session_state.message_list = []

print(f"before == {st.session_state.message_list}")

for message in st.session_state.message_list:
    with st.chat_message(message["role"]):
        st.write(message["content"])






if user_question := st.chat_input(placeholder="데이터센터에 관련한 궁금한 내용들을 말씀해주세요!"):
    with st.chat_message("user"):
        st.write(user_question)
    st.session_state.message_list.append({"role" : "user", "content": user_question})

    with st.spinner("답변을 생성하는 중입니다."):
        ai_response = get_ai_response(user_question)
        with st.chat_message("ai"):
            ai_message = st.write_stream(ai_response)
            st.session_state.message_list.append({"role" : "ai", "content": ai_message})

print(f"after == {st.session_state.message_list}")
