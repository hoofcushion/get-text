import pickle
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import model


class SRTGenerator:
    def __init__(self, use_cpu: bool = False):
        self.use_cpu = use_cpu
        self._punctuation_model = None

    def initialize_punctuation_model(self) -> Optional[Any]:
        if self._punctuation_model is None:
            try:
                # 使用 model.py 的接口获取标点模型
                self._punctuation_model = model.request_model(
                    "ct-punc",
                    lambda AutoModel: AutoModel(
                        model="ct-punc", device="cpu" if self.use_cpu else None
                    ),
                )
            except Exception:
                self._punctuation_model = None
        return self._punctuation_model

    def calculate_text_weighted_length(self, input_text: str) -> int:
        weighted_length: int = 0
        for character in input_text:
            if ord(character) < 128:
                weighted_length += 1
            else:
                weighted_length += 2
        return weighted_length

    def apply_punctuation_restoration(self, original_sentence: str) -> str:
        punctuation_model = self.initialize_punctuation_model()
        if punctuation_model is None:
            return original_sentence
        try:
            punctuation_result = punctuation_model.generate(input=original_sentence)
            if punctuation_result and len(punctuation_result) > 0:
                return punctuation_result[0]["text"]
        except Exception:
            pass
        return original_sentence

    def merge_words_into_sentences_with_dynamic_threshold(
        self,
        word_sequence: List[Dict[str, Any]],
        base_silence_threshold_ms: int = 1000,
        length_penalty_factor: float = 0.05,
        enable_punctuation_restoration: bool = True,
    ) -> List[Dict[str, Any]]:
        if not word_sequence:
            return []

        merged_sentences: List[Dict[str, Any]] = []
        current_sentence: Dict[str, Any] = {
            "text": word_sequence[0]["text"],
            "start": word_sequence[0]["start"],
            "finish": word_sequence[0]["finish"],
        }

        for word_index in range(1, len(word_sequence)):
            current_word: Dict[str, Any] = word_sequence[word_index]
            previous_word: Dict[str, Any] = word_sequence[word_index - 1]

            silence_gap_duration: float = (
                current_word["start"] - previous_word["finish"]
            )

            current_sentence_weighted_length: int = self.calculate_text_weighted_length(
                current_sentence["text"]
            )
            dynamic_silence_threshold: float = base_silence_threshold_ms - (
                current_sentence_weighted_length * length_penalty_factor * 1000
            )
            dynamic_silence_threshold = max(dynamic_silence_threshold, 100)

            if silence_gap_duration >= dynamic_silence_threshold:
                if enable_punctuation_restoration:
                    punctuated_sentence_text: str = self.apply_punctuation_restoration(
                        current_sentence["text"]
                    )
                    current_sentence["text"] = punctuated_sentence_text
                merged_sentences.append(current_sentence)

                current_sentence = {
                    "text": current_word["text"],
                    "start": current_word["start"],
                    "finish": current_word["finish"],
                }
            else:
                current_sentence["text"] += " " + current_word["text"]
                current_sentence["finish"] = current_word["finish"]

        if enable_punctuation_restoration:
            final_punctuated_text: str = self.apply_punctuation_restoration(
                current_sentence["text"]
            )
            current_sentence["text"] = final_punctuated_text
        merged_sentences.append(current_sentence)

        return merged_sentences

    def convert_milliseconds_to_srt_time_format(
        self, time_in_milliseconds: float
    ) -> str:
        total_seconds: float = time_in_milliseconds / 1000.0
        hours_component: int = int(total_seconds // 3600)
        minutes_component: int = int((total_seconds % 3600) // 60)
        seconds_component: int = int(total_seconds % 60)
        milliseconds_component: int = int(time_in_milliseconds % 1000)
        return f"{hours_component:02d}:{minutes_component:02d}:{seconds_component:02d},{milliseconds_component:03d}"

    def generate_srt_content_from_sentences(
        self, sentence_list: List[Dict[str, Any]]
    ) -> str:
        srt_content_lines: List[str] = []
        for sentence_index, sentence_data in enumerate(sentence_list, 1):
            start_time_formatted: str = self.convert_milliseconds_to_srt_time_format(
                sentence_data["start"]
            )
            end_time_formatted: str = self.convert_milliseconds_to_srt_time_format(
                sentence_data["finish"]
            )
            srt_content_lines.append(str(sentence_index))
            srt_content_lines.append(f"{start_time_formatted} --> {end_time_formatted}")
            srt_content_lines.append(sentence_data["text"])
            srt_content_lines.append("")

        return "\n".join(srt_content_lines)

    def save_srt_to_file(
        self, srt_content: str, output_file_path: Union[str, Path]
    ) -> None:
        with open(output_file_path, "w", encoding="utf-8") as output_file_handle:
            output_file_handle.write(srt_content)

    def generate_srt_from_word_timestamps(
        self,
        word_timestamps: List[Dict[str, Any]],
        output_file_path: Union[str, Path] = "output.srt",
        base_silence_threshold_ms: int = 1000,
        length_penalty_factor: float = 0.05,
        enable_punctuation_restoration: bool = True,
    ) -> Dict[str, Any]:
        if not word_timestamps:
            raise ValueError("Word timestamps list is empty")

        for word in word_timestamps:
            if not all(key in word for key in ["text", "start", "finish"]):
                raise ValueError(
                    "Invalid word timestamp format. Required keys: text, start, finish"
                )

        merged_sentences = self.merge_words_into_sentences_with_dynamic_threshold(
            word_timestamps,
            base_silence_threshold_ms=base_silence_threshold_ms,
            length_penalty_factor=length_penalty_factor,
            enable_punctuation_restoration=enable_punctuation_restoration,
        )

        srt_content = self.generate_srt_content_from_sentences(merged_sentences)
        self.save_srt_to_file(srt_content, output_file_path)

        return {
            "word_count": len(word_timestamps),
            "sentence_count": len(merged_sentences),
            "output_file": str(output_file_path),
            "srt_content": srt_content,
        }

    def generate_srt_from_recognition_result(
        self,
        recognition_result: List[Dict[str, Any]],
        output_file_path: Union[str, Path] = "output.srt",
        base_silence_threshold_ms: int = 1000,
        length_penalty_factor: float = 0.05,
        enable_punctuation_restoration: bool = True,
    ) -> Dict[str, Any]:
        word_timestamps = []

        for recognition_item in recognition_result:
            if "text" in recognition_item and "timestamp" in recognition_item:
                segmented_words: List[str] = recognition_item["text"].split(" ")
                word_timestamps_list: List[List[float]] = recognition_item["timestamp"]
                minimum_length: int = min(
                    len(segmented_words), len(word_timestamps_list)
                )
                for word_index in range(minimum_length):
                    word_timestamps.append(
                        {
                            "text": segmented_words[word_index],
                            "start": word_timestamps_list[word_index][0],
                            "finish": word_timestamps_list[word_index][1],
                        }
                    )

        if not word_timestamps:
            raise ValueError("No valid word timestamps found in recognition result")

        return self.generate_srt_from_word_timestamps(
            word_timestamps,
            output_file_path,
            base_silence_threshold_ms,
            length_penalty_factor,
            enable_punctuation_restoration,
        )
