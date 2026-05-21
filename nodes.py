"""MetaStyle T8 节点核心逻辑

输入:
  - style_key  (string): 选中的风格 key，前端 widget 写入
  - output_size (combo): 输出尺寸 original / 512 / 1024
  - seed (int): 预留
输出:
  - IMAGE        风格代表图 (BHWC float32 0~1)
  - style_name   风格全名
  - category     大类（中文）
  - sample_prompt 示例提示词（可直接接 CLIPTextEncode）
  - sample_id    数据集原始 id
  - meta_json    全量元数据 JSON 字符串
"""
import json
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

_meta_cache = None
_catalog_cache = None
_lite_cache = None


def load_meta() -> dict:
    global _meta_cache
    if _meta_cache is None:
        p = DATA / "styles_meta.json"
        _meta_cache = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _meta_cache


def load_catalog() -> dict:
    global _catalog_cache
    if _catalog_cache is None:
        p = DATA / "catalog.json"
        _catalog_cache = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _catalog_cache


def load_lite() -> list:
    global _lite_cache
    if _lite_cache is None:
        p = DATA / "styles_lite.json"
        _lite_cache = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return _lite_cache


def pil_to_tensor(im: Image.Image) -> torch.Tensor:
    """PIL -> ComfyUI 标准 IMAGE tensor: shape (1, H, W, 3), float32 0~1"""
    if im.mode != "RGB":
        im = im.convert("RGB")
    arr = np.asarray(im).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


def empty_image(w: int = 512, h: int = 512) -> torch.Tensor:
    return torch.zeros((1, h, w, 3), dtype=torch.float32)


class MetaStyleT8Picker:
    """T8 风格选择器：按风格挑选代表图与示例提示词。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 由前端 widget 维护的字符串：选中的 style key
                "style_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "metastyle_picker": True,  # 给前端 JS 识别用
                }),
                "output_size": (["original", "512", "768", "1024"],
                                {"default": "original"}),
            },
            "optional": {
                "seed": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFFF
                }),
            },
        }

    RETURN_TYPES = (
        "IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING",
    )
    RETURN_NAMES = (
        "image", "style_name", "category",
        "sample_prompt", "sample_id", "meta_json",
    )
    FUNCTION = "pick"
    CATEGORY = "T8/Style"

    def pick(self, style_key: str, output_size: str, seed: int = 0):
        meta = load_meta()
        style_key = (style_key or "").strip()
        info = meta.get(style_key)

        if not info:
            # 未选中或 key 无效 → 返回空图，提示文字
            return (
                empty_image(),
                style_key,
                "",
                "",
                "",
                json.dumps({"error": "style_key not found", "key": style_key},
                           ensure_ascii=False),
            )

        img_path = ROOT / "data" / info["image"]
        try:
            with Image.open(img_path) as im:
                im.load()
                if output_size != "original":
                    target = int(output_size)
                    im = im.copy()
                    im.thumbnail((target, target), Image.LANCZOS)
                tensor = pil_to_tensor(im)
        except Exception as e:
            return (
                empty_image(),
                style_key,
                info.get("category", ""),
                info.get("sample_content", ""),
                info.get("sample_id", ""),
                json.dumps({"error": str(e), "key": style_key},
                           ensure_ascii=False),
            )

        return (
            tensor,
            info.get("style_full", style_key),
            info.get("category", ""),
            info.get("sample_content", ""),
            info.get("sample_id", ""),
            json.dumps(info, ensure_ascii=False),
        )


NODE_CLASS_MAPPINGS = {
    "MetaStyleT8Picker": MetaStyleT8Picker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MetaStyleT8Picker": "MetaStyle T8 风格选择器",
}
