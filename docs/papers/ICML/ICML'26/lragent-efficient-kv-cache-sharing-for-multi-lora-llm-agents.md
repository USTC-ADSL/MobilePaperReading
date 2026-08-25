---
title: "LRAgent: Efficient KV Cache Sharing for Multi-LoRA LLM Agents"
conference: ICML
---
首尔大学，ICML 2026，代码已开源。

## 研究背景
场景是在Agent中可能是 plan/action/reflect 等角色共享同一 8B 基座、各挂 LoRA，并反复读取相同工具轨迹，也就是MultiLoRa。带来一个问题：不同的角色带来的 KV cache 没办法直接复用，但是不复用又带来了重复计算的开销

现有工作主要有两种方案:
- 非共享方案：为每个角色保存完整 KV 并重新 prefill；(严重的计算开销)
- 全共享方案(Full-Share)：每个角色直接全部共享所有的 KV cache ，虽然快，却会丢失小而关键的适配器差异。

作者发现，同上下文的 base value cache 高度相似，而 adapter output 几乎不相关（如下图的实线所示），Base cache 相似度都在 0.95 以上，但是 Full Cache 相似度会下降0.03；
因此应共享基座部分、保留 value 侧角色增量。问题是如何在不重算历史的同时维持角色行为；难点在于隐藏状态仍有偏差且可能跨轮累积。假设包括相同基座与分词器、高上下文重叠；BaseLRShared 还要求各 LoRA 共享下投影 A。

![image.png](https://img.195806.xyz/file/1787649867440_image.png)

## 核心方案
如下图所示，Non-Shared即不共享方案不再说明，LoRA 计算：$ (X_iW_0+(X_iA_i)B_i) $
- BaseShared: 每次共享只共享基座模型部分,也就是$X_iW_0$，LoRA Adapter 部分重新计算 
- BaseLRShared: 让不同的 Role 使用的 LoRA Adapter 的 A 相同，那么此时 LoRA 部分的 Cache 也不需要重新经过 Prefill，直接使用即可，减少了 Prefill

![image.png](https://img.195806.xyz/file/1787649626633_image.png)

## 实验结果
精度几乎无损，① BaseShared/BaseLRShared 最大准确率下降分别为 0.67/1.43 个百分点，FullShared 最差下降 5.28；② 吞吐最高提升 1.42×/2.46×；③ TTFT 最高加速 1.63×/4.44×；④ 66.4K 序列显存由 39.84GB 降至 23.99/23.74GB，Non-Shared 已 OOM。

## 相关工作
MobiLoRA(ACL'25) 通过 delta 编码和应用状态感知驱逐优化端侧 LoRA KV，但仅验证 GPU，未利用 shared-A 的跨角色代数共享；Agent-X(MobiSys'26) 通过 prompt 重构和无需 LLM 的 speculative decoding 提升端侧 Agent 效率，关注前缀可复用性而非多 LoRA KV；HeRo(DAC'26) 在 Snapdragon CPU/GPU/NPU 间调度 Agentic RAG 模块，但不处理低秩缓存的语义共享。
