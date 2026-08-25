import os

data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"

for root, dirs, files in os.walk(data_path):
    for f in files:
        if "v11" in f or "Champion" in f or "Master" in f:
            print("Found:", os.path.join(root, f))
