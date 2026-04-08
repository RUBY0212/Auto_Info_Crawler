import urllib.request
import json
import pandas as pd
import time
import os
import re

# ================= 配置区域 =================
MAX_PAGES = 50  
OUTPUT_FILE = ".xlsx"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Accept-Language': 'en-US,en;q=0.9',
}
# ===========================================

def parse_apple_link(link):
    """
    从链接中提取 国家代码 和 App ID
    例如: https://apps.apple.com/pk/app/.../id12345 -> ('pk', '12345')
    """
    link = link.strip()
    if not link:
        return None, None
        
    try:
        # 1. 提取国家代码 (域名后的第一个路径，通常是两个字母)
        country_match = re.search(r'apps\.apple\.com/([a-z]{2})/', link)
        country_code = country_match.group(1) if country_match else "us" # 默认us
        
        # 2. 提取 App ID (id后面的数字)
        id_match = re.search(r'/id(\d+)', link)
        app_id = id_match.group(1) if id_match else None
        
        return country_code, app_id
    except:
        return None, None

def fetch_reviews(app_id, country_code, app_name):
    all_reviews = []
    seen_user_ids = set() # 使用用户ID来去重，更精准
    stop_flag = False
    
    print(f"   🚀 正在爬取 [{country_code.upper()}] 区: {app_name} ...")
    
    for page in range(1, MAX_PAGES + 1):
        if stop_flag:
            break
            
        url = f"https://itunes.apple.com/{country_code}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json?page={page}"
        
        try:
            req = urllib.request.Request(url=url, headers=HEADERS)
            response = urllib.request.urlopen(req, timeout=20)
            data = response.read()
            json_data = json.loads(data.decode('utf-8'))
            
            entries = json_data.get('feed', {}).get('entry', [])
            
            if not entries:
                break
                
            new_count = 0
            for node in entries:
                if 'im:rating' not in node:
                    continue
                    
                def get_val(item):
                    return item['label'] if isinstance(item, dict) else item

                # --- 修改点：使用用户ID去重 ---
                # Apple 接口中，author 对象里通常包含 'uri' 字段，格式如 "https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewCustomer?id=123456"
                # 我们提取这个 ID 作为唯一标识
                author_node = node['author']
                user_uri = get_val(author_node.get('uri', ''))
                # 简单提取 uri 最后的数字作为 user_id，如果没有 uri 则用名字代替
                user_id_match = re.search(r'id=(\d+)', user_uri)
                unique_user_id = user_id_match.group(1) if user_id_match else get_val(author_node['name'])
                
                if unique_user_id not in seen_user_ids:
                    seen_user_ids.add(unique_user_id)
                    
                    review = {
                        "国家": country_code.upper(),
                        "App名称": app_name,
                        "评论标题": get_val(node['title']),
                        "用户": get_val(author_node['name']),
                        "评论内容": get_val(node['content']),
                        "评论时间": get_val(node['updated']),
                        "URL": f"https://apps.apple.com/{country_code}/app/id{app_id}"
                    }
                    all_reviews.append(review)
                    new_count += 1
            
            if new_count == 0:
                stop_flag = True
            
            if page > 1:
                 print(f"   ...第 {page} 页 (新增 {new_count})")
            
            time.sleep(1) 
            
        except Exception as e:
            print(f"   ❌ 网络错误: {e}")
            break
            
    print(f"   ✅ 完成，共抓取 {len(all_reviews)} 条。")
    return all_reviews

# ================= 主程序交互 =================
if __name__ == "__main__":
    print("👋 欢迎使用批量评论爬取工具")
    print("请粘贴 App Store 链接（每行一个），输入完成后直接按回车（或 Ctrl+D/Z）：")
    
    links_input = []
    try:
        while True:
            line = input()
            if line:
                links_input.append(line)
            else:
                break
    except EOFError:
        pass

    if not links_input:
        print("⚠️ 没有输入链接，退出。")
        exit()

    final_data = []

    for link in links_input:
        # 1. 解析链接
        country_code, app_id = parse_apple_link(link)
        
        if not app_id:
            print(f"⚠️ 无法解析链接: {link}，跳过。")
            continue
            
        app_name = f"App_{app_id}" 
        
        print("-" * 30)
        print(f"🔗 处理: {link}")
        print(f"🌍 识别到 -> 国家: {country_code}, ID: {app_id}")
        
        # 2. 爬取
        reviews = fetch_reviews(app_id, country_code, app_name)
        final_data.extend(reviews)
        
        time.sleep(2) 

    # ================= 写入 Excel =================
    if final_data:
        print("=" * 40)
        print("正在合并写入 Excel...")
        try:
            df = pd.DataFrame(final_data)
            # 再次去重保险
            df.drop_duplicates(subset=['用户', '评论内容'], inplace=True)
            
            columns_order = ["国家", "App名称", "评论标题", "用户", "评论内容", "评论时间", "URL"]
            df.to_excel(OUTPUT_FILE, index=False, columns=columns_order)
            
            print(f"💾 成功！共保存 {len(df)} 条不重复评论。")
            print(f"文件位置: {os.path.abspath(OUTPUT_FILE)}")
        except PermissionError:
            print(f"❌ 写入失败：请先关闭 Excel 文件 '{OUTPUT_FILE}'！")
        except Exception as e:
            print(f"❌ 写入失败: {e}")
    else:
        print("⚠️ 没抓到任何数据。")
    
    input("\n按回车键退出...")