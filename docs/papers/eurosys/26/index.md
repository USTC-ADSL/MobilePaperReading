---
title: "AIMS: Cost-Efficient LLM-Based Agent Deployment in Hybrid Cloud-Edge
  Environments"
conference: Eurosys
---
> 地址:https://dl.acm.org/doi/pdf/10.1145/3767295.3803622
>
> Tag: 端云协同、最小化 API 开销、Agent
>
> UA 和微软的联合工作

## Motivation

对比的主要工作是:HybridLLM(ICLR'23)，其主要思想是将整个任务通过路由判断是 Easy 还是 Hard，然后使用端侧 SLM 或者用云端 LLM 全权处理。

### Motivation 1: HybridLLM导致了严重的精度下降

由于HybridLLM 独立判断每个子任务的难度，然后进行任务分配，这样会导致 Agent 的 workflow 发生变化，最终导致精度的下降

### Motivation 2: 不同位置的 Subtask 的路由会造成不同影响

在 Agent workflow 中，子任务不同位置的 assignment 也会造成不同影响，将 LLM subtask 换成 SLM 所导致的平均 accuracy drop 从 Early 的 5.25%，增加到 Middle 的 7.59%、Late 的 9.53%。

### Motivation 3: SLM 路径虽然不同，但可能“重新汇合”

作者发现 SLM 通常会比 LLM 把任务拆得更细。例如 LLM：L1-> L2 -> L3

而 SLM 可能：S1 -> S2 -> S3 -> S4 -> S5
不能因为 S2 和 L2 不同，就立刻认为 SLM 已经失败。
可能存在: S4 约等于L2，也就是说 SLM 多走了两步，但是最终又回到了和 LLM 类似的状态。
AIMS 因而定义了一个非常核心的指标：`S-L distance` 表示一个 LLM subtask，需要再走多少个 SLM subtask，才能找到语义相似的状态。

## Design

Goal: max SLM Usage s.t. Accruacy

- URC(user request classifier）:判断一个任务是否能整个交给 SLM
- SSE: 判断当前一步用 SLM / LLM，下一步是否会产生类似结果
- SLE: 当前不一样，但 SLM 多走几步以后是否可以追上 LLM
- CD: 往未来 look ahead，寻找 SLM/LLM trajectory convergence
- SD: 如果还是不行，把复杂 subtask 拆成更简单的 sub-subtask
- LLM fallback: 上面都无法证明 SLM 安全，才真正调用 cloud LLM

每一个判断都是基于离线收集 SLM/LLM agent trajectory，然后训练一套小 estimator，最后URC 和 distance predictor 基于 ModernBERT；两个 subtask predictor 和 subtask decomposer 基于 Qwen3-0.6B + LoRA。整个 estimator stack 大约需要 2 GB VRAM

## 几个值得思考的问题

1. 该论文首先结果是基于5090+Cloud API 的，5090 的推理速度较快，所以 AIMS 的推理速度大约是13.33s，相对于All-LLM 的15.82s 要快，和 All-SLM 的11.14s 对比较慢；但是，本文还做了在 iPhone15 的测试，其 AIMS 的推理速度快速退化到了2.5 倍的 All-LLM。说明这个工作是 model-aware/workflow-aware 但是不是 resource-aware，其对端侧的资源利用以及云端的 prefix cache 的复用都没有做优化
2. 这个工作主要是做的 max SLM usage s.t. accuracy,但是真实情况应该是在保证准确率和 Latency 的 SLO 的前提下，最小化 cost，因此在 RTX 5090 上，“多跑 SLM”碰巧既便宜又快；但 iPhone 上，“多跑 SLM”就变成便宜但慢。
3. 最后准确度的分析有点像 AI 算法的工作的分析，F1 score 或者对比 Embedding 的余弦相似度并不能表明是否一定准确可用，只有在纯文本的 agent 可能可以表示正确性，但是对于 tool-use agent，该 metric 无法表示准确度。
4. 本文没有os-runtime 的 mechanism，主要是纯粹的算法的工作
