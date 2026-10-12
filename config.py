"""模型配置：密钥只在内存里；磁盘文件仅保存非敏感连接选项。"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from PySide6.QtCore import QStandardPaths, QSaveFile, QIODevice


PRESETS = {
    "DeepSeek": ("https://api.deepseek.com", "deepseek-flash"),
    "OpenAI": ("https://api.openai.com/v1", "gpt-4.1-mini"),
    "自定义服务": ("", ""),
}


@dataclass
class ModelConfig:
    provider: str = "DeepSeek"
    base_url: str = PRESETS["DeepSeek"][0]
    model: str = PRESETS["DeepSeek"][1]
    api_key: str = field(default="", repr=False)
    stream: bool = True
    tools_enabled: bool = False

    def endpoint(self):
        """只接受明确的服务地址，不在 URL 中携带密钥。"""
        raw = self.base_url.strip()
        if any(char.isspace() for char in raw):
            raise ValueError("API 地址不能包含空格或换行。")
        try:
            url = urlsplit(raw)
            _ = url.port  # 读取端口，让无效格式在发送前报错。
        except ValueError:
            raise ValueError("API 地址或端口格式不正确。") from None
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("请填写完整 API 地址，不要包含账号、密钥、查询参数或锚点。")
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if url.scheme != "https" and not (url.scheme == "http" and local):
            raise ValueError("远程服务请使用 HTTPS；本机服务可使用 HTTP。")
        path = url.path.rstrip("/")
        if not path.endswith("/chat/completions"):
            path += "/chat/completions"
        return urlunsplit((url.scheme, url.netloc, path, "", ""))

    def validate(self):
        endpoint = self.endpoint()
        if self.provider not in PRESETS:
            raise ValueError("请选择支持的服务商。")
        if not self.model.strip() or len(self.model) > 200:
            raise ValueError("请填写有效的模型名称。")
        if any(ord(c) < 33 or ord(c) > 126 for c in self.api_key):
            raise ValueError("API Key 应为连续的英文字符，请检查空格或换行。")
        if len(self.api_key) > 4096:
            raise ValueError("API Key 过长，请检查填写内容。")
        local = urlsplit(endpoint).hostname in {"localhost", "127.0.0.1", "::1"}
        if not self.api_key and not (self.provider == "自定义服务" and local):
            raise ValueError("请填写 API Key。本机自定义服务可留空。")
        return self


def settings_path():
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)) / "model.json"


def load_config(path=None):
    try:
        data = json.loads((path or settings_path()).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("provider") not in PRESETS:
            return ModelConfig()
        if not all(isinstance(data.get(key), str) for key in ("base_url", "model")):
            return ModelConfig()
        return ModelConfig(provider=data["provider"], base_url=data["base_url"],
                           model=data["model"], stream=data.get("stream") is not False)
    except (OSError, ValueError):
        return ModelConfig()


def save_config(config, path=None):
    config.validate()
    destination = path or settings_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    # 明确列出可保存的字段，避免以后误把 api_key 序列化到磁盘。
    data = {key: getattr(config, key) for key in ("provider", "base_url", "model", "stream")}
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    file = QSaveFile(str(destination))
    if not file.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("无法写入本机设置目录。")
    if file.write(content) != len(content) or not file.commit():
        raise OSError("保存连接设置失败，请检查本机目录权限。")
