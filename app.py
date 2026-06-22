import streamlit as st
import requests
from bs4 import BeautifulSoup
import jieba
from collections import Counter
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import WordCloud, Bar, Line, Pie, Radar, Scatter, HeatMap, TreeMap
from streamlit_echarts import st_pyecharts
import re
# 新增：导入自定义技能模块
from cache_manager import get_cache, set_cache
from error_handler import validate_url, handle_error
from ui_generator import render_progress, render_csv_download, render_footer

# --------------------------
# 1. 停用词加载（过滤无意义词汇）
# --------------------------
def load_stopwords():
    # 内置常用中文停用词，无需额外文件
    stopwords = set([
        "的", "了", "在", "是", "我", "你", "他", "她", "它", "我们", "你们", "他们",
        "这", "那", "上", "下", "左", "右", "前", "后", "个", "只", "条", "本", "件",
        "和", "与", "或", "但", "如果", "因为", "所以", "就", "才", "都", "也", "还",
        "不", "没", "有", "能", "会", "要", "可以", "将", "着", "过", "呢", "吗", "啊",
        "哦", "嗯", "嗨", "喂", "吧", "呀", "之", "于", "以", "为", "而", "则", "且",
        "其", "所", "何", "孰", "安", "更", "又", "再", "即", "若", "虽", "虽则", "尽管"
    ])
    return stopwords

# --------------------------
# 2. URL文本抓取函数
# --------------------------
def crawl_url_text(url):
    # 1. 校验URL格式
    if not validate_url(url):
        handle_error(ValueError("URL格式错误"))
        return ""
    # 2. 缓存检查
    cache_key = f"urltext:{url}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 404:
            handle_error(Exception("404"))
            return ""
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text_content = "\n".join([p.get_text().strip() for p in paragraphs])
        text_content = re.sub(r"\s+", " ", text_content)
        text_content = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s]", "", text_content)
        if not text_content.strip():
            handle_error(Exception("无内容"))
            return ""
        set_cache(cache_key, text_content)
        return text_content
    except Exception as e:
        handle_error(e)
        return ""

# --------------------------
# 3. 分词与词频统计函数
# --------------------------
def word_segment_and_count(text, stopwords, min_freq=1):
    if not text:
        return Counter(), pd.DataFrame()
    # 1. 缓存检查
    cache_key = f"wordfreq:{hash(text)}:{min_freq}"
    cached = get_cache(cache_key)
    if cached:
        return cached[0], cached[1]
    words = jieba.lcut(text)
    filtered_words = [
        word for word in words
        if word not in stopwords and len(word) > 1 and word.strip() != ""
    ]
    word_count = Counter(filtered_words)
    word_count_filtered = Counter({k: v for k, v in word_count.items() if v >= min_freq})
    word_freq_df = pd.DataFrame(
        word_count_filtered.items(),
        columns=["词汇", "频次"]
    ).sort_values(by="频次", ascending=False).reset_index(drop=True)
    set_cache(cache_key, (word_count_filtered, word_freq_df))
    return word_count_filtered, word_freq_df

