# Market Research Brief (Insight Monitor)

[English](README.md) | **简体中文**

[![Verify](https://github.com/Zhang-ZhengHao/market-research-brief/actions/workflows/verify.yml/badge.svg)](https://github.com/Zhang-ZhengHao/market-research-brief/actions/workflows/verify.yml)

Market Research Brief 可将最多 5 份用户粘贴资料整理成一份可复核的研究简报。它保留资料顺序和连续原文证据，并支持导出 Markdown、JSON 或 ZIP 研究项目包。内置示例全部为合成内容。本项目是作品集演示，不是网页抓取、事实核验或生产级研究系统。

![仅粘贴资料版操作界面](screenshots/overview.png)

## 能力与证据

- 仅提供两种资料模式：明确标注的合成示例和用户粘贴正文。
- 参考链接只是用户提供的元数据，应用不会访问或验证该链接。
- 默认规则整理不需要 API key，也不会请求模型服务。
- 报告保留资料标题、输入顺序和有长度上限的连续原文证据片段。
- 支持 Markdown、JSON 和 ZIP；ZIP 内包含 project.json 与 report.md。
- 结果只存在于当前 Streamlit 会话，除非用户主动下载。
- 可选的 OpenAI 兼容模型汇总由服务端显式开启，并保留规则回退。

| 可核查行为 | 实现与测试 |
| --- | --- |
| 1–5 份资料、顺序和字符限制 | services/sources.py、tests/test_sources.py |
| 参考链接只做语法规范化且不触网 | services/reference_links.py、tests/test_sources.py、tests/test_productization.py |
| 连续原文证据与规则回退 | services/report.py、tests/test_report.py |
| 模型来源索引对齐且不发送参考链接 | services/model_client.py、tests/test_model_client.py |
| Markdown、JSON、确定性 ZIP 导出 | services/export.py、tests/test_export.py |
| 双模式界面与版本身份 | app.py、tests/test_app.py、tests/test_version.py |

这些测试证明实现行为和资料对齐，不证明资料本身权威，也不保证结论正确。

## 五分钟演示

1. 选择一个合成模板，或切换到「粘贴正文」。
2. 按需要对照的顺序填写 1–5 份资料。
3. 可选填 HTTP(S) 参考链接；应用不会打开、解析域名或验证它。
4. 生成报告，逐份查看标题、摘要、日期线索和连续原文证据。
5. 下载 Markdown、JSON，或包含 project.json 与 report.md 的 ZIP 项目包。

内置模板全部为合成内容，不代表实时市场事实。发布或决策前，必须根据粘贴原文核对日期、数字、引述和商业结论。

## 资料与网络边界

资料导入过程不会解析域名、打开套接字或访问参考链接。参考链接仅接受不含登录凭据的 HTTP(S) 语法，移除 fragment 后作为未验证元数据保存；链接可能指向任何位置，浏览器打开前仍应视为不可信。

默认规则模式不会请求模型服务。只有部署者显式开启真实 AI 并配置服务端密钥后，已载入的资料标题和正文才会发送至指定模型服务；参考链接不会进入模型提示词。使用前应核对该服务的费用、留存、数据驻留和隐私政策。

生成前会执行以下限制：

- 每次 1–5 份粘贴资料；
- 单份最多 12,000 字符；
- 单次报告合计最多 40,000 字符。

## 本地运行

需要 Python 3.10 或更高版本：

    python3 -m venv .venv
    . .venv/bin/activate
    python3 -m pip install -r requirements-dev.txt
    python3 -m streamlit run app.py

平台托管通过 start.sh 从 PORT 环境变量读取端口，并绑定 0.0.0.0：

    PORT=8501 bash start.sh

该进程仍是开发式演示服务，只应运行在可信主机。正式部署需要补充身份认证、TLS 终止和平台级控制。

### 可选模型模式

默认规则模式不需要密钥。真实 AI 只有在服务端同时启用功能开关并配置密钥后才可用：

    export INSIGHT_MONITOR_AI_ENABLED=1
    export OPENAI_API_KEY="替换为服务端密钥"
    export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
    export OPENAI_MODEL="gpt-4o-mini"                    # 可选

不要提交凭据。密钥仅由服务端进程读取，不会显示在页面中。

## 验证

GitHub Actions 使用 Python 3.10 和 3.12。安装开发依赖后可在本地执行同样检查：

    PYTHONPATH=. python3 -m pytest -q tests
    python3 -m compileall -q app.py services tests
    python3 -m pip check

版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## 交付边界

这是客户演示和作品集实现，不包含身份认证、租户隔离、持久存储、审计日志、后台任务、配额、计费、高可用、备份、生产监控或事实准确性保证。

使用客户资料前，应取得处理授权、完成脱敏、核对可选模型服务政策，并要求人工根据粘贴原文复核报告。

## License

本项目采用 MIT License，见 [LICENSE](LICENSE)、[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 [SECURITY.md](SECURITY.md)。
