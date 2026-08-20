---
title: "SolidAttention: Low-Latency SSD-based Serving on Memory-Constrained PCs"
conference: FAST
year: 2026
status: 待读
---
> IPDADS 的工作
> 
> 地址：https://www.usenix.org/system/files/fast26-zheng.pdf

## 主要解决问题
在只有 8–16GB 可用内存、并且通常 batch=1 的个人电脑(AIPC)上，怎么利用 SSD 存放超长上下文的 KV cache，同时又不让 SSD I/O 把 decode 延迟拖垮。

## Background & Motivation

### Background：超长上下文带来的巨大的 KV cache 存储压力

如下图所示，在 128K 上下文，对于 llama-3.1-8B 来说，其 KV cache 就占用了16GB 的空间，而模型权重例如用 INT4 量化后也才 4GB 空间
![image.png](https://img.195806.xyz/file/1787219018954_image.png)

### Background：KV cache 稀疏性带来的机会
当前工作发现 KV cache 存在一定的稀疏性，也就是部分 token 贡献的权重很大，但是其他token 的 kv cache 贡献较小，因此可以只用某些 token 的 kv cache 来带来客观的精度
- 静态稀疏性：例如只选择最开始的几个 token 和对角线上的 token(StreamLLM)
- 动态稀疏性：保留整个 kv cache，将其切分，并且在计算时动态选择最重要的 token block kv进行计算

### Motivation：SSD-Based KV cache Sparsity
由于超长上下文带来的 KV cache 消耗空间大，所以往往当前工作将 KV cache 放在 SSD，但是放到 SSD 有若干问题
- 如上面的图所示，SSD 的带宽只有大块传输时速度才快（一般需要 256KiB）
- one-batch 场景下，I/O stall 无法被 compute time 来掩盖

**总结：SSD 喜欢“大块、连续、并行”的 I/O，而 sparse attention 恰恰会产生“小块、随机、动态”的 I/O -> “怎么让 sparse attention 变成一种适合 SSD 的 sparse attention？”**

## Design

| 模块                     | 解决的问题                               | 核心思想                                          |
| ---------------------- | ------------------------------------ | --------------------------------------------- |
| KV Consolidator        | SSD I/O 太碎                           | 不扩大 attention block，而是把 K/V 交错存储，放大单次 I/O     |
| Speculative Prefetcher | 选完 KV 才知道该读什么，太晚                     | 用上一 decode iteration 的选择结果预测这一 iteration      |
| SSD-aware Scheduler    | I/O 与 GPU computation 有依赖和 buffer 冲突 | 拆成 DAG microtasks，按 critical path 细粒度 overlap |

对于第一个模块 KV Consolidator：将多个 K/V 向量组织为较大的连续块，并对 K/V 进行 token 级交错布局，使稀疏注意力的细粒度随机访问转化为更适合 SSD 的粗粒度访问。
![image.png](https://img.195806.xyz/file/1787219922510_image.png)

对于第二个模块 Speculative Prefetcher：利用相邻解码步骤中注意力选择结果的时间局部性，提前预测并预取下一层可能使用的 KV block；预测错误时再补载缺失块。(相邻 decode iterations 选择的 KV blocks 平均有大约 81% 重合度。)
![image.png](https://img.195806.xyz/file/1787220093611_image.png)

对于第三个模块 SSD-aware Scheduler：把 attention、FFN、KV 选择、SSD 读取和写回拆分成细粒度任务，根据依赖关系形成 DAG，并复用同步点，在保证一致性的同时重叠 GPU 计算和 SSD I/O。
![image.png](https://img.195806.xyz/file/1787222490621_image.png)
