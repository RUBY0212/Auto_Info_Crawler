import asyncio
from twikit import Client

###########################################
# 1. 在这里填入你的推特账号信息
USERNAME = ''
EMAIL = ''
PASSWORD = ''

# 2. 在这里配置你的需求
SEARCH_KEYWORD = 'AI'   # 你想搜索的关键词
TWEET_COUNT = 10        # 你想抓取多少条推文
###########################################

client = Client('en-US')

async def main():
    print(f"正在登录账号: {USERNAME}...")
    try:
        # 登录
        await client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD
        )
        print("✅ 登录成功！\n")
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return

    print(f"正在搜索关键词: '{SEARCH_KEYWORD}' 的最新推文...\n")
    
    try:
        # 搜索最新推文 (Product='Latest' 表示按时间排序的最新结果)
        tweets = await client.search_tweet(SEARCH_KEYWORD, product='Latest')
        
        count = 0
        # 遍历抓取到的推文
        for tweet in tweets:
            if count >= TWEET_COUNT:
                break
                
            count += 1
            # 输出结果
            print(f"--- 第 {count} 条推文 ---")
            print(f"作者: {tweet.user.name}")
            print(f"内容: {tweet.text}")
            print(f"时间: {tweet.created_at}")
            print("-" * 30)

        if count == 0:
            print("⚠️ 未搜索到相关推文。")
            
    except Exception as e:
        print(f"❌ 搜索出错: {e}")

# 运行程序
asyncio.run(main())