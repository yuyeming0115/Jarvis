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
  activeTab: "tasks",
  selectedItem: null,
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
  public_access: "公网访问"
};

function el(id) {
  return document.getElementById(id);
}

function create(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "className") e.className = v;
    else if (k === "textContent") e.textContent = v;
    else if (k === "innerHTML") e.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  });
  (Array.isArray(children) ? children : [children]).forEach(c => {
    if (c) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  });
  return e;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `请求失败：${response.status}`);
  return payload;
}

function showToast(message, type = "success") {
  const panel = type === "success" ? el("toastPanel") : el("errorPanel");
  panel.textContent = message;
  panel.classList.remove("hidden");
  if (type === "success") window.setTimeout(() => panel.classList.add("hidden"), 2400);
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

function selectTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll(".metric.clickable").forEach(m => {
    m.classList.toggle("active", m.dataset.mainTab === tab);
  });
  document.querySelectorAll(".main-panel").forEach(p => {
    p.classList.toggle("hidden", p.dataset.panel !== tab);
  });
  state.selectedItem = null;
  renderDetail();
}

function renderTasks() {
  const list = el("tasksList");
  list.innerHTML = "";
  if (!state.tasks.length) { renderEmpty(list, "暂无任务"); return; }
  state.tasks.forEach(task => {
    const title = create("div", { className: "item-title" }, [
      create("strong", { textContent: task.title }),
      createTag(task.priority || "P?", `priority ${(task.priority || "").toLowerCase()}`)
    ]);
    const desc = create("p", { textContent: task.description || "暂无描述" });
    const meta = create("div", { className: "meta-row" });
    [task.status, task.project, task.due_at].filter(Boolean).forEach(v => meta.appendChild(createTag(v)));
    const item = create("article", { className: "item" }, [title, desc, meta]);
    item.addEventListener("click", () => {
      state.selectedItem = { type: "task", data: task };
      document.querySelectorAll(".item").forEach(i => i.classList.remove("selected"));
      item.classList.add("selected");
      renderDetail();
    });
    list.appendChild(item);
  });
}

function renderIdeas() {
  const list = el("ideasList");
  list.innerHTML = "";
  if (!state.ideas.length) { renderEmpty(list, "暂无灵感"); return; }
  state.ideas.forEach(idea => {
    const title = create("div", { className: "item-title" }, [
      create("strong", { textContent: idea.type || "灵感" }),
      createTag(idea.status || "未处理")
    ]);
    const raw = create("p", { textContent: idea.raw_text || "暂无内容" });
    const meta = create("div", { className: "meta-row" });
    (idea.tags || []).forEach(tag => meta.appendChild(createTag(tag)));
    const item = create("article", { className: "item" }, [title, raw, meta]);
    item.addEventListener("click", () => {
      state.selectedItem = { type: "idea", data: idea };
      document.querySelectorAll(".item").forEach(i => i.classList.remove("selected"));
      item.classList.add("selected");
      renderDetail();
    });
    list.appendChild(item);
  });
}

function renderTopics() {
  const list = el("topicsList");
  list.innerHTML = "";
  if (!state.topics.length) { renderEmpty(list, "暂无选题"); return; }
  state.topics.forEach(topic => {
    const title = create("div", { className: "item-title" }, [
      create("strong", { textContent: topic.title }),
      createTag(`${topic.score || 0}分`)
    ]);
    const angle = create("p", { textContent: topic.angle || "暂无角度" });
    const meta = create("div", { className: "meta-row" });
    [topic.platform, topic.content_type, topic.status].filter(Boolean).forEach(v => meta.appendChild(createTag(v)));
    const actions = create("div", { className: "ai-actions" }, [
      create("button", {
        className: "ai-btn",
        textContent: "✨ AI 生成大纲",
        onClick: () => generateOutlineFromTopic(topic)
      })
    ]);
    const item = create("article", {
      className: `item ${state.selectedItem?.type === "topic" && state.selectedItem.data.topic_id === topic.topic_id ? "selected" : ""}`
    }, [title, angle, meta, actions]);
    item.addEventListener("click", (e) => {
      if (e.target.tagName === "BUTTON") return;
      state.selectedItem = { type: "topic", data: topic };
      document.querySelectorAll(".item").forEach(i => i.classList.remove("selected"));
      item.classList.add("selected");
      renderDetail();
    });
    list.appendChild(item);
  });
}

