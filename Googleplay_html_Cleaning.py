import dashscope
import pandas as pd
import json
import os
import requests
from io import BytesIO
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils import get_column_letter

# ================= 配置区域 =================

# 1. API Key
dashscope.api_key = '' # 请填入你的 Key

# 2. 输入输出配置
# 假设你的 HTML 文件是本地路径
input_html_path = r'C:\Users\.html' 
output_excel_path = 'Qwen_Analysis_With_Images.xlsx'

# 3. 提示词 (针对多模态模型优化)
# 注意：这里我们要求模型提取图片链接，而不是直接生成图片
custom_prompt = """
你是一个专业的数据提取专家。请阅读我提供的 HTML 内容（或文本描述），完成以下任务：

任务目标：
1. 提取页面中的核心文本信息（标题、正文、价格、参数等）。
2. 提取页面中所有关键图片的 URL 链接（img 标签的 src 属性）。
3. 对提取的内容进行分类整理。

输出要求：
请以 JSON 格式输出，包含两个主要部分：
- "text_data": 一个列表，包含提取的文本信息，每个元素包含 {"分类": "...", "内容": "..."}。
- "images": 一个列表，包含提取到的图片 URL 链接。

注意：
- 忽略导航栏、页脚等无关信息。
- 图片链接必须是完整的 http/https 链接。如果是相对路径，请尝试补全（如果无法补全则忽略）。
- 确保 JSON 格式合法。
"""

# ================= 辅助函数 =================

def download_image(url):
    """下载图片并返回二进制流"""
    try:
        # 加上 User-Agent 防止部分网站防盗链
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return BytesIO(response.content)
    except Exception as e:
        print(f"   ⚠️ 图片下载失败 {url}: {e}")
    return None

def insert_image_to_excel(ws, img_stream, row_idx, col_idx, width=200, height=150):
    """将图片插入到 Excel 指定单元格"""
    try:
        # 使用 openpyxl 的 Image 对象
        img = OpenpyxlImage(img_stream)
        
        # 设置图片尺寸 (可选，或者保持原尺寸)
        img.width = width
        img.height = height
        
        # 这里的 anchor 决定了图片放在哪个单元格 (例如 "C2")
        col_letter = get_column_letter(col_idx)
        anchor_cell = f"{col_letter}{row_idx}"
        
        ws.add_image(img)
        # 注意：add_image 默认是浮动在单元格上方的，如果需要严格嵌入单元格需要更复杂的设置
        # 这里使用默认浮动模式，视觉上看起来像是在单元格里
        
        # 调整列宽行高以适应图片
        ws.column_dimensions[col_letter].width = width / 6  # 粗略估算
        ws.row_dimensions[row_idx].height = height * 0.75
        
    except Exception as e:
        print(f"   ⚠️ 图片插入失败: {e}")

# ================= 主程序逻辑 =================

def main():
    print("--- 程序开始运行 ---")
    
    # 第一步：读取 HTML 文件
    print(f"正在读取文件: {input_html_path}")
    try:
        with open(input_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        if not html_content.strip():
            print("❌ 错误：文件内容为空！")
            return
            
        print(f"✅ 文件读取成功，内容长度: {len(html_content)} 字符")
        
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return

    # 第二步：调用 Qwen API
    # 注意：这里我们直接把 HTML 文本作为 Prompt 发送
    # 如果 HTML 中包含 <img> 标签，Qwen 能够理解这些标签的语义
    print("正在连接 Qwen 进行分析...")
    
    try:
        response = dashscope.Generation.call(
            model='qwen-plus', # 或者 qwen-turbo, qwen-max
            prompt=f"{custom_prompt}\n\nHTML 内容如下:\n{html_content}",
            timeout=60
        )
        
        if response.status_code == 200:
            ai_result_text = response.output.text
            print("✅ AI 分析完成，正在解析 JSON...")
        else:
            print(f"❌ API 调用失败: {response.code} - {response.message}")
            return
            
    except Exception as e:
        print(f"❌ 调用 API 时发生异常: {e}")
        return

    # 第三步：解析 JSON
    data_dict = {}
    try:
        # 简单的 JSON 清洗
        json_start = ai_result_text.find('{')
        json_end = ai_result_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = ai_result_text[json_start:json_end]
            data_dict = json.loads(json_str)
        else:
            print("❌ 无法提取 JSON 数据。")
            return
    except json.JSONDecodeError:
        print("❌ JSON 解析失败。")
        print(ai_result_text[:500])
        return

    # 第四步：写入 Excel 并插入图片
    print("正在生成 Excel 文件...")
    wb = Workbook()
    ws = wb.active
    ws.title = "分析结果"
    
    # 写入表头
    ws.append(["分类", "内容", "图片预览"])
    
    # 1. 先写入文本数据
    current_row = 2
    text_data = data_dict.get("text_data", [])
    for item in text_data:
        ws.cell(row=current_row, column=1, value=item.get("分类", ""))
        ws.cell(row=current_row, column=2, value=item.get("内容", ""))
        current_row += 1
        
    print(f"   - 已写入 {len(text_data)} 条文本数据")

    # 2. 处理图片
    images = data_dict.get("images", [])
    print(f"   - 发现 {len(images)} 张图片，正在下载并插入...")
    
    # 为了防止图片太多把 Excel 撑爆，我们限制插入前 5 张关键图片
    # 或者你可以选择把图片放在对应的文本行旁边（这需要更复杂的逻辑匹配）
    # 这里演示简单的：把所有图片按顺序插入到表格下方
    
    img_start_row = current_row + 2
    ws.cell(row=img_start_row, column=1, value="--- 提取的图片 ---")
    
    for i, img_url in enumerate(images):
        if i >= 5: break # 限制最多 5 张，防止运行太慢
        
        print(f"   正在处理图片 {i+1}: {img_url}")
        img_stream = download_image(img_url)
        
        if img_stream:
            # 插入图片到第 (img_start_row + i) 行，第 1 列
            insert_image_to_excel(ws, img_stream, img_start_row + i, 1)
            ws.cell(row=img_start_row + i, column=2, value=img_url) # 顺便把链接也写下来
    
    # 保存文件
    try:
        wb.save(output_excel_path)
        print(f"\n🎉 成功！文件已保存至: {output_excel_path}")
        print("注意：图片是以浮动形式插入的，如果调整单元格大小，图片可能不会自动缩放。")
    except Exception as e:
        print(f"❌ 保存 Excel 失败: {e}")

if __name__ == '__main__':
    main()
    input("\n按回车键退出程序...")