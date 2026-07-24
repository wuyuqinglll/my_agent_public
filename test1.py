# 流式+对话历史与上下文控制
import time
import os
from pathlib import Path
from dotenv import load_dotenv
import gradio as gr
from openai import (
    OpenAI,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,  # 不要从 multiprocessing 导入
)

env_path = Path(__file__).resolve().parent/ ".env"
# print(env_path)
load_dotenv(env_path)
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
# print(api_key)

# 1.连上服务
client = OpenAI(api_key=api_key, base_url=base_url,timeout=60)
SYSTEM = "你是助手"
KEEP_ROUNDS = 6  # 保留最近几轮；一轮 = user + assistant

def respond(message: str, history: list):
    # 流式输出
    text = (message or "").strip()
    if not text:
        yield "请先输入内容。"
        return
    # -------------------------------------------------------
    # 把 Gradio 的 history 转成 OpenAI 的 messages
    # Gradio4：history = [[用户话, 助手话], [用户话, 助手话], ...]
    # Gradio5：history = [{"role":"user","content":"..."}, {"role":"assistant",...}, ...]
    # history 一般「不含本轮刚输入」；本轮 text 要在循环后再单独 append
    # -------------------------------------------------------
    # 先把gradio history 收成完整轮次（user + assistant）
    pairs = []
    pending_user = None
    for item in history or []:
        if isinstance(item, dict):
            # —— Gradio5：每一项已经是一条消息 ——
            role = item.get("role")
            content = item.get("content")
            # 只收合法角色;content必须为非空字符串
            if role not in ("user", "assistant") or not isinstance(content, str) or not content:
                continue
            msg = {"role":role, "content":content}
            if role == "user":
                pending_user = msg
            elif role == "assistant" and pending_user is not None:
                pairs.append((pending_user, msg))
                pending_user = None
        #  兼容Gradio 旧版（4.x） 的 history 格式
        elif isinstance(item, (list, tuple)) and len(item) >= 1:
            user_text = item[0] or "" # 第0个 = 用户
            bot_text = item[1] if len(item) > 1 else None # 第1个 = 助手（可能还没有）
            if user_text and bot_text:
                pairs.append((
                    {"role":"user", "content":str(user_text)},
                    {"role":"assistant", "content":str(bot_text)}
                ))
    # 只保留最近N轮
    kept = pairs[-KEEP_ROUNDS:] if KEEP_ROUNDS > 0 else []
    dropped = (len(pairs) - len(kept)) * 2

    # 拼最终 messages:system +保留轮 + 本轮
    messages = [{"role":"system", "content":SYSTEM}]
    for u,a in kept:
        messages.append(u)
        messages.append(a)
    if pending_user is not None:
        messages.append(pending_user)
    messages.append({"role":"user", "content":text})

    chars = sum(len(m["content"]) for m in messages)
    print(
        f"[ctx] msgs={len(messages)} kept{len(kept)}",
        f"dropped={dropped} chars={chars}={chars // 4}",
    )

    # 重试壳+调用
    for attempt in range(1, 4):
        # chunks: list[str] = []
        full = ""
        try:
            stream = client.chat.completions.create(  # type: ignore
                model="deepseek-chat",
                messages=messages,
                temperature=0.3,
                stream=True,
            )
            for event in stream:
                piece = event.choices[0].delta.content or ""
                if not piece:
                    continue
                full += piece
                yield full # 每来一块就更新页面（流式关键
            return
                # print(piece, end="", flush=True)  # 给用户看
                # chunks.append(piece)  # 自己攒着
            # full = "".join(chunks).strip() # 拼完整串
            # break  # 成功：离开重试循环
        except Exception as e:
            # 当场判断可不可以重试（不另写函数）
            if isinstance(e, AuthenticationError):
                retryable = False # 钥匙配错：别重试
            elif isinstance(e, (APITimeoutError, APIConnectionError, RateLimitError)):
                retryable = True # 超时，断连，429: 可重试
            else:
                retryable = False
            print(f"第{attempt}次失败 ｜{type(e).__name__}| 可重试={'是'if retryable else '否'}")

            if(not retryable) or attempt == 3:
                yield f"调用失败：{type(e).__name__}。（详情见终端）"
                return # 不可重试，或者已经第三次 --》停

            sleep_s = 0.5*(2**(attempt-1))
            print(f" 等{sleep_s}s 再试")
            time.sleep(sleep_s)

# 构造界面并启动
gr.ChatInterface(
    fn = respond,
    title = "mini_agent",
    description = "Agent's first attempt",
    examples = ["用一句话解释什么是 timeout", "pong", "为什么 API 常用 JSON？"],
).launch(server_name = "127.0.0.1", server_port = 8889, share = False)