function renderDrafts() {
  const list = el("draftsList");
  list.innerHTML = "";
  if (!state.drafts.length) { renderEmpty(list, "暂无草稿，点击右上角「+ 新草稿」或从选题生成大纲"); return; }
  state.drafts.forEach(draft => {
    const title = create("div", { className: "item-title" }, [
      create("strong", { textContent: draft.title }),
      createTag(draft.status || "大纲", "tag draft")
    ]);
    const meta = create("div", { className: "meta-row" });
    [draft.platform, draft.content_type, `${draft.word_count || 0}字`].filter(Boolean).forEach(v => meta.appendChild(createTag(v)));
    const item = create("article", {
      className: `item ${state.selectedItem?.type === "draft" && state.selectedItem.data.draft_id === draft.draft_id ? "selected" : ""}`
    }, [title, meta]);
    item.addEventListener("click", () => {
      state.selectedItem = { type: "draft", data: draft };
      document.querySelectorAll(".item").forEach(i => i.classList.remove("selected"));
      item.classList.add("selected");
      renderDetail();
    });
    list.appendChild(item);
  });
}

function renderWiki() {
  const list = el("wikiList");
  list.innerHTML = "";
  if (!state.wiki.length) { renderEmpty(list, "知识库暂无文章"); return; }
  state.wiki.forEach(page => {
    const title = create("div", { className: "item-title" }, [
      create("strong", { textContent: page.title }),
      createTag(page.status || "草稿", "tag wiki")
    ]);
    const summary = create("p", { textContent: page.summary || "" });
    const meta = create("div", { className: "meta-row" });
    (page.tags || []).slice(0, 3).forEach(tag => meta.appendChild(createTag(tag)));
    meta.appendChild(createTag(`${page.word_count || 0}字`));
    const item = create("article", {
      className: `item ${state.selectedItem?.type === "wiki" && state.selectedItem.data.page_id === page.page_id ? "selected" : ""}`
    }, [title, summary, meta]);
    item.addEventListener("click", () => {
      state.selectedItem = { type: "wiki", data: page };
      document.querySelectorAll(".item").forEach(i => i.classList.remove("selected"));
      item.classList.add("selected");
      renderDetail();
    });
    list.appendChild(item);
  });
}

function renderMedia() {
  const list = el("mediaList");
  list.innerHTML = "";
  el("mediaCountBadge").textContent = `${state.media.length} 条`;
  if (!state.media.length) { renderEmpty(list, "暂无多媒体提示词，从草稿/选题生成封面或分镜"); return; }
  state.media.forEach(prompt => {
    const title = create("div", { className: "item-title" }, [
      create("strong", { textContent: prompt.title }),
      createTag(prompt.prompt_type, "tag media")
    ]);
    const meta = create("div", { className: "meta-row" });
    [prompt.platform, prompt.status].filter(Boolean).forEach(v => meta.appendChild(createTag(v)));
    const count = (prompt.prompts || []).length;
    meta.appendChild(createTag(`${count}个提示词`));
    const item = create("article", {
      className: `item ${state.selectedItem?.type === "media" && state.selectedItem.data.prompt_id === prompt.prompt_id ? "selected" : ""}`
    }, [title, meta]);
    item.addEventListener("click", () => {
      state.selectedItem = { type: "media", data: prompt };
      document.querySelectorAll(".item").forEach(i => i.classList.remove("selected"));
      item.classList.add("selected");
      renderDetail();
    });
    list.appendChild(item);
  });
}

