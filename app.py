import json
import os
import re
import sys
import threading
import time
import winsound
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULTS = {
    "hotkey": "alt+.",
    "model": "large-v3-turbo",
    "language": "zh",
    "multilingual": True,
    "languages": ["zh", "en", "ja"],
    "language_bias": {"zh": 2.0},
    "initial_prompt": "你好，这是一段普通话。Hello, this is English. こんにちは、日本語です。",
    "auto_paste": True,
    "restore_clipboard": True,
    "max_seconds": 300,
    "chinese_script": "simplified",
    "normalize_punctuation": True,
    "notify_result": False,
}

SCRIPT_CHOICES = {"simplified": "简体中文", "traditional": "繁体中文", "none": "不转换"}
KANA = re.compile(r"[\u3040-\u30ff]")
CJK_CLASS = r"\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
CJK = re.compile(f"[{CJK_CLASS}]")
HALF_TO_FULL = {",": "，", ".": "。", "?": "？", "!": "！", ":": "：", ";": "；"}
FULL_TO_HALF = {"，": ", ", "、": ", ", "。": ". ", "？": "? ", "！": "! ", "：": ": ", "；": "; "}
ASCII_AFTER_CJK = re.compile(f"([{CJK_CLASS}])[ ]?([,.?!:;])(?![\\d.])")
SPACE_AFTER_FULL = re.compile(f"([，。？！：；、])[ ]+(?=[{CJK_CLASS}])")


