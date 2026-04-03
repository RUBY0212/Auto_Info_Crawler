import dashscope
import pandas as pd
import json
import time
from tqdm import tqdm

# ================= 配置区域 =================

# 1. 在这里填入你的 API Key
dashscope.api_key = 'sk-fa157927b8e24a2aa5767e906140b8aa'

# 2. 在这里修改你的 Prompt
# 注意：我特意在结尾加了一句“请以 JSON 格式输出”，这对生成 Excel 至关重要
custom_prompt = """
你是一个专业的汽车数据结构化专家。请读取数据，精准的将数据整理成表格：

表1：车型核心信息表
- 列：车型系列 (Series)、具体型号 (Model)、年份 (如有)、指导价 (Price)、引擎规格 (Engine)、马力 (HP)、变速箱 (Transmission)、驱动形式 (Drive)、燃油经济性 (Fuel Economy)、车身尺寸 (Dimensions)。
- 要求：尽可能补全参数，如果原文未提及则填“未说明”。

表2：下载资源与链接表
- 列：关联车型、资源类型 (如：Brochure, Owner Manual, Warranty Guide)、下载链接 (完整URL)。
- 要求：提取所有 .pdf 链接，确保链接可点击。

表3：车联网与科技功能表
- 列：车型、功能名称 (如：Toyota Safety Sense, App Connect)、功能详细描述、是否标配/选配。
- 要求：详细总结智能驾驶辅助、娱乐系统、远程控制等功能。

表4：常见问题 (FAQ)
- 列：问题 (Question)、答案 (Answer)、所属分类 (如：售后、技术、购车)。
- 要求：提取所有问答对，保持原意。

注意：
- 忽略网站导航、页脚、版权信息等噪音
- 价格请保留货币单位
- 如果某些信息在不同页面有冲突，以车型详情页为准
- 输出格式必须为清晰的表格
- 输出的信息记得标注数据源url

【重要】为了程序能自动处理，请务必将上述四个表的内容以标准的 JSON 格式返回，键名分别为 table1, table2, table3, table4。
"""

# 3. 输入和输出文件名配置
input_file_path = r'D:\Softinstall\python313\Notepad++\Smart_Crawler_v46_Playwright_Output\Smart_Crawler_v46_Playwright_bmw_pakistan_20260331_085927.txt'
output_excel_path = 'BMW_Analysis_Result.xlsx'

# ================= 主程序逻辑 =================

def main():
    print("--- 程序开始运行 ---")
    
    # 第一步：读取文件
    print(f"正在读取文件: {input_file_path}")
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            raw_data = f.read()
        
        if not raw_data.strip():
            print("❌ 错误：读取到的文件内容为空！请检查文件路径。")
            return
            
        print(f"✅ 文件读取成功，内容长度: {len(raw_data)} 字符")
        
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return

    # 第二步：调用 Qwen API
    print("正在连接 Qwen-Plus 进行分析 (这可能需要几十秒)...")
    
    # 模拟进度条，防止界面看起来卡死
    with tqdm(total=100, desc="AI 思考中") as pbar:
        try:
            # 构造发送给 AI 的完整提示词
            full_prompt = f"{custom_prompt}\n\n待分析数据如下:\n{raw_data}"
            
            response = dashscope.Generation.call(
                model='qwen-plus',
                prompt=full_prompt,
                timeout=60  # 设置60秒超时，防止无限卡住
            )
            
            pbar.update(50) # 进度条走一半
            
            if response.status_code == 200:
                pbar.update(50) # 进度条走完
                ai_result_text = response.output.text
                print("✅ AI 分析完成，正在解析数据...")
            else:
                print(f"❌ API 调用失败: {response.code} - {response.message}")
                return
                
        except Exception as e:
            print(f"❌ 调用 API 时发生异常: {e}")
            return

    # 第三步：解析 JSON 并写入 Excel
    print("正在生成 Excel 文件...")
    
    try:
        # 尝试将 AI 返回的文本解析为 JSON
        # 有时候 AI 会在 JSON 前后加废话，这里做一个简单的清洗（实际使用中如果 AI 稳定可不加）
        json_start = ai_result_text.find('{')
        json_end = ai_result_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = ai_result_text[json_start:json_end]
            data_dict = json.loads(json_str)
        else:
            print("❌ 无法从 AI 返回结果中提取 JSON 数据。")
            print("AI 返回内容预览:", ai_result_text[:200])
            return

        # 使用 pandas 写入 Excel
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            
            # 写入表1
            if 'table1' in data_dict:
                df1 = pd.DataFrame(data_dict['table1'])
                df1.to_excel(writer, sheet_name='表1_车型核心信息', index=False)
                print("  - 已写入 [表1_车型核心信息]")
            else:
                print("  - ⚠️ 未找到 [表1] 数据")

            # 写入表2
            if 'table2' in data_dict:
                df2 = pd.DataFrame(data_dict['table2'])
                df2.to_excel(writer, sheet_name='表2_下载资源', index=False)
                print("  - 已写入 [表2_下载资源]")
            else:
                print("  - ⚠️ 未找到 [表2] 数据")

            # 写入表3
            if 'table3' in data_dict:
                df3 = pd.DataFrame(data_dict['table3'])
                df3.to_excel(writer, sheet_name='表3_科技功能', index=False)
                print("  - 已写入 [表3_科技功能]")
            else:
                print("  - ⚠️ 未找到 [表3] 数据")

            # 写入表4
            if 'table4' in data_dict:
                df4 = pd.DataFrame(data_dict['table4'])
                df4.to_excel(writer, sheet_name='表4_常见问题', index=False)
                print("  - 已写入 [表4_常见问题]")
            else:
                print("  - ⚠️ 未找到 [表4] 数据")

        print(f"\n🎉 成功！所有数据已保存至: {output_excel_path}")

    except json.JSONDecodeError:
        print("❌ 错误：AI 返回的数据格式不是标准的 JSON，无法生成 Excel。")
        print("请检查 Prompt 是否要求 AI 输出 JSON 格式。")
        # 打印前500个字符用于调试
        print("AI 返回片段:", ai_result_text[:500])
    except Exception as e:
        print(f"❌ 写入 Excel 时出错: {e}")

if __name__ == '__main__':
    main()
    # 防止窗口闪退
    input("\n按回车键退出程序...")