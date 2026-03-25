import requests
import re
import time
from collections import defaultdict
from datetime import datetime
import concurrent.futures

# ========== 配置参数 ==========
SOURCE_URL = "https://raw.githubusercontent.com/gclgg/zubo/refs/heads/main/IPTV.txt"
OUTPUT_FILE = "zubo_iptv_sorted.m3u"
MAX_WORKERS = 15
CONNECT_TIMEOUT = 8
STABILITY_TEST_DURATION = 5
MIN_SPEED_KBPS = 500

# Logo仓库配置
LOGO_REPO_OWNER = "gclgg"
LOGO_REPO_NAME = "live"
LOGO_PATH_IN_REPO = "tv"
LOGO_BASE_URL = f"https://raw.githubusercontent.com/{LOGO_REPO_OWNER}/{LOGO_REPO_NAME}/main/{LOGO_PATH_IN_REPO}"

# 频道分类排序规则
CHANNEL_CATEGORIES = {
    "CCTV": 1,
    "卫视": 2,
    "数字": 3,
    "其他": 99,
}

# CCTV频道顺序
CCTV_ORDER = {
    "CCTV1": 1, "CCTV2": 2, "CCTV3": 3, "CCTV4": 4, "CCTV5": 5,
    "CCTV5+": 6, "CCTV6": 7, "CCTV7": 8, "CCTV8": 9, "CCTV9": 10,
    "CCTV10": 11, "CCTV11": 12, "CCTV12": 13, "CCTV13": 14,
    "CCTV14": 15, "CCTV15": 16, "CCTV16": 17, "CCTV17": 18,
}

# 卫视频道顺序
SATELLITE_ORDER = {
    "湖南卫视": 1, "浙江卫视": 2, "江苏卫视": 3, "东方卫视": 4,
    "北京卫视": 5, "广东卫视": 6, "深圳卫视": 7, "天津卫视": 8,
    "山东卫视": 9, "安徽卫视": 10, "辽宁卫视": 11, "黑龙江卫视": 12,
    "四川卫视": 13, "重庆卫视": 14, "河南卫视": 15, "湖北卫视": 16,
    "江西卫视": 17, "东南卫视": 18, "广西卫视": 19, "贵州卫视": 20,
    "云南卫视": 21, "吉林卫视": 22, "陕西卫视": 23, "甘肃卫视": 24,
    "青海卫视": 25, "宁夏卫视": 26, "新疆卫视": 27, "西藏卫视": 28,
    "内蒙古卫视": 29, "海南卫视": 30, "旅游卫视": 31, "卡酷少儿": 32,
    "金鹰卡通": 33, "嘉佳卡通": 34, "凤凰卫视": 35, "凤凰卫视中文台": 36,
    "凤凰卫视资讯台": 37, "凤凰卫视香港台": 38, "凤凰卫视电影台": 39,
}

# 数字频道顺序
DIGITAL_ORDER = {
    "求索纪录": 1, "求索科学": 2, "求索动物": 3, "全纪实": 4,
    "生活时尚": 5, "魅力音乐": 6, "金色频道": 7, "法治天地": 8,
    "游戏风云": 9, "欢笑剧场": 10, "都市剧场": 11, "极速汽车": 12,
    "动漫秀场": 13, "劲爆体育": 14, "新视觉": 15, "茶频道": 16,
    "CGTN": 17, "CGTN纪录片": 18, "爱上4K": 19, "4K超高清": 20,
}