def load_config():
    path = ROOT / "config.json"
    cfg = dict(DEFAULTS)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    else:
        path.write_text(json.dumps(DEFAULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def save_config():
    (ROOT / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
def add_cuda_dlls():
    site = ROOT / ".venv" / "Lib" / "site-packages" / "nvidia"
    if not site.exists():
        return
    for bin_dir in site.glob("*/bin"):
        os.add_dll_directory(str(bin_dir))
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]


add_cuda_dlls()

try:  # 声明 DPI 感知，否则 4K 屏上托盘图标会被系统位图拉伸而模糊
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import keyboard  # noqa: E402
import numpy as np  # noqa: E402
import pyperclip  # noqa: E402
import pystray  # noqa: E402
import sounddevice as sd  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402
from opencc import OpenCC  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

CONVERTERS = {"simplified": OpenCC("t2s"), "traditional": OpenCC("s2t")}


def normalize_punctuation(seg_text):
    """只处理明确的情况:汉字/假名后的半角标点转全角;纯英文句子的全角标点转半角加空格。"""
    if not CJK.search(seg_text):
        out = "".join(FULL_TO_HALF.get(c, c) for c in seg_text)
        return re.sub(r" {2,}", " ", out)
    out = ASCII_AFTER_CJK.sub(lambda m: m.group(1) + HALF_TO_FULL[m.group(2)], seg_text)
    if KANA.search(out):
        out = out.replace("，", "、")
    return SPACE_AFTER_FULL.sub(r"\1", out)


def convert_script(seg_text):
    conv = CONVERTERS.get(cfg["chinese_script"])
    # 含假名的句子是日语,汉字(如「話」)不能当繁体转
    if conv is None or KANA.search(seg_text):
        return seg_text
    return conv.convert(seg_text)

SR = 16000
COLORS = {"loading": "#888888", "idle": "#2e9e4f", "recording": "#d93025", "working": "#f2a900"}

cfg = load_config()
state = "loading"
buf = []
model = None
lock = threading.Lock()
icon = None


def make_icon(color):
    # 超采样后缩小以获得抗锯齿；256px 让 ICO 包含 16~256 全部尺寸，高 DPI 下选用大图
    big = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    ImageDraw.Draw(big).ellipse((64, 64, 960, 960), fill=color)
    return big.resize((256, 256), Image.LANCZOS)


def set_state(new, title=None):
    global state
    state = new
    if icon:
        icon.icon = make_icon(COLORS[new])
        icon.title = title or f"super-whisper: {new}"


def beep(freq, ms=100):
    threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()


def audio_cb(indata, frames, t, status):
    if state == "recording":
        buf.append(indata.copy())
        if sum(len(b) for b in buf) > cfg["max_seconds"] * SR:
            threading.Thread(target=toggle, daemon=True).start()


def transcribe(chunks):
    try:
        audio = np.concatenate(chunks).flatten()
        if len(audio) < SR * 0.3:
            set_state("idle")
            return
        segments, _ = model.transcribe(
            audio,
            language=cfg["language"],
            multilingual=cfg["multilingual"],
            vad_filter=True,
            initial_prompt=cfg["initial_prompt"] or None,
            condition_on_previous_text=False,
        )
        pieces = [convert_script(s.text) for s in segments]
        if cfg["normalize_punctuation"]:
            pieces = [normalize_punctuation(p) for p in pieces]
        text = "".join(pieces).strip()
        if text:
            previous = pyperclip.paste() if cfg["auto_paste"] and cfg["restore_clipboard"] else ""
            pyperclip.copy(text)
            beep(1200)
            if cfg["auto_paste"]:
                time.sleep(0.05)
                keyboard.send("ctrl+v")
                if previous:
                    time.sleep(0.4)  # 等目标程序读完剪贴板再还原
                    pyperclip.copy(previous)
            if icon and cfg["notify_result"]:
                icon.notify(text[:120], "已复制到剪贴板")
        else:
            beep(300, 200)
    except Exception as e:
        beep(300, 400)
        if icon:
            icon.notify(str(e)[:200], "识别失败")
    finally:
        set_state("idle")


def toggle():
    global buf
    with lock:
        if state == "idle":
            buf = []
            set_state("recording")
            beep(900)
        elif state == "recording":
            chunks, buf = buf, []
            set_state("working")
            beep(600)
            threading.Thread(target=transcribe, args=(chunks,), daemon=True).start()


class RestrictedDetector:
    """每句语言检测只在允许的语言里选,并给偏好语言加权,避免误判成韩语/粤语等。"""

    def __init__(self, inner, allowed, bias):
        self._inner = inner
        self._allowed = {f"<|{c}|>" for c in allowed}
        self._bias = {f"<|{c}|>": w for c, w in bias.items()}

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def detect_language(self, *args, **kwargs):
        results = self._inner.detect_language(*args, **kwargs)
        out = []
        for per_sample in results:
            scored = [
                (tok, p * self._bias.get(tok, 1.0))
                for tok, p in per_sample
                if tok in self._allowed
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            out.append(scored or per_sample)
        return out


def load_model():
    global model
    try:
        model = WhisperModel(cfg["model"], device="cuda", compute_type="float16")
    except Exception as e:
        icon.notify(f"CUDA 失败,改用 CPU: {e}"[:200], "super-whisper")
        model = WhisperModel(cfg["model"], device="cpu", compute_type="int8")
    if cfg["multilingual"]:
        model.model = RestrictedDetector(model.model, cfg["languages"], cfg["language_bias"])
    # 预热,避免第一次识别卡顿
    list(model.transcribe(np.zeros(SR, dtype="float32"))[0])
    set_state("idle", f"super-whisper: 就绪 ({cfg['hotkey']})")
    beep(1000)


def set_script(key):
    def handler(icon_, item):
        cfg["chinese_script"] = key
        save_config()

    return handler


def quit_app(icon_, item):
    keyboard.unhook_all()
    icon_.stop()


def build_menu():
    script_items = [
        pystray.MenuItem(
            label,
            set_script(key),
            checked=lambda item, key=key: cfg["chinese_script"] == key,
            radio=True,
        )
        for key, label in SCRIPT_CHOICES.items()
    ]
    return pystray.Menu(
        pystray.MenuItem("中文字形", pystray.Menu(*script_items)),
        pystray.MenuItem("退出", quit_app),
    )


def main():
    global icon
    stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", callback=audio_cb)
    stream.start()
    keyboard.add_hotkey(cfg["hotkey"], toggle)
    icon = pystray.Icon(
        "super-whisper",
        make_icon(COLORS["loading"]),
        "super-whisper: 加载模型中…",
        menu=build_menu(),
    )
    threading.Thread(target=load_model, daemon=True).start()
    icon.run()
    stream.stop()
    sys.exit(0)


if __name__ == "__main__":
    main()
