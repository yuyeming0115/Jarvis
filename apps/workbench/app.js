const API = {
  tasks: "/api/tasks",
  ideas: "/api/ideas",
  topics: "/api/topics",
  drafts: "/api/drafts",
  wiki: "/api/wiki",
  media: "/api/media-prompts",
  status: "/api/system-status",
  logs: "/api/logs",
  llmStatus: "/api/llm/status",
  aiConvertIdea: "/api/ideas/ai-convert",
  settings: "/api/settings",
  settingsUpdate: "/api/settings/update",
  settingsTest: "/api/settings/test-llm",
};

const TAB_CONFIG = {
  tasks: { title: "任务 & 快速录入", hasForm: true },
  ideas: { title: "灵感池", hasForm: true },
  topics: { title: "选题池", hasForm: true },
  drafts: { title: "内容草稿", hasForm: false },
  wiki: { title: "知识库", hasForm: false },
  media: { title: "多媒体提示词", hasForm: false },
};

let state = {
  tasks: [],
  ideas: [],
  topics: [],
  drafts: [],
  wiki: [],
  media: [],
  status: {},
  logs: [],
  llmConfigured: false,
  imageConfigured: false,
  activeTab: "tasks",
  selectedItem: null,
  aiWorking: null,
  aiResult: null,
};

const labels = {
  workbench: "工作台",
  backend_api: "本地 API",
  database: "数据源",
  feishu: "飞书",
  telegram: "Telegram",
  wechat: "微信",
  openclaw: "OpenClaw",
  tinyrouter: "TinyRouter",
  hermes: "Hermes",
  last_sync_at: "最近同步",
  safe_mode: "安全模式",
  public_access: "公网访问",
  platform: "平台",
};

function el(id) { return document.getElementById(id); }

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatOutlineHtml(outline, hook, suggestedTitle) {
  let html = "";
  if (suggestedTitle) html += `<p><strong>📌 建议标题：</strong>${escapeHtml(suggestedTitle)}</p>`;
  if (hook) html += `<p><strong>🎯 开头钩子：</strong>${escapeHtml(hook)}</p>`;
  if (outline && outline.length) {
    html += `<div class="outline-preview"><p><strong>📋 大纲（${outline.length} 节）：</strong></p>`;
    outline.forEach((section, i) => {
      html += `<div class="outline-section"><strong>${i + 1}. ${escapeHtml(section.section || "")}</strong>`;
      if (section.items && section.items.length) {
        html += "<ul>";
        section.items.forEach(item => {
          html += `<li>${escapeHtml(typeof item === 'string' ? item : (item.point || item.content || JSON.stringify(item)))}</li>`;
        });
        html += "</ul>";
      }
      html += "</div>";
    });
    html += "</div>";
  }
  return html;
}

function create(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "className") e.className = v;
    else if (k === "textContent") e.textContent = v;
    else if (k === "innerHTML") e.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v !== null && v !== undefined && v !== false) e.setAttribute(k, v);
  });
  (Array.isArray(children) ? children : [children]).forEach(c => {
    if (c === null || c === undefined || c === false) return;
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  });
  return e;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `请求失败：${response.status}`);
  return payload;
}

let toastTimer = null;
function showToast(message, type = "success") {
  const panel = type === "success" ? el("toastPanel") : el("errorPanel");
  panel.textContent = message;
  panel.classList.remove("hidden");
  if (type === "success") {
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => panel.classList.add("hidden"), 2500);
  }
}

function hideErrors() { el("errorPanel").classList.add("hidden"); }

function text(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "是" : "否";
  return String(value);
}

function createTag(value, className = "tag") {
  return create("span", { className, textContent: value });
}

function renderEmpty(target, message) {
  target.innerHTML = "";
  target.appendChild(create("div", { className: "empty", textContent: message }));
}

function runAction(action) {
  hideErrors();
  return action().catch(error => showToast(error.message, "error"));
}

function confirmDialog(message, title = "确认操作") {
  return new Promise(resolve => {
    el("confirmTitle").textContent = title;
    el("confirmMessage").textContent = message;
    const overlay = el("confirmOverlay");
    overlay.classList.remove("hidden");
    const okBtn = el("confirmOk");
    const cancelBtn = el("confirmCancel");
    const cleanup = (result) => {
      overlay.classList.add("hidden");
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
      overlay.removeEventListener("click", onOverlay);
      resolve(result);
    };
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    const onOverlay = (e) => { if (e.target === overlay) cleanup(false); };
    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
    overlay.addEventListener("click", onOverlay);
  });
}

function openModal(title, content) {
  if (title !== undefined) el("modalTitle").textContent = title;
  const body = el("modalBody");
  if (content !== undefined) {
    body.innerHTML = "";
    if (typeof content === "string") body.innerHTML = content;
    else body.appendChild(content);
  }
  el("modalOverlay").classList.remove("hidden");
}

function closeModal() { el("modalOverlay").classList.add("hidden"); }

function selectTab(tab) {
  state.activeTab = tab;
  state.selectedItem = null;
  document.querySelectorAll(".metric.clickable").forEach(m => {
    m.classList.toggle("active", m.dataset.mainTab === tab);
  });
  renderListPanel();
  renderDetail();
}

