"""M1-④ 自动归类
读取 data/styles_meta.json，按规则分到 30 大类，
'数字艺术' 进一步做二级细分；同时把 anime/manga 从插画拆出。
输出 data/catalog.json。
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------- 顶级大类规则（注意顺序：先匹配的优先） ----------
# 形如 (中文名, English, [关键字...])，关键字会以 lowercase substring 匹配
PRIMARY_RULES: list[tuple[str, str, list[str]]] = [
    # 二次元单独抽出，必须在"插画"之前
    ("二次元", "Anime/Manga",
     ["anime", "manga", "manhwa", "manhua", "chibi", "shojo", "shonen"]),
    # 数字艺术（之后会再做二级细分）
    ("数字艺术", "Digital Art",
     ["digital", " 3d", "3d ", "cgi", "vector", "render"]),
    # 插画
    ("插画", "Illustration",
     ["illustration", "illustrative", "comic ", "comics", "cartoon",
      "storybook", "children's book"]),
    # 图像小说（必须在插画之后才不被吃掉？其实顺序：插画里不含 graphic novel，所以放哪都行）
    ("图像小说", "Graphic Novel",
     ["graphic novel"]),
    # 排版/字体
    ("排版字体", "Typography",
     ["typography", "typographic", "lettering", "calligraphic poster"]),
    # 绘画
    ("绘画", "Painting",
     ["painting", "oil ", " oil", "acrylic", "gouache", "tempera"]),
    # 水彩水墨
    ("水彩水墨", "Watercolor/Ink",
     ["watercolor", "watercolour", "ink ", " ink", "sumi", "wash painting",
      "calligraph"]),
    # 版画与素描
    ("版画素描", "Print/Sketch",
     ["lithograph", "etching", "engraving", "woodcut", "linocut", "sketch",
      "charcoal", "pencil"]),
    # 摄影
    ("摄影", "Photography",
     ["photo", "photograph", "cinematic", "film noir", "noir"]),
    # 抽象
    ("抽象", "Abstract",
     ["abstract", "abstraction", "geometric abstraction", "minimalism",
      "minimalist"]),
    # 印象/后印象
    ("印象派", "Impressionism",
     ["impression", "post-impression", "pointillism"]),
    # 表现/超现实
    ("表现超现实", "Surreal/Expressionism",
     ["expressionism", "expressive", "surreal", "dadaism", "psychedelic"]),
    # 文艺复兴/古典
    ("古典", "Classical",
     ["renaissance", "baroque", "rococo", "neoclassic", "classical",
      "romanticism", "chiaroscuro"]),
    # 赛博朋克
    ("赛博朋克", "Cyberpunk",
     ["cyberpunk", "futuristic", "retro-futur", "sci-fi", "synthwave",
      "vaporwave"]),
    # 蒸汽朋克
    ("蒸汽朋克", "Steampunk", ["steampunk"]),
    # 波普/海报
    ("波普海报", "Pop/Poster",
     ["pop ", "pop art", "poster", "propaganda", "graffiti", "street art"]),
    # 装饰艺术
    ("装饰艺术", "Art Deco/Nouveau",
     ["deco", "nouveau", "arts and crafts"]),
    # 民俗与文化
    ("民俗文化", "Folk/Cultural",
     ["folk", "tribal", "aboriginal", "ethnic", "ukiyo", "japanese ",
      "chinese ", "indian ", "african", "celtic", "mexican"]),
    # 幻想
    ("幻想", "Fantasy",
     ["fantasy", "mythic", "mythological", "fairy"]),
    # 复古/做旧
    ("复古", "Vintage/Retro",
     ["vintage", "retro", "antique", "victorian", "edwardian", "19th",
      "18th"]),
    # 风景/自然
    ("风景自然", "Landscape/Nature",
     ["landscape", "botanical", "floral", "marine", "maritime", "seascape"]),
    # 肖像
    ("肖像", "Portrait", ["portrait", "portraiture"]),
    # 建筑/室内
    ("建筑室内", "Architecture",
     ["architectur", "interior", "urban", "cityscape"]),
    # 时尚
    ("时尚", "Fashion", ["fashion", "editorial", "runway"]),
    # 拼贴/混合
    ("拼贴混合", "Collage/Mixed",
     ["collage", "mixed media", "paper craft", "origami", "papercut"]),
    # 雕塑
    ("雕塑", "Sculpture",
     ["sculpture", "bas-relief", "relief"]),
    # 暗黑/哥特
    ("暗黑哥特", "Dark/Gothic",
     ["gothic", "dark ", "horror", "macabre", "dystop"]),
    # 写实/学院派（新增）
    ("写实学院", "Realism/Academic",
     ["realism", "realist", "academic", "academicism", "regionalism"]),
    # 现代/当代（新增）
    ("现代当代", "Modern/Contemporary",
     ["modernism", "modernist", "modern art", "contemporary"]),
]

# ---------- 数字艺术二级细分 ----------
DIGITAL_SUB_RULES: list[tuple[str, str, list[str]]] = [
    ("3D 动画/渲染", "3D Animation/Render",
     ["3d animation", "3d digital animation", "3d render", "3d rendering",
      "3d model", "3d ", " 3d"]),
    ("CGI/电影渲染", "CGI/Cinematic Render",
     ["cgi", "cinematic", "render", "rendering"]),
    ("矢量/扁平", "Vector/Flat",
     ["vector", "flat ", "flat design"]),
    ("数字绘画", "Digital Painting",
     ["digital painting"]),
    ("数字插画", "Digital Illustration",
     ["digital illustration", "digital illustrative"]),
    ("数字艺术其它", "Other Digital Art", []),  # 兜底
]


def classify(prefix: str) -> tuple[str, str, str | None, str | None]:
    """返回 (cn, en, sub_cn, sub_en)。未命中返回 ('其它','Other',None,None)。"""
    p = (prefix or "").lower()
    for cn, en, kws in PRIMARY_RULES:
        if any(k in p for k in kws):
            if cn == "数字艺术":
                for scn, sen, skws in DIGITAL_SUB_RULES:
                    if skws and any(k in p for k in skws):
                        return cn, en, scn, sen
                return cn, en, "数字艺术其它", "Other Digital Art"
            return cn, en, None, None
    return "其它", "Other", None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default=str(ROOT / "data" / "styles_meta.json"))
    ap.add_argument("--out", default=str(ROOT / "data" / "catalog.json"))
    args = ap.parse_args()

    meta_path = Path(args.meta)
    out_path = Path(args.out)
    if not meta_path.exists():
        raise SystemExit(f"找不到 {meta_path}, 请先运行 build_dataset.py")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # 主类 -> 子类 -> [style_key,...]
    catalog: dict[str, dict] = {}
    cat_count: dict[str, int] = defaultdict(int)
    sub_count: dict[str, int] = defaultdict(int)

    for key, info in meta.items():
        prefix = info.get("style_prefix") or info.get("style_full") or key
        cn, en, scn, sen = classify(prefix)
        info["category"] = cn
        info["category_en"] = en
        info["sub_category"] = scn
        info["sub_category_en"] = sen
        cat_count[cn] += 1
        bucket = catalog.setdefault(cn, {
            "name_cn": cn,
            "name_en": en,
            "count": 0,
            "subs": {},
            "items": [],   # 没有子类的直接平铺
        })
        bucket["count"] += 1
        if scn:
            sub = bucket["subs"].setdefault(scn, {
                "name_cn": scn,
                "name_en": sen,
                "count": 0,
                "items": [],
            })
            sub["count"] += 1
            sub["items"].append(key)
            sub_count[f"{cn}/{scn}"] += 1
        else:
            bucket["items"].append(key)

    # 写回 styles_meta.json (附加 category 字段)
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 写出 catalog.json
    out_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 控制台输出统计
    print(f"{'大类':<24}{'子类':<22}{'风格数':>8}")
    print("-" * 56)
    for cn, info in sorted(catalog.items(), key=lambda x: -x[1]["count"]):
        if info["subs"]:
            for scn, sub in sorted(info["subs"].items(),
                                    key=lambda x: -x[1]["count"]):
                print(f"{cn:<24}{scn:<22}{sub['count']:>8}")
        else:
            print(f"{cn:<24}{'':<22}{info['count']:>8}")
    print("-" * 56)
    total = sum(info["count"] for info in catalog.values())
    print(f"{'合计':<46}{total:>8}")
    print(f"\n[完成] catalog.json -> {out_path}")
    print(f"[完成] meta 已附加 category 字段 -> {meta_path}")


if __name__ == "__main__":
    main()
