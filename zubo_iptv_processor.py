import requests
import re
import time
from collections import defaultdict
from datetime import datetime
import concurrent.futures

# ========== 增强配置 ==========
SOURCE_URL = "https://raw.githubusercontent.com/gclgg/zubo/refs/heads/main/IPTV.txt"
OUTPUT_FILE = "zubo_iptv_sorted.m3u"
MAX_WORKERS = 15                # 并发数，不宜过高
CONNECT_TIMEOUT = 8             # 连接超时(秒)
STABILITY_TEST_DURATION = 5     # 稳定性测试时长(秒) - 模拟真实播放5秒
MIN_SPEED_KBPS = 500            # 最低要求速度(KB/s)
# =============================

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
            
            channels[channel_name].append({
                'name': channel_name,
                'url': url,
                'clean_url': clean_url,
                'group': current_group
            })
    print(f"📊 解析完成，共 {len(channels)} 个频道，{sum(len(v) for v in channels.values())} 个源")
    return channels

def stability_test(url):
    """
    模拟真实播放的稳定性测试
    返回: (是否稳定, 质量分, 平均速度KB/s)
    """
    test_start = time.time()
    total_bytes = 0
    chunk_count = 0
    
    try:
        # 使用流式下载，模拟播放器行为
        response = requests.get(url, timeout=CONNECT_TIMEOUT, stream=True)
        if response.status_code != 200:
            return False, 0, 0
        
        # 持续读取数据，模拟播放 STABILITY_TEST_DURATION 秒
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                total_bytes += len(chunk)
                chunk_count += 1
                # 如果已测试足够时间，退出
                if time.time() - test_start >= STABILITY_TEST_DURATION:
                    break
        
        elapsed = time.time() - test_start
        if elapsed < 1:
            return False, 0, 0  # 太短，无效
        
        avg_speed = total_bytes / elapsed / 1024  # KB/s
        
        # 判定标准：必须达到最低速度，且接收到的数据块足够多
        if avg_speed >= MIN_SPEED_KBPS and chunk_count >= 5:
            # 质量分 = 速度分 + 时间分
            speed_score = min(500, int(avg_speed * 1.5))
            duration_score = min(300, int(elapsed * 20))
            quality_score = speed_score + duration_score
            return True, quality_score, avg_speed
        else:
            return False, 0, avg_speed
            
    except Exception as e:
        # 任何异常都视为不稳定
        return False, 0, 0

def process_channel(channel_name, sources):
    print(f"正在检测稳定性: {channel_name} ({len(sources)} 个源)")
    
    stable_results = []
    for source in sources:
        is_stable, quality, speed = stability_test(source['clean_url'])
        if is_stable:
            stable_results.append({
                'name': source['name'],
                'url': source['url'],
                'quality_score': quality,
                'speed': speed
            })
    
    # 按质量分从高到低排序
    stable_results.sort(key=lambda x: x['quality_score'], reverse=True)
    return channel_name, stable_results

def generate_m3u(sorted_channels):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write(f"# 更新时间: {current_time}\n")
        f.write(f"# 总频道数: {len(sorted_channels)}\n")
        f.write(f"# 总有效线路数: {sum(len(v) for v in sorted_channels.values())}\n\n")
        
        for channel_name, sources in sorted_channels.items():
            if not sources:
                continue
            
            f.write(f"\n# 频道: {channel_name}\n")
            for idx, source in enumerate(sources, 1):
                # 为每个有效线路重新编号
                base_url = re.sub(r'\$.*$', '', source['url'])
                numbered_url = f"{base_url}『线路{idx}』"
                
                tvg_id = str(abs(hash(channel_name)) % 10000)
                # 在EXTINF中增加速度注释
                extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{channel_name}" group-title="IPTV源",{channel_name}'
                f.write(extinf + '\n')
                f.write(numbered_url + '\n')
                f.write(f"# 质量分: {source['quality_score']}, 速度: {source['speed']:.1f}KB/s\n")

def main():
    start_time = time.time()
    print("=" * 50)
    print("🚀 开始处理 IPTV 源 (增强稳定性检测)")
    print(f"⚙️  配置: 测试时长={STABILITY_TEST_DURATION}秒, 最低速度={MIN_SPEED_KBPS}KB/s")
    print("=" * 50)
    
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
                print(f"进度: [{i}/{total_channels}] {name} - 稳定: {valid_count}/{total_count}")
            except Exception as e:
                print(f"❌ 处理 {channel_name} 时出错: {e}")
    
    total_sources = sum(len(v) for v in channels.values())
    total_valid = sum(len(v) for v in sorted_channels.values())
    
    print("\n" + "=" * 50)
    print("📊 最终统计")
    print("=" * 50)
    print(f"总频道数: {total_channels}")
    print(f"总源数: {total_sources}")
    print(f"稳定源数: {total_valid}")
    if total_sources > 0:
        print(f"稳定比例: {total_valid/total_sources*100:.1f}%")
    
    generate_m3u(sorted_channels)
    
    elapsed = time.time() - start_time
    print(f"\n✅ 处理完成！耗时: {elapsed:.1f} 秒")
    print(f"📁 输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
