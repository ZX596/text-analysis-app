# UI生成器工具
import streamlit as st
import base64
import pandas as pd

def render_progress(progress):
    st.progress(progress)

def render_csv_download(df, filename="word_freq.csv"):
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 下载词频CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

def render_footer():
    st.markdown("""
    <hr/>
    <div style='font-size:13px; color:gray; text-align:center;'>
    本工具仅供学习交流，支持8种图表，数据缓存1小时。<br/>
    如遇网络问题、无内容、格式错误等请检查URL或稍后重试。
    </div>
    """, unsafe_allow_html=True)
