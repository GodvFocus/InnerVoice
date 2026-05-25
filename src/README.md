# 源码结构

`src/app` — 应用入口与启动编排

`src/core/config` — 配置加载与深度合并

`src/db` — SQLite 初始化与连接管理

`src/modules` — 按产品功能拆分的业务模块

`src/modules/asr` — 音频采集与讯飞 IAT 客户端

`src/modules/hotkey` — 全局热键管理

`src/modules/injector` — 文本注入与焦点恢复

`src/modules/overlay` — 悬浮窗、状态机、状态指示

`src/modules/polish` — 润色客户端与风格管理

`src/shared/types` — 共享类型与状态枚举

`src/ui` — 主窗口与润色风格管理页面