function renderListForm() {
  const area = el("listFormArea");
  area.innerHTML = "";
  if (state.activeTab === "tasks") {
    const form = create("form", { className: "entry-form", id: "taskForm" }, [
      create("label", {}, [
        create("span", { textContent: "新增任务" }),
        create("input", { name: "title", type: "text", placeholder: "周五交 Q3 方案", required: "required" }),
      ]),
      create("label", {}, [
        create("span", { textContent: "截止" }),
        create("input", { name: "due_at", type: "text", placeholder: "2026-07-05 18:00" }),
      ]),
      create("label", {}, [
        create("span", { textContent: "优先级" }),
        create("select", { name: "priority" }, [
          create("option", { textContent: "P0" }),
          create("option", { textContent: "P1" }),
          create("option", { selected: "selected", textContent: "P2" }),
          create("option", { textContent: "P3" }),
        ]),
      ]),
      create("button", { type: "submit", textContent: "+ 任务" }),
    ]);
    form.addEventListener("submit", e => {
      e.preventDefault();
      runAction(async () => {
        await api(API.tasks, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
        e.target.reset();
        showToast("任务已新增");
        await refresh();
      });
    });
    area.appendChild(form);
  } else if (state.activeTab === "ideas") {
    const form = create("form", { className: "entry-form", id: "ideaForm" }, [
      create("label", { className: "full-width" }, [
        create("span", { textContent: "记录灵感" }),
        create("textarea", { name: "raw_text", rows: "2", placeholder: "记录一个想法...", required: "required" }),
      ]),
      create("label", {}, [
        create("span", { textContent: "类型" }),
        create("input", { name: "type", type: "text", placeholder: "灵感", value: "灵感" }),
      ]),
      create("button", { type: "submit", textContent: "+ 灵感" }),
    ]);
    form.addEventListener("submit", e => {
      e.preventDefault();
      runAction(async () => {
        await api(API.ideas, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
        e.target.reset();
        e.target.querySelector('textarea').value = "";
        const typeInput = e.target.querySelector('input[name="type"]');
        if (typeInput) typeInput.value = "灵感";
        showToast("灵感已新增");
        await refresh();
      });
    });
    area.appendChild(form);
  } else if (state.activeTab === "topics") {
    const form = create("form", { className: "entry-form", id: "topicForm" }, [
      create("label", { className: "full-width" }, [
        create("span", { textContent: "新增选题" }),
        create("input", { name: "title", type: "text", placeholder: "普通人如何用 AI Agent", required: "required" }),
      ]),
      create("label", {}, [
        create("span", { textContent: "平台" }),
        create("select", { name: "platform" }, [
          create("option", { textContent: "公众号" }),
          create("option", { textContent: "小红书" }),
          create("option", { textContent: "视频号" }),
        ]),
      ]),
      create("label", {}, [
        create("span", { textContent: "角度" }),
        create("input", { name: "angle", type: "text", placeholder: "切入角度" }),
      ]),
      create("button", { type: "submit", textContent: "+ 选题" }),
    ]);
    form.addEventListener("submit", e => {
      e.preventDefault();
      runAction(async () => {
        await api(API.topics, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
        e.target.reset();
        showToast("选题已新增");
        await refresh();
      });
    });
    area.appendChild(form);
  } else if (state.activeTab === "drafts") {
    const actions = el("listHeaderActions");
    actions.innerHTML = "";
    const selectEl = create("select", { id: "draftPlatform" }, [
      create("option", { textContent: "公众号" }),
      create("option", { textContent: "小红书" }),
      create("option", { textContent: "视频号脚本" }),
      create("option", { textContent: "通用文章" }),
    ]);
    actions.appendChild(selectEl);
    const btn = create("button", { type: "button", className: "primary-btn", textContent: "+ 新草稿", onClick: () => openDraftEditor(null) });
    actions.appendChild(btn);
  } else if (state.activeTab === "wiki") {
    const actions = el("listHeaderActions");
    actions.innerHTML = "";
    const searchInput = create("input", { id: "wikiSearch", type: "text", placeholder: "搜索知识库..." });
    let searchTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(async () => {
        const q = e.target.value.trim();
        if (q) {
          state.wiki = await api(`/api/wiki/search?q=${encodeURIComponent(q)}`);
        } else {
          state.wiki = await api(API.wiki);
        }
        renderListContent();
      }, 300);
    });
    actions.appendChild(searchInput);
    actions.appendChild(create("button", { type: "button", className: "primary-btn", textContent: "+ 新文章", onClick: () => openWikiEditor(null) }));
  } else if (state.activeTab === "media") {
    el("listHeaderActions").innerHTML = "";
  }
}

function renderListContent() {
  const container = el("listContent");
  container.innerHTML = "";
  const stack = create("div", { className: "stack" });
  container.appendChild(stack);

  if (state.activeTab === "tasks") {
    if (!state.tasks.length) { renderEmpty(stack, "暂无任务"); return; }
    const urgentCount = state.tasks.filter(t => ["P0", "P1"].includes(t.priority)).length;
    el("urgentCountBadge")?.remove();
    const badge = create("span", { className: "counter", id: "urgentCountBadge", textContent: `${urgentCount} 紧急` });
    el("listHeader").querySelector(".counter")?.remove();
    el("listHeader").appendChild(badge);
    state.tasks.forEach(task => {
      const isSel = state.selectedItem?.type === "task" && state.selectedItem.data.task_id === task.task_id;
      const item = create("article", { className: `item ${isSel ? "selected" : ""}` }, [
        create("div", { className: "item-title" }, [
          create("strong", { textContent: task.title }),
          createTag(task.priority || "P?", `priority ${(task.priority || "").toLowerCase()}`),
        ]),
        create("p", { textContent: task.description || "暂无描述" }),
        create("div", { className: "meta-row" },
          [task.status, task.project, task.due_at].filter(Boolean).map(v => createTag(v))
        ),
        create("div", { className: "item-actions" }, [
          create("button", { className: "secondary", type: "button", textContent: "✓ 完成", onClick: (e) => { e.stopPropagation(); completeTask(task); } }),
          create("button", { className: "danger", type: "button", textContent: "🗑️", onClick: (e) => { e.stopPropagation(); deleteTask(task.task_id); } }),
        ]),
      ]);
      item.addEventListener("click", () => {
        state.selectedItem = { type: "task", data: task };
        renderAll();
      });
      stack.appendChild(item);
    });
  } else if (state.activeTab === "ideas") {
    if (!state.ideas.length) { renderEmpty(stack, "暂无灵感"); return; }
    state.ideas.forEach(idea => {
      const isSel = state.selectedItem?.type === "idea" && state.selectedItem.data.idea_id === idea.idea_id;
      const item = create("article", { className: `item ${isSel ? "selected" : ""}` }, [
        create("div", { className: "item-title" }, [
          create("strong", { textContent: idea.type || "灵感" }),
          createTag(idea.status || "未处理"),
        ]),
        create("p", { textContent: idea.raw_text || "暂无内容" }),
        create("div", { className: "meta-row" }, (idea.tags || []).map(t => createTag(t))),
        create("div", { className: "item-actions" }, [
          create("button", { className: "secondary", type: "button", textContent: "→ 转选题", onClick: (e) => { e.stopPropagation(); promoteIdeaToTopic(idea); } }),
          create("button", { className: "danger", type: "button", textContent: "🗑️", onClick: (e) => { e.stopPropagation(); deleteIdea(idea.idea_id); } }),
        ]),
      ]);
      item.addEventListener("click", () => {
        state.selectedItem = { type: "idea", data: idea };
        renderAll();
      });
      stack.appendChild(item);
    });
  } else if (state.activeTab === "topics") {
    if (!state.topics.length) { renderEmpty(stack, "暂无选题"); return; }
    state.topics.forEach(topic => {
      const isSel = state.selectedItem?.type === "topic" && state.selectedItem.data.topic_id === topic.topic_id;
      const item = create("article", { className: `item ${isSel ? "selected" : ""}` }, [
        create("div", { className: "item-title" }, [
          create("strong", { textContent: topic.title }),
          createTag(`${topic.score || 0}分`),
        ]),
        create("p", { textContent: topic.angle || "暂无角度" }),
        create("div", { className: "meta-row" }, [topic.platform, topic.content_type, topic.status].filter(Boolean).map(v => createTag(v))),
        create("div", { className: "item-actions" }, [
          create("button", { className: "ai-btn", type: "button", textContent: "✨ AI 生成大纲", onClick: (e) => { e.stopPropagation(); generateOutlineFromTopic(topic); } }),
        ]),
      ]);
      item.addEventListener("click", () => {
        state.selectedItem = { type: "topic", data: topic };
        renderAll();
      });
      stack.appendChild(item);
    });
  } else if (state.activeTab === "drafts") {
    if (!state.drafts.length) { renderEmpty(stack, "暂无草稿，点击右上角「+ 新草稿」或从选题生成大纲"); return; }
    state.drafts.forEach(draft => {
      const isSel = state.selectedItem?.type === "draft" && state.selectedItem.data.draft_id === draft.draft_id;
      // Status color mapping
      const statusColor = (s) => {
        if (["定稿","已发布"].includes(s)) return { bg: "#EAF3DE", color: "#3B6D11" };
        if (["已归档"].includes(s)) return { bg: "#E1F5EE", color: "#0F6E56" };
        if (["待审核"].includes(s)) return { bg: "#FAEEDA", color: "#854F0B" };
        if (["大纲"].includes(s)) return { bg: "#EEEDFE", color: "#534AB7" };
        return { bg: "#f0f0f0", color: "#666" };
      };
      const sc = statusColor(draft.status || "");
      const item = create("article", { className: `item ${isSel ? "selected" : ""} draft-list-item` }, [
        create("div", { className: "draft-item-header" }, [
          create("div", { className: "draft-item-title-row" }, [
            create("strong", { className: "draft-item-title", textContent: draft.title }),
            create("span", { className: "status-pill", style: `background:${sc.bg};color:${sc.color}`, textContent: draft.status || "草稿" }),
          ]),
          create("div", { className: "draft-item-meta" }, [
            createTag(draft.platform || "公众号", "tag platform-tag"),
            createTag(draft.content_type || "文章"),
            `${draft.word_count || 0}字`,
          ].filter(Boolean).map(v => typeof v === "string" ? create("span", { className: "meta-text", textContent: v }) : v)),
        ]),
      ]);
      item.addEventListener("click", () => {
        state.selectedItem = { type: "draft", data: draft };
        renderAll();
      });
      stack.appendChild(item);
    });
  } else if (state.activeTab === "wiki") {
    if (!state.wiki.length) { renderEmpty(stack, "知识库暂无文章"); return; }
    state.wiki.forEach(page => {
      const isSel = state.selectedItem?.type === "wiki" && state.selectedItem.data.page_id === page.page_id;
      const item = create("article", { className: `item ${isSel ? "selected" : ""}` }, [
        create("div", { className: "item-title" }, [
          create("strong", { textContent: page.title }),
          createTag(page.status || "草稿", "tag wiki"),
        ]),
        page.summary ? create("p", { textContent: page.summary }) : null,
        create("div", { className: "meta-row" }, [
          ...(page.tags || []).slice(0, 3).map(t => createTag(t)),
          createTag(`${page.word_count || 0}字`),
        ]),
      ]);
      item.addEventListener("click", () => {
        state.selectedItem = { type: "wiki", data: page };
        renderAll();
      });
      stack.appendChild(item);
    });
  } else if (state.activeTab === "media") {
    const imgGenBar = create("div", { style: "padding:10px 12px;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:center" });
    const imgGenBtn = create("button", { className: "ai-btn", textContent: "🤖 AI文生图", onClick: () => {
      // 优先使用已选中的媒体提示词
      let defaultPrompt = "", defaultNeg = "";
      const sel = state.selectedItem;
      if (sel?.type === "media" && sel.data?.prompts?.length) {
        defaultPrompt = sel.data.prompts[0].prompt || "";
        defaultNeg = sel.data.prompts[0].negative_prompt || "";
      }
      openImageGenModal(defaultPrompt, defaultNeg);
    } });
    if (!state.imageConfigured) { imgGenBtn.disabled = true; imgGenBtn.title = "图片生成 API 未配置"; }
    imgGenBar.appendChild(imgGenBtn);
    imgGenBar.appendChild(create("span", { className: "muted", style: "font-size:12px", textContent: state.imageConfigured ? "图片生成 API 已就绪" : "需在设置中配置图片生成 API" }));
    stack.appendChild(imgGenBar);
    if (!state.media.length) { renderEmpty(stack, "暂无多媒体提示词，点击上方「AI文生图」可直接生成图片"); return; }
    state.media.forEach(prompt => {
      const isSel = state.selectedItem?.type === "media" && state.selectedItem.data.prompt_id === prompt.prompt_id;
      const count = (prompt.prompts || []).length;
      const item = create("article", { className: `item ${isSel ? "selected" : ""}` }, [
        create("div", { className: "item-title" }, [
          create("strong", { textContent: prompt.title }),
          createTag(prompt.prompt_type, "tag media"),
        ]),
        create("div", { className: "meta-row" }, [
          prompt.platform, prompt.status, `${count}个提示词`
        ].filter(Boolean).map(v => createTag(v))),
      ]);
      item.addEventListener("click", () => {
        state.selectedItem = { type: "media", data: prompt };
        renderAll();
      });
      stack.appendChild(item);
    });
  }
}

function renderListPanel() {
  const cfg = TAB_CONFIG[state.activeTab];
  el("listTitle").textContent = cfg.title;
  el("listHeaderActions").innerHTML = "";
  el("listFormArea").innerHTML = "";
  renderListForm();
  renderListContent();
}

function renderAiPanel(box) {
  if (state.aiWorking) {
    const panel = create("div", { className: "ai-panel working" });
    panel.appendChild(create("div", { className: "ai-spinner" }));
    panel.appendChild(create("div", { className: "ai-status", textContent: state.aiWorking }));
    box.appendChild(panel);
  }
  if (state.aiResult && !state.aiWorking) {
    const panel = create("div", { className: "ai-panel result" });
    const header = create("div", { className: "ai-result-header" });
    header.appendChild(create("span", { className: "ai-result-title", textContent: state.aiResult.title || "AI 生成结果" }));
    const closeBtn = create("button", { className: "ai-close", textContent: "✕", onClick: () => { state.aiResult = null; renderDetail(); } });
    header.appendChild(closeBtn);
    panel.appendChild(header);
    if (state.aiResult.html) {
      const body = create("div", { className: "ai-result-body" });
      body.innerHTML = state.aiResult.html;
      panel.appendChild(body);
    }
    if (state.aiResult.error) {
      panel.appendChild(create("div", { className: "ai-error", textContent: state.aiResult.error }));
    }
    box.appendChild(panel);
  }
}

function renderDetail() {
  const box = el("detailContent");
  box.innerHTML = "";
  const sel = state.selectedItem;

  renderAiPanel(box);

  if (!sel) {
    if (!state.aiWorking && !state.aiResult) {
      box.appendChild(create("p", { className: "empty-hint", textContent: "点击列表项查看详情和 AI 工具。" }));
    }
    return;
  }

  if (sel.type === "task") {
    const t = sel.data;
    box.appendChild(create("h3", { textContent: t.title }));
    if (t.description) box.appendChild(create("p", { className: "muted", textContent: t.description }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(t.status || "未开始"),
      createTag(t.priority || "P2", `priority ${(t.priority || "p2").toLowerCase()}`),
      t.due_at ? createTag(t.due_at) : null,
      ...(t.tags || []).map(tag => createTag(tag)),
    ]));
    box.appendChild(create("div", { className: "ai-actions" }, [
      create("button", { className: "secondary", textContent: "✓ 标记完成", onClick: () => completeTask(t) }),
      create("button", { className: "danger", textContent: "🗑️ 删除任务", onClick: () => deleteTask(t.task_id) }),
    ]));
  }

  if (sel.type === "idea") {
    const i = sel.data;
    box.appendChild(create("h3", { textContent: i.type || "灵感" }));
    box.appendChild(create("p", { className: "idea-text", textContent: i.raw_text || "" }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(i.status || "未处理"),
      ...(i.tags || []).map(tag => createTag(tag)),
    ]));
    box.appendChild(create("div", { className: "ai-actions" }, [
      create("button", { className: "ai-btn", textContent: "→ AI 转选题", onClick: () => aiPromoteIdea(i) }),
      create("button", { className: "secondary", textContent: "→ 手动转选题", onClick: () => promoteIdeaToTopic(i) }),
      create("button", { className: "danger", textContent: "🗑️ 删除", onClick: () => deleteIdea(i.idea_id) }),
    ]));
  }

  if (sel.type === "topic") {
    const t = sel.data;
    box.appendChild(create("h3", { textContent: t.title }));
    if (t.angle) box.appendChild(create("p", { className: "muted", textContent: t.angle }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(t.platform || "公众号"),
      createTag(t.content_type || "文章"),
      createTag(`评分 ${t.score || 0}`),
      createTag(t.status || "候选"),
    ]));
    if (t.target_audience) {
      box.appendChild(create("p", { className: "muted", style: "margin-top:8px;font-size:12px;", textContent: `目标读者：${t.target_audience}` }));
    }
    box.appendChild(create("div", { className: "ai-actions" }, [
      create("button", { className: "ai-btn", textContent: "✨ AI 生成大纲", onClick: () => generateOutlineFromTopic(t) }),
      create("button", { className: "ai-btn", textContent: "🎨 AI 生成封面 Prompt", onClick: () => generateCover(t.title, t.platform, null, t.topic_id) }),
      create("button", { className: "ai-btn", textContent: "🎬 AI 生成即梦分镜", onClick: () => generateJimeng(t.title, "", 5, null, t.topic_id) }),
    ]));
  }

  if (sel.type === "draft") {
    const d = sel.data;
    box.appendChild(create("h3", { textContent: d.title }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(d.platform || "公众号", "tag draft"),
      createTag(d.content_type || "文章"),
      createTag(d.status || "草稿"),
      createTag(`${d.word_count || 0}字`),
    ]));

    if (d.outline && d.outline.length > 0) {
      box.appendChild(create("h4", { textContent: "大纲" }));
      const outlineBox = create("div", { className: "outline-list" });
      d.outline.forEach((s, i) => {
        const sec = create("div", { className: "outline-section" });
        sec.appendChild(create("strong", { textContent: `${i + 1}. ${s.section || ""}` }));
        if (s.items && s.items.length) {
          const ul = create("ul");
          s.items.forEach(item => {
            const text = typeof item === "string" ? item : (item.point || item.content || item.text || JSON.stringify(item));
            ul.appendChild(create("li", { textContent: text }));
          });
          sec.appendChild(ul);
        }
        outlineBox.appendChild(sec);
      });
      box.appendChild(outlineBox);
    }

    if (d.content) {
      box.appendChild(create("h4", { textContent: "正文预览" }));
      const preview = d.content.length > 2000 ? d.content.slice(0, 2000) + "\n\n... (点击预览查看完整内容)" : d.content;
      const previewBox = create("div", { className: "content-preview formatted" });
      previewBox.innerHTML = renderMarkdownToHtml(preview);
      box.appendChild(previewBox);
    }

    // Toolbar row for draft actions
    const toolbar = create("div", { className: "draft-toolbar" });
    
    // Primary generation actions
    if (!d.outline || d.outline.length === 0) {
      toolbar.appendChild(create("button", { className: "toolbar-btn primary", textContent: "生成大纲", onClick: () => generateOutlineFromDraft(d) }));
    } else if (!d.content) {
      toolbar.appendChild(create("button", { className: "toolbar-btn primary", textContent: "撰写正文", onClick: () => generateContent(d) }));
    } else {
      toolbar.appendChild(create("button", { className: "toolbar-btn", textContent: "生成大纲", onClick: () => generateOutlineFromDraft(d) }));
      toolbar.appendChild(create("button", { className: "toolbar-btn", textContent: "撰写正文", onClick: () => generateContent(d) }));
    }
    
    // Separator
    toolbar.appendChild(create("span", { className: "toolbar-sep" }));

    // Media actions
    toolbar.appendChild(create("button", { className: "toolbar-btn", textContent: "封面 Prompt", onClick: () => generateCover(d.title, d.platform, d.draft_id, d.topic_id) }));
    toolbar.appendChild(create("button", { className: "toolbar-btn", textContent: "配图 Prompt", onClick: () => generateInlineImages(d) }));
    toolbar.appendChild(create("button", { className: "toolbar-btn", textContent: "即梦分镜", onClick: () => generateJimeng(d.title, d.content, 5, d.draft_id, d.topic_id) }));
    toolbar.appendChild(create("button", { className: "toolbar-btn", textContent: "AI 生图", onClick: () => openImageGenModal(d.title) }));

    // Spacer + primary action
    toolbar.appendChild(create("span", { style: "flex:1" }));
    toolbar.appendChild(create("button", { className: "toolbar-btn accent", textContent: "预览效果", onClick: () => openDraftPreview(d) }));

    // Secondary row
    const secondaryRow = create("div", { className: "draft-secondary-actions" });
    secondaryRow.appendChild(create("button", { className: "secondary-sm", textContent: "归档到知识库", onClick: () => archiveDraft(d) }));
    secondaryRow.appendChild(create("button", { className: "secondary-sm", textContent: "编辑草稿", onClick: () => openDraftEditor(d) }));
    secondaryRow.appendChild(create("button", { className: "danger-sm", textContent: "删除", onClick: () => deleteDraft(d.draft_id) }));

    box.appendChild(toolbar);
    box.appendChild(secondaryRow);
  }

  if (sel.type === "wiki") {
    const w = sel.data;
    box.appendChild(create("h3", { textContent: w.title }));
    if (w.summary) box.appendChild(create("p", { className: "muted", textContent: w.summary }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(w.status || "草稿", "tag wiki"),
      createTag(`${w.word_count || 0}字`),
      ...(w.tags || []).slice(0, 4).map(t => createTag(t)),
    ]));
    if (w.content_md) {
      const preview = w.content_md.length > 500 ? w.content_md.slice(0, 500) + "..." : w.content_md;
      box.appendChild(create("div", { className: "content-preview", textContent: preview }));
    }
    box.appendChild(create("div", { className: "ai-actions" }, [
      create("button", { className: "secondary", textContent: "✏️ 编辑文章", onClick: () => openWikiEditor(w) }),
      create("button", { className: "danger", textContent: "🗑️ 删除", onClick: () => deleteWiki(w.page_id) }),
    ]));
  }

  if (sel.type === "media") {
    const m = sel.data;
    box.appendChild(create("h3", { textContent: m.title }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(m.prompt_type, "tag media"),
      m.platform ? createTag(m.platform) : null,
      m.status ? createTag(m.status) : null,
    ]));
    if (m.style_reference) box.appendChild(create("p", { className: "muted", textContent: `风格参考：${m.style_reference}` }));
    if (m.music_suggestion) box.appendChild(create("p", { className: "muted", textContent: `BGM 建议：${m.music_suggestion}` }));
    if (m.prompts && m.prompts.length) {
      m.prompts.forEach(p => {
        const card = create("div", { className: "shot-card" });
        card.appendChild(create("strong", { textContent: p.shot_name ? `${p.shot_number || ""} ${p.shot_name}` : (p.shot_number ? `镜头 ${p.shot_number}` : "提示词") }));
        if (p.prompt) {
          card.appendChild(create("div", { className: "prompt-block", textContent: p.prompt }));
        }
        if (p.negative_prompt) {
          card.appendChild(create("p", { className: "negative", textContent: `负面：${p.negative_prompt}` }));
        }
        card.appendChild(create("button", { className: "secondary", style: "margin-top:8px;margin-right:6px", textContent: "📋 复制提示词", onClick: () => {
          navigator.clipboard.writeText(p.prompt || "").then(() => showToast("已复制到剪贴板")).catch(() => showToast("复制失败，请手动选择", "error"));
        } }));
        if (p.prompt) {
          card.appendChild(create("button", { className: "ai-btn", style: "margin-top:8px", textContent: "🎨 用此提示词生图", onClick: () => {
            openImageGenModal(p.prompt, p.negative_prompt || "");
          } }));
        }
        box.appendChild(card);
      });
    }
    box.appendChild(create("div", { className: "ai-actions" }, [
      create("button", { className: "danger", textContent: "🗑️ 删除", onClick: () => deleteMediaPrompt(m.prompt_id) }),
    ]));
  }
}

