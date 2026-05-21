"""注册自定义 HTTP 路由到 ComfyUI 的 aiohttp server。

路由 (前缀 /metastyle):
  GET /metastyle/catalog            -> 大类 + 子类 + 计数
  GET /metastyle/lite               -> 轻量 styles 列表（首屏使用）
  GET /metastyle/search?q=&cat=&sub=&limit=  -> 搜索结果
  GET /metastyle/thumb/<key>        -> 缩略图
  GET /metastyle/preview/<key>      -> 原图（大图预览）
  GET /metastyle/meta/<key>         -> 单条完整元数据
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from aiohttp import web

try:
    from server import PromptServer  # ComfyUI 内置
except Exception:
    PromptServer = None  # 允许独立测试

from .nodes import (
    DATA, ROOT, load_catalog, load_lite, load_meta,
)

WORD_RE = re.compile(r"[a-z0-9]+")
CN_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")

_index_cache = None


def load_index() -> dict:
    global _index_cache
    if _index_cache is None:
        p = DATA / "search_index.json"
        _index_cache = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {
            "tokens": {}, "styles": []
        }
    return _index_cache


def query_tokens(q: str) -> list[str]:
    """把搜索词拆为 token 列表（与 build_index 同口径）。"""
    if not q:
        return []
    q = q.strip().lower()
    toks = WORD_RE.findall(q)
    cn = "".join(CN_CHAR_RE.findall(q))
    if cn:
        toks.extend(list(cn))
    return [t for t in toks if t]


def _safe_join(base: Path, rel: str) -> Path | None:
    """防穿越的安全拼接。"""
    p = (base / rel).resolve()
    base_r = base.resolve()
    if str(p).startswith(str(base_r)):
        return p
    return None


# ---------------- 路由实现 ----------------

routes = web.RouteTableDef()


@routes.get("/metastyle/catalog")
async def r_catalog(request: web.Request):
    cat = load_catalog()
    # 精简：去掉 items 列表，只保留计数
    light = {}
    for cn, info in cat.items():
        light[cn] = {
            "name_cn": info.get("name_cn", cn),
            "name_en": info.get("name_en", ""),
            "count": info.get("count", 0),
            "subs": {
                scn: {"name_cn": s["name_cn"],
                      "name_en": s["name_en"],
                      "count": s["count"]}
                for scn, s in info.get("subs", {}).items()
            },
        }
    return web.json_response(light)


@routes.get("/metastyle/lite")
async def r_lite(request: web.Request):
    return web.json_response(load_lite())


@routes.get("/metastyle/search")
async def r_search(request: web.Request):
    q = request.query.get("q", "").strip()
    cat = request.query.get("cat", "").strip()
    sub = request.query.get("sub", "").strip()
    try:
        limit = max(1, min(int(request.query.get("limit", "120")), 500))
    except ValueError:
        limit = 120
    try:
        offset = max(0, int(request.query.get("offset", "0")))
    except ValueError:
        offset = 0

    idx = load_index()
    styles = idx["styles"]

    # 1. 关键字命中（按 token 求交集，并以 token 命中数作为分数）
    if q:
        toks = query_tokens(q)
        scores: dict[int, int] = {}
        for t in toks:
            # 完全匹配
            for i in idx["tokens"].get(t, []):
                scores[i] = scores.get(i, 0) + 2
            # 前缀匹配（最多展开 50 个 token，避免 token 表全扫）
            if len(t) >= 2:
                cnt = 0
                for tk, ids in idx["tokens"].items():
                    if cnt > 50:
                        break
                    if tk != t and tk.startswith(t):
                        for i in ids:
                            scores[i] = scores.get(i, 0) + 1
                        cnt += 1
        candidates = sorted(scores.items(), key=lambda x: -x[1])
        ordered = [styles[i] for i, _ in candidates]
    else:
        ordered = list(styles)

    # 2. 大类/子类过滤
    if cat:
        ordered = [s for s in ordered if s.get("c") == cat or s.get("ce") == cat]
    if sub:
        ordered = [s for s in ordered if s.get("s") == sub or s.get("se") == sub]

    return web.json_response({
        "q": q, "cat": cat, "sub": sub,
        "total": len(ordered),
        "offset": offset,
        "limit": limit,
        "items": ordered[offset:offset + limit],
    })


def _send_image(key: str, sub: str, content_type_hint: str = ""):
    """通用：返回 data/<sub>/ 下与 key 对应的图片文件。"""
    meta = load_meta()
    info = meta.get(key)
    if not info:
        return web.json_response({"error": "key not found"}, status=404)

    if sub == "thumb":
        rel = f"thumbs/{key}.webp"
    else:
        rel = info["image"]

    fp = _safe_join(DATA, rel)
    if not fp or not fp.exists():
        # thumb 缺失时回退到原图
        if sub == "thumb":
            fp = _safe_join(DATA, info["image"])
            if not fp or not fp.exists():
                return web.json_response({"error": "file missing"}, status=404)
        else:
            return web.json_response({"error": "file missing"}, status=404)

    ext = fp.suffix.lower()
    mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".gif": "image/gif", ".bmp": "image/bmp",
    }.get(ext, "application/octet-stream")
    return web.FileResponse(fp, headers={
        "Content-Type": mime,
        "Cache-Control": "public, max-age=86400",
    })


@routes.get("/metastyle/thumb/{key}")
async def r_thumb(request: web.Request):
    key = request.match_info["key"]
    return _send_image(key, "thumb")


@routes.get("/metastyle/preview/{key}")
async def r_preview(request: web.Request):
    key = request.match_info["key"]
    return _send_image(key, "preview")


@routes.get("/metastyle/meta/{key}")
async def r_meta(request: web.Request):
    key = request.match_info["key"]
    info = load_meta().get(key)
    if not info:
        return web.json_response({"error": "key not found"}, status=404)
    return web.json_response(info)


# ---------------- 注册到 ComfyUI ----------------

def _register():
    if PromptServer is None or not hasattr(PromptServer, "instance"):
        print("[MetaStyle-T8] PromptServer 未就绪，跳过路由注册")
        return
    app = PromptServer.instance.app
    app.add_routes(routes)
    print("[MetaStyle-T8] 已注册 HTTP 路由 /metastyle/*")


_register()
