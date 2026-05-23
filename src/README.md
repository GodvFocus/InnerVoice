# Src Structure

`src/app`：应用入口与启动编排

`src/core`：跨模块共享的底层能力，如音频、状态、配置、日志

`src/modules`：按产品功能拆分的业务模块

`src/integrations`：第三方服务接入层，如 ASR、LLM

`src/platform`：平台相关实现，当前以 Windows 为主

`src/shared`：通用工具、类型、常量