function openDraftEditor(draft) {
  const isNew = !draft;
  const d = draft || { title: "", platform: el("draftPlatform")?.value || "公众号", content: "", outline: [], draft_id: null };
  const outlineStr = d.outline && d.outline.length ? JSON.stringify(d.outline, null, 2) : "";

  const form = create("form", { className: "editor-form" });
  form.innerHTML = `
    <label><span>标题</span><input name="title" type="text" value="${escapeHtml(d.title)}" required></label>
    <div class="form-row">
      <label><span>平台</span><select name="platform">
        <option${d.platform === "公众号" ? " selected" : ""}>公众号</option>
        <option${d.platform === "小红书" ? " selected" : ""}>小红书</option>
        <option${d.platform === "视频号脚本" ? " selected" : ""}>视频号脚本</option>
        <option${d.platform === "通用文章" ? " selected" : ""}>通用文章</option>
      </select></label>
      <label><span>状态</span><select name="status">
        <option${d.status === "大纲" ? " selected" : ""}>大纲</option>
        <option${d.status === "草稿" ? " selected" : ""}>草稿</option>
        <option${d.status === "修改中" ? " selected" : ""}>修改中</option>
        <option${d.status === "待审核" ? " selected" : ""}>待审核</option>
        <option${d.status === "定稿" ? " selected" : ""}>定稿</option>
        <option${d.status === "已发布" ? " selected" : ""}>已发布</option>
      </select></label>
    </div>
    <label><span>大纲 (JSON格式，留空则无大纲)</span><textarea name="outline_text" rows="6" placeholder='[{"section":"开篇","items":["钩子"]}]'>${escapeHtml(outlineStr)}</textarea></label>
    <label><span>正文 (Markdown)</span><textarea name="content" rows="12">${escapeHtml(d.content || "")}</textarea></label>
    <div class="form-actions">
      <button type="button" class="secondary" data-action="cancel">取消</button>
      <button type="submit">${isNew ? "创建草稿" : "保存"}</button>
    </div>
  `;
  openModal(isNew ? "新建草稿" : "编辑草稿", form);

  form.querySelector('[data-action="cancel"]').addEventListener("click", closeModal);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    await runAction(async () => {
      let outline = d.outline || [];
      const outlineText = (fd.get("outline_text") || "").trim();
      if (outlineText) {
        try {
          outline = JSON.parse(outlineText);
        } catch (err) {
          throw new Error("大纲 JSON 格式有误，请检查格式");
        }
      } else {
        outline = [];
      }
      const content = fd.get("content") || "";
      const payload = {
        title: fd.get("title"),
        platform: fd.get("platform"),
        status: fd.get("status"),
        content: content,
        outline: outline,
        word_count: content.length,
      };
      if (isNew) {
        payload.content_type = "文章";
        payload.source = "manual";
        const result = await api(API.drafts, { method: "POST", body: JSON.stringify(payload) });
        showToast("草稿已创建");
        closeModal();
        await refresh();
        if (result.draft_id) {
          const newDraft = state.drafts.find(x => x.draft_id === result.draft_id);
          if (newDraft) {
            state.selectedItem = { type: "draft", data: newDraft };
            renderAll();
          }
        }
      } else {
        await api(`/api/drafts/${d.draft_id}`, { method: "PATCH", body: JSON.stringify(payload) });
        showToast("草稿已保存");
        closeModal();
        await refresh();
      }
    });
  });
}

