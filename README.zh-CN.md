# Market Research Brief (Insight Monitor)

[English](README.md) | **简体中文**

把少量公开资料整理成一份可复核、可交付的研究项目。它适合小企业运营、内容团队、市场顾问和产品经理做竞品速览、行业周报或内容选题预研。

> 这是一个可现场演示的公开案例，不是事实核验服务，也不承诺经营结果。示例资料全部为合成内容。

![Insight Monitor 操作页](screenshots/overview.png)

## 五分钟演示

1. 选择「竞品速览」「行业周报」或「内容选题」模板。
2. 载入合成示例，或粘贴最多 5 份正文；也可以填写最多 5 个公开 http/https 地址。
3. 生成报告，逐份查看标题、日期线索、读取状态和连续原文证据片段。
4. 下载 Markdown、JSON，或下载一个包含 project.json 与 report.md 的研究项目包。

研究项目只在当前浏览器会话中生成，不建立账号、服务端历史数据库或定时任务。导出的项目元数据方便交付给客户或继续人工复核。

## 能力边界

- 只处理用户主动提供的公开 URL 或粘贴正文；不会自动搜索全网、登录、绕过付费墙、抓取社交平台或自动发送消息。
- URL 在连接前做 scheme、凭据、DNS 和地址分类检查；回环、私网、链路本地、保留和多播地址会被拒绝，重定向逐跳复验。
- 每个网页响应默认最多读取 2 MB；连接超时、总处理时间、重定向次数和资料数量都有上限。
- 原文证据片段来自本地提取到的连续文本；模型不能替失败来源补写证据。
- 报告中的判断仍需打开来源原文人工核对，尤其是数字、日期、引述和商业结论。

## 真实 AI（默认关闭）

默认使用无需密钥的规则汇总，适合公开演示。真实 AI 必须由部署者显式打开，并同时配置模型密钥。

    export INSIGHT_MONITOR_AI_ENABLED=1
    export OPENAI_API_KEY="替换为你的密钥"
    export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
    export OPENAI_MODEL="gpt-4o-mini"                    # 可选

每次 AI 汇总最多处理 5 份资料、合计 40,000 字符。开启前请确认模型服务的费用、数据留存和跨境合规政策；页面不会展示或保存密钥。

## 本地运行

Python 3.10+：

    python -m venv .venv
    . .venv/bin/activate              # Windows 可使用 .venv/Scripts/activate
    pip install -r requirements-dev.txt
    streamlit run app.py

平台托管使用 start.sh：它从 PORT 环境变量读取端口并绑定 0.0.0.0。正式产品清单见 app.toml。

## 测试与质量门槛

    pytest -q tests
    python -m compileall -q app.py services tests

发布前应在干净的 Python 环境中重复运行这两项检查。

## 交付边界

这个案例适合按模块报价：资料清洗、模板定制、报告字段调整和导出格式扩展。它不包含真实店铺凭证、多租户权限、支付、消息推送、服务端历史数据库或事实核验承诺。客户提供真实资料前，应先完成脱敏并确认外部模型政策。

## License

本项目采用 MIT License，见 LICENSE。第三方依赖与归属见 THIRD_PARTY_NOTICES.md，安全问题请按 SECURITY.md 联系。
