---
title: "SolidAttention: Low-Latency SSD-based Serving on Memory-Constrained PCs"
conference: FAST
year: 2026
status: 待读
---
* KV Consolidator：将多个 K/V 向量组织为较大的连续块，并对 K/V 进行 token 级交错布局，使稀疏注意力的细粒度随机访问转化为更适合 SSD 的粗粒度访问。
* Speculative Prefetcher：利用相邻解码步骤中注意力选择结果的时间局部性，提前预测并预取下一层可能使用的 KV block；预测错误时再补载缺失块。
- SSD-aware Scheduler：把 attention、FFN、KV 选择、SSD 读取和写回拆分成细粒度任务，根据依赖关系形成 DAG，并复用同步点，在保证一致性的同时重叠 GPU 计算和 SSD I/O。
