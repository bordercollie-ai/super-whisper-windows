# super-whisper-windows

Windows 托盘小工具：按全局快捷键开始录音，再按一次结束，本地用 faster-whisper 识别（中文为主，可混杂英语和日语），结果粘贴到当前光标处。

## 使用

1. 双击 `run.vbs` 启动（后台运行，无窗口）。托盘图标灰色表示正在加载模型，变绿并响一声后即可使用。
2. 按 `Alt+.` 开始录音（图标变红）。
3. 说话，再按一次 `Alt+.` 结束（图标变黄，识别中）。
4. 识别完成后文字自动粘贴到光标处（默认不弹通知）。
5. 右键托盘图标可以直接切换常用设置（见下），也可以退出。

开机自启：`Win+R` 输入 `shell:startup`，把 `run.vbs` 的快捷方式放进去。

## 默认设置

| 设置 | 默认值 | 说明 |
|---|---|---|
| `hotkey` | `alt+.` | 全局快捷键 |
| `model` | `large-v3-turbo` | Whisper 模型，默认使用 CUDA，失败时退回 CPU |
| `language` | `zh` | 默认语言 |
| `multilingual` | `true` | 每句话单独检测语言 |
| `languages` | `["zh", "en", "ja"]` | 检测时只在这些语言里选 |
| `language_bias` | `{"zh": 4.0}` | 给某种语言加权，数值越大越倾向它，日语或英语被误判太多时调高中文 |
| `beam_size` | `5` | 束搜索宽度，越大越准但越慢 |
| `hotwords` | 空 | 常说的词，用空格分隔，如 `提交 推送 commit push`，识别时会更倾向这些词 |
| `initial_prompt` | 中英日各一句普通问候 | 引导输出简体和标点风格，也可以放常用专有名词，留空则不使用 |
| `auto_paste` | `true` | 识别后自动粘贴；`false` 则只放剪贴板 |
| `restore_clipboard` | `true` | 自动粘贴后还原原来的剪贴板文字 |
| `max_seconds` | `300` | 录音时长上限，超过自动结束并识别 |
| `chinese_script` | `simplified` | `simplified` 简体、`traditional` 繁体、`none` 不转换 |
| `normalize_punctuation` | `true` | 中日文语境用全角标点，纯英文用半角加空格 |
| `notify_result` | `false` | 识别成功后是否弹通知；出错时总会通知 |
| `debug_log` | `false` | 设为 `true` 会把每次识别的音量、语言检测概率、文字和置信度写入 `debug.log`，用来排查识别不准 |

## 修改设置

编辑项目目录下的 `config.json`（托盘菜单里的「打开配置文件」可直接打开），保存后重启应用生效。

托盘右键菜单可以直接切换这些常用设置，切换后立即生效并写入 `config.json`：中文字形、默认语言、逐句检测语言、规范标点、自动粘贴、粘贴后还原剪贴板、识别后弹通知、调试日志。快捷键、模型、提示词、`language_bias`、`beam_size` 等只能改 `config.json`。

## 测试

```powershell
uv pip install --python .venv\Scripts\python.exe edge-tts
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`tests/test_text.py` 测试标点和繁简转换，不需要显卡。`tests/test_transcribe.py` 用 edge-tts 合成中、英、日语音并跑真实识别，需要显卡；edge-tts 会把测试句子发送到微软的在线 TTS 服务，没装 edge-tts 时这部分会被跳过。

## 安装

需要 NVIDIA 显卡和 [uv](https://docs.astral.sh/uv/)。

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe --require-hashes -r requirements.txt
```

`requirements.txt` 固定了所有依赖的版本和哈希，防止被替换成被篡改的包。升级依赖时用 `uv pip compile pyproject.toml --python-version 3.12 --python-platform windows --generate-hashes -o requirements.txt` 重新生成。

首次运行会下载模型（约 1.5GB）。
