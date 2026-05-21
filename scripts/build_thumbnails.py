"""M1-⑥ 生成缩略图
读取 data/styles/，为每张图生成 256px webp 到 data/thumbs/。
支持多进程加速。已存在的跳过。
"""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def make_thumb(args: tuple[str, str, int, int]) -> tuple[str, bool, str]:
    src, dst, size, quality = args
    if os.path.exists(dst):
        return src, True, "skip"
    try:
        with Image.open(src) as im:
            im = im.convert("RGB") if im.mode in ("RGBA", "P", "LA") else im
            im.thumbnail((size, size), Image.LANCZOS)
            im.save(dst, "WEBP", quality=quality, method=4)
        return src, True, "ok"
    except Exception as e:
        return src, False, f"err:{e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default=str(ROOT / "data" / "styles_meta.json"))
    ap.add_argument("--src-dir", default=str(ROOT / "data" / "styles"))
    ap.add_argument("--dst-dir", default=str(ROOT / "data" / "thumbs"))
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    src_dir = Path(args.src_dir)
    dst_dir = Path(args.dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for key, info in meta.items():
        src = src_dir / Path(info["image"]).name
        dst = dst_dir / f"{key}.webp"
        if not src.exists():
            continue
        tasks.append((str(src), str(dst), args.size, args.quality))

    print(f"[信息] 待处理 {len(tasks)} 张  workers={args.workers}")

    ok = skipped = err = 0
    done = 0
    total = len(tasks)
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(make_thumb, t) for t in tasks]
        for fu in as_completed(futures):
            _, success, status = fu.result()
            done += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skipped += 1
            else:
                err += 1
            if done % 200 == 0 or done == total:
                print(
                    f"  {done}/{total}  生成 {ok}  跳过 {skipped}  失败 {err}",
                    end="\r", flush=True,
                )
    print()
    print(f"[完成] 生成 {ok}, 跳过 {skipped}, 失败 {err}")


if __name__ == "__main__":
    main()
