---
title: "ReMoE: Boosting Expert Reuse through Router Fine-Tuning in
  Memory-Constrained MoE LLM Inference"
conference: ICML
---
> 地址：https://arxiv.org/pdf/2605.27081
>
> 北航和华为联合的工作

## Motivation

ReMoE 不减少一个 token 激活多少 expert，也不裁剪 expert；减少的是相邻 token 之间 expert working set 的变化速度。

![image.png](https://img.195806.xyz/file/1787212730931_image.png)

### 主要原因：训练目标和端侧部署目标不一致

MoE 训练时一般希望 expert load balance,鼓励不同 token 尽量分散到各个 expert 上，这对于 expert parallel training 很合理，因为不希望某几个 expert overloaded。但是对于端侧部署，却不希望分散很大，比较希望短时间内用的 expert 集中在若干个里。所以 ReMoE 做了微调，直接把原来的 load-balancing loss 关闭，并接受 inference-time expert utilization 更不均衡

## Evaluation

微调后，expert 的重叠度上升，准确率下降不大，从而得到了明显的吞吐上的收益

实验平台：RTX 3090 & Jetson 

模型选择：DeepSeek-V2-Lite & Qwen1.5-MoE-A2.7B

![image.png](https://img.195806.xyz/file/1787213225056_image.png)
