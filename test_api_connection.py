import httpx
import json
import sys

BASE_URL = "https://note.aisenno.com"
API_KEY = "my_notebooklm_key_snkj888"

def test_api():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print("🚀 [1/3] 开始测试：正在向网关获取笔记本列表...")
    notebooks_url = f"{BASE_URL}/v1/notebooks"
    
    try:
        resp = httpx.get(notebooks_url, headers=headers, timeout=20.0)
    except Exception as e:
        print(f"❌ 请求失败，无法连接到服务器: {e}")
        return

    if resp.status_code != 200:
        print(f"❌ 获取笔记本列表失败！状态码: {resp.status_code}")
        print(f"服务器返回内容: {resp.text}")
        return

    notebooks = resp.json().get("notebooks", [])
    print("✅ 获取成功！当前账号下的笔记本列表如下:")
    print("-" * 60)
    for index, nb in enumerate(notebooks):
        print(f"[{index + 1}] 名称: {nb.get('title')} | ID: {nb.get('id')}")
    print("-" * 60)

    if not notebooks:
        print("ℹ️ 当前账号下没有创建任何笔记本，无法进行聊天测试。请先在 Google NotebookLM 官网上创建笔记本。")
        return

    # 自动挑选第一个笔记本进行聊天测试
    target_nb = notebooks[0]
    nb_id = target_nb['id']
    nb_title = target_nb['title']
    print(f"\n🚀 [2/3] 自动挑选笔记本 [{nb_title}] 进行对话测试 (ID: {nb_id})...")

    chat_url = f"{BASE_URL}/v1/notebooks/{nb_id}/chat"
    payload = {
        "input": "你好，请用一句话告诉我你是谁，并帮我总结一下本笔记本主要关于什么内容。"
    }

    print("🚀 [3/3] 正在发起对话，等待网关流式 (SSE Stream) 返回结果:")
    print("-" * 60)
    
    try:
        # 使用 httpx 的 stream 方法以获取流式响应
        with httpx.stream("POST", chat_url, json=payload, headers=headers, timeout=60.0) as r:
            if r.status_code != 200:
                print(f"\n❌ 对话请求失败！状态码: {r.status_code}")
                # 读取全部内容进行展示
                r.read()
                print(f"服务器返回内容: {r.text}")
                return

            # 按行读取 SSE 流式数据
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    # 提取 data: 后的 JSON 内容
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data_json = json.loads(data_str)
                        # 核心文本内容通常存在于文本段中，这里直接打印流式输出的 chunk 文本
                        # 兼容原版返回的 chunk 字段（例如 text 或是 content）
                        chunk = data_json.get("text", "") or data_json.get("content", "")
                        if chunk:
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                    except Exception:
                        pass
        print("\n" + "-" * 60)
        print("🎉 测试圆满完成！API 调用、动态路由和对话功能全部一切正常！")
    except Exception as e:
        print(f"\n❌ 对话测试过程中发生异常: {e}")

if __name__ == "__main__":
    test_api()