function renderDetail() {
  const box = el("detailContent");
  box.innerHTML = "";
  const sel = state.selectedItem;
  if (!sel) {
    box.appendChild(create("p", { className: "empty-hint", textContent: "点击列表项查看详情和 AI 工具。" }));
    return;
  }

  if (sel.type === "topic") {
    const t = sel.data;
    box.appendChild(create("h3", { textContent: t.title }));
    box.appendChild(create("p", { textContent: t.angle || "暂无角度", style: "color:var(--muted);font-size:12px;margin:6px 0;" }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(t.platform || "公众号"),
      createTag(t.content_type || "文章"),
      createTag(`评分 ${t.score || 0}`),
    ]));
    const actions = create("div", { className: "ai-actions" });
    actions.appendChild(create("button", {
      className: "ai-btn", textContent: "✨ AI 生成大纲",
      onClick: () => generateOutlineFromTopic(t)
    }));
    actions.appendChild(create("button", {
      className: "ai-btn", textContent: "🎨 AI 生成封面 Prompt",
      onClick: () => generateCover(t.title, t.platform, null, t.topic_id)
    }));
    actions.appendChild(create("button", {
      className: "ai-btn", textContent: "🎬 AI 生成即梦分镜",
      onClick: () => generateJimeng(t.title, "", 5, null, t.topic_id)
    }));
    box.appendChild(actions);
  }

  if (sel.type === "draft") {
    const d = sel.data;
    box.appendChild(create("h3", { textContent: d.title }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(d.platform, "tag draft"),
      createTag(d.content_type),
      createTag(d.status),
      createTag(`${d.word_count || 0}字`),
    ]));
    if (d.outline && d.outline.length > 0) {
      box.appendChild(create("h4", { textContent: "大纲" }));
      const outlineBox = create("div");
      d.outline.forEach((s, i) => {
        outlineBox.appendChild(create("p", {
          textContent: `${i + 1}. ${s.section || ""}`,
          style: "font-size:12px;margin:4px 0;"
        }));
      });
      box.appendChild(outlineBox);
    }
    if (d.content) {
      box.appendChild(create("h4", { textContent: "正文预览" }));
      box.appendChild(create("div", { className: "content-preview", textContent: d.content.slice(0, 500) + (d.content.length > 500 ? "..." : "") }));
    }
    const actions = create("div", { className: "ai-actions" });
    if (!d.outline || d.outline.length === 0) {
      actions.appendChild(create("button", {
        className: "ai-btn", textContent: "✨ AI 生成大纲",
        onClick: () => generateOutlineFromDraft(d)
      }));
    } else if (!d.content) {
      actions.appendChild(create("button", {
        className: "ai-btn", textContent: "📝 AI 生成正文",
        onClick: () => generateContent(d)
      }));
    }
    actions.appendChild(create("button", {
      className: "ai-btn", textContent: "🎨 封面 Prompt",
      onClick: () => generateCover(d.title, d.platform, d.draft_id, d.topic_id)
    }));
    actions.appendChild(create("button", {
      className: "ai-btn", textContent: "🖼️ 正文配图 Prompt",
      onClick: () => generateInlineImages(d)
    }));
    actions.appendChild(create("button", {
      className: "ai-btn", textContent: "🎬 即梦分镜",
      onClick: () => generateJimeng(d.title, d.content, 5, d.draft_id, d.topic_id)
    }));
    actions.appendChild(create("button", {
      className: "secondary", textContent: "📦 归档到知识库",
      onClick: () => archiveDraft(d)
    }));
    actions.appendChild(create("button", {
      textContent: "✏️ 编辑草稿",
      onClick: () => openDraftEditor(d)
    }));
    actions.appendChild(create("button", {
      className: "danger", textContent: "🗑️ 删除",
      onClick: () => deleteDraft(d.draft_id)
    }));
    box.appendChild(actions);
  }

  if (sel.type === "wiki") {
    const w = sel.data;
    box.appendChild(create("h3", { textContent: w.title }));
    if (w.summary) box.appendChild(create("p", { textContent: w.summary, style: "color:var(--muted);font-size:12px;margin:6px 0;" }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(w.status, "tag wiki"),
      createTag(`${w.word_count || 0}字`),
      ...(w.tags || []).slice(0, 3).map(t => createTag(t))
    ]));
    box.appendChild(create("button", {
      textContent: "✏️ 编辑文章", style: "margin-top:10px;",
      onClick: () => openWikiEditor(w)
    }));
  }

  if (sel.type === "media") {
    const m = sel.data;
    box.appendChild(create("h3", { textContent: m.title }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(m.prompt_type, "tag media"),
      createTag(m.platform || ""),
    ]));
    if (m.style_reference) {
      box.appendChild(create("p", { textContent: `风格：${m.style_reference}`, style: "font-size:12px;color:var(--muted);margin:6px 0;" }));
    }
    if (m.music_suggestion) {
      box.appendChild(create("p", { textContent: `BGM：${m.music_suggestion}`, style: "font-size:12px;color:var(--muted);" }));
    }
    (m.prompts || []).forEach(p => {
      const card = create("div", { className: "shot-card" });
      card.appendChild(create("strong", { textContent: `${p.shot_number || ""}. ${p.shot_name || "提示词"}` }));
      if (p.prompt) {
        card.appendChild(create("div", { className: "prompt-block", textContent: p.prompt }));
      }
      if (p.negative_prompt) {
        card.appendChild(create("p", { textContent: `负面：${p.negative_prompt}`, style: "font-size:11px;color:var(--red);" }));
      }
      card.appendChild(create("button", {
        className: "secondary", textContent: "📋 复制提示词", style: "margin-top:6px;",
        onClick: () => {
          navigator.clipboard.writeText(p.prompt || "");
          showToast("已复制到剪贴板");
        }
      }));
      box.appendChild(card);
    });
    box.appendChild(create("button", {
      className: "danger", textContent: "🗑️ 删除", style: "margin-top:10px;",
      onClick: () => deleteMediaPrompt(m.prompt_id)
    }));
  }

  if (sel.type === "task" || sel.type === "idea") {
    const item = sel.data;
    box.appendChild(create("h3", { textContent: item.title || item.raw_text || "" }));
    if (item.description) box.appendChild(create("p", { textContent: item.description, style: "font-size:12px;margin:6px 0;" }));
    box.appendChild(create("div", { className: "meta-row" }, [
      createTag(sel.type === "task" ? (item.status || "未开始") : (item.type || "灵感")),
      ...(item.tags || []).map(t => createTag(t))
    ]));
  }
}

