# -*- coding: utf-8 -*-
import os
import time
import random
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

# 引入 Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# ==========================================
# ⚙️ 1. 全局配置 (保持 v45.0 原味)
# ==========================================
PROJECT_NAME = "Smart_Crawler_v46_Playwright"
OUTPUT_DIR = f"./{PROJECT_NAME}_Output"

MAX_FILE_SIZE_KB = 80000
TASK_TIME_LIMIT = 900 
MAX_PAGES_PER_TASK = 300
MAX_DEPTH = 3

# 保持英文关键词，这是 v45.0 的精髓
KEYWORDS = ['manual', 'warranty', 'brochure', 'guide', 'owner', 'specification', 'price', 'feature', 'download', 'pdf', 'service', 'book', 'suv', 'model', 'contact', 'login', 'car', 'auto', 'vehicle']

STATIC_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp', '.mp4', '.mp3', '.zip', '.rar', '.css', '.js', '.woff', '.ttf', '.xml', '.json')
DOCUMENT_EXTENSIONS = ('.pdf',)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

# ==========================================
# 💾 2. 安全写入器 (保持 v45.0 原味)
# ==========================================
class SafeWriter:
    def __init__(self, task_name, start_url, mode_tag):
        self.task_name = re.sub(r'[^a-zA-Z0-9]', '_', task_name)[:50]
        self.date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        self.current_part = 1
        self.current_file = None
        self.current_size = 0
        self.max_size_bytes = MAX_FILE_SIZE_KB * 1024
        self.total_count = 0
        self.mode_tag = mode_tag
        
        self._open_new_file()
        self._write_header(start_url, mode_tag)

    def _get_filename(self):
        suffix = "" if self.current_part == 1 else f"_Part{self.current_part:03d}"
        rescue_tag = "_RESCUE" if self.mode_tag == 'Dynamic_Rescue' else ""
        return os.path.join(OUTPUT_DIR, f"{PROJECT_NAME}_{self.task_name}{rescue_tag}_{self.date_str}{suffix}.txt")

    def _open_new_file(self):
        if self.current_file:
            self.current_file.close()
        path = self._get_filename()
        self.current_file = open(path, 'w', encoding='utf-8')
        self.current_size = 0
        print(f"      📝 文件: {os.path.basename(path)}")

    def _write_header(self, start_url, mode_tag):
        header = f"\n{'='*60}\n[SYSTEM] PHASE: {mode_tag.upper()}\nTime: {datetime.now().isoformat()}\nTarget: {start_url}\n{'='*60}\n"
        self.current_file.write(header)
        self.current_file.flush()
        self.current_size += len(header.encode('utf-8'))

    def write(self, content_type, url, title, content=""):
        self.total_count += 1
        ts = datetime.now().strftime("%H:%M:%S")
        block = f"\n{'-'*60}\n[{ts}] {content_type}\nURL: {url}\nTITLE: {title}\n"
        if content:
            clean_content = content[:1500] + "\n...(truncated)" if len(content) > 1500 else content
            block += f"CONTENT:\n{clean_content}\n"
        block += f"{'-'*60}\n"
        
        data = block.encode('utf-8')
        if self.current_size + len(data) > self.max_size_bytes:
            print(f"      ⚠️ 分卷...")
            self.current_part += 1
            self._open_new_file()
            self._write_header(f"Part {self.current_part}", self.mode_tag)
            
        self.current_file.write(block)
        self.current_file.flush()
        self.current_size += len(data)

    def close(self):
        if self.current_file:
            footer = f"\n{'='*60}\n[END] Total Saved: {self.total_count}\n{'='*60}\n"
            self.current_file.write(footer)
            self.current_file.flush()
            self.current_file.close()
            print(f"      ✅ 本阶段完成，保存 {self.total_count} 条。")
    
    def get_count(self):
        return self.total_count

