# Auto-RSS-Digest

🤖 AI-powered RSS digest, automatically generated daily at 07:00 SGT.

## 📰 Latest Digest

👉 [View Full Report](archives/2026-02-02.md)

---

# RSS Digest - 2026-02-02

> 本日共收录 **3** 篇文章，来自 **1** 个分类。
>
> 📊 内容获取统计：LLM直读 0 | Jina Reader 3 | RSS降级 0

---

## Blogs

### [TIL: Running OpenClaw in Docker](https://simonwillison.net/2026/Feb/1/openclaw-in-docker/#atom-everything)
> 来源: simonwillison.net | 发布时间: 2026-02-01 15:59

**核心观点**: 作者分享了在Mac上使用Docker运行OpenClaw AI助手平台的具体配置和管理经验。

**关键要点**:
- 使用Docker Compose配置是部署OpenClaw的推荐方法，涉及一系列初始化设置问题。
- 平台提供Web管理界面和多种管理命令，支持通过Telegram机器人等方式进行交互。
- OpenClaw具备丰富的工具集，包括文件操作、Shell命令执行、网页搜索与抓取以及UI渲染等功能。

---

### [OpenClaw (a.k.a. Moltbot) is everywhere all at once, and a disaster waiting to happen](https://garymarcus.substack.com/p/openclaw-aka-moltbot-is-everywhere)
> 来源: garymarcus.substack.com | 发布时间: 2026-02-01 11:12

**核心观点**: 文章警告称，迅速流行的AI代理系统OpenClaw（又名Moltbot）及其社交网络Moltbook存在严重的安全与隐私漏洞，可能对用户设备和数据构成灾难性风险。

**关键要点**:
- OpenClaw作为基于大语言模型（LLM）的代理级联系统，继承了LLM的幻觉和不可靠性，且被授予了系统级广泛访问权限，极易遭受提示注入等攻击，破坏操作系统原有的安全隔离机制。
- 专为AI代理设计的社交平台Moltbook已成为攻击试验场，研究证实针对AI的操纵攻击有效且可规模化，平台已出现数据库暴露等严重漏洞，使得代理可能被任意控制。
- 作者强烈建议，出于对设备和数据安全的考虑，用户应避免使用OpenClaw，并警惕已安装该软件的设备，因为其可能危及所有在该设备上输入的信息。

---

### [The Browser’s Little White Lies](https://blog.jim-nielsen.com/2026/browsers-white-lies/)
> 来源: blog.jim-nielsen.com | 发布时间: 2026-02-01 11:00

**核心观点**: 浏览器出于隐私保护，对CSS中`:visited`伪类的样式查询进行限制，导致某些选择器（如`:has()`）无法按预期工作。

**关键要点**:
- 浏览器为防止通过CSS样式探测用户历史记录，会限制`:visited`伪类的可用样式，并在某些场景下返回“未访问”的虚假信息。
- 使用`:has(a:visited)`等高级选择器时，浏览器可能统一将元素视为未访问，以阻断隐私泄露漏洞。
- 当CSS因隐私限制无法实现功能时，需转向JavaScript解决方案，这体现了JS在动态交互中的不可替代性。

---

*Generated at 2026-02-02 15:29:06 (SGT)*

---

## 📚 Archives

Browse all daily digests in the [`archives/`](./archives) directory.

## ⚙️ Configuration

- **Schedule**: Daily at 07:00 SGT (23:00 UTC)
- **LLM**: Gemini 2.0 Flash / DeepSeek V3
- **Subscriptions**: See [`feeds.opml`](./feeds.opml)