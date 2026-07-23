使用Gradio调用deepseek api创建本地对话页
使用方法
git clone https://github.com/wuyuqinglll/my_agent_public.git
cd my_agent_public
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入自己的密钥
python script.py