# --------------------------
# 4. 图表构建函数（支持≥7种图表）
# --------------------------
def create_chart(chart_type, word_freq_df, top_n=20):
    # 取前N个词汇（默认20）
    top_word_df = word_freq_df.head(top_n).copy()
    words = top_word_df["词汇"].tolist()
    freqs = top_word_df["频次"].tolist()
    
    if not words or not freqs:
        st.warning("暂无足够数据生成图表，请调整低频词阈值或更换URL")
        return None
    
    # 1. 词云图
    if chart_type == "词云图":
        wc = (
            WordCloud()
            .add(series_name="词频统计", data_pair=list(zip(words, freqs)), word_size_range=[20, 100])
            .set_global_opts(
                title_opts=opts.TitleOpts(title="文章词汇词云图", pos_left="center"),
                tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}: {c}")
            )
        )
        return wc
    
    # 2. 柱状图
    elif chart_type == "柱状图":
        bar = (
            Bar()
            .add_xaxis(words)
            .add_yaxis("词汇频次", freqs)
            .reversal_axis()  # 横向柱状图，便于显示词汇
            .set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20柱状图", pos_left="center"),
                xaxis_opts=opts.AxisOpts(name="频次"),
                yaxis_opts=opts.AxisOpts(name="词汇")
            )
        )
        return bar
    
    # 3. 折线图
    elif chart_type == "折线图":
        line = (
            Line()
            .add_xaxis(words)
            .add_yaxis("词汇频次", freqs, markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="max"), opts.MarkPointItem(type_="min")]))
            .set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20折线图", pos_left="center"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                yaxis_opts=opts.AxisOpts(name="频次")
            )
        )
        return line
    
    # 4. 饼图
    elif chart_type == "饼图":
        pie = (
            Pie()
            .add("", list(zip(words, freqs)), radius=["30%", "75%"])
            .set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20饼图", pos_left="center"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="left")
            )
            .set_series_opts(tooltip_opts=opts.TooltipOpts(formatter="{b}: {c} ({d}%)"))
        )
        return pie
    
    # 5. 雷达图
    elif chart_type == "雷达图":
        # 雷达图需要统一维度名称
        radar_data = [freqs]
        schema = [opts.RadarIndicatorItem(name=word, max_=max(freqs)) for word in words]
        radar = (
            Radar()
            .add_schema(schema, shape="polygon")
            .add("词汇频次", radar_data, color="#1890ff")
            .set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20雷达图", pos_left="center"),
                legend_opts=opts.LegendOpts(is_show=False)
            )
        )
        return radar
    
    # 6. 散点图
    elif chart_type == "散点图":
        scatter = (
            Scatter()
            .add_xaxis(words)
            .add_yaxis("词汇频次", freqs, symbol_size=10)
            .set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20散点图", pos_left="center"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                yaxis_opts=opts.AxisOpts(name="频次")
            )
        )
        return scatter
    
    # 7. 矩形树图
    elif chart_type == "矩形树图":
        treemap_data = [{"name": word, "value": freq} for word, freq in zip(words, freqs)]
        treemap = (
            TreeMap()
            .add("词频统计", treemap_data)
            .set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20矩形树图", pos_left="center"),
                tooltip_opts=opts.TooltipOpts(formatter="{b}: {c}")
            )
        )
        return treemap
    
    # 8. 热力图（额外补充，满足≥7种要求）
    elif chart_type == "热力图":
        # 构造热力图数据（二维结构）
        heat_data = []
        for i in range(len(words)):
            heat_data.append([0, i, freqs[i]])  # 简化为单行热力图
        heatmap = (
            HeatMap()
            .add_xaxis(words)
            .add_yaxis("频次", ["词汇频次"], heat_data)
            .set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20热力图", pos_left="center"),
                visualmap_opts=opts.VisualMapOpts(min_=min(freqs), max_=max(freqs)),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45))
            )
        )
        return heatmap

