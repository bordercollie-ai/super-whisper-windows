"""端到端识别测试：用 edge-tts 合成中/英/日语音，走和托盘应用相同的 recognize()。

需要 NVIDIA 显卡（没有则退回 CPU，会很慢）和 edge-tts。
注意：edge-tts 会把测试文本发送到微软的在线 TTS 服务。
合成的音频缓存在 tests/_audio/，删掉即可重新生成。
"""
import asyncio
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app  # noqa: E402

try:
    import av
    import edge_tts
except ImportError:
    edge_tts = None

AUDIO_DIR = Path(__file__).resolve().parent / "_audio"
CLIPS = {
    "zh_en": ("zh-CN-XiaoxiaoNeural", "我们今天讨论一下 API 的设计，然后 deploy 到 production 环境。"),
    "ja": ("ja-JP-NanamiNeural", "これは日本語のテストです。明日は会議があります。"),
    "zh_short": ("zh-CN-YunxiNeural", "帮我把这个文件发给他。"),
    "en": ("en-US-AriaNeural", "Please send me the report by tomorrow."),
}


def synthesize(name):
    path = AUDIO_DIR / f"{name}.mp3"
    if not path.exists():
        AUDIO_DIR.mkdir(exist_ok=True)
        voice, text = CLIPS[name]
        asyncio.run(edge_tts.Communicate(text, voice).save(str(path)))
    return path


def decode(path):
    container = av.open(str(path))
    resampler = av.AudioResampler(format="s16", layout="mono", rate=app.SR)
    parts = []
    for frame in container.decode(audio=0):
        parts += [f.to_ndarray().flatten() for f in resampler.resample(frame)]
    parts += [f.to_ndarray().flatten() for f in resampler.resample(None)]
    return np.concatenate(parts).astype("float32") / 32768


@unittest.skipIf(edge_tts is None, "需要安装 edge-tts: uv pip install edge-tts")
class RecognitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.cfg.update(chinese_script="simplified", normalize_punctuation=True, debug_log=False)
        app.model = app.create_model()

    def recognize(self, name):
        return app.recognize(decode(synthesize(name)))

    def test_chinese_with_english_words(self):
        text = self.recognize("zh_en")
        for word in ["我们", "API", "设计", "环境"]:
            self.assertIn(word, text)
        self.assertIn("deploy", text.lower())

    def test_japanese_stays_japanese(self):
        text = self.recognize("ja")
        self.assertIn("日本語", text)
        self.assertIn("会議", text)
        self.assertNotIn("，", text)

    def test_short_chinese_sentence(self):
        text = self.recognize("zh_short")
        self.assertIn("文件", text)

    def test_english_sentence_not_hallucinated(self):
        text = self.recognize("en").lower()
        self.assertIn("report", text)
        self.assertIn("tomorrow", text)


if __name__ == "__main__":
    unittest.main()
