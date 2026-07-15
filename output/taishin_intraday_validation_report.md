# 觀察名單籌碼持股成本分佈評估報告 (台新 Nova API 高頻小時級)

本報告包含您的觀察名單（共 36 檔）所有市場持股成本分佈的模擬結果與可信度評估。本報告已徹底排除日 K 線的路徑歧義（Path Ambiguity），改採 **台新證券 Nova API 小時級 K 線（60-Minute Candles）** 進行無歧義籌碼狀態估計。

---

## 一、 觀察名單數據總覽 (2023/05/23 ~ 2026/07)

以下為所有觀察名單股票的最新持股成本分析結果：

| 股票代號與名稱 | 最新收盤價 (元) | 平均成本 (元) | 中位成本 (元) | 最密集籌碼點 POC | 獲利籌碼佔比 | 套牢籌碼佔比 | 模型可信度 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2330 台積電** | 2440.00 | 429.50 | 178.00 | 18.00 (30.6%) | 99.64% | 0.36% | **低 (Low)** |
| **8299 群聯** | 2170.00 | 2287.49 | 2347.00 | 2752.00 (2.5%) | 25.49% | 74.51% | **高 (High)** |
| **8272 全景軟體** | 68.50 | 102.88 | 106.00 | 118.50 (4.5%) | 0.93% | 99.07% | **極低 (Very Low) - 新上市歷史過短** |
| **7722 LINEPAY** | 306.50 | 585.96 | 591.00 | 591.00 (5.2%) | 2.99% | 97.01% | **極低 (Very Low) - 新上市歷史過短** |
| **2382 廣達** | 378.00 | 271.68 | 278.00 | 281.50 (1.2%) | 94.71% | 5.29% | **中 (Medium)** |
| **2412 中華電** | 133.50 | 109.01 | 117.50 | 79.50 (13.6%) | 84.24% | 15.76% | **中低 (Medium-Low) - 股權鎖定重** |
| **3034 聯詠** | 467.50 | 468.60 | 484.00 | 382.00 (2.1%) | 41.57% | 58.43% | **中 (Medium)** |
| **2379 瑞昱** | 756.00 | 564.38 | 540.00 | 478.00 (1.7%) | 86.83% | 13.17% | **低 (Low)** |
| **2454 聯發科** | 3825.00 | 1897.57 | 1430.00 | 151.00 (0.7%) | 84.38% | 15.62% | **低 (Low)** |
| **2480 敦陽科** | 163.50 | 147.61 | 149.00 | 159.50 (3.6%) | 86.15% | 13.85% | **低 (Low)** |
| **2301 光寶科** | 222.00 | 165.32 | 167.70 | 208.00 (1.1%) | 85.85% | 14.15% | **中 (Medium)** |
| **2303 聯電** | 153.50 | 86.53 | 67.40 | 178.30 (1.1%) | 88.66% | 11.34% | **中 (Medium)** |
| **2308 台達電** | 1890.00 | 761.13 | 402.00 | 132.00 (5.3%) | 88.16% | 11.84% | **低 (Low)** |
| **2317 鴻海** | 236.50 | 192.30 | 205.50 | 63.00 (1.8%) | 78.24% | 21.76% | **低 (Low)** |
| **2324 仁寶** | 36.65 | 34.31 | 34.40 | 36.60 (3.3%) | 67.88% | 32.12% | **中 (Medium)** |
| **2354 鴻準** | 56.60 | 64.43 | 62.90 | 62.40 (2.9%) | 13.55% | 86.45% | **中 (Medium)** |
| **2356 英業達** | 64.70 | 54.07 | 50.00 | 64.60 (2.5%) | 72.56% | 27.44% | **中 (Medium)** |
| **2357 華碩** | 704.00 | 550.18 | 549.00 | 646.00 (1.2%) | 89.41% | 10.59% | **中 (Medium)** |
| **2376 技嘉** | 335.50 | 301.08 | 301.00 | 342.50 (2.3%) | 71.39% | 28.61% | **高 (High)** |
| **2377 微星** | 149.50 | 129.05 | 134.00 | 148.50 (4.0%) | 94.18% | 5.82% | **中 (Medium)** |
| **2458 義隆** | 183.00 | 155.05 | 153.20 | 191.20 (3.4%) | 80.64% | 19.36% | **中 (Medium)** |
| **3014 聯陽** | 138.00 | 145.50 | 149.00 | 159.00 (5.1%) | 31.07% | 68.93% | **中 (Medium)** |
| **3022 威強電** | 88.30 | 80.40 | 80.10 | 83.80 (2.6%) | 79.33% | 20.67% | **中 (Medium)** |
| **3035 智原** | 213.00 | 208.54 | 211.00 | 214.00 (5.8%) | 58.31% | 41.69% | **極高 (Very High)** |
| **3045 台灣大** | 109.50 | 91.58 | 86.00 | 73.50 (22.7%) | 77.92% | 22.08% | **中低 (Medium-Low) - 股權鎖定重** |
| **3231 緯創** | 143.50 | 145.43 | 143.50 | 185.80 (2.4%) | 50.11% | 49.89% | **高 (High)** |
| **4938 和碩** | 82.60 | 75.37 | 77.80 | 39.90 (4.4%) | 62.35% | 37.65% | **低 (Low)** |
| **6214 精誠** | 141.00 | 127.72 | 129.00 | 133.50 (1.9%) | 76.85% | 23.15% | **低 (Low)** |
| **6231 系微** | 259.50 | 296.24 | 301.00 | 311.50 (5.0%) | 6.51% | 93.49% | **極高 (Very High)** |
| **6285 啟碁** | 259.00 | 256.68 | 265.80 | 269.00 (3.2%) | 44.64% | 55.36% | **極高 (Very High)** |
| **6669 緯穎** | 4960.00 | 4035.73 | 4165.00 | 4145.00 (1.0%) | 77.24% | 22.76% | **中 (Medium)** |
| **6925 意藍** | 59.40 | 96.14 | 79.90 | 79.60 (3.5%) | 4.38% | 95.62% | **極低 (Very Low) - 新上市歷史過短** |
| **6996 力領科技** | 185.50 | 223.05 | 236.00 | 268.00 (5.6%) | 33.61% | 66.39% | **極低 (Very Low) - 新上市歷史過短** |
| **7728 光焱科技** | 673.00 | 609.97 | 710.50 | 823.50 (2.3%) | 40.24% | 59.76% | **極低 (Very Low) - 新上市歷史過短** |
| **7734 印能科技** | 2770.00 | 2109.04 | 1720.00 | 1710.00 (1.8%) | 73.72% | 26.28% | **極低 (Very Low) - 新上市歷史過短** |
| **7765 中華資安** | 222.50 | 317.80 | 332.00 | 341.00 (12.2%) | 1.74% | 98.26% | **極低 (Very Low) - 新上市歷史過短** |

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
