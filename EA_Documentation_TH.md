# 📘 คู่มือ XAUUSD Multi-TF Scalping EA v2.0

---

## 🎯 **ภาพรวมของระบบ**

EA นี้ออกแบบมาเพื่อ**ทำกำไรจากการเทรดทองคำ (XAUUSD)** โดยใช้วิธี Multi-Timeframe Trend Following กับ Cascade Take Profit System

### **วิธีการทำงาน:**
```
ขั้นตอนที่ 1: ตรวจสอบเทรนด์
└─ H4 + H1 + M30 ต้องแสดงการขึ้น/ลง ต่อเนื่อง (HH/HL หรือ LL/LH)

ขั้นตอนที่ 2: หาสัญญาณเข้า (Entry Confirmation)
└─ M5 ต้องมีแท่งเขียว (Close > Open) สำหรับ BUY
└─ M5 ต้องมีแท่งแดง (Close < Open) สำหรับ SELL

ขั้นตอนที่ 3: เปิดออเดอร์
└─ ตั้ง SL ที่ Low ของแท่งก่อนหน้า - 100-200 pips
└─ คำนวณ Lot Size จาก 15% Risk ของ Account

ขั้นตอนที่ 4: Cascade Take Profit
└─ RR 1:2 → ขยับ SL ไป Breakeven + 50% profit
└─ RR 1:3 → ขยับ SL ไปต่อ
└─ RR 1:5 → ขยับ SL ไปต่อ
└─ RR 1:10 → ขยับ SL ไปต่อ
└─ RR 1:15 → ปิดออเดอร์ทั้งหมด ✅
```

---

## 📊 **ตัวอย่างการเทรดจริง**

### **Scenario 1: ขาขึ้น (BUY)**
```
H4/H1/M30: แท่งต่อเนื่องขึ้น (HH/HL) ✅
M5: แท่งปิดเขียว (Close > Open) ✅

เข้า @ 2450.00
SL @ 2400 (Previous Low 2415 - 150 pips buffer)
Risk = 50 pips × $10/pip = $500

Profit Levels:
├─ TP1 (RR 1:2) @ 2500 → SL ขยับ → 2475 (Breakeven + 25)
├─ TP2 (RR 1:3) @ 2550 → SL ขยับ → 2525 (Entry + 75)
├─ TP3 (RR 1:5) @ 2650 → SL ขยับ → 2625 (Entry + 175)
├─ TP4 (RR 1:10) @ 2950 → SL ขยับ → 2925 (Entry + 475)
└─ TP5 (RR 1:15) @ 3250 → ❌ ปิดออเดอร์
```

---

## 🔧 **Input Parameters**

| Parameter | ค่า Default | คำอธิบาย |
|-----------|-----------|----------|
| **RiskPercent** | 15.0 | ความเสี่ยงต่อออเดอร์ = 15% ของ Account Balance |
| **SL_Buffer** | 150 | Buffer SL = 150 pips ต่ำกว่า Previous M5 Low |
| **MagicNumber** | 100001 | หมายเลขติดตามออเดอร์ (ไม่ต้องเปลี่ยน) |
| **UseTradeHours** | true | เปิด/ปิด Time Filter |
| **TradeHours1_Start** | 11:00 | เริ่มเทรด Session 1 (GMT+7) |
| **TradeHours1_End** | 16:00 | สิ้นสุด Session 1 |
| **TradeHours2_Start** | 16:00 | เริ่มเทรด Session 2 (GMT+7) |
| **TradeHours2_End** | 02:00 | สิ้นสุด Session 2 |
| **AllowNewOrders** | true | เปิดออเดอร์ใหม่ในช่วงเทรดได้ |
| **CloseOutsideHours** | false | ปิดออเดอร์นอกช่วงเทรด (false = ถือค้าง) |

### **ตัวอย่างการปรับแต่ง:**

**Conservative (ความเสี่ยงต่ำ):**
```
RiskPercent = 8.0
SL_Buffer = 200
```

**Aggressive (ความเสี่ยงสูง):**
```
RiskPercent = 20.0
SL_Buffer = 100
```

---

## 📥 **วิธีติดตั้ง**

### **ขั้นตอนที่ 1: Copy EA File**
```
1. ลอก XAUUSD_MultiTF_Scalping_EA_v2.mq5
2. Paste ไปที่ MetaTrader 5 → Experts Folder
   Windows: C:\Users\[Username]\AppData\Roaming\MetaQuotes\Terminal\[ID]\MQL5\Experts
   Mac: ~/Library/Application Support/MetaQuotes/Terminal/[ID]/MQL5/Experts
```

### **ขั้นตอนที่ 2: Compile**
```
1. เปิด MetaTrader 5
2. View → Toolbox → Experts
3. คลิก File → Open Data Folder
4. ไปที่ MQL5\Experts
5. คลิกขวา XAUUSD_MultiTF_Scalping_EA_v2.mq5 → Modify
6. MetaEditor เปิดขึ้น → F7 (Compile)
7. ตรวจสอบว่า "0 errors" ก่อนปิด
```