# --------------------------
# 5. 移动端UI样式注入
# --------------------------
def inject_mobile_style():
    css = """
    <style>
    /* 隐藏默认菜单与右上角菜单按钮 */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    button[aria-label="Open main menu"], button[title="Open main menu"], button[aria-label="Open app menu"], button[title="Open app menu"] {
        display: none !important;
    }

    /* 全宽输入控件 */
    .stTextInput>div>div>input,
    .stSelectbox>div>div>div,
    .stSlider>div,
    .stButton>button,
    .stNumberInput>div>input {
        width: 100% !important;
        min-height: 48px !important;
        font-size: 16px !important;
        color: inherit !important;
        background-color: inherit !important;
    }
    .stSelectbox>div>div>div {
        padding: 0 12px !important;
        line-height: 1.4 !important;
    }
    .stButton>button {
        min-height: 48px !important;
        width: 100% !important;
        border-radius: 12px !important;
    }

    /* 图表占满宽度，禁止横向滚动 */
    .stEcharts, .stEcharts > div {
        width: 100% !important;
        overflow-x: hidden !important;
    }
    .streamlit-expanderHeader, .stMarkdown, .stText, .stDataFrameContainer {
        word-break: break-word !important;
        white-space: normal !important;
    }

    /* 手机屏幕下强制单列布局 */
    @media (max-width: 768px) {
        .css-1lcbmhc.e1fqkh3o0, .css-1d391kg, .css-1v3fvcr, .css-1q1n0ol {
            flex-direction: column !important;
        }
        .block-container {
            padding-left: 12px !important;
            padding-right: 12px !important;
        }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# --------------------------
# 5. Streamlit主应用
# --------------------------
def main():
    # 页面配置
    st.set_page_config(
        page_title="文章词频分析工具",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    inject_mobile_style()
    st.title("📝 文章URL词频分析与可视化工具")
    st.divider()

    # 加载停用词
    stopwords = load_stopwords()

    # --------------------------
    # 输入区域（移动端优先单列布局）
    # --------------------------
    with st.container():
        url = st.text_input("请输入文章URL地址", placeholder="例如：https://www.example.com/article.html")
        min_freq_threshold = st.slider(
            "请设置低频词过滤阈值（过滤低于该频次的词汇）",
            min_value=1,
            max_value=20,
            value=2,
            step=1,
        )
        top_n = st.selectbox(
            "请选择词频排名展示数量",
            options=[10, 20, 30, 50],
            index=1,
        )
        
        # 提交按钮
        submit_btn = st.button("开始分析", type="primary")

    # --------------------------
    # 侧边栏：图表筛选（≥7种）
    # --------------------------
    st.sidebar.title("📊 图表筛选")
    chart_types = ["词云图", "柱状图", "折线图", "饼图", "雷达图", "散点图", "矩形树图", "热力图"]
    selected_chart = st.sidebar.selectbox("请选择要展示的图表", options=chart_types, index=0)
    st.sidebar.markdown(f"**当前图表：** {selected_chart}")
    st.sidebar.info("支持8种图表切换，选择后自动更新展示")

    # --------------------------
    # 分析逻辑执行
    # --------------------------

    if submit_btn and url:
        progress = 0
        render_progress(progress)
        with st.spinner("正在抓取URL文本并分析..."):
            # 1. 抓取文本
            progress = 10
            render_progress(progress)
            text_content = crawl_url_text(url)
            if not text_content:
                render_progress(0)
                st.stop()
            progress = 40
            render_progress(progress)
            # 2. 分词与词频统计
            word_count, word_freq_df = word_segment_and_count(text_content, stopwords, min_freq_threshold)
            if word_freq_df.empty:
                st.warning("分析结果为空，请降低低频词阈值或更换有效URL")
                render_progress(0)
                st.stop()
            progress = 70
            render_progress(progress)
            # 3. 提取前N个词汇
            top_word_df = word_freq_df.head(top_n).copy()
            progress = 100
            render_progress(progress)
            st.success(f"分析完成！共提取到 {len(word_freq_df)} 个有效词汇")
            st.info(f"已选择图表：{selected_chart}；展示词数：{top_n}")
            st.divider()
            # --------------------------
            # 结果展示区域
            # --------------------------
            tab1, tab2 = st.tabs(["📊 图表展示", "📈 词频排名"])
            # 标签页1：图表展示
            with tab1:
                chart = create_chart(selected_chart, word_freq_df, top_n)
                if chart:
                    st_pyecharts(chart, height="700px")
            # 标签页2：词频排名
            with tab2:
                st.subheader(f"词频排名前 {top_n} 词汇")
                st.dataframe(top_word_df, use_container_width=True)
                render_csv_download(top_word_df, filename="word_freq.csv")
                # 额外展示前20的横向柱状图（固定展示，便于查看排名）
                st.subheader("词频前20可视化排名")
                top20_df = word_freq_df.head(20)
                bar_top20 = (
                    Bar()
                    .add_xaxis(top20_df["词汇"].tolist())
                    .add_yaxis("频次", top20_df["频次"].tolist())
                    .reversal_axis()
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title="词频前20排名柱状图", pos_left="center"),
                        xaxis_opts=opts.AxisOpts(name="频次"),
                        yaxis_opts=opts.AxisOpts(name="词汇")
                    )
                )
                st_pyecharts(bar_top20, height="55vh")
        render_footer()

    elif submit_btn and not url:
        st.warning("请先输入有效的文章URL！")

if __name__ == "__main__":
    main()