async function generateOutlineFromTopic(topic) {
  if (!state.llmConfigured) { showToast("请先配置 TinyRouter LLM", "error"); return; }
  showToast("AI 正在生成大纲...");
  await runAction(async () => {
    const result = await api("/api/drafts/generate-outline", {
      method: "POST",
      body: JSON.stringify({
        title: topic.title,
        platform: topic.platform || "公众号",
        angle: topic.angle || "",
        target_audience: topic.target_audience || "",
        topic_id: topic.topic_id,
        auto_save: true,
      })
    });
    showToast("大纲生成成功！");
    await refresh();
    if (result.draft) {
      state.selectedItem = { type: "draft", data: result.draft };
      renderDetail();
      document.querySelector(`.metric[data-main-tab="drafts"]`).click();
    }
  });
}

async function generateOutlineFromDraft(draft) {
  if (!state.llmConfigured) { showToast("请先配置 TinyRouter LLM", "error"); return; }
  showToast("AI 正在生成大纲...");
  await runAction(async () => {
    const result = await api("/api/drafts/generate-outline", {
      method: "POST",
      body: JSON.stringify({
        title: draft.title,
        platform: draft.platform || "公众号",
        auto_save: false,
      })
    });
    await api(`/api/drafts/${draft.draft_id}`, {
      method: "PATCH",
      body: JSON.stringify({ outline: result.outline, status: "大纲" })
    });
    showToast("大纲已更新！");
    await refresh();
  });
}

async function generateContent(draft) {
  if (!state.llmConfigured) { showToast("请先配置 TinyRouter LLM", "error"); return; }
  showToast("AI 正在生成正文（可能需要几十秒）...");
  await runAction(async () => {
    const result = await api("/api/drafts/generate-content", {
      method: "POST",
      body: JSON.stringify({
        title: draft.title,
        outline: draft.outline,
        platform: draft.platform,
        draft_id: draft.draft_id,
      })
    });
    showToast(`正文生成完成！约 ${result.word_count} 字`);
    await refresh();
  });
}

async function generateCover(title, platform, draftId, topicId) {
  if (!state.llmConfigured) { showToast("请先配置 TinyRouter LLM", "error"); return; }
  showToast("AI 正在生成封面提示词...");
  await runAction(async () => {
    const result = await api("/api/media/generate-cover", {
      method: "POST",
      body: JSON.stringify({ title, platform, draft_id: draftId, topic_id: topicId, auto_save: true })
    });
    showToast("封面提示词已生成！");
    await refresh();
    selectTab("media");
  });
}

async function generateJimeng(title, content, count, draftId, topicId) {
  if (!state.llmConfigured) { showToast("请先配置 TinyRouter LLM", "error"); return; }
  showToast("AI 正在生成即梦分镜...");
  await runAction(async () => {
    const result = await api("/api/media/generate-jimeng", {
      method: "POST",
      body: JSON.stringify({ title, content, shot_count: count, draft_id: draftId, topic_id: topicId, auto_save: true })
    });
    showToast("即梦分镜已生成！");
    await refresh();
    selectTab("media");
  });
}

