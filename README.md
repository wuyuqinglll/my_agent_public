使用Gradio调用deepseek api创建本地对话页

使用方法：

```bash
git clone https://github.com/wuyuqinglll/my_agent_public.git
cd my_agent_public
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入自己的密钥
```

运行：

- `python script.py` — 流式对话页（端口 8888）
- `python script1.py` — 非流式对话页（端口 8888）
- `python test1.py` — 流式 + 对话历史截断（端口 8889）
- `python test2.py` — CSV 批量摘要（读 `data/raw/batch_in.csv`，写 `data/out/batch_out.csv`）
