---
title: "Act Before It's Too Late: Power-Efficient LLM Inference on Mobile Device"
conference: Mobisys
---
> 地址：https://dl.acm.org/doi/pdf/10.1145/3745756.3809208
> 
> 作者: BUPT 郑霄龙课题组

## 总结

> 如何在基本不牺牲 LLM 推理延迟和模型精度的情况下，显著降低手机端 LLM inference 的功耗。

手机端 LLM 推理并不是 GPU 一直在连续计算。相反，在大量连续 kernel 之间，存在非常频繁的 GPU stall。TurboInfer 的核心就是在这些 stall 出现时及时降低 GPU frequency，在真正的 kernel computation 开始时再迅速升频。

## Motivation

### Motivation1: On-device LLM 的功耗已经成为实际瓶颈

在同一个任务上，从一个约 4.86M 参数的小模型增长到 3B 参数的 RedPajama 时，能耗增长约 36 倍。Gemma2-2B、RedPajama-3B 等 LLM 与 social media、music、short video、shopping 等普通手机 App 相比，功耗高出 3.11×–6.15×；
![image.png](https://img.195806.xyz/file/1787225379327_image.png)

### Motivaiton2（核心）：GPU 实际上有大量 stall

GPU 工作负载不是连续矩形，而是大量短 kernel 和大量短 idle/stall 交错出现。如下图所示，在推理过程中，Kernel Runtiming 可以看到，其中存在大量的 GPU Stalls，但是 Default DVFS 却一直维持最高水平，主要原因是 DVFS 无法发现这些 stall。
![image.png](https://img.195806.xyz/file/1787224692719_image.png)

#### GPU stall 原因1：Host-controlled execution pipeline

在手机的 SoC 中，CPU 是 host，GPU 更多是一个执行后端。每执行一个 GPU kernel，CPU 通常需要：
- 准备 operator metadata；
- 设置 tensor pointer；
- 准备 command；
- submit GPU work；
- GPU 再从 shared system memory 中读取需要的数据。

因此 kernel A 结束以后，kernel B 并不一定能够立即执行。GPU 很可能需要等待：CPU prepare → command submission → tensor/data ready。(Server GPU一般没这个情况，因为其一般拥有：更独立的 GPU memory； HBM； 更强的执行自治能力；因此 kernels 更容易 back-to-back execution。)

#### GPU stall 原因2：Shared DRAM architecture
手机的 SoC 架构导致CPU、GPU 等处理器共同使用 system DRAM。因此 GPU 要读取：model weights、activations、KV cache、input tensor时可能和其他 processing units 争抢 memory bandwidth。GPU 计算单元即使已经准备好了，如果数据还没进入 cache / memory hierarchy，也只能等待。

因此：GPU stall ≠ GPU 没工作可做。而是: GPU stall = GPU 此时不能有效执行 arithmetic instructions。

这一区分直接决定了 TurboInfer 为什么要看 PMU instruction count，而不能只看 conventional utilization。

### Motivation3: GPU 越快，stall ratio 可能越高
随着 mobile GPU computation capability 增强，stall ratio 反而可能升高。

### Motivation4：Stall 不只发生在 kernel 之间，也发生在 token 之间
生成 token (t) 后，系统需要进行： KV cache update； 将新的 KV cache 写入 DRAM； sampling； attention mask update； 为下一token 做准备。

这些都可能造成 GPU idle。Paper 中经过测试在低端的处理器上大约有 600ms 的延迟，随着模型变大，这个数据还进一步增长

## Design

### Requirement 1：Fine-grained workload sensing
必须知道 GPU 在 毫秒甚至微秒级到底在不在做真正 computation。

解决方案：AGI、Perfetto、Snapdragon Toolkit 等 profiling 工具实际上已经可以提供很精细的 GPU information，但是这些工具都是 offline 的工具，也就是执行完毕后提供数据，不符合 real-time 的需求。为了拿到准确的 PMU 的指令数据，Paper 修改了 Android kernel，拿到了 GPU 的寄存器数据。

### Requirement 2：Fine-grained frequency actuation
Frequency 调整时间必须比 stall 时间短
![image.png](https://img.195806.xyz/file/1787228927208_image.png)
解决方案：作者发现 Android thermal framework 会对 frequency request 做 aggregation，典型的时间为 80ms（存疑，我们自己测试时间没有这么长），所以 paper 在 kernel level 注册一个： custom cooling device 然后把 frequency control command 直接通过 IOCTL 连接到 KGSL。
### Requirement 3：Runtime adaptivity
最佳频率会随着模型、后台 App 数量、内存大小变化，所以需要动态调整
![image.png](https://img.195806.xyz/file/1787228757806_image.png)
解决方案：定义了一个变量: 指令数/频率，用于表示 workload 强度，如果该变量较大，说明当前频率较低，如果较小，说明当前频率过高；并且如上图所示，不同模型和不同的空闲内存对应的最佳的 Sweet spot 也不同。
### Requirement 4：Controller 本身必须极轻量
如果一个 kernel 只有 1ms，而 controller 自己算 2ms，那么系统优化反而成为 overhead。

解决方案：Tube-based Model Predictive Control（TMPC）,不仅看当前状态决定 action，而是预测未来几个时间点的状态，然后选择一个未来整体看来最优的控制 sequence。(该部分较为复杂，不展开了)

## Evaluation

实验平台： OnePlus8 and Samsung GalaxyNote 10. 功耗测量使用 Monsoon High Voltage Power Monitor（998 美元）https://www.msoon.com/online-store/High-Voltage-Power-Monitor-p90002590

模型选择：1.5B-3B

Baseline: Default DVFS;zTT(Freq 调控策略)
![image.png](https://img.195806.xyz/file/1787229415297_image.png)