async function generateInlineImages(draft) {
  if (!state.llmConfigured) { showToast("请先配置 TinyRouter LLM", "error"); return; }
  showToast("AI 正在生成正文配图提示词...");
  await runAction(async () => {
    const result = await api("/api/media/generate-inline-images", {
      method: "POST",
      body: JSON.stringify({
        title: draft.title, outline: draft.outline, platform: draft.platform,
        draft_id: draft.draft_id, auto_save: true
      })
    });
    showToast("正文配图提示词已生成！");
    await refresh();
    selectTab("media");
  });
}

async function archiveDraft(draft) {
  await runAction(async () => {
    await api(`/api/drafts/${draft.draft_id}/archive-wiki`, { method: "POST", body: JSON.stringify({}) });
    showToast("已归档到知识库");
    await refresh();
  });
}

async function deleteDraft(id) {
  if (!confirm("确定删除此草稿？")) return;
  await runAction(async () => {
    await api(`/api/drafts/${id}`, { method: "DELETE" });
    showToast("已删除");
    state.selectedItem = null;
    await refresh();
  });
}

async function deleteMediaPrompt(id) {
  if (!confirm("确定删除此提示词？")) return;
  await runAction(async () => {
    await api(`/api/media-prompts/${id}`, { method: "DELETE" });
    showToast("已删除");
    state.selectedItem = null;
    await refresh();
  });
}

function openModal(title, bodyHtml) {
  el("modalTitle").textContent = title;
  el("modalBody").innerHTML = "";
  if (typeof bodyHtml === "string") el("modalBody").innerHTML = bodyHtml;
  else el("modalBody").appendChild(bodyHtml);
  el("modalOverlay").classList.remove("hidden");
}

function closeModal() { el("modalOverlay").classList.add("hidden"); }