function openDraftPreview(draft) {
  const modalBody = create("div");
  modalBody.style.cssText = "max-height:80vh;overflow:auto;padding:16px;";

  // 标题
  modalBody.appendChild(create("h2", { textContent: draft.title }));
  modalBody.appendChild(create("div", { className: "meta-row" }, [
    createTag(draft.platform || "公众号", "tag draft"),
    createTag(draft.content_type || "文章"),
    createTag(`${draft.word_count || 0}字`),
  ]));

  // 渲染正文（Markdown → HTML 简易转换）
  if (draft.content) {
    const contentHtml = renderMarkdownToHtml(draft.content);
    const contentBox = create("div", {
      className: "preview-content",
      innerHTML: contentHtml,
    });
    contentBox.style.cssText = "margin-top:16px;line-height:1.8;font-size:15px;";
    modalBody.appendChild(contentBox);
  }

  // 如果有内联图片提示词，显示在底部
  if (draft.inline_image_prompts) {
    let prompts = [];
    try { prompts = JSON.parse(draft.inline_image_prompts); } catch (_) { prompts = []; }
    if (prompts.length > 0) {
      modalBody.appendChild(create("h3", { textContent: "📷 配图提示词", style: "margin-top:24px;" }));
      const promptList = create("div");
      prompts.forEach((p, i) => {
        promptList.appendChild(create("div", {
          className: "prompt-item",
          innerHTML: `<strong>图${i + 1}（${p.position || "正文"}）：</strong>${escapeHtml(p.prompt || "")}`,
          style: "margin:8px 0;padding:8px;background:#f5f5f5;border-radius:4px;",
        }));
      });
      modalBody.appendChild(promptList);
    }
  }

  openModal(`👁️ 预览：${draft.title}`, modalBody);
}

