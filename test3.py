# Gradio 文本总结器：粘贴或上传 .txt → 非流式摘要
# 本课写法：流程写直，不抽 call_llm / 读文件辅助函数
import time
from pathlib import Path

import gradio as gr
from openai import (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
)

from llm_client import make_client

BASE = Path(__file__).resolve().parent
SYSTEM = "你是简洁的中文助手。只输出 2～4 句中文摘要，不要编号，不要解释。"
EXAMPLE = (
    "新品降噪耳机上周发货，音质不错，但客服回复偏慢；"
    "希望后续加强售后响应，并考虑推出更轻的旅行款。"
)

client, model = make_client(BASE)

# Gradio 的 btn.click 必须挂一个可调用对象；业务逻辑全写在里面，不另拆函数
def summarize(text, file_obj):
    # —— 取输入：优先粘贴，否则读上传的 .txt ——
    source = (text or "").strip()
    if not source and file_obj is not None:
        path = Path(file_obj if isinstance(file_obj, str) else getattr(file_obj, "name", ""))
        if path.is_file():
            try:
                source = path.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError:
                source = path.read_text(encoding="utf-8-sig", errors="replace").strip()

    if not source:
        return "请先粘贴文本，或上传 .txt 文件。"

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"用 2～4 句中文总结下面内容：\n{source}"},
    ]

    # —— 重试壳 + 非流式调用（与 script1 同一套路）——
    for attempt in range(1, 4):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            if isinstance(e, AuthenticationError):
                retryable = False
            elif isinstance(e, (APITimeoutError, APIConnectionError, RateLimitError)):
                retryable = True
            else:
                retryable = False
            print(f"第{attempt}次失败｜{type(e).__name__}| 可重试={'是' if retryable else '否'}")

            if (not retryable) or attempt == 3:
                return f"调用失败：{type(e).__name__}。（详情见终端；密钥不会显示在本页。）"

            sleep_s = 0.5 * (2 ** (attempt - 1))
            print(f" 等{sleep_s}s 再试")
            time.sleep(sleep_s)

with gr.Blocks(title="L2 文本总结器") as demo:
    gr.Markdown(
        "# L2 文本总结器\n"
        "粘贴文本或上传 `.txt` → 点「总结」→ 右侧可复制摘要。"
    )
    with gr.Row():
        with gr.Column():
            clear_inp = gr.Button("清除", size="sm", render=False)
            inp = gr.Textbox(
                lines=12,
                label="粘贴文本",
                placeholder="在此粘贴要总结的内容…",
                value=EXAMPLE,
                buttons=[clear_inp],
            )
            upload = gr.File(label="或上传 .txt", file_types=[".txt"])
            btn = gr.Button("总结", variant="primary")
        with gr.Column():
            clear_out = gr.Button("清除", size="sm", render=False)
            out = gr.Textbox(
                lines=12,
                label="摘要（可复制）",
                buttons=["copy", clear_out],
            )
    clear_inp.click(fn=lambda: "", outputs=inp)
    clear_out.click(fn=lambda: "", outputs=out)
    btn.click(fn=summarize, inputs=[inp, upload], outputs=out)
    gr.Examples(
        examples=[[EXAMPLE, None]],
        inputs=[inp, upload],
        label="示例输入",
    )

demo.launch(server_name="127.0.0.1", server_port=7862, share=False)
