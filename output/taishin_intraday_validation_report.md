# 觀察名單籌碼持股成本分佈評估報告 (台新 Nova API 高頻小時級)

本報告包含您的觀察名單（共 36 檔）所有市場持股成本分佈的模擬結果與可信度評估。本報告已徹底排除日 K 線的路徑歧義（Path Ambiguity），改採 **台新證券 Nova API 小時級 K 線（60-Minute Candles）** 進行無歧義籌碼狀態估計。

---

## 一、 觀察名單數據總覽 (2023/05/23 ~ 2026/07)

以下為所有觀察名單股票的最新持股成本分析結果：

| 股票代號與名稱 | 最新收盤價 (元) | 平均成本 (元) | 中位成本 (元) | 最密集籌碼點 POC | 獲利籌碼佔比 | 套牢籌碼佔比 | 模型可信度 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2330 台積電** | 2440.00 | 959.32 | 906.00 | 16.00 (2.5%) | 98.84% | 1.16% | **低 (Low)** |
| **8299 群聯** | 2170.00 | 2316.50 | 2355.00 | 2752.00 (2.6%) | 22.40% | 77.60% | **高 (High)** |
| **8272 全景軟體** | 68.50 | 104.36 | 109.00 | 118.50 (5.1%) | 0.88% | 99.12% | **極高 (Very High)** |
| **7722 LINEPAY** | 306.50 | 543.39 | 590.00 | 591.00 (5.5%) | 8.46% | 91.54% | **極高 (Very High)** |
| **2382 廣達** | 378.00 | 318.14 | 308.00 | 367.50 (1.9%) | 86.76% | 13.24% | **中 (Medium)** |
| **2412 中華電** | 133.50 | 125.35 | 130.00 | 133.50 (4.1%) | 66.60% | 33.40% | **中低 (Medium-Low) - 股權鎖定重** |
| **3034 聯詠** | 467.50 | 468.71 | 484.00 | 481.00 (2.3%) | 40.11% | 59.89% | **中 (Medium)** |
| **2379 瑞昱** | 756.00 | 597.55 | 555.00 | 478.00 (1.7%) | 80.71% | 19.29% | **低 (Low)** |
| **2454 聯發科** | 3825.00 | 2390.85 | 1752.00 | 4340.00 (0.8%) | 74.11% | 25.89% | **低 (Low)** |
| **2480 敦陽科** | 163.50 | 144.64 | 148.00 | 159.50 (3.1%) | 86.65% | 13.35% | **低 (Low)** |
| **2301 光寶科** | 222.00 | 194.69 | 205.70 | 208.00 (1.8%) | 72.68% | 27.32% | **中 (Medium)** |
| **2303 聯電** | 153.50 | 116.37 | 124.30 | 178.30 (2.4%) | 75.72% | 24.28% | **中 (Medium)** |
| **2308 台達電** | 1890.00 | 1196.74 | 1027.00 | 400.00 (0.7%) | 74.57% | 25.43% | **低 (Low)** |
| **2317 鴻海** | 236.50 | 217.59 | 223.50 | 224.00 (1.3%) | 65.57% | 34.43% | **低 (Low)** |
| **2324 仁寶** | 36.65 | 35.64 | 36.00 | 36.60 (4.1%) | 59.45% | 40.55% | **中 (Medium)** |
| **2354 鴻準** | 56.60 | 63.64 | 62.40 | 62.40 (3.2%) | 14.33% | 85.67% | **中 (Medium)** |
| **2356 英業達** | 64.70 | 60.81 | 64.70 | 64.60 (3.3%) | 50.24% | 49.76% | **中 (Medium)** |
| **2357 華碩** | 704.00 | 597.55 | 590.00 | 646.00 (1.8%) | 83.46% | 16.54% | **中 (Medium)** |
| **2376 技嘉** | 335.50 | 316.67 | 327.00 | 386.50 (3.0%) | 57.56% | 42.44% | **高 (High)** |
| **2377 微星** | 149.50 | 130.79 | 137.00 | 148.50 (5.5%) | 98.49% | 1.51% | **中 (Medium)** |
| **2458 義隆** | 183.00 | 159.51 | 163.30 | 191.20 (4.3%) | 74.98% | 25.02% | **中 (Medium)** |
| **3014 聯陽** | 138.00 | 144.52 | 146.50 | 159.00 (4.6%) | 34.01% | 65.99% | **中 (Medium)** |
| **3022 威強電** | 88.30 | 79.68 | 80.70 | 83.80 (3.2%) | 82.54% | 17.46% | **中 (Medium)** |
| **3035 智原** | 213.00 | 207.63 | 211.00 | 214.00 (5.3%) | 60.52% | 39.48% | **極高 (Very High)** |
| **3045 台灣大** | 109.50 | 109.27 | 110.50 | 107.50 (5.8%) | 46.19% | 53.81% | **中低 (Medium-Low) - 股權鎖定重** |
| **3231 緯創** | 143.50 | 151.28 | 147.20 | 185.80 (3.0%) | 38.52% | 61.48% | **高 (High)** |
| **4938 和碩** | 82.60 | 82.67 | 82.40 | 83.50 (1.8%) | 50.77% | 49.23% | **低 (Low)** |
| **6214 精誠** | 141.00 | 129.42 | 129.70 | 141.80 (1.9%) | 75.42% | 24.58% | **低 (Low)** |
| **6231 系微** | 259.50 | 295.40 | 300.50 | 311.50 (4.8%) | 7.86% | 92.14% | **極高 (Very High)** |
| **6285 啟碁** | 259.00 | 269.50 | 269.70 | 269.00 (4.7%) | 34.01% | 65.99% | **極高 (Very High)** |
| **6669 緯穎** | 4960.00 | 4308.26 | 4455.00 | 4925.00 (1.0%) | 70.88% | 29.12% | **中 (Medium)** |
| **6925 意藍** | 59.40 | 97.46 | 80.50 | 79.60 (4.0%) | 2.62% | 97.38% | **極高 (Very High)** |
| **6996 力領科技** | 185.50 | 205.81 | 192.00 | 268.00 (7.5%) | 40.93% | 59.07% | **極高 (Very High)** |
| **7728 光焱科技** | 673.00 | 735.34 | 758.50 | 823.50 (3.4%) | 12.95% | 87.05% | **極高 (Very High)** |
| **7734 印能科技** | 2770.00 | 2535.03 | 2440.00 | 3645.00 (1.8%) | 53.56% | 46.44% | **極高 (Very High)** |
| **7765 中華資安** | 222.50 | 311.88 | 340.00 | 341.00 (16.9%) | 2.72% | 97.28% | **極高 (Very High)** |