function openDraftEditor(draft) {
  const form = create("form");
  form.innerHTML = `
    <label><span>标题</span><input name="title" value="${(draft.title || "").replace(/"/g, "&quot;")}" required></label>
    <label style="margin-top:10px"><span>平台</span><select name="platform">
      <option${draft.platform === "公众号" ? " selected" : ""}>公众号</option>
      <option${draft.platform === "小红书" ? " selected" : ""}>小红书</option>
      <option${draft.platform === "视频号脚本" ? " selected" : ""}>视频号脚本</option>
      <option${draft.platform === "通用文章" ? " selected" : ""}>通用文章</option>
    </select></label>
    <label style="margin-top:10px"><span>正文 (Markdown)</span><textarea name="content" rows="12">${draft.content || ""}</textarea></label>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px;">
      <button type="button" id="cancelDraft" class="secondary">取消</button>
      <button type="submit">保存</button>
    </div>
  `;
  openModal("编辑草稿", form);
  form.querySelector("#cancelDraft").addEventListener("click", closeModal);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    await runAction(async () => {
      await api(`/api/drafts/${draft.draft_id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: fd.get("title"),
          platform: fd.get("platform"),
          content: fd.get("content"),
          word_count: (fd.get("content") || "").length,
        })
      });
      closeModal();
      showToast("草稿已保存");
      await refresh();
    });
  });
}

function openWikiEditor(page) {
  const form = create("form");
  const isNew = !page;
  form.innerHTML = `
    <label><span>标题</span><input name="title" value="${(page?.title || "").replace(/"/g, "&quot;")}" required></label>
    <label style="margin-top:10px"><span>摘要</span><input name="summary" value="${(page?.summary || "").replace(/"/g, "&quot;")}"></label>
    <label style="margin-top:10px"><span>标签 (逗号分隔)</span><input name="tags_str" value="${(page?.tags || []).join(", ")}"></label>
    <label style="margin-top:10px"><span>内容 (Markdown)</span><textarea name="content_md" rows="12">${page?.content_md || ""}</textarea></label>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px;">
      <button type="button" id="cancelWiki" class="secondary">取消</button>
      <button type="submit">${isNew ? "创建" : "保存"}</button>
    </div>
  `;
  openModal(isNew ? "新建知识库文章" : "编辑知识库文章", form);
  form.querySelector("#cancelWiki").addEventListener("click", closeModal);
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
        await api("/api/wiki", { method: "POST", body: JSON.stringify(payload) });
      } else {
        await api(`/api/wiki/${page.page_id}`, { method: "PATCH", body: JSON.stringify(payload) });
      }
      closeModal();
      showToast(isNew ? "文章已创建" : "文章已保存");
      await refresh();
    });
  });
}

function renderStatus() {
  const list = el("statusList");
  list.innerHTML = "";
  Object.entries(state.status).forEach(([key, value]) => {
    if (["safe_mode", "public_access"].includes(key)) return;
    const row = create("div", { className: "status-row" }, [
      create("strong", { textContent: labels[key] || key }),
      create("span", { textContent: text(value) })
    ]);
    list.appendChild(row);
  });
  el("workbenchState").textContent = state.status.workbench || "unknown";
  el("workbenchState").className = state.status.workbench === "online" ? "counter good" : "counter warn";
  el("safeModeBadge").className = state.status.safe_mode ? "status-pill good" : "status-pill warn";
  el("accessBadge").className = state.status.public_access ? "status-pill warn" : "status-pill good";
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

function renderCounts() {
  el("taskCount").textContent = state.tasks.length;
  el("ideaCount").textContent = state.ideas.length;
  el("topicCount").textContent = state.topics.length;
  el("draftCount").textContent = state.drafts.length;
  el("wikiCount").textContent = state.wiki.length;
  el("mediaCount").textContent = state.media.length;
  el("urgentCount").textContent = `${state.tasks.filter(t => ["P0", "P1"].includes(t.priority)).length} 紧急`;
}

function renderAll() {
  renderCounts();
  renderTasks();
  renderIdeas();
  renderTopics();
  renderDrafts();
  renderWiki();
  renderMedia();
  renderStatus();
  renderLogs();
  renderDetail();
}

async function refresh() {
  const [tasks, ideas, topics, drafts, wiki, media, status, logs, llmStatus] = await Promise.all([
    api(API.tasks), api(API.ideas), api(API.topics), api(API.drafts),
    api(API.wiki), api(API.media), api(API.status), api(API.logs),
    api(API.llmStatus).catch(() => ({ configured: false }))
  ]);
  state = { ...state, tasks, ideas, topics, drafts, wiki, media, status, logs, llmConfigured: llmStatus.configured };
  renderAll();
}

function bindEvents() {
  document.querySelectorAll(".metric.clickable").forEach(m => {
    m.addEventListener("click", () => selectTab(m.dataset.mainTab));
  });

  el("taskForm").addEventListener("submit", e => {
    e.preventDefault();
    runAction(async () => {
      await api(API.tasks, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
      e.target.reset();
      showToast("任务已新增");
      await refresh();
    });
  });

  el("ideaForm").addEventListener("submit", e => {
    e.preventDefault();
    runAction(async () => {
      await api(API.ideas, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
      e.target.reset();
      showToast("灵感已新增");
      await refresh();
    });
  });

  el("topicForm").addEventListener("submit", e => {
    e.preventDefault();
    runAction(async () => {
      await api(API.topics, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
      e.target.reset();
      showToast("选题已新增");
      await refresh();
    });
  });

  el("newDraftBtn").addEventListener("click", () => {
    const platform = el("draftPlatform").value;
    openDraftEditor({ title: "", platform, content: "", draft_id: null });
    const modalForm = el("modalBody").querySelector("form");
    modalForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(modalForm);
      await runAction(async () => {
        await api(API.drafts, {
          method: "POST",
          body: JSON.stringify({
            title: fd.get("title"),
            platform: fd.get("platform"),
            content: fd.get("content"),
            content_type: "文章",
            status: "大纲",
            source: "manual",
          })
        });
        closeModal();
        showToast("草稿已创建");
        await refresh();
      });
    }, { once: true });
  });

  el("newWikiBtn").addEventListener("click", () => openWikiEditor(null));

  let wikiSearchTimer;
  el("wikiSearch").addEventListener("input", (e) => {
    clearTimeout(wikiSearchTimer);
    wikiSearchTimer = setTimeout(async () => {
      const q = e.target.value.trim();
      if (q) {
        state.wiki = await api(`/api/wiki/search?q=${encodeURIComponent(q)}`);
      } else {
        state.wiki = await api(API.wiki);
      }
      renderWiki();
    }, 300);
  });

  el("modalClose").addEventListener("click", closeModal);
  el("modalOverlay").addEventListener("click", e => {
    if (e.target === el("modalOverlay")) closeModal();
  });
}

async function init() {
  bindEvents();
  selectTab("tasks");
  try {
    await refresh();
  } catch (error) {
    el("errorPanel").textContent = error.message;
    el("errorPanel").classList.remove("hidden");
  }
}

init();
