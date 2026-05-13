# AI Judge 商业变现方案

> 你已选定 Open-Core BSL 许可。以下是具体的变现路径分析。

---

## 方案对比总览

| 方案 | 用户获取 | 转化率预期 | 收入天花板 | 适合阶段 |
|------|---------|-----------|-----------|---------|
| **A: 联系方式 + 人工销售** | 慢 | 5-15% | 高（企业合同） | 现在 |
| **B: AI 支付链接（Stripe/Lemon Squeezy）** | 快 | 1-3% | 中（自助购买） | 1-2 周后 |
| **C: 混合（两者兼有）** | 最快 | 分层转化 | 最高 | **推荐** |

---

## 方案 A：留联系方式 + 人工对接（现在就可以做）

### 做法

在 landing page 和 README 底部放置：

```html
<!-- CTA 区块 -->
<div class="cta-contact">
  <h3>Get Production Access</h3>
  <p>Community tier is free for evaluation.
     For Personal ($49), Team ($199), or Enterprise deployment,
     reach out directly.</p>
  <p>📧 <strong>your@email.com</strong></p>
  <p>💬 <a href="https://discord.gg/ai-judge">Discord Community</a></p>
  <p>🐦 <a href="https://twitter.com/yourhandle">Twitter DM</a></p>
</div>
```

### 优势
- **零技术依赖** — 不需要 Stripe 账号、不需要支付集成
- **高客单价可能** — 人工对接可以了解真实需求，向上销售 Enterprise
- **建立关系** — 早期用户的人肉反馈比自动转化更有价值
- **立即生效** — 今天 push 代码，今天就能收到邮件

### 劣势
- 转化率低（用户需要主动联系你）
- 无法自动化（你得亲自回复）
- 缺少"冲动购买"路径（用户看到 $49 想立刻买，但找不到按钮）

### 适合场景
- 你还没注册 Stripe / Lemon Squeezy
- 你想先验证需求再建支付
- 你的目标客单价 >$199（企业用户不会自助购买）

---

## 方案 B：AI 支付链接（1 周内可上线）

### 做法

使用 **Lemon Squeezy**（推荐，开箱即用）或 **Stripe Payment Links**：

#### Lemon Squeezy 三步走

1. 注册 [lemonsqueezy.com](https://lemonsqueezy.com)（5 分钟）
2. 创建 3 个产品：
   - Personal License → $49 one-time
   - Team License → $199 one-time
   - Enterprise → "Contact us"
3. 在 landing page 嵌入支付链接：

```html
<a href="https://yourstore.lemonsqueezy.com/checkout/..." 
   class="btn btn-primary">Buy License — $49</a>
```

#### 为什么推荐 Lemon Squeezy 而非 Stripe

| | Lemon Squeezy | Stripe |
|---|---|---|
| 注册难度 | 5 分钟，无需公司 | 需要公司信息 |
| 税务处理 | 自动处理全球 VAT/GST | 需要自己配置 |
| 中国用户 | 支持支付宝/微信 | 需要额外集成 |
| 手续费 | 5% + $0.50 | 2.9% + $0.30 |
| 许可 Key 发放 | 需自己写 webhook | 需自己写 webhook |

**注意**：无论用哪个，License Key 的自动发放都需要你写一个简单的 webhook 服务（或手动发 key）。这是 BSL 模式的技术成本。

### 优势
- 用户看到价格可以立即购买
- 自动化，无需你手动回复每一单
- Lemon Squeezy 支持中国支付方式

### 劣势
- 需要注册外部服务
- License Key 发放需要技术实现
- 自助购买的平均客单价低（$49 而非 $199+）

---

## 方案 C：混合变现（推荐）

### 具体做法

在 landing page 上同时放置两个 CTA：

```
┌──────────────────────────────────────────────┐
│          Get AI Judge                         │
│                                               │
│  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Community       │  │  Personal        │     │
│  │  Free             │  │  $49 one-time    │     │
│  │  Evaluation only  │  │  2 machines       │     │
│  │  [GitHub]         │  │  [Buy Now →]     │     │
│  └─────────────────┘  └─────────────────┘     │
│                                               │
│  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Team            │  │  Enterprise      │     │
│  │  $199 one-time   │  │  Custom           │     │
│  │  5 machines       │  │  SSO · SLA        │     │
│  │  [Buy Now →]     │  │  [Contact Us →]   │     │
│  └─────────────────┘  └─────────────────┘     │
│                                               │
│  📧 your@email.com  ·  💬 Discord             │
└──────────────────────────────────────────────┘
```

### 为什么混合作

- Community 免费 → 获取 GitHub star + 社区口碑
- Personal $49 → Lemon Squeezy 自助（冲动购买）
- Team $199 → Lemon Squeezy 自助
- Enterprise → 人工对接（高客单价必须有人聊）

### 时间线

| 阶段 | 做什么 | 耗时 |
|------|-------|------|
| **今天** | GitHub 发布，README 放联系方式 | 0 |
| **本周** | 注册 Lemon Squeezy，创建产品 | 1 天 |
| **下周** | 在 landing page 加支付链接 | 1 天 |
| **视需求** | 建 webhook 自动发 License Key | 2-3 天 |

---

## 我的建议

**先走方案 A（今天就能上线），再逐步迁移到方案 C。**

理由：
1. 你现在连一个付费用户都没有，不要花时间建支付流程
2. 先让社区版在 GitHub 上积累 star，验证需求
3. 如果有人主动联系你说"我想买"，那就是最强的产品信号
4. 等到有 3-5 个人问你怎么买的时候，再花半天建 Lemon Squeezy

---

## Landing Page 上的具体 CTA 文案

我推荐在 landing page 底部放以下内容（具体联系方式留给你填）：

```html
<div class="pricing">
  <div class="plan">
    <h3>Community</h3>
    <div class="price">Free</div>
    <ul>
      <li>Full CLI + docs</li>
      <li>Swift bridge source</li>
      <li>Docker packaging</li>
      <li>GitHub Issues support</li>
    </ul>
    <a href="https://github.com/reguorider-gif/ai-judge" class="btn">GitHub</a>
  </div>

  <div class="plan featured">
    <h3>Personal</h3>
    <div class="price">$49</div>
    <ul>
      <li>Everything in Community</li>
      <li>9-seat jury runs</li>
      <li>Full audit artifacts</li>
      <li>2 machines</li>
      <li>Email support</li>
    </ul>
    <a href="#" class="btn primary">Coming Soon</a>
  </div>

  <div class="plan">
    <h3>Team / Enterprise</h3>
    <div class="price">$199+</div>
    <ul>
      <li>Execution Council</li>
      <li>5+ machines</li>
      <li>Custom seats</li>
      <li>SSO · SLA</li>
    </ul>
    <a href="mailto:your@email.com" class="btn">Contact Us</a>
  </div>
</div>
```

---

## 总结

| 你需要决定的事 | 建议 |
|--------------|------|
| Landing page 上放什么 CTA？ | 放联系方式 + "Coming Soon" 按钮 |
| 要不要马上建支付？ | 不要。先验证需求 |
| 用 Stripe 还是 Lemon Squeezy？ | 到时候用 Lemon Squeezy（支持中国支付） |
| License Key 怎么自动发？ | 等有 3-5 个付费用户后再建 webhook |
| 价格要不要改？ | $49/$199/$Custom 保持，但先不收钱 |
