import json

jsonl_path = r"D:\Trade_Gus\Conversation_Archive\transcript_full.jsonl"
md_path = r"D:\Trade_Gus\Conversation_Archive\Full_Conversation_History.md"

with open(jsonl_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

md_output = []
md_output.append("# 📜 บันทึกประวัติบทสนทนาและขั้นตอนการทำงานทั้งหมด (Full Conversation Archive)")
md_output.append("## **โครงการพัฒนา XAUUSD EA Series (v2.0, v3.0, v3 Scalp, v4 Apex)**\n")
md_output.append("--- \n")

step_num = 1
for line in lines:
    try:
        data = json.loads(line)
        step_type = data.get("type", "")
        content = data.get("content", "")
        created_at = data.get("created_at", "")
        
        if step_type == "USER_INPUT" and content:
            md_output.append(f"### 👤 **ผู้ใช้ (USER) - [{created_at}]**\n")
            md_output.append(f"{content}\n")
            md_output.append("\n---\n")
            step_num += 1
            
        elif step_type == "PLANNER_RESPONSE" and content:
            md_output.append(f"### 🤖 **ผู้ช่วย Antigravity (AI Assistant) - [{created_at}]**\n")
            md_output.append(f"{content}\n")
            md_output.append("\n---\n")
            step_num += 1
            
    except Exception as e:
        continue

with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_output))

print(f"Successfully generated readable markdown archive at {md_path}")
