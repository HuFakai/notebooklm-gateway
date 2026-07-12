import httpx
import json
import sys
import time
import os

BASE_URL = "http://localhost:18388"
API_KEY = "nmlg_example_key_12345"

# 定义公共的 HTTP 头部
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 全局上下文缓存，用于单步调试
ctx = {
    "notebook_id": None,
    "source_id": None,
    "note_id": None,
    "task_id": None
}

def get_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

def print_ctx():
    print("\n" + "=" * 60)
    print("🛠️  当前交互调试上下文缓存:")
    print(f"   - 笔记本 ID (notebook_id) : {ctx['notebook_id'] or '未绑定'}")
    print(f"   - 来源 ID   (source_id)   : {ctx['source_id'] or '未绑定'}")
    print(f"   - 笔记 ID   (note_id)     : {ctx['note_id'] or '未绑定'}")
    print(f"   - 任务 ID   (task_id)     : {ctx['task_id'] or '未绑定'}")
    print("=" * 60)

def ensure_notebook_id():
    """保证当前有可用的笔记本 ID，若没有则引导拉取列表并绑定第一个"""
    if ctx["notebook_id"]:
        return ctx["notebook_id"]
    
    print("\nℹ️ 正在尝试拉取可用笔记本列表...")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks", headers=get_headers(), timeout=10.0)
        if resp.status_code == 200:
            notebooks = resp.json().get("notebooks", [])
            if notebooks:
                ctx["notebook_id"] = notebooks[0].get("id")
                print(f"🎯 自动绑定列表首个笔记本 ID: {ctx['notebook_id']} ({notebooks[0].get('title')})")
                return ctx["notebook_id"]
            else:
                print("⚠️ 该账号下没有任何笔记本！")
        else:
            print(f"⚠️ 拉取笔记本失败！状态码: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ 网络异常: {e}")
    
    user_id = input("👉 请手动输入要测试的笔记本 ID (或直接回车退出): ").strip()
    if user_id:
        ctx["notebook_id"] = user_id
        return user_id
    return None

def ensure_source_id():
    """保证当前有可用的文档来源 ID"""
    if ctx["source_id"]:
        return ctx["source_id"]
    nb_id = ensure_notebook_id()
    if not nb_id:
        return None
    print("\nℹ️ 正在拉取该笔记本下的所有来源...")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks/{nb_id}/sources", headers=get_headers(), timeout=10.0)
        if resp.status_code == 200:
            sources = resp.json().get("sources", [])
            if sources:
                ctx["source_id"] = sources[0].get("id")
                print(f"🎯 自动绑定首个文档来源 ID: {ctx['source_id']} ({sources[0].get('title')})")
                return ctx["source_id"]
            else:
                print("⚠️ 该笔记本下没有任何文档来源！")
        else:
            print(f"⚠️ 拉取来源失败！状态码: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ 网络异常: {e}")
    
    user_id = input("👉 请手动输入要测试的来源 ID (或直接回车退出): ").strip()
    if user_id:
        ctx["source_id"] = user_id
        return user_id
    return None

def ensure_note_id():
    """保证当前有可用的笔记 ID"""
    if ctx["note_id"]:
        return ctx["note_id"]
    nb_id = ensure_notebook_id()
    if not nb_id:
        return None
    print("\nℹ️ 正在拉取该笔记本下的所有笔记...")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks/{nb_id}/notes", headers=get_headers(), timeout=10.0)
        if resp.status_code == 200:
            notes = resp.json().get("notes", [])
            if notes:
                ctx["note_id"] = notes[0].get("id")
                print(f"🎯 自动绑定首个笔记 ID: {ctx['note_id']} ({notes[0].get('title')})")
                return ctx["note_id"]
            else:
                print("⚠️ 该笔记本下没有任何笔记！")
        else:
            print(f"⚠️ 拉取笔记失败！状态码: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ 网络异常: {e}")
    
    user_id = input("👉 请手动输入要测试的笔记 ID (或直接回车退出): ").strip()
    if user_id:
        ctx["note_id"] = user_id
        return user_id
    return None

