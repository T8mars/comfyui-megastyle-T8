/* MetaStyle T8 节点 UI 扩展
 *
 * 在 MetaStyleT8Picker 节点中插入：
 *  - 大类下拉
 *  - 模糊搜索框
 *  - 缩略图网格
 *  - 实时大图预览
 *  - 当前选中风格信息（名称 / 示例提示词）
 */
import { app } from "/scripts/app.js";

const NODE_NAME = "MetaStyleT8Picker";
const API = "/metastyle";

// 自动加载同目录下的样式文件
(function injectCSS() {
    const id = "metastyle-t8-css";
    if (document.getElementById(id)) return;
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = "/extensions/comfyui-metastyle-T8/metastyle.css";
    document.head.appendChild(link);
})();

// 简单防抖
function debounce(fn, ms = 200) {
    let t = null;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), ms);
    };
}

// 全局缓存
let _catalogCache = null;
async function fetchCatalog() {
    if (_catalogCache) return _catalogCache;
    const r = await fetch(`${API}/catalog`);
    _catalogCache = await r.json();
    return _catalogCache;
}

async function fetchSearch(q, cat, sub, limit = 120) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (cat) params.set("cat", cat);
    if (sub) params.set("sub", sub);
    params.set("limit", String(limit));
    const r = await fetch(`${API}/search?${params}`);
    return r.json();
}

async function fetchMeta(key) {
    const r = await fetch(`${API}/meta/${encodeURIComponent(key)}`);
    if (!r.ok) return null;
    return r.json();
}

