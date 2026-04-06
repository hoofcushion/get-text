from typing import List, TypedDict, Optional
import model

class WordTimestamp(TypedDict):
    text: str
    start: int
    end: int

def align_text_timestamps(
    text: str, timestamps: List[List[int]]
) -> List[WordTimestamp]:
    """将文本单词与时间戳对齐，返回单词级时间戳列表"""
    words = text.split(" ")

    # 处理长度不匹配的情况
    if len(words) != len(timestamps):
        if len(timestamps) == 1:
            timestamps = [timestamps[0]] * len(words)
        else:
            min_length = min(len(words), len(timestamps))
            words = words[:min_length]
            timestamps = timestamps[:min_length]

    result = []
    for word, (start, end) in zip(words, timestamps):
        result.append({"text": word, "start": start, "end": end})
    return result

def timestamp_prediction(audio_path: str, text: str, device: Optional[str] = None):
    """使用强制对齐模型预测单词时间戳"""
    model_ = model.request_model(
        "fa-zh",
        lambda AutoModel: AutoModel(
            model="fa-zh",
            device=device
        ),
    )
    res = model_.generate(input=(audio_path, text), data_type=("sound", "text"))
    return res[0]["text"], res[0]["timestamp"]

def to_word_timestamp_list(
    audio_path: str, result: Optional[dict], device: Optional[str] = None
) -> Optional[List[WordTimestamp]]:
    """
    从识别结果中提取或生成单词级时间戳列表。
    如果 result 中已有 timestamp，则直接对齐；否则调用强制对齐模型补全。
    """
    if not result:
        return None

    if result.get("text") and result.get("timestamp"):
        # 已有时间戳，直接对齐
        return align_text_timestamps(result["text"], result["timestamp"])
    elif result.get("text") and not result.get("timestamp"):
        # 缺失时间戳，调用强制对齐
        text, timestamp = timestamp_prediction(audio_path, result["text"], device=device)
        if text and timestamp:
            return align_text_timestamps(text, timestamp)
    return None
