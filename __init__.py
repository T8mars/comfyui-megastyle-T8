"""ComfyUI 入口：注册节点、注册前端目录、注册自定义 HTTP 路由。"""
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# 让 ComfyUI 把 web/ 目录暴露为静态资源 /extensions/comfyui-metastyle-T8/*
WEB_DIRECTORY = "./web"

# 注册自定义 HTTP API 路由
try:
    from . import api  # noqa: F401  导入即注册
except Exception as e:
    print(f"[MetaStyle-T8] api 路由注册失败: {e}")

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]

print("[MetaStyle-T8] 节点已加载: MetaStyleT8Picker")
