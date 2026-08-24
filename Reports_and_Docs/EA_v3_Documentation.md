# 📘 คู่มือ EA v3.0: XAUUSD Multi-TF Scalping EA v3.0 (Advanced Edition)

ระบบ EA เวอร์ชัน 3.0 พัฒนาต่อยอดตามโครงสร้างสเปก **Multi-Timeframe Trend Following & Scalping Execution** สำหรับ **XAUUSD (ทองคำ)** บน MT5

---

### ⚙️ จุดเด่นและฟีเจอร์หลักในเวอร์ชัน v3.0

1. **Multi-Timeframe Trend Filter (M30, H1, H4):**
   - วิเคราะห์ทิศทางเทรนด์หลักพร้อมกันใน 3 ไทม์เฟรม (**M30, H1, H4**) ด้วยโครงสร้าง EMA Alignment
   - เทรดเฉพาะตามทิศทางเทรนด์หลักเท่านั้น (เช่น เมื่อ H4, H1, M30 เป็นขาขึ้น จะรอโฟกัสฝั่ง Buy บน M5)

2. **Entry Rules บน M5 (Bullish / Bearish Close Confirmation):**
   - รอการพักตัวบนไทม์เฟรม M5 จนเกิดแท่งปิดยืนยันการกลับตัว (**Bullish Close: Close > Open**)
   - เปิดออเดอร์ทันทีที่ราคาเปิดของแท่งถัดไป (**Next Candle Open**)

3. **Dynamic Stop Loss (SL ตามไส้แท่งแดงก่อนหน้า):**
   - คำนวณหาจุดต่ำสุด (**Lowest Low**) ของแท่งแดงก่อนหน้า (Previous Red Candle Low) สำหรับฝั่ง Buy 
   - ลบระยะ Buffer ลบเผื่อความปลอดภัย (**SL_Buffer_Pips = 150 points / $1.50**) ป้องกัน Noise สไปค์ราคาหลอก

4. **ระบบ Take Profit & Partial Close แบ่งปิดทำกำไร (RR 1:2, 1:3, 1:5, 1:10, 1:15):**
   - รองรับการแบ่งปิดล็อกกำไร 50% (**Partial Close 50%**) เมื่อราคาขยับไปถึงแต่ละระดับ RR (1:2, 1:3, 1:5, 1:10)
   - ขยับ SL ตามล็อกกำไรหน้าทุนอัตโนมัติ (**Trailing Stop Lock**)

5. **ตัวกรองเวลาเทรดประเทศไทย (GMT+7 Trading Hours Filter):**
   - **Session 1 (ช่วงเช้า-บ่าย):** `11:00 - 16:00` น. (เวลาไทย GMT+7)
   - **Session 2 (ช่วงดึก):** `22:00 - 02:00` น. (เวลาไทย GMT+7)
   - นอกเวลาเทรด: ถือค้างออเดอร์เดิมได้ แต่จะไม่เปิดออเดอร์ใหม่เพิ่ม

---

### 📂 ไฟล์ที่บันทึกในระบบ:
- 📄 [XAUUSD_MultiTF_Scalping_EA_v3.mq5](file:///D:/Trade_Gus/EA_Source/XAUUSD_MultiTF_Scalping_EA_v3.mq5) (ซอร์สโค้ด MQL5 v3.0)
- 📄 [XAUUSD_MultiTF_Scalping_EA_v3.ex5](file:///C:/Users/PC/AppData/Roaming/MetaQuotes/Terminal/E3E3B02889D32F38295D39BF94B6AD4A/MQL5/Experts/XAUUSD_MultiTF_Scalping_EA_v3.ex5) (ไฟล์ไบนารีบน MT5)