# 完整Logo库
COMMON_LOGOS = {
    # ========== 央视系列 ==========
    "CCTV1": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV1.png",
    "CCTV2": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV2.png",
    "CCTV3": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV3.png",
    "CCTV4": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV4.png",
    "CCTV5": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV5.png",
    "CCTV5+": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV5Plus.png",
    "CCTV6": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV6.png",
    "CCTV7": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV7.png",
    "CCTV8": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV8.png",
    "CCTV9": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV9.png",
    "CCTV10": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV10.png",
    "CCTV11": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV11.png",
    "CCTV12": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV12.png",
    "CCTV13": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV13.png",
    "CCTV14": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV14.png",
    "CCTV15": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV15.png",
    "CCTV16": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV16.png",
    "CCTV17": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CCTV17.png",
    
    # ========== 凤凰系列 ==========
    "凤凰卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Phoenix.png",
    "凤凰卫视中文台": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/PhoenixChinese.png",
    "凤凰卫视资讯台": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/PhoenixInfo.png",
    "凤凰卫视香港台": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/PhoenixHK.png",
    "凤凰卫视电影台": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/PhoenixMovies.png",
    
    # ========== 卫视频道 ==========
    "湖南卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Hunan.png",
    "浙江卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Zhejiang.png",
    "江苏卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Jiangsu.png",
    "东方卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/DragonTV.png",
    "北京卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Beijing.png",
    "广东卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Guangdong.png",
    "深圳卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Shenzhen.png",
    "天津卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Tianjin.png",
    "山东卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Shandong.png",
    "安徽卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Anhui.png",
    "辽宁卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Liaoning.png",
    "黑龙江卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Heilongjiang.png",
    "四川卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Sichuan.png",
    "重庆卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Chongqing.png",
    "河南卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Henan.png",
    "湖北卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Hubei.png",
    "江西卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Jiangxi.png",
    "东南卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Southeast.png",
    "广西卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Guangxi.png",
    "贵州卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Guizhou.png",
    "云南卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Yunnan.png",
    "吉林卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Jilin.png",
    "陕西卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Shaanxi.png",
    "甘肃卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Gansu.png",
    "青海卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Qinghai.png",
    "宁夏卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Ningxia.png",
    "新疆卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Xinjiang.png",
    "西藏卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Tibet.png",
    "内蒙古卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Neimenggu.png",
    "海南卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Hainan.png",
    "旅游卫视": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Travel.png",
    "卡酷少儿": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Kaku.png",
    "金鹰卡通": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Jinying.png",
    "嘉佳卡通": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Jiajia.png",
    
    # ========== 数字频道 ==========
    "求索纪录": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Discovery.png",
    "求索科学": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/DiscoveryScience.png",
    "求索动物": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/DiscoveryAnimal.png",
    "全纪实": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Documentary.png",
    "生活时尚": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Lifestyle.png",
    "魅力音乐": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Music.png",
    "金色频道": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Golden.png",
    "法治天地": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Law.png",
    "游戏风云": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Game.png",
    "欢笑剧场": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Comedy.png",
    "都市剧场": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/City.png",
    "极速汽车": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Car.png",
    "动漫秀场": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Anime.png",
    "劲爆体育": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Sports.png",
    "新视觉": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/NewVision.png",
    "茶频道": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/Tea.png",
    "CGTN": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CGTN.png",
    "CGTN纪录片": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/CGTNDoc.png",
    "爱上4K": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/4K.png",
    "4K超高清": "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/4K.png",
}

# =============================

def get_channel_category(channel_name):
    """获取频道分类"""
    if channel_name.startswith("CCTV"):
        return "CCTV"
    elif channel_name in SATELLITE_ORDER:
        return "卫视"
    elif channel_name in DIGITAL_ORDER:
        return "数字"
    else:
        return "其他"

def get_channel_sort_key(channel_name):
    """获取频道排序键值"""
    category = get_channel_category(channel_name)
    category_order = CHANNEL_CATEGORIES.get(category, 99)
    
    if category == "CCTV":
        order = CCTV_ORDER.get(channel_name, 999)
    elif category == "卫视":
        order = SATELLITE_ORDER.get(channel_name, 999)
    elif category == "数字":
        order = DIGITAL_ORDER.get(channel_name, 999)
    else:
        order = 999
    
    return (category_order, order, channel_name)

