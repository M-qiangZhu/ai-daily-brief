# AI Daily Brief 🤖📰

每日 AI 资讯聚合日报，自动抓取全球 AI 新闻、研究博客和技术媒体，生成精美网页并推送至 QQ。

## 🌟 特性

- **多源聚合**：自动抓取 20+ 个顶级 AI 信息源
  - 🏢 大模型公司官方（OpenAI、Anthropic、DeepMind 等）
  - 👨‍🔬 顶级研究员（Karpathy、Lilian Weng、Simon Willison 等）
  - 📰 技术媒体（HN 中文、AI Hub Today）
  - 🇨🇳 国内 AI 媒体（机器之心、量子位、新智元等）

- **精美网页**：现代化暗色主题设计，响应式布局
- **自动部署**：GitHub Actions 定时构建，自动发布到 GitHub Pages
- **即时推送**：生成后自动推送 QQ 消息通知

## 🚀 快速开始

### 本地运行

```bash
# 克隆仓库
git clone <your-repo-url>
cd ai-daily-brief

# 安装依赖
pip install -r requirements.txt

# 生成日报
python main.py

# 查看生成的网页
open dist/index.html
```

### GitHub Pages 部署

1. Fork 本仓库
2. 启用 GitHub Pages（Settings → Pages → Source: GitHub Actions）
3. GitHub Actions 将每天 08:00 (CST) 自动生成并部署

## 📁 项目结构

```
ai-daily-brief/
├── config/
│   └── sources.yaml          # 数据源配置
├── src/
│   ├── fetcher.py            # 内容抓取
│   └── generator.py          # HTML 生成
├── templates/
│   └── newsletter.html.j2    # 网页模板
├── .github/workflows/
│   └── deploy.yml            # 自动部署
├── main.py                   # 主入口
└── README.md
```

## ⚙️ 配置

编辑 `config/sources.yaml` 添加/修改数据源：

```yaml
sources:
  my_source:
    name: "Source Name"
    url: "https://example.com"
    type: "rss"  # 或 "web" 用于网页抓取
    rss_url: "https://example.com/feed.xml"
    category: "media"
    enabled: true
```

## 📊 输出示例

生成的日报包含：
- 📈 统计概览（文章数、分类、来源）
- 📑 按分类组织的文章卡片
- 🔗 直达原文的链接
- ⏰ 发布时间信息

## 🔗 在线示例

部署后访问：`https://<your-username>.github.io/ai-daily-brief/`

## 📝 定时任务

GitHub Actions 默认每天 08:00 (CST) 运行。如需修改：

编辑 `.github/workflows/deploy.yml`：
```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 时间 00:00 = CST 08:00
```

## 🤝 贡献

欢迎提交 PR 添加新的数据源或改进功能！

## 📄 License

MIT License
