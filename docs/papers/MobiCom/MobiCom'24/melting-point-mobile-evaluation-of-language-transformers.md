---
title: "MELTing Point: Mobile Evaluation of Language Transformers"
conference: MobiCom
---
> 链接：https://arxiv.org/abs/2403.12844
>
> 采用自己设计的MELT测量框架，测试了端侧LLM的吞吐量、温度、能耗等用户使用时较为关心的指标

### Motivation

LLM展现了惊人的智能，但体积庞大，常部署在云端。这会带来隐私泄露和网络依赖的问题。如今已经存在一些性能成熟的端侧设备和轻量级推理框架（如llama.cpp）以及量化技术，这些为端侧LLM的运行带来了可能。作者构建了MELT自动化测试平台，测量了iPhone 14 pro、iPhone SE、Galaxy S23和Pixel 6a这四部设备上运行一些轻量级LLM（参数量从1.1B 到 13B均有）时的对用户体验影响较大的几个指标。

### Design

MELT 的架构如下图所示：

![MELT Architecture](https://img.195806.xyz/file/1787214015202_MELT_pic1.png)

总体的工作流和我们平时的测试流程较为相似，但是文章中的MELT可以将该流程自动化运行，便于实验和分析。

### Models

![Models](https://img.195806.xyz/file/1787214741158_MELT_pic2.png)

实验共测量了5种不同模型。模型运行在llama.cpp和MLC-LLM两种框架上。

### Method

实验具体测试了下列几组关键指标：

吞吐量
分为Prefill吞吐量和Generatio吞吐量。
使用OAAST真实对话数据集（50组多轮对话），让模型像真人聊天一样生成不定长回复（遇到`<EOS>`才停止）。测量端到端的平均生成速度。
为了控制变量，另设一组固定输入/输出长度（各256个tokens）的实验，剔除`<EOS>`干扰，精准测量纯计算速度。

细粒度算子延迟
模型中各核心操作（如反量化、矩阵乘）的耗时占比。
编译开启了`vm_profiler`（性能分析器）的MLC-LLM定制版本，在Galaxy S23手机上单独运行Llama-7B（3-bit）。

能耗与放电率
每次推理的总能耗（mWh）和每生成一个token消耗的电池电量（mAh/token）。
宏观实验（真实对话）执行期间，通过Monsoon高压电源监测仪（5KHz采样）获取手机的实时功率曲线，并结合推理总耗时计算累计能耗。

实时功耗曲线
推理过程中不同阶段（模型加载、预填充、生成）的瞬时功率峰值（W）和波动模式。
抽取 Zephyr-3B（4-bit）模型运行6轮提示词，将功耗数据与自动化脚本记录的日志进行时间轴对齐（已同步时钟防漂移），绘制出彩色波形图。

内存占用
内存分配与GPU计算的重叠度，定位是否因内存带宽不足导致计算单元“饿死”。
在 iPhone 14 Pro 上使用Xcode的Instruments（xctrace）工具进行内存时间线分析，观察GPU利用率是否因等待数据传输而出现大片空白。

模型加载耗时
从点击应用开始到模型权重完全载入内存、可进行首次对话的耗时。
在连续推理的宏观实验中，记录第一次推理开始前的准备阶段时长，考察期间设备是否出现无响应。

持续性能稳定性
连续运行多个推理请求后，吞吐量是否因发热而降频。
让Zephyr-3B在iPhone 14 Pro上连续不停地跑 50 个提示词，观察生成吞吐量随次数的变化趋势，并记录性能拐点位置。

设备温度
推理过程中设备外壳或内部SoC达到的最高温度。
利用Flir One Edge热像仪远距离拍摄，重点关注持续推理后的温度峰值。

量化精度
不同量化位宽（3-bit vs 4-bit）和不同方案（GPTQ vs AWQ）在标准NLP任务上的准确率或评分。
使用LM-Evaluation Harness工具，配合作者自己实现的的接口提取token对数概率，在HellaSwag、Winogrande、TruthfulQA、ARC四个标准测试集上跑分，绘制出“精度-模型大小”权衡曲线。
