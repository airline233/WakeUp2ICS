# WakeUp2ICS 项目完成总结

## 项目概述

WakeUp2ICS 是一个基于 Python FastAPI 的 Web 服务，用于将 WakeUp 课程表的分享口令转换为标准 ICS（iCalendar）格式文件，可直接导入到任何日历应用。

## 已实现的功能

### ✅ 核心功能
1. **WakeUp口令解析** - 完整实现了WakeUpDecoder的调用，支持APK签名提取、反作弊验证、RC4解密
2. **ICS文件生成** - 符合RFC 5545标准的iCalendar格式
3. **时间智能处理** - 自动读取课程表的时间表和学期开始日期
4. **Web API服务** - FastAPI框架，支持多种调用方式

### ✅ API端点

| 端点 | 方法 | 说明 | 示例 |
|------|------|------|------|
| `/{code}` | GET | 简洁路径调用，直接返回ICS | `http://127.0.0.1:8888/2bce137ad56d4ad19539c79834647dac` |
| `/parse` | POST | 仅解析，返回JSON数据 | 用于调试和查看原始数据 |
| `/generate-ics` | POST | 高级自定义生成ICS | 支持自定义学期开始日期、提醒时间 |
| `/health` | GET | 健康检查 | 用于监控服务状态 |
| `/docs` | GET | Swagger API文档 | 自动生成的交互式文档 |

### ✅ 数据处理特性

1. **完整的时间表支持**
   - 自动读取课程表中每个节次的开始/结束时间
   - 无需手动配置作息时间
   - 支持多达60个节次的定义

2. **智能日期计算**
   - 自动从WakeUp数据中读取学期开始日期
   - 根据周次和星期准确计算每节课的实际日期
   - 处理跨周课程（为每周生成独立事件）

3. **自定义时间处理**
   - 支持 `ownTime` 字段的课程（如考试）
   - 优先使用自定义时间，而非标准节次时间

4. **完整课程信息**
   - 课程名称、教师、教室
   - 周次、节次信息
   - 15分钟提前提醒（可配置）

## 测试验证

### ✅ 测试覆盖

```
测试1: 解析器测试 - ✓ 通过
  - APK信息提取
  - 反作弊签名生成
  - 网络请求和数据解密

测试2: ICS生成器测试 - ✓ 通过
  - 数据解析
  - 时间映射
  - ICS格式生成

测试3: API服务测试 - ✓ 通过
  - 健康检查
  - 解析接口
  - ICS生成接口
```

### ✅ 时间准确性验证

1. **标准节次时间** ✓
   - 例：第3-4节 = 10:10-11:50（来自时间表node 3和4）

2. **日期计算** ✓
   - 学期开始：2026-03-02（周一）
   - 第1周周四：2026-03-05 ✓

3. **自定义时间** ✓
   - 考试时间正确使用ownTime字段

## 项目结构

```
WakeUp2ICS/
├── .env                  # 配置文件
├── .env.example          # 配置模板
├── .gitignore           # Git忽略规则
├── requirements.txt      # Python依赖
├── README.md            # 项目文档
├── app.py               # FastAPI主程序 (287行)
├── decoder.py           # WakeUpDecoder包装器 (267行)
├── ics_generator.py     # ICS生成器 (277行)
└── test.py              # 测试套件 (185行)
```

## 配置说明

### 必需配置
- `APK_PATH` - WakeUp APK文件路径（用于提取签名）
- `ANDROID_ID` - 16位十六进制设备ID

### 可选配置
- `SDK_VERSION`, `DEVICE_MODEL`, `DEVICE_BRAND` - 设备参数
- `API_HOST`, `ANTISPAM_HOST` - API服务器地址
- `REMINDER_MINUTES` - 上课提醒时间（默认15分钟）
- `HOST`, `PORT` - Web服务监听地址（默认127.0.0.1:8888）

### 无需配置
- ❌ ~~`SEMESTER_START_DATE`~~ - 自动从课程表数据读取
- ❌ ~~`TIME_SLOTS`~~ - 自动从课程表数据读取

## 使用方法

### 启动服务
```bash
python app.py
```

### 方式1：浏览器直接访问（推荐）
```
http://127.0.0.1:8888/<你的分享口令>
```

### 方式2：命令行下载
```bash
curl http://127.0.0.1:8888/2bce137ad56d4ad19539c79834647dac -o schedule.ics
```

### 方式3：POST请求（高级）
```bash
curl -X POST http://127.0.0.1:8888/generate-ics \
  -H "Content-Type: application/json" \
  -d '{"code": "你的分享口令"}' \
  --output schedule.ics
```

## 技术栈

- **Web框架**: FastAPI 0.104+
- **HTTP服务器**: Uvicorn
- **日历库**: icalendar 5.0+
- **加密库**: cryptography 41.0+
- **HTTP客户端**: requests 2.31+
- **配置管理**: python-dotenv 1.0+
- **时区支持**: pytz

## 依赖项目

- [WakeUpDecoder](https://github.com/airline233/WakeUpDecoder) - 提供口令解析算法

## 已知问题

无已知问题。所有核心功能正常工作。

## 后续扩展方向

1. ✨ Web界面 - 添加简单的HTML前端
2. ✨ 批量导入 - 支持多个口令合并为一个ICS
3. ✨ Docker部署 - 提供Dockerfile
4. ✨ 缓存优化 - 缓存APK解析结果，提升响应速度
5. ✨ 多学期支持 - 在URL中指定学期参数

## 许可证

本项目遵循 Apache 2.0 许可证。

## 致谢

- WakeUpDecoder 项目提供的解析算法
- FastAPI 框架
- icalendar 库

---

**项目状态**: ✅ 已完成并通过所有测试

**最后更新**: 2026-06-23
