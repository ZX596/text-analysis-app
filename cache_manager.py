import streamlit as st
import time
import hashlib
import pickle
import os

CACHE_DIR = ".cache"
CACHE_EXPIRE = 3600  # 1小时

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(key):
    hashed = hashlib.md5(key.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{hashed}.pkl")

def set_cache(key, value):
    path = get_cache_path(key)
    with open(path, "wb") as f:
        pickle.dump({"value": value, "ts": time.time()}, f)

def get_cache(key):
    path = get_cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
            # 检查缓存是否过期
            if time.time() - data["ts"] > CACHE_EXPIRE:
                try:
                    os.remove(path)  # 尝试删除过期缓存
                    st.toast("清理过期缓存✅", icon="🗑️")
                except (PermissionError, OSError):
                    # 捕获文件被占用错误，不阻断程序运行
                    st.warning("缓存文件被占用，跳过删除", icon="⚠️")
                return None
            return data["value"]
    except (pickle.UnpicklingError, EOFError):
        # 处理缓存文件损坏问题
        try:
            os.remove(path)
            st.error("缓存文件损坏，已清理", icon="🚨")
        except (PermissionError, OSError):
            st.error("缓存文件损坏且被占用，无法清理", icon="🚨")
        return None