# ----------------------------------------------------
# API 路由独立方法
# ----------------------------------------------------
def cmd_list_notebooks():
    url = f"{BASE_URL}/v1/notebooks"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        notebooks = resp.json().get("notebooks", [])
        if notebooks:
            ctx["notebook_id"] = notebooks[0].get("id") # 自动缓存
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_create_notebook():
    url = f"{BASE_URL}/v1/notebooks"
    title = input("📝 请输入新建笔记本名称 (留空默认随机): ").strip()
    if not title:
        title = f"Test_Notebook_{int(time.time())}"
    print(f"\n🚀 请求: POST {url}")
    try:
        resp = httpx.post(url, headers=get_headers(), json={"title": title}, timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        if resp.status_code in (200, 201):
            ctx["notebook_id"] = resp.json().get("id")
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_rename_notebook():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}"
    title = input("📝 请输入修改后的新名字: ").strip()
    if not title: return
    print(f"\n🚀 请求: PATCH {url}")
    try:
        resp = httpx.patch(url, headers=get_headers(), json={"title": title}, timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_notebook_detail():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_add_text_source():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/text"
    print(f"\n🚀 请求: POST {url}")
    payload = {
        "title": "深空探测技术简史",
        "text": "深空探测是指航天器在距离地球200万公里以上的空间进行的探测活动。目前，中国嫦娥系列探测器在月球背面的成功着陆，为人类探索太空奠定了重要基石。"
    }
    try:
        resp = httpx.post(url, headers=get_headers(), json=payload, timeout=25.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        if resp.status_code in (200, 201):
            ctx["source_id"] = resp.json().get("id") or resp.json().get("source", {}).get("id")
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_add_file_source():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/file"
    print(f"\n🚀 请求: POST {url}")
    
    test_filename = "gateway_test_upload.txt"
    with open(test_filename, "w", encoding="utf-8") as f:
        f.write("引力波是时空弯曲中的涟漪，爱因斯坦在广义相对论中预言了它的存在。这一发现在天体物理学上具有划时代意义。")
    
    file_headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        with open(test_filename, "rb") as f:
            files = {"file": (test_filename, f, "text/plain")}
            resp = httpx.post(url, headers=file_headers, files=files, timeout=40.0)
            print(f"状态码: {resp.status_code}")
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            if resp.status_code in (200, 201):
                ctx["source_id"] = resp.json().get("id") or resp.json().get("source", {}).get("id")
    except Exception as e:
        print(f"❌ 异常: {e}")
    finally:
        if os.path.exists(test_filename):
            os.remove(test_filename)

def cmd_add_url_source():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/url"
    target_url = input("🔗 请输入要挂载解析的网页 URL: ").strip()
    if not target_url: return
    print(f"\n🚀 请求: POST {url}")
    try:
        resp = httpx.post(url, headers=get_headers(), json={"url": target_url}, timeout=30.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        if resp.status_code in (200, 201):
            ctx["source_id"] = resp.json().get("id") or resp.json().get("source", {}).get("id")
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_add_batch_urls():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/batch"
    urls_str = input("🔗 请输入要批量挂载的 URL 列表 (逗号分隔): ").strip()
    if not urls_str: return
    urls = [u.strip() for u in urls_str.split(",") if u.strip()]
    print(f"\n🚀 请求: POST {url}")
    try:
        resp = httpx.post(url, headers=get_headers(), json={"urls": urls}, timeout=30.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_list_sources():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        sources = resp.json().get("sources", [])
        if sources:
            ctx["source_id"] = sources[0].get("id")
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_source_detail():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    src_id = ensure_source_id()
    if not src_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/{src_id}"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_get_source_text():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    src_id = ensure_source_id()
    if not src_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/{src_id}/text"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_wait_sources():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/wait"
    print(f"\n🚀 请求: POST {url}")
    try:
        resp = httpx.post(url, headers=get_headers(), json={"timeout": 60.0}, timeout=60.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_configure_chat():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/chat/configure"
    print(f"\n🚀 请求: POST {url} (自定义 Persona)")
    payload = {
        "chat_mode": None,
        "goal": "你是一个深空探索的领航员，请用富有科幻感和冷酷理性的语气回答问题。",
        "response_length": "short"
    }
    try:
        resp = httpx.post(url, headers=get_headers(), json=payload, timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_suggested_prompts():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/suggested-prompts"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_chat_stream():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/chat"
    question = input("💬 请输入提问内容 (留空默认随机): ").strip()
    if not question:
        question = "请用一句话告诉我，引力波是如何被爱因斯坦预言的？"
    payload = {"question": question}
    print(f"\n🚀 请求: POST {url}")
    print("-" * 60)
    try:
        with httpx.stream("POST", url, json=payload, headers=get_headers(), timeout=60.0) as r:
            if r.status_code == 200:
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            chunk = data_json.get("text", "") or data_json.get("content", "")
                            if chunk:
                                sys.stdout.write(chunk)
                                sys.stdout.flush()
                        except Exception:
                            pass
                print()
            else:
                r.read()
                print(f"❌ 对话失败！状态码: {r.status_code}, 内容: {r.text}")
    except Exception as e:
        print(f"\n❌ 流式交互异常: {e}")
    print("-" * 60)

def cmd_create_note():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/notes"
    print(f"\n🚀 请求: POST {url}")
    payload = {
        "title": "量子力学新脑洞",
        "content": "波粒二象性证明了在微观尺度下时空并非连续的。"
    }
    try:
        resp = httpx.post(url, headers=get_headers(), json=payload, timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        if resp.status_code in (200, 201):
            ctx["note_id"] = resp.json().get("id") or resp.json().get("note", {}).get("id")
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_list_notes():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/notes"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        notes = resp.json().get("notes", [])
        if notes:
            ctx["note_id"] = notes[0].get("id")
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_update_note():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    nt_id = ensure_note_id()
    if not nt_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/notes/{nt_id}"
    print(f"\n🚀 请求: PUT {url}")
    payload = {
        "title": "量子力学新脑洞(已修改)",
        "content": "修改后的内容：宇宙的微观底层可能完全是由信息编码构成的。"
    }
    try:
        resp = httpx.put(url, headers=get_headers(), json=payload, timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_get_share():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/share"
    print(f"\n🚀 请求: GET {url}")
    try:
        resp = httpx.get(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_generate_artifact():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/artifacts"
    print(f"\n🚀 请求: POST {url}")
    payload = {
        "type": "quiz",
        "quantity": "standard",
        "difficulty": "medium",
        "instructions": "出一份关于深空探测历史的小测验卷。"
    }
    try:
        resp = httpx.post(url, headers=get_headers(), json=payload, timeout=20.0)
        print(f"状态码: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        if resp.status_code in (200, 202):
            ctx["task_id"] = resp.json().get("task_id")
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_delete_note():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    nt_id = ensure_note_id()
    if not nt_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/notes/{nt_id}"
    print(f"\n🚀 请求: DELETE {url}")
    try:
        resp = httpx.delete(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        if resp.status_code in (200, 204):
            print("✅ 删除成功！")
            ctx["note_id"] = None
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_delete_source():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    src_id = ensure_source_id()
    if not src_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}/sources/{src_id}"
    print(f"\n🚀 请求: DELETE {url}")
    try:
        resp = httpx.delete(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        if resp.status_code in (200, 204):
            print("✅ 删除成功！")
            ctx["source_id"] = None
    except Exception as e:
        print(f"❌ 异常: {e}")

def cmd_delete_notebook():
    nb_id = ensure_notebook_id()
    if not nb_id: return
    url = f"{BASE_URL}/v1/notebooks/{nb_id}"
    print(f"\n🚀 请求: DELETE {url}")
    try:
        resp = httpx.delete(url, headers=get_headers(), timeout=20.0)
        print(f"状态码: {resp.status_code}")
        if resp.status_code in (200, 204):
            print("✅ 删除成功！")
            ctx["notebook_id"] = None
    except Exception as e:
        print(f"❌ 异常: {e}")

# ----------------------------------------------------
# 0. 一键全流程闭环自动化测试
# ----------------------------------------------------
def run_pipeline():
    print("\n🌟 开始执行全流程闭环自动化流水线测试 🌟")
    
    # 1. 创建临时笔记本
    print("\n[Step 1] 创建临时笔记本...")
    create_payload = {"title": f"AutoPipeline_{int(time.time())}"}
    try:
        resp = httpx.post(f"{BASE_URL}/v1/notebooks", headers=get_headers(), json=create_payload, timeout=20.0)
        if resp.status_code not in (200, 201):
            print(f"❌ 管道阻断：创建笔记本失败: {resp.text}")
            return
        nb_id = resp.json().get("id")
        print(f"✅ 创建成功 ID: {nb_id}")
    except Exception as e:
        print(f"❌ 网络错误: {e}")
        return

    try:
        # 2. 上传文本来源
        print("\n[Step 2] 添加自定义文本来源...")
        source_payload = {"title": "自闭环测试文档", "text": "光速是宇宙的限制，没有任何静止质量的物体能够超过光速。这一规律限制了星际航行。"}
        resp = httpx.post(f"{BASE_URL}/v1/notebooks/{nb_id}/sources/text", headers=get_headers(), json=source_payload, timeout=25.0)
        print(f"   状态码: {resp.status_code}")

        # 3. 配置对话 Persona
        print("\n[Step 3] 配置对话 System Prompt Persona...")
        config_payload = {"chat_mode": None, "goal": "你是一个严谨的物理学家，回答简短且充满物理学符号。"}
        resp = httpx.post(f"{BASE_URL}/v1/notebooks/{nb_id}/chat/configure", headers=get_headers(), json=config_payload, timeout=20.0)
        print(f"   状态码: {resp.status_code}")

        # 4. 进行对话
        print("\n[Step 4] 发起流式对话提问...")
        chat_payload = {"question": "超光速旅行在目前物理学中为什么是不可能的？"}
        with httpx.stream("POST", f"{BASE_URL}/v1/notebooks/{nb_id}/chat", json=chat_payload, headers=get_headers(), timeout=60.0) as r:
            if r.status_code == 200:
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]": break
                        try:
                            chunk = json.loads(data_str).get("text", "")
                            if chunk:
                                sys.stdout.write(chunk)
                                sys.stdout.flush()
                        except Exception: pass
                print()
            else:
                print(f"❌ 对话失败: {r.status_code}")

        # 5. 创建笔记
        print("\n[Step 5] 在笔记本中创建笔记...")
        resp = httpx.post(f"{BASE_URL}/v1/notebooks/{nb_id}/notes", headers=get_headers(), json={"title": "管道笔记", "content": "测试数据"}, timeout=20.0)
        print(f"   状态码: {resp.status_code}")

    finally:
        # 6. 数据销毁闭环
        print("\n[Step 6] 销毁临时创建的笔记本，还原数据...")
        resp = httpx.delete(f"{BASE_URL}/v1/notebooks/{nb_id}", headers=get_headers(), timeout=20.0)
        print(f"   删除状态码: {resp.status_code}")
        print("🎉 自动化流水线闭环测试圆满完成！")

# ----------------------------------------------------
# 菜单主入口
# ----------------------------------------------------
def main_menu():
    menu_options = {
        "0": ("一键运行自动化流水线闭环测试 (零污染流程)", run_pipeline),
        "1": ("获取笔记本列表 (GET /v1/notebooks)", cmd_list_notebooks),
        "2": ("创建笔记本 (POST /v1/notebooks)", cmd_create_notebook),
        "3": ("重命名笔记本 (PATCH /v1/notebooks/{id})", cmd_rename_notebook),
        "4": ("获取笔记本详情 (GET /v1/notebooks/{id})", cmd_notebook_detail),
        "5": ("添加文本来源 (POST /v1/notebooks/{id}/sources/text)", cmd_add_text_source),
        "6": ("上传物理文件来源 (POST /v1/notebooks/{id}/sources/file)", cmd_add_file_source),
        "7": ("挂载网页 URL 来源 (POST /v1/notebooks/{id}/sources/url)", cmd_add_url_source),
        "8": ("批量挂载 URL 来源 (POST /v1/notebooks/{id}/sources/batch)", cmd_add_batch_urls),
        "9": ("获取来源列表 (GET /v1/notebooks/{id}/sources)", cmd_list_sources),
        "10": ("获取来源解析详情 (GET /v1/notebooks/{id}/sources/{src_id})", cmd_source_detail),
        "11": ("获取文档来源脱水文本 (GET /v1/notebooks/{id}/sources/{src_id}/text)", cmd_get_source_text),
        "12": ("同步阻塞等待文档就绪 (POST /v1/notebooks/{id}/sources/wait)", cmd_wait_sources),
        "13": ("配置对话行为 (自定义 Persona/Goal) (POST /v1/notebooks/{id}/chat/configure)", cmd_configure_chat),
        "14": ("获取引导提问建议词 (GET /v1/notebooks/{id}/suggested-prompts)", cmd_suggested_prompts),
        "15": ("发起流式对话测试 (POST /v1/notebooks/{id}/chat)", cmd_chat_stream),
        "16": ("创建测试笔记 (POST /v1/notebooks/{id}/notes)", cmd_create_note),
        "17": ("获取笔记列表 (GET /v1/notebooks/{id}/notes)", cmd_list_notes),
        "18": ("修改测试笔记内容 (PUT /v1/notebooks/{id}/notes/{nt_id})", cmd_update_note),
        "19": ("获取共享状态与链接详情 (GET /v1/notebooks/{id}/share)", cmd_get_share),
        "20": ("发起异步测验工件生成 (POST /v1/notebooks/{id}/artifacts)", cmd_generate_artifact),
        "21": ("删除临时笔记 (DELETE /v1/notebooks/{id}/notes/{nt_id})", cmd_delete_note),
        "22": ("删除临时来源文档 (DELETE /v1/notebooks/{id}/sources/{src_id})", cmd_delete_source),
        "23": ("清理删除测试笔记本 (DELETE /v1/notebooks/{id})", cmd_delete_notebook),
    }

    while True:
        print_ctx()
        print("💡 请输入选项前的数字执行测试 (输入 q 退出调试):")
        # 2列排序输出
        keys = list(menu_options.keys())
        for idx in range(0, len(keys), 2):
            k1 = keys[idx]
            n1 = menu_options[k1][0]
            col1 = f"[{k1:>2}] {n1:<65}"
            if idx + 1 < len(keys):
                k2 = keys[idx + 1]
                n2 = menu_options[k2][0]
                col2 = f"[{k2:>2}] {n2}"
                print(col1 + col2)
            else:
                print(col1)

        choice = input("\n👉 请选择输入: ").strip()
        if choice.lower() == 'q':
            print("👋 已退出 API 调试主控台。")
            break
        
        if choice in menu_options:
            print("\n" + "*" * 40)
            print(f"🎬 正在执行: {menu_options[choice][0]}")
            print("*" * 40)
            menu_options[choice][1]()
            input("\n按下 【回车键/Enter】 返回主菜单...")
        else:
            print("❌ 无效的输入，请重新选择！")

if __name__ == "__main__":
    main_menu()
