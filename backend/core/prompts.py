"""
Prompt 加载器和版本管理
"""
import os
import json
from datetime import datetime
from pathlib import Path

# Prompt 文件目录
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Prompt 缓存
_prompt_cache = {}


def load_prompt(prompt_name, channel=None, content_type=None, version=None):
    """
    加载 prompt 模板文件
    
    Args:
        prompt_name: prompt 名称（如 'draft-wechat-article'）
        channel: 渠道（如 'wechat', 'xiaohongshu', 'video'）
        content_type: 内容类型（如 'article', 'short_post', 'script'）
        version: 版本号（如 'v1', 默认最新版本）
    
    Returns:
        dict: {
            'name': prompt_name,
            'content': prompt_content,
            'file_path': file_path,
            'version': version
        }
    """
    # 构建文件名
    if channel and content_type:
        # 尝试加载特定渠道和类型的 prompt
        filename = f"{prompt_name}-{channel}-{content_type}.md"
        file_path = PROMPTS_DIR / filename
        if not file_path.exists():
            # fallback 到通用 prompt
            filename = f"{prompt_name}.md"
            file_path = PROMPTS_DIR / filename
    else:
        filename = f"{prompt_name}.md"
        file_path = PROMPTS_DIR / filename

    # 检查文件是否存在
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {file_path}")

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        'name': prompt_name,
        'content': content,
        'file_path': str(file_path),
        'version': version or 'latest'
    }


def render_prompt(prompt_content, variables):
    """
    渲染 prompt（替换变量）
    
    Args:
        prompt_content: prompt 内容（包含 {variable} 占位符）
        variables: dict，变量名 -> 值
        
    Returns:
        str: 渲染后的 prompt
    """
    rendered = prompt_content
    for key, value in variables.items():
        placeholder = '{' + key + '}'
        if placeholder in rendered:
            rendered = rendered.replace(placeholder, str(value))
    return rendered


def list_available_prompts():
    """
    列出所有可用的 prompt 模板
    
    Returns:
        list: prompt 文件名列表
    """
    if not PROMPTS_DIR.exists():
        return []

    prompts = []
    for file_path in PROMPTS_DIR.glob('*.md'):
        prompts.append(file_path.stem)

    return sorted(prompts)


def get_prompt_variables(prompt_content):
    """
    提取 prompt 中的变量名
    
    Args:
        prompt_content: prompt 内容
        
    Returns:
        list: 变量名列表（如 ['topic_title', 'topic_summary']）
    """
    import re
    variables = re.findall(r'\{(\w+)\}', prompt_content)
    return list(set(variables))


def save_prompt_version(prompt_name, content, version, description='', db_conn=None):
    """
    保存 prompt 版本到数据库
    
    Args:
        prompt_name: prompt 名称
        content: prompt 内容
        version: 版本号
        description: 版本描述
        db_conn: 数据库连接（可选，如果不提供则只保存到文件）
        
    Returns:
        bool: 是否成功
    """
    # 1. 保存到文件
    filename = f"{prompt_name}@{{version}}.md"
    file_path = PROMPTS_DIR / filename

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 2. 保存到数据库（如果提供了数据库连接）
    if db_conn:
        prompt_id = f"{prompt_name}@{version}"
        now = datetime.now().isoformat()

        db_conn.execute("""
            INSERT OR REPLACE INTO prompt_versions
            (prompt_id, name, version, file_path, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (prompt_id, prompt_name, version, str(file_path), description, now, now))
        db_conn.commit()

    return True


def load_prompt_version(prompt_name, version):
    """
    加载指定版本的 prompt
    
    Args:
        prompt_name: prompt 名称
        version: 版本号
        
    Returns:
        dict: prompt 信息，如果版本不存在则返回 None
    """
    filename = f"{prompt_name}@{version}.md"
    file_path = PROMPTS_DIR / filename

    if not file_path.exists():
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        'name': prompt_name,
        'content': content,
        'file_path': str(file_path),
        'version': version
    }


def get_template_fallback(topic, channel, content_type):
    """
    获取模板降级内容（当 LLM 未配置时使用）
    
    Args:
        topic: dict，包含 topic_id, title, summary 等
        channel: 渠道
        content_type: 内容类型
        
    Returns:
        str: 模板生成的内容
    """
    topic_title = topic.get('title', '未命名选题')
    topic_summary = topic.get('summary', '')

    # 根据渠道和内容类型生成不同的模板
    if channel == 'wechat' and content_type == 'article':
        return _generate_wechat_article_template(topic_title, topic_summary)
    elif channel == 'xiaohongshu' and content_type == 'short_post':
        return _generate_xiaohongshu_template(topic_title, topic_summary)
    elif channel == 'video' and content_type == 'script':
        return _generate_video_script_template(topic_title, topic_summary)
    else:
        # 通用模板
        return _generate_generic_template(topic_title, topic_summary)


def _generate_wechat_article_template(title, summary):
    """生成公众号文章模板"""
    return f"""# {title}

## 核心观点

{summary if summary else '这里是核心观点的扩展说明...'}

## 正文草稿

这是基于当前选题生成的模板草稿。请在人工审核阶段补充案例、细节和表达风格。

### 第一部分：引入

（在这里写引人入胜的开头，可以是一个故事、一个问题或一组数据）

### 第二部分：主体

（在这里展开论述，分 3-5 个要点，每个要点配具体案例）

### 第三部分：总结

（在这里总结全文，并给出行动建议）

## 待补充

- [ ] 具体案例
- [ ] 个人观点
- [ ] 数据支撑
- [ ] 发布渠道适配

---

*这是模板生成的草稿，请在人工审核阶段完善内容。*
"""


def _generate_xiaohongshu_template(title, summary):
    """生成小红书短文模板"""
    return f"""✨ {title} ✨

你有没有想过...

（这里写吸引人的开头，3-5 行）

---

## 💡 核心观点

{summary if summary else '这里写核心观点...'}

## 📝 具体方法

1️⃣ 第一步：...
2️⃣ 第二步：...
3️⃣ 第三步：...

## ✅ 效果

（这里写使用后的效果或改变）

---

#干货分享 #{title[:10]} #实用技巧 #经验分享

---

*这是模板生成的草稿，请在人工审核阶段完善内容。*
"""


def _generate_video_script_template(title, summary):
    """生成视频口播稿模板"""
    return f"""# {title}

## 开场（0:00-0:10）

**画面**：[对着镜头微笑]

**口播**：
"你有没有想过...（抛出问题或痛点）"

## 要点一（0:10-1:30）

**画面**：[展示关键画面或文字]

**口播**：
{summary if summary else '这里写第一个要点...'}

## 要点二（1:30-3:00）

**画面**：[展示案例或演示]

**口播**：
（这里写第二个要点...）

## 结尾（3:00-3:10）

**画面**：[对着镜头微笑]

**口播**：
"以上就是今天的分享，如果对你有帮助，记得点赞关注哦！"

**引导**：点赞、关注、评论区见

---

*这是模板生成的草稿，请在人工审核阶段完善内容。*
"""


def _generate_generic_template(title, summary):
    """生成通用模板"""
    return f"""# {title}

## 核心观点

{summary if summary else '这里是核心观点的扩展说明...'}

## 正文草稿

这是基于当前选题生成的模板草稿。请在人工审核阶段补充案例、细节和表达风格。

## 待补充

- [ ] 具体案例
- [ ] 个人观点
- [ ] 发布渠道适配

---

*这是模板生成的草稿，请在人工审核阶段完善内容。*
"""
