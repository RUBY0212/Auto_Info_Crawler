import pandas as pd
import dashscope
from dashscope import Generation
import os

# ==========================================
# 1. 配置部分
# ==========================================
# 👇 在这里填入你的 API Key
api_key = "" 

if not api_key or api_key == "sk-这里填入你的密钥":
    print("错误：请先在代码中填入有效的 API Key")
    exit()

dashscope.api_key = api_key
MODEL_NAME = 'qwen-plus-2025-07-28'
INPUT_FILE = r'C:\Users\.xlsx'

# ==========================================
# 2. 辅助函数
# ==========================================
def call_ai(messages):
    """封装好的 AI 调用函数，负责发送消息并接收回复"""
    try:
        response = Generation.call(
            model=MODEL_NAME,
            messages=messages,
            result_format='message'
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            return f"Error: {response.code} - {response.message}"
    except Exception as e:
        return f"Exception: {str(e)}"

def load_data(file_path):
    """读取 Excel 文件"""
    print(f"正在读取文件: {file_path} ...")
    try:
        df = pd.read_excel(file_path)
        if '评论内容' not in df.columns:
            print("错误：Excel 中必须包含 '评论内容' 列")
            return None
        return df
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None

# ==========================================
# 3. 主程序入口 (交互式)
# ==========================================
if __name__ == '__main__':
    # 1. 加载数据
    df = load_data(INPUT_FILE)

    if df is not None:
        # 2. 准备数据
        comments_list = df['评论内容'].tolist()
        # 防止太长，这里限制前 500 条作为上下文（你可以根据需要调整）
        max_lines = min(500, len(comments_list))
        comments_str = "\n".join([f"- {c}" for c in comments_list[:max_lines]])

        print(f"已加载 {len(df)} 条评论，选取前 {max_lines} 条作为分析基础。")

        # 3. 初始化“记忆”列表 (System Prompt + 数据)
        # 这一步很关键：我们把数据作为“第一条用户消息”发给 AI
        messages = [
            {'role': 'system', 'content': '''你是一位拥有跨国产品经验的资深APP产品经理和数据分析师。我将提供一份包含某APP在不同国家用户评论的Excel数据。请严格按照以下步骤进行深度分析，并生成一份专业的产品分析报告：
                ### 第一步：多语言预处理
                1. 识别数据中的语言类型（如英语、阿拉伯语、西班牙语等）。
                2. **精准翻译**：在分析前，请确保准确理解非英语评论的语义，不要因翻译错误导致分析偏差。

                ### 第二步：分区域洞察
                请根据数据中的“国家”字段，分析不同市场的表现差异：
                1. **核心市场表现**：主要国家的用户主要讨论什么？
                2. **地域性差异**：特定地区是否有特有的问题（例如：某些功能在特定语言环境下无法使用，或特定地区的文化禁忌）？

                ### 第三步：核心问题深挖（重点）
                请忽略表面的赞美，重点挖掘负面反馈，归纳为以下三类：
                1. **用户痛点**：用户在使用APP时最感到沮丧、不便或无法完成的目标是什么？（例如：注册流程繁琐、广告过多、找不到功能入口）。
                2. **APP缺陷**：具体的技术BUG或功能缺失（例如：闪退、卡顿、黑屏、无法登录、支付失败）。
                3. **待改进点**：用户明确提出的建议或竞品对比中显露的短板（例如：UI设计过时、缺少深色模式、客服响应慢）。

                ### 第四步：总结与建议
                基于以上分析，为产品团队提供3-5条高优先级的改进建议。

                ---
                **输出格式要求**：
                - 先针对各个国家按照上述步骤进行分析，每个国家输出一段分析，要求每个国家的问题必须分析详尽，不能有遗漏，最后输出总结。
                - 请使用Markdown格式输出，结构清晰，重点内容加粗。
                - 在列举缺陷时，请尽量引用（翻译后的）典型用户原话作为佐证。
                - 禁止扭曲，编造用户评论，一切分析必须基于用户的真实数据。
                - 保持客观、专业的分析口吻。
                - 不要根据语言来区分国家，不要编造国家，编造评论。
                - 输出的分析需用中文，可以引用用户外语的评论，但引用后需要翻译或者解释。'''},
            {'role': 'user', 'content': f"这是用户评论数据：\n{comments_str}"}
        ]

        # 4. 进行第一次分析
        print("-" * 30)
        print("正在生成初始分析报告...")
        first_response = call_ai(messages)
        
        # 把 AI 的回答也存入记忆
        messages.append({'role': 'assistant', 'content': first_response})

        print("\n📊 初始分析结果：")
        print("=" * 40)
        print(first_response)
        print("=" * 40)

        # 5. 进入交互循环
        print("\n👋 现在你可以对我进行追问了（输入 'quit' 退出）：")
        
        while True:
            try:
                # 获取用户输入
                user_input = input("\n👉 请输入你的要求: ")

                # 退出条件
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见！")
                    break
                
                if not user_input.strip():
                    continue

                # 把用户的新要求加入记忆
                messages.append({'role': 'user', 'content': user_input})

                # 调用 AI
                print("正在思考...")
                response = call_ai(messages)

                # 把 AI 的新回答加入记忆
                messages.append({'role': 'assistant', 'content': response})

                # 打印结果
                print("\n🤖 AI 回复:")
                print("-" * 40)
                print(response)
                print("-" * 40)

            except KeyboardInterrupt:
                print("\n\n程序被用户强制中断。")
                break