---

## 二、 觀察名單高頻籌碼分佈圖 (Carousel)

您可以使用下方 Carousel 快速滑動瀏覽所有觀察名單的小時級持股成本分佈圖：

````carousel
![台積電 2330 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2330_cost_distribution_taishin.png)
<!-- slide -->
![群聯 8299 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/8299_cost_distribution_taishin.png)
<!-- slide -->
![全景軟體 8272 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/8272_cost_distribution_taishin.png)
<!-- slide -->
![LINEPAY 7722 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/7722_cost_distribution_taishin.png)
<!-- slide -->
![廣達 2382 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2382_cost_distribution_taishin.png)
<!-- slide -->
![中華電 2412 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2412_cost_distribution_taishin.png)
<!-- slide -->
![聯詠 3034 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/3034_cost_distribution_taishin.png)
<!-- slide -->
![瑞昱 2379 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2379_cost_distribution_taishin.png)
<!-- slide -->
![聯發科 2454 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2454_cost_distribution_taishin.png)
<!-- slide -->
![敦陽科 2480 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2480_cost_distribution_taishin.png)
<!-- slide -->
![光寶科 2301 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2301_cost_distribution_taishin.png)
<!-- slide -->
![聯電 2303 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2303_cost_distribution_taishin.png)
<!-- slide -->
![台達電 2308 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2308_cost_distribution_taishin.png)
<!-- slide -->
![鴻海 2317 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2317_cost_distribution_taishin.png)
<!-- slide -->
![仁寶 2324 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2324_cost_distribution_taishin.png)
<!-- slide -->
![鴻準 2354 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2354_cost_distribution_taishin.png)
<!-- slide -->
![英業達 2356 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2356_cost_distribution_taishin.png)
<!-- slide -->
![華碩 2357 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2357_cost_distribution_taishin.png)
<!-- slide -->
![技嘉 2376 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2376_cost_distribution_taishin.png)
<!-- slide -->
![微星 2377 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2377_cost_distribution_taishin.png)
<!-- slide -->
![義隆 2458 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/2458_cost_distribution_taishin.png)
<!-- slide -->
![聯陽 3014 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/3014_cost_distribution_taishin.png)
<!-- slide -->
![威強電 3022 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/3022_cost_distribution_taishin.png)
<!-- slide -->
![智原 3035 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/3035_cost_distribution_taishin.png)
<!-- slide -->
![台灣大 3045 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/3045_cost_distribution_taishin.png)
<!-- slide -->
![緯創 3231 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/3231_cost_distribution_taishin.png)
<!-- slide -->
![和碩 4938 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/4938_cost_distribution_taishin.png)
<!-- slide -->
![精誠 6214 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/6214_cost_distribution_taishin.png)
<!-- slide -->
![系微 6231 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/6231_cost_distribution_taishin.png)
<!-- slide -->
![啟碁 6285 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/6285_cost_distribution_taishin.png)
<!-- slide -->
![緯穎 6669 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/6669_cost_distribution_taishin.png)
<!-- slide -->
![意藍 6925 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/6925_cost_distribution_taishin.png)
<!-- slide -->
![力領科技 6996 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/6996_cost_distribution_taishin.png)
<!-- slide -->
![光焱科技 7728 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/7728_cost_distribution_taishin.png)
<!-- slide -->
![印能科技 7734 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/7734_cost_distribution_taishin.png)
<!-- slide -->
![中華資安 7765 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/7765_cost_distribution_taishin.png)
````

報告生成時間：2026-07-14
