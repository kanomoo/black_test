# 🏆 XAUUSD Multi-TF Scalping & Institutional EA Series - Complete Package

ระบบช่วยเทรดอัตโนมัติ (Expert Advisor) สำหรับทองคำ **XAUUSD (Gold)** บนโปรแกรม **MetaTrader 5 (MT5)** พร้อมคู่มือการติดตั้ง Antigravity CLI และการเชื่อมต่อโปรโตคอล MetaTrader 5 Native MCP

---

## 📂 โครงสร้างโฟลเดอร์โปรเจกต์ (Project Directory Structure)

```text
D:\Trade_Gus\
│
├── 📂 Conversation_Archive/                 # บันทึกประวัติบทสนทนาและ log ทั้งหมด
│   ├── Full_Conversation_History.md         # ประวัติบทสนทนาฉบับอ่านง่ายแบบ Markdown
│   ├── transcript_full.jsonl                # บันทึกประวัติคำสั่งระบบแบบเต็ม (Full Raw JSONL Log)
│   └── transcript.jsonl                     # บันทึกประวัติคำสั่งระบบ (Summary Log)
│
├── 📂 EA_Source/                            # โฟลเดอร์ซอร์สโค้ดและไฟล์คอมไพล์ MT5
│   ├── XAUUSD_MultiTF_Scalping_EA_v3_Scalp.mq5 # [แนะนำ 🔥] EA v3.0 Scalp Edition (สำหรับ HFM Cent & Standard)
│   ├── XAUUSD_MultiTF_Scalping_EA_v3_Scalp.ex5 # ไบนารี EA v3 Scalp Edition ติดตั้งใน MT5
│   ├── XAUUSD_Apex_Institutional_EA_v4.mq5     # EA v4.0 Apex Institutional Engine (เรือธงสถาบัน)
│   ├── XAUUSD_Apex_Institutional_EA_v4.ex5     # ไบนารี EA v4.0 ติดตั้งใน MT5
│   ├── XAUUSD_MultiTF_Scalping_EA_v3.mq5       # EA v3.0 Standard Edition
│   ├── XAUUSD_MultiTF_Scalping_EA_v2.mq5       # EA v2.0 Trend Cascade
│   └── XAUUSD_MultiTF_Scalping_EA_v2.ex5       # ไบนารี EA v2.0
│
├── 📂 Backtest_Engine/                     # เครื่องมือจำลองและทดสอบย้อนหลัง Python
│   ├── run_master_all_versions_comparison.py# ระบบรันเปรียบเทียบทุกเวอร์ชัน
│   ├── run_realworld_v4_backtest.py         # ระบบรัน Backtest EA v4.0
│   ├── optimize_v3_scalp.py                 # ระบบค้นหาค่าสเกลป์ทำกำไรสูงสุด v3 Scalp
│   └── run_cent_account_15.py               # ระบบจำลองพอร์ตทุน $15.00 (Cent Account)
│
├── 📂 Reports_and_Docs/                     # รายงานสรุปผลวิเคราะห์และคู่มือฉบับเต็ม
│   ├── Master_All_Versions_Comparison_Report.md # รายงานเปรียบเทียบทุกเวอร์ชัน
│   ├── EA_v4_Apex_Institutional_Report.md   # รายงานสรุป EA v4.0 Flagship Edition
│   ├── EA_v2_vs_v3_Comparison_Report.md     # รายงานเปรียบเทียบ v2.0 vs v3.0
│   └── XAUUSD_Backtest_Report.md            # รายงานผลทดสอบ 2 ปี & Max Profit Report
│
└── README.md                                # คู่มือสรุปภาพรวมโปรเจกต์ฉบับนี้
```

---

## 🛠️ 1. คู่มือการติดตั้งและตั้งค่า Antigravity CLI (AGY CLI Setup Guide)

**Antigravity CLI (AGY)** คือเครื่องมือระบบช่วยเขียนโค้ดและพัฒนาซอฟต์แวร์อัจฉริยะ (AI Agentic Coding Assistant) โดย Google DeepMind

### 1.1 ที่ตั้งโฟลเดอร์ระบบ (System Directories):
- **App Data Directory:** `C:\Users\PC\.gemini\antigravity-cli`
- **Brain & Artifact Directory:** `C:\Users\PC\.gemini\antigravity-cli\brain\<conversation-id>`
- **Customizations & Skills:** `C:\Users\PC\.gemini\antigravity-cli\builtin\skills`

### 1.2 การเรียกใช้และตั้งค่าพื้นฐาน:
1. สั่งเปิดใช้งานคำสั่งผ่าน PowerShell หรือ Command Prompt:
   ```bash
   agy --version
   ```
2. โฟลเดอร์ Skill ปรับแต่งความสามารถระบบอยู่ที่:
   `C:\Users\PC\.gemini\antigravity-cli\builtin\skills\antigravity_guide\SKILL.md`

---

## 🔌 2. คู่มือการเชื่อมต่อ MetaTrader 5 Native MCP Server (MT5 MCP Protocol Integration Guide)

