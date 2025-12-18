# init.py

在本地一键把任意在线视频(yt-dlp)转成中文文字
流水线：URL → yt-dlp → 音频 → ffmpeg → 16 kHz WAV → FunASR → 中文文本

## 安装
```bash
# install
git clone https://github.com/hoofcushion/get-text
cd get-text

# venv
python -m venv .venv
source venv/bin/activate
pip install -r requirements.txt

# or uv
uv sync
```

## 使用
```bash
# direct use
python init.py "https://www.youtube.com/watch?v=XXXXXXX"

# uv
uv run python init.py "https://www.youtube.com/watch?v=XXXXXXX"

# linux
./launch.sh "https://www.youtube.com/watch?v=XXXXXXX"

# windows
./launch.ps1 "https://www.youtube.com/watch?v=XXXXXXX"
```
运行后在 `output/` 目录生成 `<上传时间>-<上传者>-<视频标题>.txt`（UTF-8）。

## 环境要求
- Python ≥ 3.11
- FFmpeg（系统包或 https://ffmpeg.org 下载）
- yt-dlp（requirements.txt 自动安装）
- FunASR 及模型

## 小技巧
- 第一次运行会下载 Paraformer 模型，请保持网络畅通。
- 如需英文或其它语言，修改脚本里的 `MODEL` 变量即可。
- 请自行检查磁盘空闲、网络通畅
- 如果需要硬件加速，请自行指定 pytorch 的 whl 版本

## 断点继续
脚本会自动在 `jobs/` 目录生成中间文件，中断后可自动识别断点继续运行。
