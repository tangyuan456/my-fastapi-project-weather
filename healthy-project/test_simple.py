import streamlit as st
st.set_page_config(page_title="测试2")
st.title("测试2: 导入healthy_main")

import sys
import os
sys.path.append(".")

try:
    from healthy_main import HealthAssistantBot
    st.success("✅ 导入成功")
    st.write("继续下一步...")
except Exception as e:
    st.error(f"❌ 导入失败: {e}")
    import traceback
    st.code(traceback.format_exc())