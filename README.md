# 🏆 XAUUSD Multi-TF Scalping & Institutional EA Series - Complete Package

ระบบช่วยเทรดอัตโนมัติ (Expert Advisor) สำหรับทองคำ **XAUUSD (Gold)** บนโปรแกรม **MetaTrader 5 (MT5)**

---

## 📂 โครงสร้างโฟลเดอร์โปรเจกต์ (Project Directory Structure)

```text
D:\Trade_Gus\
│
├── 📂 Conversation_Archive/                 # [ใหม่ 📜] บันทึกประวัติบทสนทนาและ log ทั้งหมด
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
├── 📂 Backtest_Engine/                      # เครื่องมือจำลองและทดสอบย้อนหลัง Python
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

📄 **ผู้พัฒนา:** Antigravity AI Coding Assistant  
🗓️ **อัปเดตล่าสุด:** 24 สิงหาคม 2026