function escHtml(s) {
    if (s == null) return "";
    return String(s).replace(/[&<>"']/g,
        c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function buildPickerDOM(node) {
    const root = document.createElement("div");
    root.className = "metastyle-picker";
    root.innerHTML = `
        <div class="ms-bar">
            <select class="ms-cat" title="大类"></select>
            <select class="ms-sub" title="子类" style="display:none;"></select>
            <input class="ms-q" type="text" placeholder="搜索: 风格 / 配色 / 拼音 (Enter 立即搜)">
        </div>
        <div class="ms-stats"></div>
        <div class="ms-grid"></div>
        <div class="ms-preview">
            <img class="ms-preview-img" alt="">
            <div class="ms-preview-info">
                <div class="ms-name">未选择</div>
                <div class="ms-cat-tag"></div>
                <div class="ms-prompt"></div>
            </div>
        </div>
    `;
    return root;
}

async function rebuildCategoryOptions(rootEl) {
    const cat = await fetchCatalog();
    const sel = rootEl.querySelector(".ms-cat");
    const subSel = rootEl.querySelector(".ms-sub");
    sel.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = ""; opt0.textContent = `全部 (${Object.values(cat).reduce((a, b) => a + b.count, 0)})`;
    sel.appendChild(opt0);
    const sorted = Object.entries(cat).sort((a, b) => b[1].count - a[1].count);
    for (const [cn, info] of sorted) {
        const o = document.createElement("option");
        o.value = cn;
        o.textContent = `${info.name_cn} ${info.name_en} (${info.count})`;
        sel.appendChild(o);
    }
    sel.addEventListener("change", () => {
        const v = sel.value;
        const subs = (cat[v] && cat[v].subs) || {};
        subSel.innerHTML = "";
        if (Object.keys(subs).length) {
            const o0 = document.createElement("option");
            o0.value = ""; o0.textContent = `全部子类`;
            subSel.appendChild(o0);
            for (const [scn, sInfo] of Object.entries(subs).sort((a, b) => b[1].count - a[1].count)) {
                const o = document.createElement("option");
                o.value = scn;
                o.textContent = `${sInfo.name_cn} (${sInfo.count})`;
                subSel.appendChild(o);
            }
            subSel.style.display = "";
        } else {
            subSel.style.display = "none";
        }
    });
}

function renderGrid(rootEl, items, total, q) {
    const grid = rootEl.querySelector(".ms-grid");
    const stats = rootEl.querySelector(".ms-stats");
    stats.textContent = `命中 ${total} 个风格${q ? `（关键字: ${q}）` : ""}，显示前 ${items.length}`;
    grid.innerHTML = "";
    const frag = document.createDocumentFragment();
    for (const it of items) {
        const card = document.createElement("div");
        card.className = "ms-card";
        card.dataset.key = it.k;
        card.title = it.p || it.k;
        const img = document.createElement("img");
        img.loading = "lazy";
        img.src = `${API}/thumb/${encodeURIComponent(it.k)}`;
        img.alt = it.p;
        const label = document.createElement("div");
        label.className = "ms-card-label";
        label.textContent = it.p || it.k;
        card.appendChild(img);
        card.appendChild(label);
        frag.appendChild(card);
    }
    grid.appendChild(frag);
}

function setSelected(rootEl, key) {
    rootEl.querySelectorAll(".ms-card.selected")
        .forEach(el => el.classList.remove("selected"));
    if (!key) return;
    const c = rootEl.querySelector(`.ms-card[data-key="${CSS.escape(key)}"]`);
    if (c) c.classList.add("selected");
}

async function refreshPreview(rootEl, key) {
    const img = rootEl.querySelector(".ms-preview-img");
    const nameEl = rootEl.querySelector(".ms-name");
    const catTag = rootEl.querySelector(".ms-cat-tag");
    const promptEl = rootEl.querySelector(".ms-prompt");
    if (!key) {
        img.removeAttribute("src");
        nameEl.textContent = "未选择";
        catTag.textContent = "";
        promptEl.textContent = "";
        return;
    }
    img.src = `${API}/preview/${encodeURIComponent(key)}`;
    const m = await fetchMeta(key);
    if (m) {
        nameEl.textContent = m.style_full || key;
        catTag.textContent = `${m.category || ""} ${m.sub_category || ""}`.trim();
        promptEl.textContent = m.sample_content || "";
    } else {
        nameEl.textContent = key;
        catTag.textContent = "";
        promptEl.textContent = "";
    }
}

function findStyleKeyWidget(node) {
    return node.widgets?.find(w => w.name === "style_key");
}

app.registerExtension({
    name: "T8.MetaStyle.Picker",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData?.name !== NODE_NAME) return;

        const onCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onCreated?.apply(this, arguments);
            const node = this;

            // 隐藏原始 style_key 文本框（保留为底层数据载体）
            const w = findStyleKeyWidget(node);
            if (w) {
                w.computeSize = () => [0, -4]; // 占位但不显示
            }

            // 注入 DOM widget
            const dom = buildPickerDOM(node);
            const widget = node.addDOMWidget("metastyle_ui", "div", dom, {
                serialize: false,
                hideOnZoom: false,
            });
            // 设定一个合理的高度
            widget.computeSize = function (width) {
                return [width, 520];
            };

            // 恢复已选中
            const restoreKey = (w && typeof w.value === "string") ? w.value : "";

            // 初始化下拉
            rebuildCategoryOptions(dom).then(() => doSearch());

            const qInput = dom.querySelector(".ms-q");
            const catSel = dom.querySelector(".ms-cat");
            const subSel = dom.querySelector(".ms-sub");

            const doSearch = async () => {
                const q = qInput.value.trim();
                const cat = catSel.value;
                const sub = subSel.value;
                const data = await fetchSearch(q, cat, sub, 120);
                renderGrid(dom, data.items || [], data.total || 0, q);
                if (restoreKey) setSelected(dom, restoreKey);
            };

            const debounced = debounce(doSearch, 220);
            qInput.addEventListener("input", debounced);
            qInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") { e.preventDefault(); doSearch(); }
            });
            catSel.addEventListener("change", () => doSearch());
            subSel.addEventListener("change", () => doSearch());

            dom.querySelector(".ms-grid").addEventListener("click", (e) => {
                const card = e.target.closest(".ms-card");
                if (!card) return;
                const key = card.dataset.key;
                if (w) {
                    w.value = key;
                    if (typeof w.callback === "function") w.callback(key);
                    node.setDirtyCanvas(true, true);
                }
                setSelected(dom, key);
                refreshPreview(dom, key);
            });

            // 初次预览（若有恢复值）
            if (restoreKey) refreshPreview(dom, restoreKey);

            return r;
        };
    },
});
