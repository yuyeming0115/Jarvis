const dataFiles = {
  tasks: "/api/tasks",
  ideas: "/api/ideas",
  topics: "/api/topics",
  status: "/api/system-status",
  logs: "/api/logs"
};

let state = {
  tasks: [],
  ideas: [],
  topics: [],
  status: {},
  logs: []
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

async function loadJson(name, path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${name} 读取失败：${response.status}`);
  }
  return response.json();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `请求失败：${response.status}`);
  }
  return payload;
}

function el(id) {
  return document.getElementById(id);
}

function text(value, fallback = "未设置") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "是" : "否";
  return String(value);
}

function createTag(value, className = "tag") {
  const span = document.createElement("span");
  span.className = className;
  span.textContent = value;
  return span;
}

function showToast(message, type = "success") {
  const panel = type === "success" ? el("toastPanel") : el("errorPanel");
  panel.textContent = message;
  panel.classList.remove("hidden");
  if (type === "success") {
    window.setTimeout(() => panel.classList.add("hidden"), 2400);
  }
}

function hideErrors() {
  el("errorPanel").classList.add("hidden");
}

function renderEmpty(target, message) {
  target.innerHTML = "";
  const empty = document.createElement("div");
  empty.className = "empty";
  empty.textContent = message;
  target.appendChild(empty);
}

function renderTasks(tasks) {
  const list = el("tasksList");
  list.innerHTML = "";

  if (!tasks.length) {
    renderEmpty(list, "暂无任务");
    return;
  }

  tasks.forEach((task) => {
    const item = document.createElement("article");
    item.className = "item";

    const title = document.createElement("div");
    title.className = "item-title";
    const heading = document.createElement("strong");
    heading.textContent = task.title;
    title.appendChild(heading);
    title.appendChild(createTag(task.priority || "P?", `priority ${(task.priority || "").toLowerCase()}`));

    const desc = document.createElement("p");
    desc.textContent = task.description || "暂无描述";

    const meta = document.createElement("div");
    meta.className = "meta-row";
    [task.status, task.project, task.due_at, task.sync_status].filter(Boolean).forEach((value) => {
      meta.appendChild(createTag(value));
    });

    const controls = document.createElement("form");
    controls.className = "inline-controls";
    controls.dataset.taskId = task.task_id;
    controls.innerHTML = `
      <select name="status" aria-label="任务状态">
        ${["未开始", "进行中", "已完成", "已取消"].map((value) => `<option${value === task.status ? " selected" : ""}>${value}</option>`).join("")}
      </select>
      <select name="priority" aria-label="优先级">
        ${["P0", "P1", "P2", "P3"].map((value) => `<option${value === task.priority ? " selected" : ""}>${value}</option>`).join("")}
      </select>
      <button type="submit">保存</button>
      <button type="button" data-complete="${task.task_id}">完成</button>
    `;

    item.append(title, desc, meta, controls);
    list.appendChild(item);
  });
}

function renderIdeas(ideas) {
  const list = el("ideasList");
  list.innerHTML = "";

  if (!ideas.length) {
    renderEmpty(list, "暂无灵感");
    return;
  }

  ideas.forEach((idea) => {
    const item = document.createElement("article");
    item.className = "item";
    const title = document.createElement("div");
    title.className = "item-title";
    const heading = document.createElement("strong");
    heading.textContent = idea.type || "灵感";
    title.appendChild(heading);
    title.appendChild(createTag(idea.status || "未处理"));

    const raw = document.createElement("p");
    raw.textContent = idea.raw_text || "暂无内容";
    const summary = document.createElement("p");
    summary.textContent = idea.ai_summary || "暂无摘要";

    const meta = document.createElement("div");
    meta.className = "meta-row";
    (idea.tags || []).forEach((tag) => meta.appendChild(createTag(tag)));

    item.append(title, raw, summary, meta);
    list.appendChild(item);
  });
}

function renderTopics(topics) {
  const list = el("topicsList");
  list.innerHTML = "";

  if (!topics.length) {
    renderEmpty(list, "暂无选题");
    return;
  }

  topics.forEach((topic) => {
    const item = document.createElement("article");
    item.className = "item";
    const title = document.createElement("div");
    title.className = "item-title";
    const heading = document.createElement("strong");
    heading.textContent = topic.title;
    title.appendChild(heading);
    title.appendChild(createTag(`${topic.score || 0} 分`));

    const angle = document.createElement("p");
    angle.textContent = topic.angle || "暂无角度";

    const meta = document.createElement("div");
    meta.className = "meta-row";
    [topic.platform, topic.content_type, topic.status, topic.draft_status].filter(Boolean).forEach((value) => {
      meta.appendChild(createTag(value));
    });

    item.append(title, angle, meta);
    list.appendChild(item);
  });
}

function renderStatus(status) {
  const list = el("statusList");
  list.innerHTML = "";
  Object.entries(status).forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "status-row";
    const name = document.createElement("strong");
    name.textContent = labels[key] || key;
    const val = document.createElement("span");
    val.textContent = text(value);
    row.append(name, val);
    list.appendChild(row);
  });

  el("workbenchState").textContent = status.workbench || "unknown";
  el("workbenchState").className = status.workbench === "online" ? "counter good" : "counter warn";
  el("safeModeBadge").className = status.safe_mode ? "status-pill good" : "status-pill warn";
  el("accessBadge").className = status.public_access ? "status-pill warn" : "status-pill good";
}

function renderLogs(logs) {
  const list = el("logsList");
  list.innerHTML = "";

  if (!logs.length) {
    renderEmpty(list, "暂无日志");
    return;
  }

  logs.slice().reverse().forEach((log) => {
    const row = document.createElement("div");
    row.className = "log-row";
    [log.created_at, log.event_type, log.message, log.status].forEach((value) => {
      const span = document.createElement("span");
      span.textContent = text(value);
      row.appendChild(span);
    });
    list.appendChild(row);
  });
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      const active = button.dataset.tab;
      el("ideasList").classList.toggle("hidden", active !== "ideas");
      el("topicsList").classList.toggle("hidden", active !== "topics");
    });
  });
}

function bindForms() {
  el("taskForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitForm(event.currentTarget, "/api/tasks", "任务已新增");
  });

  el("ideaForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitForm(event.currentTarget, "/api/ideas", "灵感已新增");
  });

  el("topicForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitForm(event.currentTarget, "/api/topics", "选题已新增");
  });

  el("tasksList").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const taskId = form.dataset.taskId;
    const payload = Object.fromEntries(new FormData(form).entries());
    await runAction(async () => {
      await api(`/api/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      showToast("任务已更新");
      await refresh();
    });
  });

  el("tasksList").addEventListener("click", async (event) => {
    const taskId = event.target.dataset.complete;
    if (!taskId) return;
    await runAction(async () => {
      await api(`/api/tasks/${taskId}/complete`, {
        method: "POST",
        body: JSON.stringify({})
      });
      showToast("任务已完成");
      await refresh();
    });
  });
}