function renderMarkdownToHtml(md) {
  if (!md) return "";
  const lines = md.split("\n");
  let html = "";
  let inList = false;
  let inCodeBlock = false;
  let codeContent = "";
  let codeLang = "";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // 代码块
    if (line.startsWith("```")) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
        codeContent = "";
      } else {
        inCodeBlock = false;
        html += `<pre><code class="lang-${codeLang}">${escapeHtml(codeContent.trim())}</code></pre>`;
      }
      continue;
    }
    if (inCodeBlock) {
      codeContent += line + "\n";
      continue;
    }

    // 标题
    if (/^### /.test(line)) {
      closeList(); html += `<h4>${renderInline(line.slice(4))}</h4>`; continue;
    }
    if (/^## /.test(line)) {
      closeList(); html += `<h3>${renderInline(line.slice(3))}</h3>`; continue;
    }
    if (/^# /.test(line)) {
      closeList(); html += `<h2>${renderInline(line.slice(2))}</h2>`; continue;
    }

    // 列表
    if (/^[-*] /.test(line)) {
      if (!inList) { inList = true; html += "<ul>"; }
      html += `<li>${renderInline(line.replace(/^[-*] /, ""))}</li>`;
      continue;
    } else {
      closeList();
    }

    // 空行 = 段落分隔
    if (line.trim() === "") {
      if (html && !html.endsWith("</p>")) html += "</p>";
      continue;
    }

    // 普通段落
    if (!html.endsWith("<p>") && html && !html.endsWith("</p>") && !html.endsWith("<br>")) {
      html += "<p>";
    }
    html += renderInline(line) + "<br>";
  }

  closeList();
  if (html && !html.endsWith("</p>")) html += "</p>";

  function closeList() {
    if (inList) { inList = false; html += "</ul>"; }
  }

  function renderInline(text) {
    if (!text) return "";
    text = escapeHtml(text);
    text = text.replace(/!\[(.*?)\]\((.+?)\)/g, '<img src="$2" alt="$1" loading="lazy">');
    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
    text = text.replace(/`(.+?)`/g, "<code>$1</code>");
    text = text.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');
    return text;
  }

  return html;
}

function openWikiEditor(page) {
  const isNew = !page;
  const w = page || { title: "", summary: "", content_md: "", tags: [], page_id: null };
  const form = create("form", { className: "editor-form" });
  form.innerHTML = `
    <label><span>标题</span><input name="title" type="text" value="${escapeHtml(w.title)}" required></label>
    <label><span>摘要</span><input name="summary" type="text" value="${escapeHtml(w.summary || "")}"></label>
    <label><span>标签 (逗号分隔)</span><input name="tags_str" type="text" value="${escapeHtml((w.tags || []).join(", "))}"></label>
    <label><span>内容 (Markdown)</span><textarea name="content_md" rows="12">${escapeHtml(w.content_md || "")}</textarea></label>
    <div class="form-actions">
      <button type="button" class="secondary" data-action="cancel">取消</button>
      <button type="submit">${isNew ? "创建文章" : "保存"}</button>
    </div>
  `;
  openModal(isNew ? "新建知识库文章" : "编辑知识库文章", form);
  form.querySelector('[data-action="cancel"]').addEventListener("click", closeModal);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const tags = (fd.get("tags_str") || "").split(/[,，]/).map(s => s.trim()).filter(Boolean);
    const payload = {
      title: fd.get("title"),
      summary: fd.get("summary"),
      content_md: fd.get("content_md"),
      tags,
      status: "草稿",
    };
    await runAction(async () => {
      if (isNew) {
        await api(API.wiki, { method: "POST", body: JSON.stringify(payload) });
        showToast("文章已创建");
      } else {
        await api(`/api/wiki/${w.page_id}`, { method: "PATCH", body: JSON.stringify(payload) });
        showToast("文章已保存");
      }
      closeModal();
      await refresh();
    });
  });
}

async function completeTask(task) {
  await runAction(async () => {
    await api(`/api/tasks/${task.task_id}`, { method: "PATCH", body: JSON.stringify({ status: "已完成" }) });
    showToast("任务已完成");
    state.selectedItem = null;
    await refresh();
  });
}

async function deleteTask(id) {
  if (!await confirmDialog("确定删除此任务？")) return;
  await runAction(async () => {
    await api(`/api/tasks/${id}`, { method: "DELETE" });
    showToast("已删除");
    state.selectedItem = null;
    await refresh();
  });
}

