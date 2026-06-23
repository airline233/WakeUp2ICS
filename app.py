#!/usr/bin/env python3
"""
WakeUp2ICS - FastAPI Web服务
将WakeUp课程表分享口令转换为ICS日历文件
"""
import os
import sys
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 导入本地模块
from decoder import parse_wakeup_code, WakeUpDecoderError, ConfigError, ParseError, NetworkError
from ics_generator import generate_ics, ICSGeneratorError

# 修复Windows控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="WakeUp2ICS API",
    description="将WakeUp课程表分享口令转换为ICS日历文件",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局配置
DECODER_CONFIG = {
    "apk_path": os.getenv("APK_PATH", "../WakeUpDecoder/WakeUp课程表_6.1.70.apk"),
    "android_id": os.getenv("ANDROID_ID", "0000000000000000"),
    "sdk_version": int(os.getenv("SDK_VERSION", "35")),
    "device_model": os.getenv("DEVICE_MODEL", "Pixel 7"),
    "device_brand": os.getenv("DEVICE_BRAND", "google"),
    "screen_size": os.getenv("SCREEN_SIZE", "1080x2400"),
    "cpu_abis": os.getenv("CPU_ABIS", "arm64-v8a"),
    "api_host": os.getenv("API_HOST", "https://api.wakeup.fun"),
    "antispam_host": os.getenv("ANTISPAM_HOST", "https://api.wakeup.fun"),
    "request_timeout": float(os.getenv("REQUEST_TIMEOUT", "15.0")),
}

DEFAULT_SEMESTER_START = os.getenv("SEMESTER_START_DATE", None)  # None表示从数据中读取
DEFAULT_REMINDER_MINUTES = int(os.getenv("REMINDER_MINUTES", "15"))


# 请求模型
class ParseRequest(BaseModel):
    code: str = Field(..., description="WakeUp课程表分享口令")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "2bce137ad56d4ad19539c79834647dac"
            }
        }


class GenerateICSRequest(BaseModel):
    code: str = Field(..., description="WakeUp课程表分享口令")
    semester_start: Optional[str] = Field(None, description="学期开始日期（YYYY-MM-DD格式），留空则从课程表数据中读取")
    reminder_minutes: Optional[int] = Field(15, description="上课前提醒时间（分钟）")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "2bce137ad56d4ad19539c79834647dac",
                "semester_start": "2024-09-01",
                "reminder_minutes": 15
            }
        }


# 响应模型
class SuccessResponse(BaseModel):
    success: bool = True
    data: dict

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "schedule_name": "我的课程表",
                    "courses": []
                }
            }
        }


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "解析失败",
                "detail": "无效的分享口令"
            }
        }


# API端点
@app.get("/", tags=["基础"])
async def root():
    """根路径，返回API信息"""
    return {
        "name": "WakeUp2ICS API",
        "version": "1.0.0",
        "description": "将WakeUp课程表分享口令转换为ICS日历文件",
        "docs": "/docs",
        "usage": {
            "simple": "GET /<分享口令> - 直接获取ICS文件",
            "advanced": "POST /generate-ics - 自定义参数生成ICS"
        },
        "example": "http://127.0.0.1:8888/2bce137ad56d4ad19539c79834647dac"
    }


@app.get("/health", tags=["基础"])
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/parse", response_model=SuccessResponse, tags=["解析"])
async def parse_schedule(request: ParseRequest):
    """
    解析WakeUp课程表分享口令，返回JSON格式的课程数据

    - **code**: WakeUp课程表分享口令
    """
    try:
        # 解析课程表
        schedule_data = parse_wakeup_code(request.code, DECODER_CONFIG)

        return {
            "success": True,
            "data": schedule_data
        }

    except ConfigError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "配置错误", "detail": str(e)}
        )
    except NetworkError as e:
        raise HTTPException(
            status_code=503,
            detail={"success": False, "error": "网络请求失败", "detail": str(e)}
        )
    except ParseError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "解析失败", "detail": str(e)}
        )
    except WakeUpDecoderError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "内部错误", "detail": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "未知错误", "detail": str(e)}
        )


@app.post("/generate-ics", tags=["生成"])
async def generate_ics_file(request: GenerateICSRequest):
    """
    解析WakeUp课程表分享口令并生成ICS日历文件

    - **code**: WakeUp课程表分享口令
    - **semester_start**: 学期开始日期（YYYY-MM-DD格式），留空则从课程表数据中读取
    - **reminder_minutes**: 上课前提醒时间（分钟），默认15分钟

    返回ICS文件，可直接导入日历应用
    """
    try:
        # 解析课程表
        schedule_data = parse_wakeup_code(request.code, DECODER_CONFIG)

        # 生成ICS
        semester_start = request.semester_start or DEFAULT_SEMESTER_START
        reminder_minutes = request.reminder_minutes if request.reminder_minutes is not None else DEFAULT_REMINDER_MINUTES

        ics_content = generate_ics(
            schedule_data,
            semester_start=semester_start,
            reminder_minutes=reminder_minutes
        )

        # 返回ICS文件
        return Response(
            content=ics_content,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=schedule.ics"
            }
        )

    except ConfigError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "配置错误", "detail": str(e)}
        )
    except NetworkError as e:
        raise HTTPException(
            status_code=503,
            detail={"success": False, "error": "网络请求失败", "detail": str(e)}
        )
    except ParseError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "解析失败", "detail": str(e)}
        )
    except ICSGeneratorError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "生成ICS失败", "detail": str(e)}
        )
    except WakeUpDecoderError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "内部错误", "detail": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "未知错误", "detail": str(e)}
        )


@app.get("/{code:path}", tags=["生成"])
async def generate_ics_by_path(code: str):
    """
    通过路径参数解析WakeUp课程表分享口令并生成ICS日历文件

    直接访问: http://domain:port/<分享口令或完整分享文案>

    支持以下格式:
    1. 纯口令: http://domain/2bce137ad56d4ad19539c79834647dac
    2. 完整文案: 将整段分享文案作为URL路径参数

    - **code**: WakeUp课程表分享口令或完整分享文案（路径参数）

    返回ICS文件，可直接导入日历应用
    """
    try:
        # 解析课程表
        schedule_data = parse_wakeup_code(code, DECODER_CONFIG)

        # 生成ICS
        semester_start = DEFAULT_SEMESTER_START
        reminder_minutes = DEFAULT_REMINDER_MINUTES

        ics_content = generate_ics(
            schedule_data,
            semester_start=semester_start,
            reminder_minutes=reminder_minutes
        )

        # 返回ICS文件
        return Response(
            content=ics_content,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=schedule.ics"
            }
        )

    except ConfigError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "配置错误", "detail": str(e)}
        )
    except NetworkError as e:
        raise HTTPException(
            status_code=503,
            detail={"success": False, "error": "网络请求失败", "detail": str(e)}
        )
    except ParseError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "解析失败", "detail": str(e)}
        )
    except ICSGeneratorError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "生成ICS失败", "detail": str(e)}
        )
    except WakeUpDecoderError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "内部错误", "detail": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "未知错误", "detail": str(e)}
        )


# 启动服务
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print(f"🚀 启动WakeUp2ICS服务...")
    print(f"   监听地址: http://{host}:{port}")
    print(f"   API文档: http://{host}:{port}/docs")
    print(f"   调试模式: {'开启' if debug else '关闭'}")
    print()

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
