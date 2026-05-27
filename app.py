import streamlit as st

st.title("테스트 앱")

@st.dialog("알림")
def show_popup():
    st.write("김예림 바보")

if st.button("클릭"):
    show_popup()