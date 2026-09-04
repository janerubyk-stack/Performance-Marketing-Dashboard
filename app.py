import streamlit as st


st.set_page_config(
    page_title="성과 비교 분석",
    page_icon="📈",
    layout="wide"
)


pages = [
    st.Page(
        "성과_비교_분석.py",
        title="성과 비교 분석",
        icon="📈"
    ),

    st.Page(
        "pages/2_캠페인별_성과_분석.py",
        title="캠페인별 성과 분석",
        icon="📊"
    ),
]


pg = st.navigation(pages)

pg.run()
