# app_fixed_final.py
import streamlit as st
import sys
import os



# 2. 添加路径（如果有需要）
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 3. 安全导入（放在页面内容之后）
HealthAssistantBot = None
try:
    from healthy_main import HealthAssistantBot

    bot_available = True
except ImportError:
    bot_available = False

# 4. 页面开始
st.title("🏃 AI Fitness")

with st.sidebar:
    st.header("📋 导航菜单")
    menu_option = st.selectbox(
        "选择功能",
        ["🏠 主页", "💬 聊天助手", "📋 健康档案", "⚖️ 记录体重"]
    )
    st.markdown("---")
    st.caption("版本 1.0 | 学习项目")

# 主页
if menu_option == "🏠 主页":
    st.header("主页")
    st.write("欢迎使用AI健康减肥助手！")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("状态", "良好", "↑")
    with col2:
        st.metric("体重", "65.0 kg", "-0.5")
    with col3:
        st.metric("BMI", "21.2", "正常")

# 聊天助手
elif menu_option == "💬 聊天助手":
    st.header("💬 聊天助手")
    st.write("我是你的健康小伙伴~")

    # 在这里才创建bot对象
    if bot_available and HealthAssistantBot:
        bot = HealthAssistantBot()
        st.success("✅ AI助手已加载")
    else:
        st.warning("⚠️ 使用模拟模式")


        class SimpleBot:
            def chat(self, msg):
                return f"模拟回复: {msg}"


        bot = SimpleBot()

    # 聊天界面
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "你好！我是你的健康教练"}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("输入消息...")
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            response = bot.chat(user_input)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

# 其他页面
elif menu_option == "📋 健康档案":
    st.header("健康档案")
    st.write("功能开发中...")

elif menu_option == "⚖️ 记录体重":
    st.header("记录体重")
    st.write("功能开发中...")

# 5. 确保Streamlit保持运行
# 这行不是必须的，但加了更明确
if __name__ == "__main__":
    pass