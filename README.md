# WakeUp2ICS - WakeUp课程表转ICS日历服务

将WakeUp课程表的分享口令转换为标准ICS日历文件的Web API服务。

## 功能特性

- 🔓 解析WakeUp课程表分享口令
- 📅 生成标准iCalendar (ICS) 格式文件
- 🌐 RESTful API接口
- ⚙️ 灵活的配置选项
- 📱 支持导入到任何日历应用（Google Calendar、Outlook、Apple Calendar等）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

**必需配置**：
- `APK_PATH`: WakeUp APK文件路径（用于提取签名信息）
- `ANDROID_ID`: 16位十六进制设备ID（如 `0000000000000000`）

**注意**：学期开始日期会自动从课程表数据中读取，无需配置 `SEMESTER_START_DATE`。

### 3. 启动服务

```bash
python app.py
```

或使用uvicorn：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动。

## API使用

### 方式1: 简洁路径调用（推荐）

直接访问 `http://domain:port/<分享口令>` 即可获取ICS文件：

```bash
# 浏览器直接访问
http://127.0.0.1:62778/2bce137ad56d4ad19539c79834647dac

# 或使用curl下载
curl http://127.0.0.1:62778/2bce137ad56d4ad19539c79834647dac -o schedule.ics
```

### 方式2: POST接口（高级自定义）

#### 2.1 解析课程表（仅获取JSON）

```bash
curl -X POST http://localhost:62778/parse \
  -H "Content-Type: application/json" \
  -d '{"code": "你的分享口令"}'
```

#### 2.2 生成ICS文件（自定义参数）

```bash
curl -X POST http://localhost:62778/generate-ics \
  -H "Content-Type: application/json" \
  -d '{
    "code": "你的分享口令",
    "semester_start": "2024-09-01",
    "reminder_minutes": 15
  }' \
  --output schedule.ics
```

### 方式3: 健康检查

```bash
curl http://localhost:62778/health
```

## API文档

启动服务后访问：
- Swagger UI: `http://localhost:62778/docs`
- ReDoc: `http://localhost:62778/redoc`

## 使用示例

### 快速开始

启动服务后，直接在浏览器访问：

```
http://127.0.0.1:62778/你的分享口令
```

浏览器会自动下载 `schedule.ics` 文件，可直接导入到：
- Google Calendar
- Apple Calendar (iCal)
- Outlook
- 其他支持iCalendar格式的日历应用

### 命令行使用

```bash
# 下载ICS文件
curl http://127.0.0.1:62778/2bce137ad56d4ad19539c79834647dac -o mycourse.ics

# 查看课程表JSON数据
curl -X POST http://127.0.0.1:62778/parse \
  -H "Content-Type: application/json" \
  -d '{"code": "你的分享口令"}'
```

## 配置说明

### 必需配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| APK_PATH | WakeUp APK文件路径 | `WakeUp课程表_6.1.70.apk` |
| ANDROID_ID | Android设备ID | `0000000000000000` |

**注意**：学期开始日期和作息时间会自动从课程表数据中读取，无需手动配置。

### 可选配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| SDK_VERSION | Android SDK版本 | `35` |
| DEVICE_MODEL | 设备型号 | `Pixel 7` |
| DEVICE_BRAND | 设备品牌 | `google` |
| API_HOST | WakeUp API地址 | `https://api.wakeup.fun` |
| REQUEST_TIMEOUT | 请求超时时间（秒） | `15.0` |
| REMINDER_MINUTES | 上课前提醒时间（分钟） | `15` |
| SEMESTER_START_DATE | 覆盖课程表的学期开始日期（可选） | `2024-09-01` |
| HOST | 服务监听地址 | `127.0.0.1` |
| PORT | 服务监听端口 | `62778` |

## 项目结构

```
WakeUp2ICS/
├── .env.example          # 配置模板
├── .env                  # 实际配置（不入库）
├── .gitignore           # Git忽略文件
├── requirements.txt      # Python依赖
├── app.py               # FastAPI主程序
├── decoder.py           # WakeUpDecoder包装模块
├── ics_generator.py     # ICS文件生成器
└── README.md            # 本文件
```

## 依赖项目

本项目依赖 [WakeUpDecoder](https://github.com/airline233/WakeUpDecoder) 提供核心的口令解析功能。

## 常见问题

### Q: 如何获取WakeUp APK？

从官方渠道或应用商店下载WakeUp课程表应用的APK文件。

### Q: ANDROID_ID填什么？

请填写使用过WakeUp课程表的设备的Android ID（可使用DevCheck查看），否则会命中反作弊

### Q: 生成的ICS文件无法导入？

1. 确认学期开始日期配置正确
2. 检查课程时间是否超出合理范围
3. 尝试使用不同的日历应用导入

### Q: 提示网络错误？

检查：
1. API_HOST配置是否正确
2. 网络连接是否正常
3. 防火墙设置

## 许可证

本项目遵循 Apache 2.0 许可证。

## 致谢

感谢 GPT-5.5 的逆向支持
感谢 opus-4.8 完成本项目
