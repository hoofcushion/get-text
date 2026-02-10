# 语音转文字工具

将在线视频或本地音频文件转换为中文文字。

## 安装

```bash
git clone https://github.com/hoofcushion/get-text
cd get-text

# 推荐使用 uv
uv sync

# 或使用 venv，需要自行管理版本
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用方法

### 命令行模式
```bash
uv run python init.py "https://www.youtube.com/watch?v=XXXXXXX"
```

### GUI模式
```bash
uv run python gui.py
```

## 功能特点

- 支持 YouTube、Bilibili 等在线视频
- 支持本地音频/视频文件
- 多任务并行处理（GUI模式）
- 断点续传功能
- 自动生成带时间戳的文本文件

## 环境要求

- Python ≥ 3.11
- FFmpeg
- 网络连接（首次使用需下载模型）

## 输出格式

处理完成后在 `output/` 目录生成格式为 `时间-上传者-标题.{txt/srt}` 的文本文件。
