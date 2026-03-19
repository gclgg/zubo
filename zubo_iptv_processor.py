import requests
import re
import time
from collections import defaultdict
from datetime import datetime
import concurrent.futures
import socket

# 配置参数
SOURCE_URL = "https://raw.githubusercontent.com/gclgg/zubo/refs/heads/main/IPTV.txt"
OUTPUT_FILE = "zubo_iptv_sorted.m3u"
MAX_WORKERS = 20  # 并发检测线程数
TIMEOUT = 5  # 连接超时时间（秒）

def fetch_source():
    """拉取源文件"""
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
    """解析IPTV.txt内容，按频道名分组"""
    channels = defaultdict(list)
    current_group = "未分组"
    lines = content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 处理分组行
        if '#genre#' in line:
            current_group = line.split(',')[0].strip()
            continue
        
        # 处理频道行
        if ',' in line:
            parts = line.split(',', 1)
            channel_name = parts[0].strip()
            url = parts[1].strip()
            
            # 提取纯净URL（去掉$后面的参数）
            clean_url = re.sub(r'\$.*$', '', url)
            
            channels[channel_name].append({
                'name': channel_name,
                'url': url,
                'clean_url': clean_url,
                'group': current_group
            })
    
    print(f"📊 解析完成，共 {len(channels)} 个频道，{sum(len(v) for v in channels.values())} 个源")
    return channels

def check_url_quality(url):
    """检测URL的质量（响应时间）"""
    try:
        start_time = time.time()
        # 使用HEAD请求快速检测
        response = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        elapsed = int((time.time() - start_time) * 1000)  # 毫秒
        
        if response.status_code == 200:
            # 质量分 = 1000 - 响应时间(ms)，响应越快分越高
            quality_score = max(0, 1000 - elapsed)
            return {
                'valid': True,
                'quality_score': quality_score,
                'response_time': elapsed,
                'status': response.status_code
            }
        else:
            return {
                'valid': False,
                'quality_score': 0,
                'response_time': None,
                'status': response.status_code
            }
    except requests.exceptions.Timeout:
        return {'valid': False, 'quality_score': 0, 'error': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'valid': False, 'quality_score': 0, 'error': 'connection_error'}
    except Exception as e:
        return {'valid': False, 'quality_score': 0, 'error': str(e)[:50]}

def process_channel(channel_name, sources):
    """处理单个频道的所有源，按质量排序"""
    print(f"正在检测: {channel_name} ({len(sources)} 个源)")
    
    results = []
    for source in sources:
        quality = check_url_quality(source['clean_url'])
        if quality['valid']:
            results.append({
                'name': source['name'],
                'url': source['url'],
                'quality_score': quality['quality_score'],
                'response_time': quality['response_time']
            })
    
    # 按质量分从高到低排序
    results.sort(key=lambda x: x['quality_score'], reverse=True)
    
    return channel_name, results

def generate_m3u(sorted_channels):
    """生成最终的M3U文件"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # 写入文件头
        f.write("#EXTM3U\n")
        f.write(f"# 更新时间: {current_time}\n")
        f.write(f"# 总频道数: {len(sorted_channels)}\n")
        f.write(f"# 总源数: {sum(len(v) for v in sorted_channels.values())}\n\n")
        
        # 按频道写入
        for channel_name, sources in sorted_channels.items():
            if not sources:
                continue
            
            f.write(f"\n# 频道: {channel_name}\n")
            for idx, source in enumerate(sources, 1):
                # 添加线路编号
                if '『线路' in source['url']:
                    # 如果已有线路标记，替换
                    base_url = re.sub(r'『线路.*』', '', source['url'])
                    numbered_url = f"{base_url}『线路{idx}』"
                elif '$' in source['url']:
                    # 如果有$参数，在$前添加线路标记
                    base_url = source['url'].split('$')[0]
                    params = source['url'].split('$')[1] if '$' in source['url'] else ''
                    if params:
                        numbered_url = f"{base_url}『线路{idx}』${params}"
                    else:
                        numbered_url = f"{base_url}『线路{idx}』"
                else:
                    # 普通URL，直接添加线路标记
                    numbered_url = f"{source['url']}『线路{idx}』"
                
                # 写入EXTINF行
                tvg_id = str(abs(hash(channel_name)) % 10000)
                extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{channel_name}"'
                extinf += f' group-title="IPTV源",{channel_name}'
                f.write(extinf + '\n')
                
                # 写入URL
                f.write(numbered_url + '\n')
                
                # 可选：添加注释说明质量
                f.write(f"# 质量分: {source['quality_score']}, 响应时间: {source['response_time']}ms\n")

def main():
    start_time = time.time()
    print("=" * 50)
    print("🚀 开始处理 IPTV 源")
    print("=" * 50)
    
    # 1. 拉取源
    content = fetch_source()
    if not content:
        return
    
    # 2. 解析内容
    channels = parse_content(content)
    
    # 3. 并发检测所有频道
    sorted_channels = {}
    total_channels = len(channels)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_channel = {
            executor.submit(process_channel, name, sources): name 
            for name, sources in channels.items()
        }
        
        # 收集结果
        for i, future in enumerate(concurrent.futures.as_completed(future_to_channel), 1):
            channel_name = future_to_channel[future]
            try:
                name, results = future.result()
                sorted_channels[name] = results
                valid_count = len(results)
                total_count = len(channels[name])
                print(f"进度: [{i}/{total_channels}] {name} - 有效: {valid_count}/{total_count}")
            except Exception as e:
                print(f"❌ 处理 {channel_name} 时出错: {e}")
    
    # 4. 统计信息
    total_sources = sum(len(v) for v in channels.values())
    total_valid = sum(len(v) for v in sorted_channels.values())
    
    print("\n" + "=" * 50)
    print("📊 统计信息")
    print("=" * 50)
    print(f"总频道数: {total_channels}")
    print(f"总源数: {total_sources}")
    print(f"有效源数: {total_valid}")
    print(f"有效比例: {total_valid/total_sources*100:.1f}%")
    
    # 5. 生成M3U文件
    generate_m3u(sorted_channels)
    
    elapsed = time.time() - start_time
    print(f"\n✅ 处理完成！耗时: {elapsed:.1f} 秒")
    print(f"📁 输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
