"""M1-② 构建数据集
从源数据 (E:\\parquet\\) 拷贝代表图到 data/styles/，
并从 parquet 反查每个风格的代表 content/id，输出 data/styles_meta.json。

用法:
    python build_dataset.py                       # 默认 copy 模式
    python build_dataset.py --mode link           # 同卷硬链接（更省空间）
    python build_dataset.py --src E:\\parquet --dst ../data
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent  # comfyui-metastyle-T8/
ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def parse_index_tsv(tsv_path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(tsv_path, "r", encoding="utf-8") as f:
        f.readline()  # 表头
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            style, row, sid, fname = parts[0], int(parts[1]), parts[2], parts[3]
            out[style] = {"row": row, "id": sid, "filename": fname}
    return out


def fetch_contents_by_rows(parquet_path: Path, rows_needed: set[int]) -> dict[int, str]:
    pf = pq.ParquetFile(str(parquet_path))
    n_groups = pf.metadata.num_row_groups
    rg_offsets = []
    acc = 0
    for i in range(n_groups):
        rg_offsets.append(acc)
        acc += pf.metadata.row_group(i).num_rows
    rg_offsets.append(acc)

    rows_per_rg: dict[int, list[int]] = {}
    for r in rows_needed:
        lo, hi = 0, n_groups - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if r < rg_offsets[mid]:
                hi = mid - 1
            elif r >= rg_offsets[mid + 1]:
                lo = mid + 1
            else:
                rows_per_rg.setdefault(mid, []).append(r)
                break

    result: dict[int, str] = {}
    total = len(rows_needed)
    done = 0
    for rg_idx in sorted(rows_per_rg.keys()):
        wanted = rows_per_rg[rg_idx]
        batch = pf.read_row_group(rg_idx, columns=["content"]).to_pylist()
        rg_start = rg_offsets[rg_idx]
        for r in wanted:
            local = r - rg_start
            if 0 <= local < len(batch):
                result[r] = batch[local].get("content") or ""
        done += len(wanted)
        print(f"  反查 content: {done}/{total}", end="\r", flush=True)
    print()
    return result


def link_or_copy(src: Path, dst: Path, mode: str) -> bool:
    if dst.exists():
        return False
    if mode == "link":
        try:
            os.link(src, dst)
            return True
        except OSError:
            shutil.copy2(src, dst)
            return True
    shutil.copy2(src, dst)
    return True


def idx_map_lookup(idx_map: dict, key: str) -> str | None:
    if key in idx_map:
        return key
    for full in idx_map.keys():
        cleaned = ILLEGAL.sub("_", full)[:80].strip(" .")
        if cleaned == key:
            return full
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=r"E:\parquet")
    ap.add_argument("--dst", default=str(ROOT / "data"))
    ap.add_argument("--mode", choices=["copy", "link"], default="copy")
    ap.add_argument("--parquet-name", default="train-00000.parquet")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    src_styles = src / "styles"
    src_index = src_styles / "styles_index.tsv"
    src_parquet = src / args.parquet_name

    if not src_styles.exists():
        sys.exit(f"[错误] 找不到源 styles 目录: {src_styles}")
    if not src_parquet.exists():
        sys.exit(f"[错误] 找不到 parquet: {src_parquet}")

    dst_styles = dst / "styles"
    dst.mkdir(parents=True, exist_ok=True)
    dst_styles.mkdir(parents=True, exist_ok=True)

    image_files = [f for f in os.listdir(src_styles)
                   if not f.endswith(".tsv")]
    print(f"[信息] 源风格图片: {len(image_files)} 张")

    idx_map: dict[str, dict] = {}
    if src_index.exists():
        idx_map = parse_index_tsv(src_index)
        print(f"[信息] 解析 styles_index.tsv: {len(idx_map)} 条")
    else:
        print("[警告] 未找到 styles_index.tsv，content/id 字段将留空")

    print(f"[信息] {args.mode} 图片到 {dst_styles} ...")
    new_count = 0
    for i, fname in enumerate(image_files):
        s = src_styles / fname
        d = dst_styles / fname
        if link_or_copy(s, d, args.mode):
            new_count += 1
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(image_files)}", end="\r", flush=True)
    print(f"  完成，新增 {new_count} 个文件")

    meta_path = dst / "styles_meta.json"
    cached: dict = {}
    if meta_path.exists():
        try:
            cached = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            cached = {}

    rows_needed: set[int] = set()
    style_to_row: dict[str, int] = {}
    style_to_id: dict[str, str] = {}
    for fname in image_files:
        key = os.path.splitext(fname)[0]
        if key in cached and cached[key].get("sample_content"):
            continue
        full = idx_map_lookup(idx_map, key)
        if full and idx_map.get(full):
            rows_needed.add(idx_map[full]["row"])
            style_to_row[key] = idx_map[full]["row"]
            style_to_id[key] = idx_map[full]["id"]

    print(f"[信息] 需要反查 content 的行数: {len(rows_needed)}")
    contents: dict[int, str] = {}
    if rows_needed:
        contents = fetch_contents_by_rows(src_parquet, rows_needed)

    meta = dict(cached)
    for fname in image_files:
        key = os.path.splitext(fname)[0]
        if key in meta and meta[key].get("sample_content"):
            continue
        row = style_to_row.get(key)
        sid = style_to_id.get(key, "")
        content = contents.get(row, "") if row is not None else ""
        prefix = ""
        m = re.match(r"In the style of ([^,]+)", key, re.I)
        if m:
            prefix = m.group(1).strip()
        meta[key] = {
            "key": key,
            "image": f"styles/{fname}",
            "thumb": f"thumbs/{key}.webp",
            "style_full": key,
            "style_prefix": prefix,
            "sample_id": sid,
            "sample_row": row,
            "sample_content": content,
        }

    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[完成] styles_meta.json 写入 {meta_path}  共 {len(meta)} 条")


if __name__ == "__main__":
    main()
