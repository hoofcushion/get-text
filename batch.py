#!/usr/bin/env python3
"""
批量处理B站视频链接 - 直接调用 init.py 的函数
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# 直接导入 init.py 的所有功能
import init

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def main():
    if len(sys.argv) < 2:
        print("用法: python batch.py <链接文件>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not Path(input_file).exists():
        print(f"错误: 文件 '{input_file}' 不存在")
        sys.exit(1)

    # 读取所有链接
    urls = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)

    print(f"\n找到 {len(urls)} 个链接，开始处理...")
    print("=" * 60)

    success = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] 处理: {url}")
        
        # 自定义日志函数
        def log_callback(msg):
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {msg}")
            with open(LOG_DIR / f"{i:03d}.log", 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {msg}\n")
        
        try:
            start = time.time()
            results = init.run_full_transcription_pipeline(url, "text", log_callback)
            elapsed = time.time() - start
            
            print(f"  ✅ 成功 (耗时: {elapsed:.1f}秒)")
            for r in results:
                print(f"    生成: {Path(r).name}")
            success += 1
            
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            failed += 1
        
        time.sleep(2)

    print("\n" + "=" * 60)
    print(f"处理完成！成功: {success}, 失败: {failed}")

if __name__ == "__main__":
    main()
