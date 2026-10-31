# super-whisper-windows

Windows 托盘小工具：按全局快捷键开始录音，再按一次结束，本地用 faster-whisper 识别（中文为主，可混杂英语和日语），结果粘贴到当前光标处。

## 使用

1. 双击 `run.vbs` 启动（后台运行，无窗口）。托盘图标灰色表示正在加载模型，变绿并响一声后即可使用。
2. 按 `Alt+.` 开始录音（图标变红）。
3. 说话，再按一次 `Alt+.` 结束（图标变黄，识别中）。
4. 识别完成后文字自动粘贴到光标处（默认不弹通知）。
5. 右键托盘图标可切换中文字形或退出。

开机自启：`Win+R` 输入 `shell:startup`，把 `run.vbs` 的快捷方式放进去。

## 默认设置

| 设置 | 默认值 | 说明 |
|---|---|---|
| `hotkey` | `alt+.` | 全局快捷键 |
| `model` | `large-v3-turbo` | Whisper 模型，默认使用 CUDA，失败时退回 CPU |
| `language` | `zh` | 默认语言 |
| `multilingual` | `true` | 每句话单独检测语言 |
| `languages` | `["zh", "en", "ja"]` | 检测时只在这些语言里选 |
| `language_bias` | `{"zh": 2.0}` | 给某种语言加权，数值越大越倾向它 |
| `initial_prompt` | 中英日各一句普通问候 | 引导输出简体和标点风格，也可以放常用专有名词，留空则不使用 |
| `auto_paste` | `true` | 识别后自动粘贴；`false` 则只放剪贴板 |
| `restore_clipboard` | `true` | 自动粘贴后还原原来的剪贴板文字 |
| `max_seconds` | `300` | 录音时长上限，超过自动结束并识别 |
| `chinese_script` | `simplified` | `simplified` 简体、`traditional` 繁体、`none` 不转换 |
| `normalize_punctuation` | `true` | 中日文语境用全角标点，纯英文用半角加空格 |
| `notify_result` | `false` | 识别成功后是否弹通知；出错时总会通知 |

## 修改设置

编辑项目目录下的 `config.json`，保存后重启应用生效。只有「中文字形」可以在托盘右键菜单里直接切换，切换后立即生效并写入 `config.json`。

## 安装

需要 NVIDIA 显卡和 [uv](https://docs.astral.sh/uv/)。

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r pyproject.toml
```

首次运行会下载模型（约 1.5GB）。
