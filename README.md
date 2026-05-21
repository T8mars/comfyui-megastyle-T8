# comfyui-metastyle-T8

> **MetaStyle T8 风格选择器** —— 把上万种艺术风格的代表图、示例提示词全部装进 ComfyUI 节点，支持中英拼音模糊搜索 + 实时大图预览。

![version](https://img.shields.io/badge/version-1.1.0-blue) ![ComfyUI](https://img.shields.io/badge/ComfyUI-custom--node-orange) ![python](https://img.shields.io/badge/python-3.10%2B-green) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## ✨ 特性

- 🎨 **10000+ 风格**：涵盖数字艺术、二次元、赛博朋克、文艺复兴、水彩水墨、印象派……一站式选择
- 🗂️ **30 个大类 + 数字艺术 6 个子类**：自动归类、按大类筛选不再迷路
- 🔎 **模糊搜索**：支持中文 / 英文 / 拼音全拼 / 拼音首字母（如 `cyberpunk` / `赛博` / `saibo` / `sb` 都能命中）
- 🖼️ **实时大图预览**：节点内嵌缩略图墙 + 高清预览，**不需要运行工作流**就能看到风格效果
- 📤 **多端口输出**：图像 / 风格名 / 大类 / 示例提示词 / 原始 ID / 完整元数据 JSON
- ⚡ **零卡顿**：256px WebP 缩略图懒加载，倒排索引秒级搜索
- 📄 **分页浏览**：每页 120 张缩略图，支持上一页/下一页翻页，10000 张风格轻松浏览

---

## 🗺️ 更新日志

### v1.1.0（2026-05-21）
- ✅ **修复缩略图显示问题**：修复网格高度计算错误导致图片不显示的 bug
- ✅ **新增翻页功能**：支持上一页/下一页翻页浏览，每页显示 120 张缩略图
- ✅ **优化网格布局**：固定行高 72px，确保所有缩略图以正方形正确显示
- ✅ **API 支持分页**：`/metastyle/search` 新增 `offset` 参数支持

### v1.0.0（2026-05-21）
- 🎉 **首版发布**：30 大类 + 模糊搜索 + 实时预览
-  内置 10,000 张风格原图 + 10,000 张缩略图
- ️ 30 个大类自动归类（数字艺术、插画、二次元、赛博朋克等）
- 🔎 支持中文 / 英文 / 拼音模糊搜索

---

## 📷 节点界面

```
┌────────────────────────────────────────────┐
│ MetaStyle T8 风格选择器                     │
├────────────────────────────────────────────┤
│ [赛博朋克 Cyberpunk (259) ▼] [搜索框]      │
├────────────────────────────────────────────┤
│  ▣ 缩略图网格（按需加载，悬停高亮）         │
│   ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐         │
│   │  ││  ││★ ││  ││  ││  ││  ││  │         │
│   └──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘         │
├────────────────────────────────────────────┤
│  [大图预览]  风格名: cyberpunk fantasy ...  │
│              大类: 赛博朋克                 │
│              示例提示词: Barbell on rack…   │
└────────────────────────────────────────────┘

输出: image | style_name | category | sample_prompt | sample_id | meta_json
```

---

## 🚀 安装

### 方法 1：git clone（推荐）

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/T8mars/comfyui-metastyle-T8.git
cd comfyui-metastyle-T8
pip install -r requirements.txt
```

数据已包含在仓库中，无需额外下载或构建。

### 方法 2：ComfyUI Manager

未来发布到 Registry 后可一键安装。

---

##  数据集

> **v1.0.0 起，数据已内置在仓库中，无需手动构建。**
>
> 仓库包含 10,000 张风格原图 + 10,000 张缩略图 + 元数据索引，总计 ~410 MB。
>
> `git clone` 后开箱即用。

### 如需重新生成数据（开发者）

适合你已经持有 `train-00000.parquet` 源数据集，想自行构建或更新风格库的情况：

```bash
cd custom_nodes/comfyui-metastyle-T8

# 1. 提取每个风格的代表图
python ../../extract_styles.py --out E:\parquet\styles

# 2. 拷贝/链接图片 + 反查 content/id
python scripts/build_dataset.py --src E:\parquet --mode link

# 3. 自动归类 30 大类
python scripts/auto_classify.py

# 4. 生成 256px WebP 缩略图（多进程加速）
python scripts/build_thumbnails.py

# 5. 构建模糊搜索倒排索引
python scripts/build_index.py
```

完成后 `data/` 目录会得到：
```
data/
├── styles/                10000 张原图
├── thumbs/                10000 张 256px WebP
├── styles_meta.json       完整元数据 (~8 MB)
├── catalog.json           大类目录 (~1 MB)
├── styles_lite.json       前端轻量列表
└── search_index.json      倒排索引 (6000+ tokens)
```

---

## 🎬 使用

1. **重启 ComfyUI**，控制台应出现：
   ```
   [MetaStyle-T8] 节点已加载: MetaStyleT8Picker
   [MetaStyle-T8] 已注册 HTTP 路由 /metastyle/*
   ```
2. 画布右键：`Add Node → T8 → Style → MetaStyle T8 风格选择器`
3. 节点上：
   - 顶部下拉选择**大类**（"全部"=不限）
   - 搜索框输入**任意关键字**（中文/英文/拼音都行）
   - 点击网格中的缩略图即选中，下方实时显示大图与示例提示词
4. 把节点输出连到下游：
   - `image` → `PreviewImage` / `IPAdapter` / `ControlNet` 等
   - `sample_prompt` → `CLIPTextEncode`（直接用作 prompt 起手式）
   - `style_name` / `category` → `Show Text` 调试

---

## 🧠 节点 IO

### Inputs
| 名称 | 类型 | 说明 |
|---|---|---|
| `style_key` | STRING | 选中的风格 key（由前端 widget 自动维护） |
| `output_size` | COMBO | `original` / `512` / `768` / `1024` |
| `seed` | INT (可选) | 预留，用于将来多张候选随机切换 |

### Outputs
| 名称 | 类型 | 说明 |
|---|---|---|
| `image` | IMAGE | 风格代表图（BHWC float32 0~1） |
| `style_name` | STRING | 风格全名 |
| `category` | STRING | 大类（中文） |
| `sample_prompt` | STRING | 示例提示词，可直接接 CLIPTextEncode |
| `sample_id` | STRING | 数据集中的原始 id（便于溯源） |
| `meta_json` | STRING | 该风格全量元数据 JSON 字符串 |

---

## 🛠️ 后端 HTTP 路由

注册前缀 `/metastyle/`，全部由 ComfyUI 内置 aiohttp server 提供：

| 路由 | 作用 |
|---|---|
| `GET /metastyle/catalog` | 大类 + 子类 + 数量统计 |
| `GET /metastyle/lite` | 全量轻量风格列表（首屏） |
| `GET /metastyle/search?q=&cat=&sub=&limit=` | 模糊搜索 |
| `GET /metastyle/thumb/<key>` | 256px 缩略图 |
| `GET /metastyle/preview/<key>` | 原图大图 |
| `GET /metastyle/meta/<key>` | 单条完整元数据 |

可在浏览器直接访问，便于调试。

---

## 🗂️ 项目结构

```
comfyui-metastyle-T8/
├── __init__.py              # ComfyUI 加载入口
├── nodes.py                 # 节点核心逻辑
├── api.py                   # HTTP 路由
├── pyproject.toml           # ComfyUI Registry 元数据
├── requirements.txt
├── scripts/                 # 数据构建脚本（可重复运行）
│   ├── build_dataset.py
│   ├── auto_classify.py
│   ├── build_thumbnails.py
│   └── build_index.py
├── web/                     # 前端 UI
│   ├── metastyle.js
│   └── metastyle.css
├── data/                    # 数据（git 忽略）
└── examples/                # 示例工作流
```

---

## ❓ 常见问题

### Q1：节点加载失败 / 画布上找不到节点
- 确认依赖已安装：`pip install -r requirements.txt`
- 查看 ComfyUI 启动日志中是否有 `[MetaStyle-T8] 节点已加载` 字样
- 确保 `data/styles_meta.json` 存在（运行过 `build_dataset.py`）

### Q2：缩略图全 404 / 显示横条
- 缩略图未生成：运行 `python scripts/build_thumbnails.py`
- 浏览器有旧 CSS 缓存：按 `Ctrl + F5` 强制刷新

### Q3：搜索没结果
- 索引未生成：运行 `python scripts/build_index.py`
- 中文搜索不命中：确认安装了 `pypinyin`，重新生成索引

### Q4：想自定义大类 / 关键字规则
编辑 [scripts/auto_classify.py](scripts/auto_classify.py) 中的 `PRIMARY_RULES`，
重新跑 `auto_classify.py` + `build_index.py` 即可。

---

## 📜 License

MIT © T8mars

---

## 🙏 致谢

- 基于 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 自定义节点机制
- 拼音支持来自 [pypinyin](https://github.com/mozillazg/python-pinyin)
- 训练数据集来源：用户私有 parquet 数据集（不在仓库中）

---

## 🗺️ Roadmap

- [ ] 多张候选图随机/手动切换
- [ ] 收藏夹（标记常用风格）
- [ ] 拖拽风格图导出 LoRA 训练用 zip
- [ ] 数据包 CDN 镜像
- [ ] ComfyUI Registry 一键安装

欢迎 PR / Issue！