# ==========================================
# 🧠 3. 智能爬虫 (v46.0 - Playwright 核心版)
# ==========================================
class AdaptiveCrawler:
    def __init__(self):
        self.keywords = [k.lower() for k in KEYWORDS]
        self.playwright = None
        self.browser = None
        self.driver_failed = False

    def init_driver(self):
        """初始化 Playwright 浏览器"""
        if self.browser: return True
        if self.driver_failed or not PLAYWRIGHT_AVAILABLE: return False
        
        print("\n🔄 [补救阶段] 启动 Playwright 浏览器...")
        try:
            self.playwright = sync_playwright().start()
            # 启动浏览器
            self.browser = self.playwright.chromium.launch(
                headless=False, # 可见模式，方便观察
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            
            print("✅ 浏览器启动成功。")
            return True
        except Exception as e:
            print(f"❌ 浏览器启动失败: {e}")
            self.driver_failed = True
            return False

    def fetch_static(self, url):
        """静态抓取逻辑 (保持不变)"""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=5)
            if resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True).lower()
            
            if len(text) < 20:
                return None
            
            links_count = 0
            base_netloc = urlparse(url).netloc
            for a in soup.find_all('a', href=True):
                href = a['href'].split('#')[0]
                if href and not href.startswith(('mailto', 'tel', 'javascript')):
                    full_url = urljoin(url, href)
                    if urlparse(full_url).netloc == base_netloc:
                        links_count += 1
            
            return soup, text, links_count
        except Exception:
            return None

    def fetch_dynamic(self, url):
        """
        动态抓取逻辑 (替换为 Playwright)
        保留 v45.0 的核心：等待 -> 抓取 -> 提取
        """
        if not self.init_driver():
            return None
        
        try:
            # 创建新上下文和页面
            context = self.browser.new_context(
                user_agent=HEADERS['User-Agent'],
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # 注入脚本隐藏特征 (Playwright 方式)
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """)

            print("      ⏳ 正在加载页面...")
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # 模拟 v45.0 的等待逻辑，给 JS 渲染时间
            # 这里可以优化为等待特定元素，但为了通用性，先保持简单等待
            page.wait_for_timeout(5000) 
            
            print("      ✅ 页面加载完成，正在提取 HTML...")
            html = page.content()
            
            # 关闭当前页面，释放内存
            page.close()
            context.close()

            if not html or len(html) < 100:
                return None

            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True).lower()
            
            if len(text) < 20:
                return None

            # 统计子链接 (保持 v45.0 逻辑)
            links_count = 0
            base_netloc = urlparse(url).netloc
            for a in soup.find_all('a', href=True):
                href = a['href'].split('#')[0]
                if href and not href.startswith(('mailto', 'tel', 'javascript')):
                    full_url = urljoin(url, href)
                    if urlparse(full_url).netloc == base_netloc:
                        links_count += 1
            
            return soup, text, links_count
            
        except Exception as e:
            err_msg = str(e)
            print(f"\n      ⚠️ 抓取异常: {err_msg[:60]}... (已跳过)")
            return None

    def run_task_phase(self, start_url, force_dynamic=False):
        """
        核心任务逻辑 (完全保留 v45.0 的队列遍历机制)
        """
        base_domain = urlparse(start_url).netloc
        task_name = base_domain.replace('www.', '').split('.')[0]
        mode_tag = "Dynamic_Rescue" if force_dynamic else "Static_Scan"
        
        print(f"\n--- 阶段: {mode_tag} ---")
        print(f"🔗 {start_url}")
        
        writer = SafeWriter(task_name, start_url, mode_tag)
        
        visited = set()
        queue = [(start_url, 0)] # (url, depth)
        start_time = time.time()
        count = 0
        empty_streak = 0
        
        # --- 广度优先遍历核心循环 ---
        while queue:
            if time.time() - start_time > TASK_TIME_LIMIT: 
                print("\n⏰ 时间到。")
                break
            if count >= MAX_PAGES_PER_TASK: 
                break
            if count > 30 and empty_streak > 100: 
                break

            current_url, depth = queue.pop(0)
            
            # 过滤逻辑
            if current_url in visited: continue
            if urlparse(current_url).netloc != base_domain: continue
            if any(current_url.endswith(ext) for ext in STATIC_EXTENSIONS): continue
            # 简单的日期路径过滤
            if re.search(r'/\d{4}/\d{2}/\d{2}', current_url): 
                visited.add(current_url); continue

            visited.add(current_url)
            count += 1
            
            if count % 5 == 0: 
                icon = "🌐" if force_dynamic else "⚡"
                print(f"   {icon} 进度: {count} | 有效: {writer.total_count}")

            soup = None
            text_content = ""
            link_count = 0
            success = False

            # 选择抓取方式
            if force_dynamic:
                res = self.fetch_dynamic(current_url)
                if res:
                    soup, text_content, link_count = res
                    success = True
            else:
                res = self.fetch_static(current_url)
                if res:
                    soup, text_content, link_count = res
                    success = True

            if not success:
                empty_streak += 1
                continue
            
            empty_streak = 0
            
            title = soup.title.string.strip() if soup.title else "No Title"
            
            # PDF 直接保存
            if current_url.endswith(DOCUMENT_EXTENSIONS):
                writer.write('PDF', current_url, os.path.basename(current_url))
                continue

            saved = False
            # 内容筛选逻辑 (保持 v45.0)
            # 1. 检查关键词
            has_keyword = any(k in text_content for k in self.keywords)
            
            # 2. 提取主要内容
            if has_keyword or force_dynamic: # 动态模式下放宽条件，或者只保存有内容的
                 # 提取 p, h1-h3, li 标签，且长度大于20
                content_parts = []
                for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']):
                    txt = tag.get_text(strip=True)
                    if len(txt) > 20:
                        content_parts.append(txt)
                
                content = " ".join(content_parts)
                
                if content:
                    writer.write('HTML', current_url, title, content)
                    saved = True
            
            # 更新空连击计数
            if link_count > 0:
                empty_streak = 0
            elif not saved:
                empty_streak += 1

            # 将新链接加入队列 (广度优先)
            if depth < MAX_DEPTH and link_count > 0:
                links = soup.find_all('a', href=True)
                for a in links:
                    href = a['href'].split('#')[0]
                    if not href or href.startswith(('mailto', 'tel', 'javascript')): continue
                    new_url = urljoin(current_url, href)
                    if new_url not in visited and urlparse(new_url).netloc == base_domain:
                        queue.append((new_url, depth + 1))

        writer.close()
        return writer.get_count()

    def run(self):
        print("🤖 智能爬虫 v46.0 (Playwright 核心版)")
        print("✨ 策略: 先静态全量扫描 -> 失败项动态补救 -> 最终失败项记录")
        
        urls = []
        print("\n请输入链接 (输入 'done' 开始):")
        while True:
            try:
                u = input(f"> [{len(urls)+1}] ").strip()
            except EOFError: break
            if not u or u.lower() == 'done': break
            if u.startswith('http'): urls.append(u)
            
        if not urls: return

        print(f"\n📋 共 {len(urls)} 个任务。开始 Phase 1 (静态扫描)...\n")
        
        failed_tasks = []

        # --- Phase 1: 静态扫描 ---
        try:
            for i, url in enumerate(urls, 1):
                count = self.run_task_phase(url, force_dynamic=False)
                if count == 0:
                    print(f"   ⚠️ 任务 [{i}] 静态结果为 0，标记为需补救。")
                    failed_tasks.append(url)
                if i < len(urls): time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断 Phase 1。")

        # --- Phase 2: 动态补救 ---
        if failed_tasks:
            print(f"\n{'='*60}")
            print(f"🚨 Phase 1 结束。发现 {len(failed_tasks)} 个任务结果为 0。")
            print(f"🚀 启动 Phase 2: Playwright 动态补救模式...")
            print(f"{'='*60}\n")
            
            final_failures = []
            
            try:
                for i, url in enumerate(failed_tasks, 1):
                    print(f"\n[补救 {i}/{len(failed_tasks)}] {url}")
                    count = self.run_task_phase(url, force_dynamic=True)
                    
                    if count == 0:
                        print(f"   ❌ 即使使用了浏览器，该任务依然失败。记录到失败名单。")
                        final_failures.append(url)
                        
                    if i < len(failed_tasks): time.sleep(1)
            except KeyboardInterrupt:
                print("\n⚠️ 用户中断 Phase 2。")
            
            # --- Phase 3: 记录最终失败 ---
            if final_failures:
                self.save_final_failures(final_failures)
            else:
                print("\n🎉 太棒了！所有失败任务在 Phase 2 中均已抢救成功。")
        else:
            print("\n🎉 太棒了！所有任务在静态阶段均已成功，无需补救。")

        # 关闭浏览器
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            print("🔒 浏览器已关闭。")
        
        print("\n🏁 全部流程结束！")

    def save_final_failures(self, failures):
        print(f"\n📝 正在生成最终失败报告...")
        filename = os.path.join(OUTPUT_DIR, f"Failed_Records_{datetime.now().strftime('%Y%m%d')}.txt")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("以下链接经过静态和动态尝试后，依然无法获取数据：\n")
            f.write("-" * 60 + "\n")
            for url in failures:
                f.write(f"{url}\n")
        print(f"✅ 失败报告已保存至: {filename}")

if __name__ == "__main__":
    AdaptiveCrawler().run()