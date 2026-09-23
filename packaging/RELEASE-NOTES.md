Windows x64 and macOS Apple Silicon desktop preview / 桌面预览版

- Windows: download the windows-x64 ZIP, extract the whole folder, open Epivra.exe.
- macOS 14+ Apple Silicon: download the macos-arm64 DMG, drag Epivra into Applications.
- No separately installed Python, Git, Node.js or database is required.
- The first launch opens connection settings. Enter your own provider API key.
- OCR document parsing and Docker analysis are independent optional components in Settings.
  Docker Desktop must be installed separately. Optional downloads can require several GB.
- Application files and user data are separate. Quit Epivra before replacing the app.
- These downloads have no publisher certificate or Apple notarization. OS warnings are expected.
  Do not disable system security globally. Organizations that require signed apps should wait for a signed release.
- Native build checks cover launch, relocation, duplicate launch, authentication, parser subprocesses,
  Tk availability, shutdown and restart. They do not establish research-report quality.

Windows：完整解压 ZIP，双击 Epivra.exe。
macOS：打开 DMG，将 Epivra 拖入“应用程序”。仅支持 Apple Silicon，系统版本 14 或以上。
基础功能无需安装开发环境。首次在界面配置自己的供应商密钥，API 调用可能收费。
OCR 和 Docker 分析按需准备；Docker Desktop 需单独安装。当前为未签名、未公证预览版。
更新前请退出应用并备份数据目录。数据位置与详细步骤见仓库使用说明。