async function deleteIdea(id) {
  if (!await confirmDialog("确定删除此灵感？")) return;
  await runAction(async () => {
    await api(`/api/ideas/${id}`, { method: "DELETE" });
    showToast("已删除");
    state.selectedItem = null;
    await refresh();
  });
}

async function promoteIdeaToTopic(idea) {
  const title = idea.raw_text ? idea.raw_text.slice(0, 40) : "";
  const payload = {
    title: title || "来自灵感的选题",
    platform: "公众号",
    angle: idea.raw_text || "",
    source_type: "idea",
    source_id: idea.idea_id,
    score: 60,
    status: "候选",
  };
  await runAction(async () => {
    await api(API.topics, { method: "POST", body: JSON.stringify(payload) });
    showToast("已转为选题");
    selectTab("topics");
    await refresh();
  });
}

async function aiPromoteIdea(idea) {
  if (!state.llmConfigured) { showToast("请先配置 AI", "error"); return; }
  await startAiWork("🤖 AI 正在分析灵感...", async () => {
    const result = await api("/api/ideas/ai-convert", {
      method: "POST",
      body: JSON.stringify({
        idea_id: idea.idea_id,
        text: idea.raw_text || idea.content || "",
        auto_create: true,
      }),
    });
    if (result.topic) {
      showToast(`AI 选题已创建：${result.topic.title}`);
      selectTab("topics");
      await refresh();
    }
    return result;
  });
}

async function startAiWork(label, fn) {
  if (!state.llmConfigured) { showToast("AI 未配置，请检查 TinyRouter 是否运行", "error"); return; }
  state.aiWorking = label;
  state.aiResult = null;
  renderDetail();
  try {
    const result = await fn();
    state.aiWorking = null;
    renderDetail();
    return result;
  } catch (e) {
    state.aiWorking = null;
    state.aiResult = { title: "生成失败", error: e.message || String(e) };
    renderDetail();
    throw e;
  }
}

async function generateOutlineFromTopic(topic) {
  await startAiWork("🤖 正在生成大纲...", async () => {
    const result = await api("/api/drafts/generate-outline", {
      method: "POST",
      body: JSON.stringify({
        title: topic.title,
        platform: topic.platform || "公众号",
        angle: topic.angle || "",
        target_audience: topic.target_audience || "",
        topic_id: topic.topic_id,
        auto_save: true,
      }),
    });
    await refresh();
    selectTab("drafts");
    let draft = null;
    if (result.draft_id) {
      draft = state.drafts.find(x => x.draft_id === result.draft_id);
      if (draft) state.selectedItem = { type: "draft", data: draft };
    }
    const outlineHtml = formatOutlineHtml(result.outline || [], result.hook, result.suggested_title);
    state.aiResult = { title: "✅ 大纲生成完成", html: outlineHtml };
    renderAll();
  });
}

async function generateOutlineFromDraft(draft) {
  await startAiWork("🤖 正在生成大纲...", async () => {
    const result = await api("/api/drafts/generate-outline", {
      method: "POST",
      body: JSON.stringify({ title: draft.title, platform: draft.platform || "公众号", auto_save: false }),
    });
    await api(`/api/drafts/${draft.draft_id}`, {
      method: "PATCH",
      body: JSON.stringify({ outline: result.outline, status: "大纲" }),
    });
    await refresh();
    const updated = state.drafts.find(x => x.draft_id === draft.draft_id);
    if (updated) state.selectedItem = { type: "draft", data: updated };
    state.aiResult = { title: "✅ 大纲已更新", html: formatOutlineHtml(result.outline || [], result.hook, result.suggested_title) };
    renderAll();
  });
}

async function generateContent(draft) {
  if (!draft.outline || !draft.outline.length) {
    showToast("请先生成大纲", "error");
    return;
  }
  await startAiWork("✍️ 正在撰写正文...", async () => {
    const result = await api("/api/drafts/generate-content", {
      method: "POST",
      body: JSON.stringify({ title: draft.title, outline: draft.outline, platform: draft.platform, draft_id: draft.draft_id }),
    });
    await refresh();
    const updated = state.drafts.find(x => x.draft_id === draft.draft_id);
    if (updated) state.selectedItem = { type: "draft", data: updated };
    const contentPreview = (result.content || "").slice(0, 500).replace(/\n/g, "<br>");
    state.aiResult = {
      title: `✅ 正文生成完成（${result.word_count} 字）`,
      html: `<div class="content-preview">${contentPreview}${result.content.length > 500 ? '<br><em>...（完整内容请点击「编辑草稿」查看）</em>' : ''}</div>`
    };
    renderAll();
  });
}

async function generateCover(title, platform, draftId, topicId) {
  await startAiWork("🎨 正在生成封面提示词...", async () => {
    const result = await api("/api/media/generate-cover", {
      method: "POST",
      body: JSON.stringify({ title, platform, draft_id: draftId, topic_id: topicId, auto_save: true }),
    });
    await refresh();
    selectTab("media");
    state.aiResult = {
      title: "✅ 封面提示词已生成",
      html: `<div class="prompt-result"><p><strong>提示词：</strong></p><p class="prompt-text">${escapeHtml(result.cover_prompt || '')}</p>${result.cover_negative_prompt ? `<p><strong>负面词：</strong></p><p class="prompt-text neg">${escapeHtml(result.cover_negative_prompt)}</p>` : ''}</div>`
    };
    renderAll();
  });
}

async function generateJimeng(title, content, count, draftId, topicId) {
  await startAiWork("🎬 正在生成即梦分镜...", async () => {
    const result = await api("/api/media/generate-jimeng", {
      method: "POST",
      body: JSON.stringify({ title, content, shot_count: count, draft_id: draftId, topic_id: topicId, auto_save: true }),
    });
    await refresh();
    selectTab("media");
    const shots = (result.prompts || []).map((p, i) =>
      `<div class="shot-item"><strong>镜头 ${i+1}：${escapeHtml(p.shot_description || '')}</strong><p class="prompt-text">${escapeHtml(p.prompt || '')}</p></div>`
    ).join("");
    state.aiResult = {
      title: `✅ 即梦分镜已生成（${result.prompts?.length || 0} 个镜头）`,
      html: `<div class="shots-result">${shots}</div>`
    };
    renderAll();
  });
}

async function generateInlineImages(draft) {
  await startAiWork("🖼️ 正在生成配图提示词...", async () => {
    const result = await api("/api/media/generate-inline-images", {
      method: "POST",
      body: JSON.stringify({ title: draft.title, outline: draft.outline, platform: draft.platform, draft_id: draft.draft_id, auto_save: true }),
    });
    await refresh();
    selectTab("media");
    const imgs = (result.images || []).map((img, i) =>
      `<div class="shot-item"><strong>配图 ${i+1}：${escapeHtml(img.position || '')}</strong><p class="prompt-text">${escapeHtml(img.prompt || '')}</p></div>`
    ).join("");
    state.aiResult = {
      title: `✅ 配图提示词已生成（${result.images?.length || 0} 张）`,
      html: `<div class="shots-result">${imgs}</div>`
    };
    renderAll();
  });
}