def get_logo_url(channel_name):
    """获取频道Logo URL，支持精确匹配和模糊匹配"""
    # 精确匹配
    if channel_name in COMMON_LOGOS:
        return COMMON_LOGOS[channel_name]
    
    # 模糊匹配：尝试去除空格、特殊字符后匹配
    clean_name = channel_name.replace(" ", "").replace("-", "")
    for name, url in COMMON_LOGOS.items():
        if clean_name == name.replace(" ", "").replace("-", ""):
            return url
    
    # 尝试匹配前缀
    for name, url in COMMON_LOGOS.items():
        if channel_name.startswith(name) or name.startswith(channel_name):
            return url
    
    return ""

def fetch_source():
    print(f"📡 正在拉取源: {SOURCE_URL}")
    try:
        response = requests.get(SOURCE_URL, timeout=30)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            print(f"✅ 拉取成功，大小: {len(response.text)} 字节")
            return response.text
        else:
            print(f"❌ 拉取失败: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 拉取异常: {e}")
        return None

def parse_content(content):
    channels = defaultdict(list)
    current_group = "未分组"
    lines = content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '#genre#' in line:
            current_group = line.split(',')[0].strip()
            continue
        if ',' in line:
            parts = line.split(',', 1)
            channel_name = parts[0].strip()
            url = parts[1].strip()
            clean_url = re.sub(r'\$.*$', '', url)
            
            # 标准化频道名称
            if channel_name.startswith("CCTV-"):
                channel_name = channel_name.replace("CCTV-", "CCTV")
            channel_name = channel_name.strip()
            
            channels[channel_name].append({
                'name': channel_name,
                'url': url,
                'clean_url': clean_url,
                'group': current_group
            })
    
    print(f"📊 解析完成，共 {len(channels)} 个频道，{sum(len(v) for v in channels.values())} 个源")
    return channels

def stability_test(url):
    test_start = time.time()
    total_bytes = 0
    chunk_count = 0
    first_byte_time = None
    
    try:
        response = requests.get(url, timeout=CONNECT_TIMEOUT, stream=True)
        if response.status_code != 200:
            return False, 0, 0, 0, 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                if first_byte_time is None:
                    first_byte_time = time.time() - test_start
                total_bytes += len(chunk)
                chunk_count += 1
                if time.time() - test_start >= STABILITY_TEST_DURATION:
                    break
        
        elapsed = time.time() - test_start
        if elapsed < 1 or chunk_count < 3:
            return False, 0, 0, 0, 0
        
        avg_speed = total_bytes / elapsed / 1024
        
        if avg_speed < MIN_SPEED_KBPS:
            return False, 0, 0, 0, avg_speed
        
        speed_score = min(500, int(avg_speed * 1.2))
        if first_byte_time:
            fb_score = max(0, 200 - int(first_byte_time * 50))
        else:
            fb_score = 0
        stability_score = min(300, chunk_count * 15)
        
        quality_score = speed_score + fb_score + stability_score
        
        return True, quality_score, avg_speed, first_byte_time, chunk_count
        
    except Exception as e:
        return False, 0, 0, 0, 0

def process_channel(channel_name, sources):
    print(f"正在检测稳定性: {channel_name} ({len(sources)} 个源)")
    
    results = []
    for idx, source in enumerate(sources, 1):
        print(f"  [{idx}/{len(sources)}] 测试: {source['clean_url'][:60]}...")
        is_stable, quality, speed, fb_time, chunks = stability_test(source['clean_url'])
        
        if is_stable:
            results.append({
                'name': source['name'],
                'url': source['url'],
                'quality_score': quality,
                'speed': speed,
                'first_byte': fb_time,
                'chunks': chunks
            })
            print(f"    ✅ 稳定 质量分:{quality} 速度:{speed:.1f}KB/s")
        else:
            print(f"    ❌ 不稳定")
    
    results.sort(key=lambda x: (-x['quality_score'], -x['speed'], x['first_byte']))
    
    if results:
        print(f"  📊 {channel_name} 排序结果: 共{len(results)}条稳定线路")
    
    return channel_name, results

