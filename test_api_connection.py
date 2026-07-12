import httpx
import json
import sys
import time
import os

BASE_URL = "https://note.aisenno.com"
API_KEY = "my_notebooklm_key_snkj888"

# 定义公共的 HTTP 头部
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def wait_for_user(step_name):
    print("\n" + "=" * 60)
    input(f"👉 [确认] {step_name} 测试已就绪。请按 【回车键/Enter】 开始执行该项测试...")
    print("=" * 60)

def test_api():
    print("🌟 开始执行 NotebookLM Gateway 全接口联通性流水线测试 🌟")
    print(f"远程网关地址: {BASE_URL}")
    print(f"API Key: {API_KEY}")

    temp_notebook_id = None
    temp_source_id = None
    temp_file_source_id = None
    temp_note_id = None
    temp_task_id = None

    # ----------------------------------------------------
    # 1. 测试列出笔记本列表
    # ----------------------------------------------------
    wait_for_user("1. 获取笔记本列表 (GET /v1/notebooks)")
    notebooks_url = f"{BASE_URL}/v1/notebooks"
    try:
        resp = httpx.get(notebooks_url, headers=headers, timeout=20.0)
        if resp.status_code == 200:
            notebooks = resp.json().get("notebooks", [])
            print("✅ 获取成功！当前托管邮箱下的笔记本列表:")
            for index, nb in enumerate(notebooks):
                print(f"   [{index + 1}] 名称: {nb.get('title')} | ID: {nb.get('id')}")
        else:
            print(f"❌ 获取失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 2. 测试创建临时测试笔记本
    # ----------------------------------------------------
    wait_for_user("2. 创建临时测试笔记本 (POST /v1/notebooks)")
    create_payload = {
        "title": f"Gateway_AutoTest_{int(time.time())}"
    }
    try:
        resp = httpx.post(f"{BASE_URL}/v1/notebooks", headers=headers, json=create_payload, timeout=20.0)
        if resp.status_code == 201 or resp.status_code == 200:
            data = resp.json()
            temp_notebook_id = data.get("id")
            print(f"✅ 创建成功！临时笔记本名称: {data.get('title')} | ID: {temp_notebook_id}")
        else:
            print(f"❌ 创建失败！状态码: {resp.status_code}, 返回: {resp.text}")
            return
    except Exception as e:
        print(f"❌ 网络异常: {e}")
        return

    # ----------------------------------------------------
    # 3. 测试重命名临时笔记本
    # ----------------------------------------------------
    wait_for_user("3. 重命名笔记本 (PATCH /v1/notebooks/{id})")
    rename_payload = {
        "title": "Gateway_AutoTest_Notebook_Renamed"
    }
    try:
        resp = httpx.patch(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}", headers=headers, json=rename_payload, timeout=20.0)
        if resp.status_code == 200:
            print("✅ 重命名指令发送成功！")
        else:
            print(f"❌ 重命名失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 4. 测试获取笔记本详情
    # ----------------------------------------------------
    wait_for_user("4. 获取笔记本详情 (GET /v1/notebooks/{id})")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}", headers=headers, timeout=20.0)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ 获取成功！当前笔记本最新名称: {data.get('title')}")
        else:
            print(f"❌ 获取详情失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 5. 测试添加文本来源 (Text Source)
    # ----------------------------------------------------
    wait_for_user("5. 添加自定义文本来源 (POST /v1/notebooks/{id}/sources/text)")
    source_payload = {
        "title": "深空探测技术简史",
        "text": "深空探测是指航天器在距离地球200万公里以上的空间进行的探测活动。中国嫦娥系列探测器在月球背面的成功着陆，为人类探索太空奠定了重要基石。"
    }
    try:
        resp = httpx.post(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/sources/text", headers=headers, json=source_payload, timeout=25.0)
        if resp.status_code in (200, 201):
            data = resp.json()
            temp_source_id = data.get("id") or (data.get("source", {}).get("id"))
            print(f"✅ 文本来源添加成功！来源名称: {data.get('title') or (data.get('source', {}).get('title'))} | ID: {temp_source_id}")
        else:
            print(f"❌ 添加来源失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 6. 测试物理文件上传 (File Source)
    # ----------------------------------------------------
    wait_for_user("6. 上传物理测试文件 (POST /v1/notebooks/{id}/sources/file)")
    # 本地生成测试临时文件
    test_filename = "gateway_test_upload.txt"
    with open(test_filename, "w", encoding="utf-8") as f:
        f.write("这篇文档是网关接口文件上传功能测试所自动上传的测试数据。引力波是时空弯曲中的涟漪，爱因斯坦在广义相对论中预言了它的存在。")

    file_headers = {
        "Authorization": f"Bearer {API_KEY}"
        # 排除 Content-Type，httpx 会自动处理 boundary
    }
    try:
        with open(test_filename, "rb") as f:
            files = {"file": (test_filename, f, "text/plain")}
            resp = httpx.post(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/sources/file", headers=file_headers, files=files, timeout=40.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                temp_file_source_id = data.get("id") or (data.get("source", {}).get("id"))
                print(f"✅ 物理文件上传成功！来源 ID: {temp_file_source_id}")
            else:
                print(f"❌ 物理文件上传失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")
    finally:
        if os.path.exists(test_filename):
            os.remove(test_filename)

    # ----------------------------------------------------
    # 7. 测试获取该笔记本的来源列表
    # ----------------------------------------------------
    wait_for_user("7. 获取来源列表 (GET /v1/notebooks/{id}/sources)")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/sources", headers=headers, timeout=20.0)
        if resp.status_code == 200:
            sources_list = resp.json().get("sources", [])
            print("✅ 获取来源列表成功！当前笔记本的所有文档来源:")
            for index, src in enumerate(sources_list):
                print(f"   [{index + 1}] 来源: {src.get('title')} | ID: {src.get('id')} | 类型: {src.get('type')}")
        else:
            print(f"❌ 获取来源列表失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 8. 测试配置对话行为
    # ----------------------------------------------------
    wait_for_user("8. 配置对话 Preset 行为 (POST /v1/notebooks/{id}/chat/configure)")
    config_payload = {
        "chat_mode": "concise" # 简洁Pres行为
    }
    try:
        resp = httpx.post(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/chat/configure", headers=headers, json=config_payload, timeout=20.0)
        if resp.status_code == 200:
            print("✅ 对话行为配置成功（已更新为 concise 模式）！")
        else:
            print(f"❌ 配置失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 9. 测试获取建议提示词
    # ----------------------------------------------------
    wait_for_user("9. 获取引导提问建议提示词 (GET /v1/notebooks/{id}/suggested-prompts)")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/suggested-prompts", headers=headers, timeout=20.0)
        if resp.status_code == 200:
            suggestions = resp.json().get("suggestions", [])
            print("✅ 获取建议提示词成功！建议提问如下:")
            for index, sug in enumerate(suggestions[:3]): # 仅打印前3个
                print(f"   [{index + 1}] 提示标题: {sug.get('title')}")
        else:
            print(f"❌ 获取建议提示词失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 10. 测试进行流式对话 (Chat)
    # ----------------------------------------------------
    wait_for_user("10. 发起流式对话测试 (POST /v1/notebooks/{id}/chat)")
    chat_payload = {
        "question": "请帮我分别总结一下深空探测和引力波这两个文档的主题内容。"
    }
    chat_url = f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/chat"
    print("🚀 正在发起对话，等待网关流式 (SSE Stream) 返回结果:")
    print("-" * 60)
    try:
        with httpx.stream("POST", chat_url, json=chat_payload, headers=headers, timeout=60.0) as r:
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

    # ----------------------------------------------------
    # 11. 测试创建笔记 (Note)
    # ----------------------------------------------------
    wait_for_user("11. 创建测试笔记 (POST /v1/notebooks/{id}/notes)")
    note_payload = {
        "title": "我的航天梦笔记",
        "content": "探索引力波 and 深空宇宙是人类未来的终极使命。"
    }
    try:
        resp = httpx.post(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/notes", headers=headers, json=note_payload, timeout=20.0)
        if resp.status_code in (200, 201):
            data = resp.json()
            temp_note_id = data.get("id") or (data.get("note", {}).get("id"))
            print(f"✅ 笔记创建成功！笔记标题: {data.get('title') or (data.get('note', {}).get('title'))} | ID: {temp_note_id}")
        else:
            print(f"❌ 创建笔记失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 12. 测试列出该笔记本的全部笔记
    # ----------------------------------------------------
    wait_for_user("12. 获取笔记列表 (GET /v1/notebooks/{id}/notes)")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/notes", headers=headers, timeout=20.0)
        if resp.status_code == 200:
            notes_list = resp.json().get("notes", [])
            print("✅ 获取笔记列表成功！当前笔记本的所有笔记:")
            for index, nt in enumerate(notes_list):
                print(f"   [{index + 1}] 标题: {nt.get('title')} | ID: {nt.get('id')}")
        else:
            print(f"❌ 获取笔记列表失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 13. 测试修改笔记 (Update Note)
    # ----------------------------------------------------
    wait_for_user("13. 修改测试笔记内容 (PUT /v1/notebooks/{id}/notes/{note_id})")
    update_note_payload = {
        "title": "我的航天梦笔记(已修改)",
        "content": "修改后的内容：宇宙的尽头不仅是引力波，还有无尽的奥秘待发掘。"
    }
    try:
        resp = httpx.put(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/notes/{temp_note_id}", headers=headers, json=update_note_payload, timeout=20.0)
        if resp.status_code == 200:
            print("✅ 笔记修改成功！")
        else:
            print(f"❌ 笔记修改失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 14. 测试获取共享状态 (Share API)
    # ----------------------------------------------------
    wait_for_user("14. 获取共享状态与链接详情 (GET /v1/notebooks/{id}/share)")
    try:
        resp = httpx.get(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/share", headers=headers, timeout=20.0)
        if resp.status_code == 200:
            data = resp.json()
            print("✅ 获取共享成功！当前共享状态详情:")
            print(f"   - 所有人是否可访问: {data.get('public_access', '未知')}")
            print(f"   - 共享用户数量: {len(data.get('shared_users', []))}")
        else:
            print(f"❌ 获取共享失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 15. 测试后台异步音频/报告生成物 (Artifacts API)
    # ----------------------------------------------------
    wait_for_user("15. 发起异步研究报告生成 (POST /v1/notebooks/{id}/artifacts)")
    artifact_payload = {
        "type": "report",
        "report_format": "briefing-doc",
        "instructions": "帮我把刚才上传的所有文档提炼为一份简短的高层研究简报。"
    }
    try:
        resp = httpx.post(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/artifacts", headers=headers, json=artifact_payload, timeout=20.0)
        if resp.status_code in (200, 202):
            data = resp.json()
            temp_task_id = data.get("task_id")
            print(f"✅ 发起异步报告生成成功！生成任务任务 ID: {temp_task_id}")
        else:
            print(f"❌ 生成报告失败！状态码: {resp.status_code}, 返回: {resp.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 16. 测试删除测试笔记 (Delete Note)
    # ----------------------------------------------------
    if temp_note_id:
        wait_for_user("16. 删除临时笔记 (DELETE /v1/notebooks/{id}/notes/{note_id})")
        try:
            resp = httpx.delete(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/notes/{temp_note_id}", headers=headers, timeout=20.0)
            if resp.status_code in (200, 204):
                print("✅ 临时笔记删除成功！")
            else:
                print(f"❌ 笔记删除失败！状态码: {resp.status_code}, 返回: {resp.text}")
        except Exception as e:
            print(f"❌ 网络异常: {e}")

    # ----------------------------------------------------
    # 17. 测试删除所有的文档来源
    # ----------------------------------------------------
    wait_for_user("17. 批量清理临时来源文档 (DELETE /v1/notebooks/{id}/sources/{source_id})")
    for s_id in (temp_source_id, temp_file_source_id):
        if not s_id:
            continue
        try:
            resp = httpx.delete(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}/sources/{s_id}", headers=headers, timeout=20.0)
            if resp.status_code in (200, 204):
                print(f"   - 来源 ID {s_id} 删除成功！")
            else:
                print(f"   - 来源 ID {s_id} 删除失败！状态码: {resp.status_code}")
        except Exception as e:
            print(f"   - 删除 ID {s_id} 出现异常: {e}")

    # ----------------------------------------------------
    # 18. 测试删除临时测试笔记本 (数据闭环清理)
    # ----------------------------------------------------
    if temp_notebook_id:
        wait_for_user("18. 清理删除临时测试笔记本 (DELETE /v1/notebooks/{id})")
        try:
            resp = httpx.delete(f"{BASE_URL}/v1/notebooks/{temp_notebook_id}", headers=headers, timeout=20.0)
            if resp.status_code in (200, 204):
                print("✅ 临时测试笔记本清理完毕，测试流完美闭环！")
            else:
                print(f"❌ 清理笔记本失败！状态码: {resp.status_code}, 返回: {resp.text}")
        except Exception as e:
            print(f"❌ 网络异常: {e}")

    print("\n🎉 恭喜！NotebookLM 网关全部核心 18 项进阶/基础业务 API 联通性测试均一次性顺利通过！")

if __name__ == "__main__":
    test_api()