let imageGenModal = null;
function openImageGenModal(defaultPrompt, defaultNegative) {
  if (!state.imageConfigured) {
    showToast("图片生成未配置，请在设置中填写图片生成 API 地址", "error");
    return;
  }
  if (imageGenModal) {
    document.body.removeChild(imageGenModal);
  }
  const overlay = create("div", { className: "modal-overlay", onClick: (e) => { if (e.target === overlay) closeImageGenModal(); } });
  const modal = create("div", { className: "modal image-gen-modal" });
  modal.appendChild(create("div", { className: "modal-header", textContent: "🤖 AI 图片生成" }));

  const body = create("div", { className: "modal-body" });
  const promptInput = create("textarea", { rows: 3, placeholder: "输入图片描述，例如：一只可爱的橘猫坐在木桌上，暖光，数码艺术风格，高质量", value: defaultPrompt || "" });
  promptInput.style.width = "100%";
  promptInput.style.padding = "10px";
  promptInput.style.borderRadius = "8px";
  promptInput.style.border = "1px solid var(--border)";
  promptInput.style.resize = "vertical";
  body.appendChild(create("label", { textContent: "提示词 (Prompt)", style: "display:block;margin-bottom:6px;font-weight:600" }));
  body.appendChild(promptInput);

  const negInput = create("textarea", { rows: 2, placeholder: "负面提示词（可选），例如：模糊, 低质量, 变形, 多余手指", value: defaultNegative || "" });
  negInput.style.width = "100%";
  negInput.style.padding = "10px";
  negInput.style.borderRadius = "8px";
  negInput.style.border = "1px solid var(--border)";
  negInput.style.marginTop = "12px";
  negInput.style.resize = "vertical";
  body.appendChild(create("label", { textContent: "负面提示词 (Negative)", style: "display:block;margin:12px 0 6px;font-weight:600" }));
  body.appendChild(negInput);

  const sizeRow = create("div", { className: "form-row", style: "display:flex;gap:12px;margin-top:12px;align-items:center" });
  sizeRow.appendChild(create("label", { textContent: "尺寸:", style: "font-weight:600" }));
  const sizeSel = create("select");
  ["1024x1024", "1024x768", "768x1024", "1280x720", "720x1280"].forEach(s => {
    const opt = document.createElement("option");
    opt.value = s; opt.textContent = s;
    sizeSel.appendChild(opt);
  });
  sizeRow.appendChild(sizeSel);
  body.appendChild(sizeRow);

  const resultArea = create("div", { id: "imgGenResult", style: "margin-top:16px;min-height:100px;display:flex;flex-direction:column;gap:12px;align-items:center" });
  body.appendChild(resultArea);

  const footer = create("div", { className: "modal-footer" });
  const genBtn = create("button", { className: "primary", textContent: "🎨 生成图片", onClick: async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) { showToast("请输入提示词", "error"); return; }
    resultArea.innerHTML = '<div style="color:var(--muted);padding:20px">⏳ 正在生成图片，约需10-20秒...</div>';
    genBtn.disabled = true; genBtn.textContent = "⏳ 生成中...";
    try {
      const res = await api("/api/image/generate", {
        method: "POST",
        body: JSON.stringify({
          prompt,
          negative_prompt: negInput.value.trim(),
          size: sizeSel.value,
          n: 1,
        }),
      });
      resultArea.innerHTML = "";
      // 显示提示词处理信息（清洗/重试）
      const meta = res.prompt_meta;
      if (meta) {
        const metaDiv = create("div", { style: "padding:8px 12px;background:#fef3c7;border-radius:8px;font-size:12px;color:#92400e;display:flex;flex-direction:column;gap:4px" });
        if (meta.cleaned) {
          metaDiv.appendChild(create("span", { textContent: "⚠️ 提示词已自动清理敏感内容以通过内容审核" }));
          if (meta.removed_parts && meta.removed_parts.length) {
            metaDiv.appendChild(create("span", { className: "muted", textContent: "移除: " + meta.removed_parts.join(", ") }));
          }
        }
        if (meta.simplified) {
          metaDiv.appendChild(create("span", { textContent: "✂️ 提示词已自动简化（截取核心描述）" }));
        }
        if (meta.retried) {
          metaDiv.appendChild(create("span", { textContent: "🔄 自动重试 " + meta.retry_count + " 次后成功" }));
        }
        resultArea.appendChild(metaDiv);
      }
      (res.images || []).forEach((img, i) => {
        const card = create("div", { className: "img-result-card", style: "border:1px solid var(--border);border-radius:10px;padding:12px;display:flex;flex-direction:column;align-items:center;gap:8px" });
        let imgSrc = "";
        let isLocal = false;
        if (img.local_path) {
          // local_path 是相对于 ROOT 的路径，如 "data/images/xxx.jpg"
          const filename = img.local_path.split("/").pop().split("\\").pop();
          imgSrc = `/api/image-file/${encodeURIComponent(filename)}`;
          isLocal = true;
        } else if (img.url) {
          imgSrc = img.url;
        }
        if (imgSrc) {
          const imgEl = document.createElement("img");
          imgEl.src = imgSrc;
          imgEl.style.maxWidth = "100%";
          imgEl.style.borderRadius = "8px";
          imgEl.style.boxShadow = "0 2px 8px rgba(0,0,0,0.1)";
          imgEl.style.cursor = "pointer";
          imgEl.title = "点击在新窗口打开";
          imgEl.onclick = () => window.open(imgSrc, "_blank");
          card.appendChild(imgEl);
        }
        if (isLocal) {
          const savedBadge = create("span", { textContent: "已保存到本地", style: "font-size:11px;color:#16a34a;background:#dcfce7;padding:2px 8px;border-radius:999px" });
          card.appendChild(savedBadge);
          const pathLabel = create("p", { className: "muted", style: "font-size:11px;margin:2px 0 0;word-break:break-all" });
          // 显示相对路径
          pathLabel.textContent = img.local_path;
          card.appendChild(pathLabel);
        }
        if (img.revised_prompt) {
          const revP = create("p", { className: "muted", style: "font-size:12px;margin:4px 0 0;text-align:center", textContent: "优化提示词: " + img.revised_prompt });
          card.appendChild(revP);
        }
        resultArea.appendChild(card);
      });
      resultArea.appendChild(create("div", { className: "muted", style: "font-size:12px", textContent: `✅ 生成耗时 ${res.elapsed_seconds}s · 模型: ${res.model}` }));
    } catch (e) {
      resultArea.innerHTML = `<div style="color:#ef4444;padding:20px">❌ 生成失败: ${escapeHtml(e.message || String(e))}</div>`;
    } finally {
      genBtn.disabled = false; genBtn.textContent = "🎨 生成图片";
    }
  }});
  footer.appendChild(genBtn);
  footer.appendChild(create("button", { className: "secondary", textContent: "关闭", onClick: closeImageGenModal }));
  modal.appendChild(body);
  modal.appendChild(footer);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
  imageGenModal = overlay;
  promptInput.focus();
}

function closeImageGenModal() {
  if (imageGenModal) {
    document.body.removeChild(imageGenModal);
    imageGenModal = null;
  }
}

async function archiveDraft(draft) {
  await runAction(async () => {
    await api(`/api/drafts/${draft.draft_id}/archive-wiki`, { method: "POST", body: JSON.stringify({}) });
    showToast("已归档到知识库");
    await refresh();
  });
}

async function deleteDraft(id) {
  if (!await confirmDialog("确定删除此草稿？删除后无法恢复。")) return;
  await runAction(async () => {
    await api(`/api/drafts/${id}`, { method: "DELETE" });
    showToast("已删除");
    state.selectedItem = null;
    await refresh();
  });
}

async function deleteWiki(id) {
  if (!await confirmDialog("确定删除此知识库文章？")) return;
  await runAction(async () => {
    await api(`/api/wiki/${id}`, { method: "DELETE" });
    showToast("已删除");
    state.selectedItem = null;
    await refresh();
  });
}

async function deleteMediaPrompt(id) {
  if (!await confirmDialog("确定删除此提示词？")) return;
  await runAction(async () => {
    await api(`/api/media-prompts/${id}`, { method: "DELETE" });
    showToast("已删除");
    state.selectedItem = null;
    await refresh();
  });
}

