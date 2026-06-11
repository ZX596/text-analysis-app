# 错误处理工具
import streamlit as st
import requests
from requests.exceptions import Timeout, RequestException
from urllib.parse import urlparse

def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False

def handle_error(e):
    if isinstance(e, Timeout):
        st.error("网络请求超时，请检查网络或稍后重试。")
    elif isinstance(e, RequestException):
        st.error(f"网络请求失败：{str(e)}")
    elif isinstance(e, ValueError):
        st.error("URL格式错误，请输入以http/https开头的有效链接。")
    elif hasattr(e, 'response') and getattr(e, 'response', None) is not None and e.response.status_code == 404:
        st.error("404：页面未找到，请检查URL是否正确。")
    else:
        st.error(f"发生未知错误：{str(e)}")