async function submitForm(form, endpoint, message) {
  const payload = Object.fromEntries(new FormData(form).entries());
  await runAction(async () => {
    await api(endpoint, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    form.reset();
    showToast(message);
    await refresh();
  });
}

async function runAction(action) {
  hideErrors();
  try {
    await action();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderAll() {
  const { tasks, ideas, topics, status, logs } = state;

  el("taskCount").textContent = tasks.length;
  el("ideaCount").textContent = ideas.length;
  el("topicCount").textContent = topics.length;
  el("dataSource").textContent = status.database || "json_only";
  el("urgentCount").textContent = `${tasks.filter((task) => ["P0", "P1"].includes(task.priority)).length} 紧急`;
  el("logCount").textContent = `${logs.length} 条`;

  renderTasks(tasks);
  renderIdeas(ideas);
  renderTopics(topics);
  renderStatus(status);
  renderLogs(logs);
}

async function refresh() {
  const [tasks, ideas, topics, status, logs] = await Promise.all(
    Object.entries(dataFiles).map(([name, path]) => loadJson(name, path))
  );
  state = { tasks, ideas, topics, status, logs };
  renderAll();
}

async function init() {
  bindTabs();
  bindForms();
  try {
    await refresh();
  } catch (error) {
    const panel = el("errorPanel");
    panel.textContent = error.message;
    panel.classList.remove("hidden");
  }
}

init();
