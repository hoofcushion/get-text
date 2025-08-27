# get-text.py

一键把任意在线视频转成中文文字
流水线：URL → yt-dlp → 音频 → ffmpeg → 16 kHz WAV → FunASR → 中文文本

## 安装
```bash
git clone https://github.com/hoofcushion/get-text
cd get-text
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 使用
```bash
python get-text.py "https://www.youtube.com/watch?v=XXXXXXX"
```
运行后在 `output/` 目录生成 `<上传时间>-<上传者>-<视频标题>.txt`（UTF-8）。

## 环境要求
- Python ≥ 3.8
- FFmpeg（系统包或 https://ffmpeg.org 下载）
- yt-dlp（requirements.txt 自动安装）
- FunASR 及模型（首次运行自动下载，约 1 GB）

## 小技巧
- 第一次运行会下载 Paraformer 模型，请保持网络畅通。
- 如需英文或其它语言，修改脚本里的 `MODEL` 变量即可。
- 请自行检查磁盘空闲、网络通畅

## 断点继续
脚本会自动在 `jobs/` 目录生成中间文件，中断后可自动识别断点继续运行。
