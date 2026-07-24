# CSV 批量调用,学会把模型接到流水线上，一次处理很多条业务文本；
import csv
import time
from pathlib import Path

from llm_client import make_client

BASE = Path(__file__).resolve().parent
IN_PATH = BASE / "data" / "raw" / "batch_in.csv"
OUT_PATH  = BASE / "data" / "out" / "batch_out.csv"

SYSTEM = "你是简洁的中文助手。只输出一句中文摘要，不要编号，不要解释。"

# 项目里 make_client 返回 (OpenAI客户端, model名)
client, model = make_client(BASE)
fail = 0
ok = 0
SLEEP_S = 0.4

# —— 读入 ——
with open(IN_PATH, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit(f"输入为空：{IN_PATH}")
if "text" not in rows[0]:
    raise SystemExit("CSV 需要 text 列")

for i, row in enumerate(rows, start=1):
    text = (row.get("text") or "").strip()
    print(f"\n[{i}/{len(rows)}] id={row.get('id', '')} chars={len(text)}")

    if not text:
        row["summary"] = ""
        row["error"] = "empty_text"
        fail += 1
        print("  跳过：空 text")
    else:
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"用一句话总结：\n{text}"},
        ]
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
            )
            summary = (resp.choices[0].message.content or "").strip()
            row["summary"] = summary
            row["error"] = ""
            ok += 1
            print("  summary:", summary[:80] + ("…" if len(summary) > 80 else ""))
        except Exception as exc:
            # 单行失败 continue：不中断整表
            row["summary"] = ""
            row["error"] = type(exc).__name__
            fail += 1
            print(f"  失败: {type(exc).__name__}")

    if i < len(rows) and SLEEP_S > 0:
        time.sleep(SLEEP_S)
# —— 写出 ——
fieldnames = list(rows[0].keys())
for col in ("summary", "error"):
    if col not in fieldnames:
        fieldnames.append(col)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)