function renderStatus() {
  const list = el("statusList");
  list.innerHTML = "";
  Object.entries(state.status).forEach(([key, value]) => {
    if (["safe_mode", "public_access"].includes(key)) return;
    list.appendChild(create("div", { className: "status-row" }, [
      create("strong", { textContent: labels[key] || key }),
      create("span", { textContent: text(value) }),
    ]));
  });
  el("workbenchState").textContent = state.status.workbench || "unknown";
  el("workbenchState").className = state.status.workbench === "online" ? "counter good" : "counter warn";
  el("safeModeBadge").className = state.status.safe_mode ? "status-pill good" : "status-pill warn";
  el("accessBadge").className = state.status.public_access ? "status-pill warn" : "status-pill good";
  el("accessBadge").textContent = state.status.public_access ? "局域网访问" : "本机访问";
  el("llmStatus").className = state.llmConfigured ? "status-pill good" : "status-pill warn";
  el("llmStatus").textContent = state.llmConfigured ? "AI 已就绪" : "AI 未配置";
}

function renderLogs() {
  const list = el("logsList");
  list.innerHTML = "";
  el("logCount").textContent = `${state.logs.length} 条`;
  if (!state.logs.length) { list.appendChild(create("div", { className: "empty", textContent: "暂无日志" })); return; }
  state.logs.slice().reverse().slice(0, 30).forEach(log => {
    const row = create("div", { className: "log-row" });
    [log.created_at, log.event_type, log.message].forEach(v => {
      row.appendChild(create("span", { textContent: text(v) }));
    });
    list.appendChild(row);
  });
}

// ===== 设置功能 =====
let settingsCache = {};

async function showSettings() {
  el("modalTitle").textContent = "⚙️ 系统设置";
  el("modalBody").innerHTML = '<div class="settings-loading">加载中...</div>';
  openModal();
  try {
    const data = await api(API.settings);
    settingsCache = data.settings || {};
    renderSettingsForm();
  } catch (err) {
    el("modalBody").innerHTML = `<div class="notice error">加载失败：${escapeHtml(err.message)}</div>`;
  }
}

function renderSettingsForm() {
  let html = "";
  const groupLabels = {
    llm: "🔗 API 统一入口（文本+图片共用）",
    image: "🖼️ 图片生成配置（独立 API，不经过 TinyRouter）",
    system: "⚙️ 系统设置",
    content: "📝 内容生成默认值"
  };
  // API 说明
  html += `<div class="settings-notice">
    <strong>TinyRouter 统一入口（文本）</strong> — 文本生成共用一个地址<br>
    <span class="settings-hint">模型组已启用：text-smart-fallback，自动故障切换</span><br>
    <strong style="margin-top:6px;display:block">图片生成（独立 API）</strong> — 需单独配置图片生成服务地址
  </div>`;
  for (const [group, items] of Object.entries(settingsCache)) {
    const label = groupLabels[group];
    if (!label || !items.length) continue;
    html += `<div class="settings-group"><div class="settings-group-title">${label}</div>`;
    items.forEach(s => {
      const isSecret = s.is_secret;
      const val = s.value || "";
      const inputType = isSecret ? "password" : "text";
      html += `<div class="settings-item">
        <label class="settings-label" for="setting_${escapeHtml(s.key)}">${escapeHtml(s.description || s.key)}</label>
        <input class="settings-input" type="${inputType}" id="setting_${escapeHtml(s.key)}" value="${escapeHtml(val)}" data-key="${escapeHtml(s.key)}" data-secret="${isSecret ? "1" : "0"}">
      </div>`;
      if (isSecret && val) {
        html += `<div class="settings-hint">当前已设置（点击输入框可修改）</div>`;
      }
    });
    if (group === "llm") {
      html += `<div class="settings-actions">
        <button type="button" class="btn-sm" id="testLlmBtn">测试连接</button>
        <span id="testResult" class="settings-status"></span>
      </div>`;
    }
    html += `</div>`;
  }
  html += `<div class="settings-actions"><button type="button" class="btn-sm primary" id="saveSettingsBtn">保存设置</button></div>`;
  html += `<div id="saveResult" class="settings-status"></div>`;
  el("modalBody").innerHTML = html;

  // 绑定事件
  const testBtn = el("testLlmBtn");
  if (testBtn) testBtn.addEventListener("click", testLlmConnection);
  el("saveSettingsBtn").addEventListener("click", saveSettings);
}

async function testLlmConnection() {
  const resultEl = el("testResult");
  resultEl.textContent = "测试中...";
  resultEl.className = "settings-status";
  const baseUrl = el("setting_tinytrouter_base_url")?.value || "";
  const apiKey = el("setting_tinytrouter_api_key")?.value || "";
  const model = el("setting_default_llm_model")?.value || "deepseek-chat";
  try {
    const result = await api(API.settingsTest, { method: "POST", body: JSON.stringify({ base_url: baseUrl, api_key: apiKey, model }) });
    if (result.ok) {
      resultEl.textContent = `✅ 连接成功！模型：${result.model || model}`;
      resultEl.className = "settings-status ok";
    } else {
      resultEl.textContent = `❌ 连接失败：${result.error || "未知错误"}`;
      resultEl.className = "settings-status err";
    }
  } catch (err) {
    resultEl.textContent = `❌ 测试失败：${err.message}`;
    resultEl.className = "settings-status err";
  }
}

async function saveSettings() {
  const resultEl = el("saveResult");
  resultEl.textContent = "保存中...";
  resultEl.className = "settings-status";
  const inputs = el("modalBody").querySelectorAll(".settings-input");
  const payload = {};
  inputs.forEach(input => {
    const key = input.dataset.key;
    let value = input.value;
    // 如果是密钥字段且值为空（脱敏显示），则不更新
    if (input.dataset.secret === "1" && input.type === "password" && !value) {
      return;
    }
    payload[key] = value;
  });
  try {
    await api(API.settingsUpdate, { method: "POST", body: JSON.stringify(payload) });
    resultEl.textContent = "✅ 保存成功！部分设置需要重启服务后生效。";
    resultEl.className = "settings-status ok";
    // 重新加载设置
    const data = await api(API.settings);
    settingsCache = data.settings || {};
  } catch (err) {
    resultEl.textContent = `❌ 保存失败：${err.message}`;
    resultEl.className = "settings-status err";
  }
}

function renderCounts() {
  el("taskCount").textContent = state.tasks.length;
  el("ideaCount").textContent = state.ideas.length;
  el("topicCount").textContent = state.topics.length;
  el("draftCount").textContent = state.drafts.length;
  el("wikiCount").textContent = state.wiki.length;
  el("mediaCount").textContent = state.media.length;
}

function renderAll() {
  renderCounts();
  renderListPanel();
  renderDetail();
  renderStatus();
  renderLogs();
}

async function refresh() {
  try {
    const [tasks, ideas, topics, drafts, wiki, media, status, logs, llmStatus] = await Promise.all([
      api(API.tasks), api(API.ideas), api(API.topics), api(API.drafts),
      api(API.wiki), api(API.media), api(API.status), api(API.logs),
      api(API.llmStatus).catch(() => ({ configured: false })),
    ]);
    const prevSel = state.selectedItem;
    state = { ...state, tasks, ideas, topics, drafts, wiki, media, status, logs, llmConfigured: llmStatus.configured, imageConfigured: llmStatus.image_configured };
    if (prevSel) {
      const list = state[prevSel.type + "s"] || state[prevSel.type === "media" ? "media" : prevSel.type + "s"];
      const idKey = prevSel.type + "_id";
      const found = list?.find(x => x[idKey] === prevSel.data[idKey]);
      if (found) state.selectedItem = { type: prevSel.type, data: found };
      else state.selectedItem = null;
    }
    renderAll();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function bindEvents() {
  document.querySelectorAll(".metric.clickable").forEach(m => {
    m.addEventListener("click", () => selectTab(m.dataset.mainTab));
  });
  el("modalClose").addEventListener("click", closeModal);
  el("modalOverlay").addEventListener("click", e => { if (e.target === el("modalOverlay")) closeModal(); });
  el("settingsBtn").addEventListener("click", showSettings);
}

async function init() {
  bindEvents();
  selectTab("tasks");
  try {
    await refresh();
  } catch (error) {
    showToast(error.message, "error");
  }
  setInterval(refresh, 30000);
}

init();
