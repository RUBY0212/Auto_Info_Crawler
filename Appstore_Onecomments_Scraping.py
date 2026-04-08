import urllib.request
import json
import pandas as pd
import time
import os

# ================= 配置区域 =================
APP_LINK = "https://apps.apple.com/gb/app/my-gwm/id6472026587"
COUNTRY_CODE = "gb"
APP_ID = "6472026587"
APP_NAME = "My GWM"

MAX_PAGES = 50  
OUTPUT_FILE = ".xlsx"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Accept-Language': 'en-US,en;q=0.9',
}
# ===========================================

def fetch_reviews(page=1):
    url = f"https://itunes.apple.com/{COUNTRY_CODE}/rss/customerreviews/id={APP_ID}/sortBy=mostRecent/json?page={page}"
    
    try:
        req = urllib.request.Request(url=url, headers=HEADERS)
        response = urllib.request.urlopen(req, timeout=20)
        data = response.read()
        json_data = json.loads(data.decode('utf-8'))
        
        entries = json_data.get('feed', {}).get('entry', [])
        
        reviews_on_page = []
        for node in entries:
            if 'im:rating' not in node:
                continue
                
            def get_val(item):
                return item['label'] if isinstance(item, dict) else item

            # --- 修改点：在这里提取日期 ---
            review = {
                "国家": COUNTRY_CODE.upper(),
                "App名称": APP_NAME,
                "评论标题": get_val(node['title']),
                "用户": get_val(node['author']['name']),
                "评论内容": get_val(node['content']),
                "评论时间": get_val(node['updated']), # 新增：抓取更新时间
                "URL": APP_LINK
            }
            reviews_on_page.append(review)
            
        return reviews_on_page

    except Exception as e:
        print(f"❌ 网络错误: {e}")
        return []

# ================= 主程序 =================
if __name__ == "__main__":
    all_reviews = []
    seen_fingerprints = set() 
    stop_flag = False
    
    print("🚀 开始爬取（包含评论时间）...")
    
    for page in range(1, MAX_PAGES + 1):
        if stop_flag:
            break
            
        reviews = fetch_reviews(page)
        
        if not reviews:
            print(f"🏁 第 {page} 页无数据，结束。")
            break
            
        new_count = 0
        for r in reviews:
            # 指纹去重逻辑保持不变
            fingerprint = f"{r['评论标题']}_{r['用户']}"
            
            if fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)
                all_reviews.append(r)
                new_count += 1
        
        print(f"✅ 第 {page} 页：抓到 {len(reviews)} 条，新增 {new_count} 条 (共 {len(all_reviews)})")
        
        if new_count == 0:
            print(f"🏁 数据开始重复，停止爬取。")
            stop_flag = True
            
        time.sleep(1)
    
    # ================= 写入 Excel =================
    if all_reviews:
        print("-" * 40)
        print("正在写入 Excel...")
        
        try:
            df = pd.DataFrame(all_reviews)
            
            # --- 修改点：在表头列表中加入“评论时间” ---
            columns_order = ["国家", "App名称", "评论标题", "用户", "评论内容", "评论时间", "URL"]
            
            df.to_excel(OUTPUT_FILE, index=False, columns=columns_order)
            print(f"💾 成功！共保存 {len(all_reviews)} 条带时间的评论。")
            print(f"文件位置: {os.path.abspath(OUTPUT_FILE)}")
        except PermissionError:
            print(f"❌ 写入失败：请先关闭 Excel 文件 '{OUTPUT_FILE}'！")
        except Exception as e:
            print(f"❌ 写入失败: {e}")
    else:
        print("⚠️ 没抓到数据。")
    
    input("\n按回车键退出...")