โปรแกรม **MetaTrader 5 Build 6140+** มีระบบเซิร์ฟเวอร์ **MCP (Model Context Protocol)** ในตัว ช่วยให้ AI สามารถเข้าดูข้อมูลและควบคุม MT5 ผ่านโปรโตคอล JSON-RPC 2.0 บนพอร์ต HTTP ได้โดยตรง

---

### 2.1 ขั้นตอนการเปิดใช้งาน MCP ในโปรแกรม MT5:

1. เปิดโปรแกรม **MetaTrader 5**
2. ไปที่เมนู **Tools** ➔ **Options** (หรือกด `Ctrl + O`)
3. คลิกเลือกแท็บ **`AI Assistant`** หรือ **`MCP`**
4. กำหนดค่าการเชื่อมต่อ:
   - **Enable MCP Server:** ติ๊กถูกเปิดใช้งาน (Checked)
   - **Server Address:** `http://127.0.0.1:22346/mcp`
   - **API Key:** คัดลอกรหัส API Key ของคุณ (ตัวอย่าง: `2tK9SIPthWlXQVuKNro42NuY83v0hVTL8dePzBfxUC`)
5. กดปุ่ม **OK**

---

### 2.2 โฟลเดอร์การตั้งค่าระบบ MT5 MCP (Config File Location):

โปรแกรม MT5 จะบันทึกรหัส API Key และพอร์ตลงในไฟล์คอนฟิก:
`C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\<TERMINAL_ID>\config\assistant.ini`

**ตัวอย่างเนื้อหาไฟล์ `assistant.ini`:**
```ini
[MCP]
Enabled=1
Address=http://127.0.0.1:22346/mcp
ApiKey=2tK9SIPthWlXQVuKNro42NuY83v0hVTL8dePzBfxUC
```

---

### 2.3 รูปแบบโปรโตคอลการรับส่งข้อมูล (JSON-RPC 2.0 Headers & Authentication):

การเรียกใช้งานคำสั่ง MCP ผ่าน HTTP Client (เช่น curl, Python หรือ PowerShell) จะต้องส่งข้อมูลผ่าน HTTP Headers ดังนี้:

- **Endpoint URL:** `http://127.0.0.1:22346/mcp`
- **HTTP Headers:**
  - `Authorization: Bearer <ApiKey>`
  - `Mcp-Session-Id: <SessionID>` (ได้รับคืนมาจากคำสั่ง initialize)
  - `Content-Type: application/json`

---

### 2.4 ตัวอย่างขั้นตอนการเชื่อมต่อ (Handshake & Execution Steps):

#### **ขั้นตอนที่ 1: สั่ง Initialize เพื่อขอ Session ID**
```bash
curl.exe -s -i -H "Authorization: Bearer 2tK9SIPthWlXQVuKNro42NuY83v0hVTL8dePzBfxUC" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"Antigravity","version":"1.0"}}}' \
  "http://127.0.0.1:22346/mcp"
```
*(คัดลอกค่า `Mcp-Session-Id` จาก Response Header ที่ได้กลับมา)*

#### **ขั้นตอนที่ 2: สั่งส่งแจ้งเตือน Initialized**
```bash
curl.exe -s -H "Authorization: Bearer 2tK9SIPthWlXQVuKNro42NuY83v0hVTL8dePzBfxUC" \
  -H "Mcp-Session-Id: <SessionID>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  "http://127.0.0.1:22346/mcp"
```

#### **ขั้นตอนที่ 3: เรียกดูคำสั่งมมือ Tool ที่ MT5 รองรับ (tools/list)**
```bash
curl.exe -s -H "Authorization: Bearer 2tK9SIPthWlXQVuKNro42NuY83v0hVTL8dePzBfxUC" \
  -H "Mcp-Session-Id: <SessionID>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  "http://127.0.0.1:22346/mcp"
```

---

### 2.5 รายชื่อคำสั่ง MT5 Native MCP Tools ที่รองรับ:

| ชื่อคำสั่ง Tool Name | คำอธิบายการทำงาน (Function Description) |
| :--- | :--- |
| **`get_workspace_info`** | ดึงข้อมูลเวอร์ชัน MT5, Terminal ID, และสถานะพอร์ตการลงทุน |
| **`tester_run_backtest`** | สั่งรันการทดสอบย้อนหลัง (Backtest) อัตโนมัติตามไฟล์โปรไฟล์ `.ini` |
| **`tester_get_status`** | เช็คสถานะความคืบหน้าของการรัน Backtest (RUNNING, STOPPED) |
| **`tester_get_report`** | ดึงตารางสรุปผลรายงาน Backtest Report จาก MT5 |
| **`tester_stop`** | สั่งหยุดกระบวนการรัน Backtest ใน MT5 |

---

📄 **ผู้พัฒนา:** Antigravity AI Coding Assistant  
🗓️ **อัปเดตล่าสุด:** 24 สิงหาคม 2026
