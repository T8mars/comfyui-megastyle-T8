"""M1-⑧ 构建搜索索引
读取 styles_meta.json，生成两份产物：

1. data/search_index.json
   {
     "tokens": { "<token>": [idx1, idx2, ...] },   # 倒排
     "styles": [ {key, prefix, cat, sub, thumb}, ... ]   # 轻量列表（按 idx 索引）
   }
2. data/styles_lite.json   （前端首屏快速加载）
   [ {key, prefix, cat, sub, thumb}, ... ]   # 与 styles 同序

token 来源:
- style_prefix 拆词
- style_full 拆词
- category / sub_category（中英）
- sample_content 中的高频名词（截断）

特点:
- 全部 lowercase
- 中文按字符切分（避免依赖 jieba）
- 拼音可选（pypinyin 已安装则启用）
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from pypinyin import lazy_pinyin, Style
    HAS_PINYIN = True
except Exception:
    HAS_PINYIN = False

WORD_RE = re.compile(r"[a-z0-9]+")
CN_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> set[str]:
    """English 按 \\w 切分；中文按单字切分；并加入拼音首字母与全拼。"""
    if not text:
        return set()
    text = text.lower()
    tokens: set[str] = set(WORD_RE.findall(text))

    cn = "".join(CN_CHAR_RE.findall(text))
    if cn:
        # 单字 token
        for ch in cn:
            tokens.add(ch)
        if HAS_PINYIN:
            full = "".join(lazy_pinyin(cn))
            initials = "".join(
                p[0] for p in lazy_pinyin(cn, style=Style.FIRST_LETTER) if p
            )
            if full:
                tokens.add(full)
            if initials:
                tokens.add(initials)
            # 同时把每个字符的全拼加入
            for p in lazy_pinyin(cn):
                if p:
                    tokens.add(p)
    return tokens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default=str(ROOT / "data" / "styles_meta.json"))
    ap.add_argument("--out", default=str(ROOT / "data" / "search_index.json"))
    ap.add_argument("--lite", default=str(ROOT / "data" / "styles_lite.json"))
    ap.add_argument("--content-words", type=int, default=8,
                    help="每条 sample_content 取前 N 个英文单词进入索引")
    args = ap.parse_args()

    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    print(f"[信息] 共 {len(meta)} 条风格  pypinyin={HAS_PINYIN}")

    styles_list: list[dict] = []
    inv: dict[str, list[int]] = defaultdict(list)

    for idx, (key, info) in enumerate(meta.items()):
        prefix = info.get("style_prefix") or ""
        cat = info.get("category") or ""
        cat_en = info.get("category_en") or ""
        sub = info.get("sub_category") or ""
        sub_en = info.get("sub_category_en") or ""
        full = info.get("style_full") or key
        content = info.get("sample_content") or ""

        # content 仅取前若干词，避免索引过大
        content_short = " ".join(WORD_RE.findall(content.lower())[: args.content_words])

        toks: set[str] = set()
        toks |= tokenize(prefix)
        toks |= tokenize(full)
        toks |= tokenize(cat)
        toks |= tokenize(cat_en)
        toks |= tokenize(sub)
        toks |= tokenize(sub_en)
        toks |= tokenize(content_short)

        for t in toks:
            if 1 <= len(t) <= 32:
                inv[t].append(idx)

        styles_list.append({
            "k": key,                # key (style_full safe-name)
            "p": prefix,             # 风格前缀（短）
            "c": cat,                # 大类中文
            "ce": cat_en,            # 大类英文
            "s": sub,                # 子类中文（可空）
            "se": sub_en,            # 子类英文（可空）
            "t": f"thumbs/{key}.webp",
            "i": f"styles/{Path(info.get('image','')).name}",
        })

        if (idx + 1) % 1000 == 0:
            print(f"  索引中 {idx+1}/{len(meta)}", end="\r", flush=True)

    print()
    # 把 inv 中的 list 排序去重
    for t in inv:
        inv[t] = sorted(set(inv[t]))

    out = {
        "version": 1,
        "count": len(styles_list),
        "has_pinyin": HAS_PINYIN,
        "tokens": inv,
        "styles": styles_list,
    }
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    Path(args.lite).write_text(
        json.dumps(styles_list, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    print(f"[完成] search_index.json -> {args.out}")
    print(f"  tokens: {len(inv)}, styles: {len(styles_list)}")
    print(f"[完成] styles_lite.json  -> {args.lite}")


if __name__ == "__main__":
    main()