def generate_m3u(sorted_channels):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 对频道进行排序
    sorted_channel_names = sorted(sorted_channels.keys(), key=get_channel_sort_key)
    
    # 分组名称映射
    category_names = {
        "CCTV": "央视频道",
        "卫视": "卫视频道",
        "数字": "数字频道",
        "其他": "其他频道"
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write(f"# 更新时间: {current_time}\n")
        f.write(f"# 总频道数: {len(sorted_channels)}\n")
        f.write(f"# 总有效线路数: {sum(len(v) for v in sorted_channels.values())}\n")
        f.write(f"# 筛选标准: 测试{STABILITY_TEST_DURATION}秒, 最低速度{MIN_SPEED_KBPS}KB/s\n\n")
        
        # 按分类输出
        for category in ["CCTV", "卫视", "数字", "其他"]:
            category_channels = [name for name in sorted_channel_names if get_channel_category(name) == category]
            if not category_channels:
                continue
            
            display_name = category_names.get(category, category)
            
            # 央视频道上方添加更新时间
            if category == "CCTV":
                f.write(f"\n# ========== {display_name} ==========\n")
                f.write(f"# 更新时间: {current_time}\n\n")
            else:
                f.write(f"\n# ========== {display_name} ==========\n")
            
            for channel_name in category_channels:
                sources = sorted_channels[channel_name]
                if not sources:
                    continue
                
                f.write(f"\n# 频道: {channel_name}\n")
                f.write(f"# 可用线路数: {len(sources)}\n")
                
                for idx, source in enumerate(sources, 1):
                    base_url = re.sub(r'『线路.*』', '', source['url'])
                    base_url = re.sub(r'\$.*$', '', base_url)
                    numbered_url = f"{base_url}『线路{idx}』"
                    
                    tvg_id = str(abs(hash(channel_name)) % 10000)
                    logo_url = get_logo_url(channel_name)
                    
                    extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{display_name}",{channel_name}'
                    f.write(extinf + '\n')
                    f.write(numbered_url + '\n')
                    f.write(f"# 质量分: {source['quality_score']} | 速度: {source['speed']:.1f}KB/s | 首字节: {source['first_byte']:.2f}s\n")

def main():
    start_time = time.time()
    print("=" * 60)
    print("🚀 开始处理 IPTV 源 (分类排序+Logo版)")
    print(f"⚙️  配置: 测试时长={STABILITY_TEST_DURATION}秒, 最低速度={MIN_SPEED_KBPS}KB/s")
    print("=" * 60)
    
    content = fetch_source()
    if not content:
        return
    
    channels = parse_content(content)
    sorted_channels = {}
    total_channels = len(channels)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_channel = {
            executor.submit(process_channel, name, sources): name 
            for name, sources in channels.items()
        }
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_channel), 1):
            channel_name = future_to_channel[future]
            try:
                name, results = future.result()
                sorted_channels[name] = results
                valid_count = len(results)
                total_count = len(channels[name])
                print(f"\n📊 进度: [{i}/{total_channels}] {name} - 稳定: {valid_count}/{total_count}\n")
            except Exception as e:
                print(f"❌ 处理 {channel_name} 时出错: {e}")
    
    total_sources = sum(len(v) for v in channels.values())
    total_valid = sum(len(v) for v in sorted_channels.values())
    
    print("\n" + "=" * 60)
    print("📊 最终统计")
    print("=" * 60)
    print(f"总频道数: {total_channels}")
    print(f"总源数: {total_sources}")
    print(f"稳定源数: {total_valid}")
    if total_sources > 0:
        print(f"稳定比例: {total_valid/total_sources*100:.1f}%")
    
    generate_m3u(sorted_channels)
    
    elapsed = time.time() - start_time
    print(f"\n✅ 处理完成！耗时: {elapsed:.1f} 秒")
    print(f"📁 输出文件: {OUTPUT_FILE}")
    print(f"\n📺 频道排序规则: 央视频道(1-17) → 卫视频道 → 数字频道 → 其他频道")

if __name__ == "__main__":
    main()