### **ขั้นตอนที่ 3: Attach to Chart**
```
1. เปิด XAUUSD Chart (Timeframe ใด ก็ได้)
2. คลิกขวา Chart → Attach Expert Advisor
3. เลือก XAUUSD_MultiTF_Scalping_EA_v2
4. Set Parameters ตามต้องการ
5. คลิก OK
```

---

## 🧪 **Backtesting (สำคัญ!)**

### **ขั้นตอนการ Backtest:**

```
1. MetaTrader 5 → View → Strategy Tester (Ctrl+R)
2. Settings:
   ├─ Expert Advisor: XAUUSD_MultiTF_Scalping_EA_v2
   ├─ Symbol: XAUUSD
   ├─ Timeframe: H1 (ให้ EA ตรวจสอบเอง)
   ├─ Model: Open Price (ปิดทันที - ไม่ต้องเฉียบ)
   ├─ Period: 6-12 เดือน
   ├─ Initial Deposit: 10,000 USD
   └─ Leverage: 1:100 (ตามบัญชีของคุณ)

3. คลิก "Start" และรอผลลัพธ์
```

### **สิ่งที่ต้องดู:**
```
✅ Win Rate > 40%
✅ Profit Factor > 1.5 (กำไร / ขาดทุน)
✅ Max Drawdown < 20% (ความเสี่ยง)
✅ Consecutive Wins > 5
```

---

## 📈 **การติดตามผลการทำงาน**

### **Logs ที่ EA เขียน:**
```
[Trade Opened - Type: BUY Entry: 2450.00 SL: 2400 Lot: 0.10]
[TP Level 1 (RR 1:2) - SL moved to 2475]
[TP Level 2 (RR 1:3) - SL moved to 2525]
```

**ตำแหน่ง Log:**
- MetaTrader 5 → View → Journal Tab
- เลือก "Expert" filter เพื่อดู EA logs เท่านั้น

---

## ⚠️ **ข้อควรระวัง**

### **1. Slippage & Latency**
- Slippage อาจทำให้ SL ไม่แน่นอน
- วิธีแก้: ใช้ VPS เพื่อลด Latency

### **2. Market Gap (Opening Gap)**
- ราคา Gap ตอนเปิด Market อาจทำให้ SL ถูกตี
- วิธีแก้: ปิด EA เมื่อ Market ปิด (Friday 23:59 GMT+7)

### **3. News Impact**
- ข่าวใหญ่ (Non-Farm Payroll ฯลฯ) อาจทำให้ราคาไม่แน่นอน
- วิธีแก้: ปิด EA ช่วง 1 ชั่วโมงก่อนข่าว

### **4. Lot Size ต่ำเกินไป**
- ถ้า Lot Size < 0.01 EA จะไม่เปิดออเดอร์
- วิธีแก้: เพิ่ม RiskPercent หรือ Account Balance

---

## 🔄 **Live Trading Checklist**

```
□ Backtesting ผ่านแล้ว (6+ เดือน)
□ Demo Trading 2+ สัปดาห์
□ ตั้ง SL ที่บัญชีแล้ว (Account SL)
□ เปิด EA ที่ Demo สำหรับทดสอบ
□ Monitor EA ทุกวันเช่น 1 สัปดาห์
□ Go Live ด้วย Lot Size เล็กสุด
□ ประเมินผลทุกเดือน
```

---

## 🆘 **Troubleshooting**

### **ปัญหา: EA ไม่เปิดออเดอร์**

**สาเหตุที่เป็นไปได้:**
1. ❌ ไม่อยู่ใน Trading Hours
   - ✅ ตรวจสอบเวลา (GMT+7)
   
2. ❌ Trend ไม่ชัดเจน
   - ✅ ดู H4/H1/M30 ว่ามี HH/HL ต่อเนื่องไหม
   
3. ❌ ยังมี Position เปิดอยู่
   - ✅ EA จะเปิดได้ 1 position เท่านั้น
   
4. ❌ Lot Size เล็กเกินไป
   - ✅ เพิ่ม Account หรือ RiskPercent

### **ปัญหา: EA ปิดตำแหน่งสามารถ**

**อาจเป็น:**
1. ✅ SL ถูกตี (ปกติ - ความเสี่ยงของระบบ)
2. ✅ ถึง TP Level 5 (RR 1:15) - ปิดโปรแกรมแล้ว

---

## 📞 **สนับสนุนและอัปเดต**

- **Version:** 2.0 (Updated 2024)
- **Tested Symbol:** XAUUSD (Gold)
- **Tested Brokers:** ICmarkets, Pepperstone, HotForex

---

**Happy Trading! 🚀**
