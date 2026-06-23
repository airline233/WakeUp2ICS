#!/usr/bin/env python3
"""
WakeUpDecoder包装器
提供简化的API接口用于解析WakeUp课程表分享口令
"""
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

# 导入当前目录的wakeup_share_sim模块
try:
    import wakeup_share_sim as sim
    import requests
except ImportError as e:
    raise ImportError(
        f"无法导入WakeUpDecoder模块: {e}\n"
        f"请确保已安装依赖: pip install requests cryptography"
    )


class WakeUpDecoderError(Exception):
    """WakeUpDecoder相关错误的基类"""
    pass


class ConfigError(WakeUpDecoderError):
    """配置错误"""
    pass


class ParseError(WakeUpDecoderError):
    """解析错误"""
    pass


class NetworkError(WakeUpDecoderError):
    """网络请求错误"""
    pass


def extract_share_code(text: str) -> str:
    """
    从分享文案中提取口令

    支持以下格式:
    1. 纯口令: "2bce137ad56d4ad19539c79834647dac"
    2. 分享文案: "这是来自「WakeUp课程表」的课表分享...分享口令为「2bce137ad56d4ad19539c79834647dac」"
    3. URL格式: "http://domain/2bce137ad56d4ad19539c79834647dac"
    4. 书名号包裹: "「2bce137ad56d4ad19539c79834647dac」"

    Args:
        text: 分享文案或口令

    Returns:
        提取的口令字符串

    Raises:
        ParseError: 无法提取有效口令
    """
    # 移除首尾空白
    text = text.strip()

    # 模式1: 匹配「」或『』中的32位十六进制字符串
    match = re.search(r'[「『]([a-f0-9]{32})[」』]', text, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    # 模式2: 匹配URL中的32位十六进制字符串
    match = re.search(r'https?://[^/\s]+/([a-f0-9]{32})', text, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    # 模式3: 如果文本本身就是32位十六进制字符串
    if re.fullmatch(r'[a-f0-9]{32}', text, re.IGNORECASE):
        return text.lower()

    # 模式4: 在文本中搜索任意32位十六进制字符串（作为fallback）
    match = re.search(r'\b([a-f0-9]{32})\b', text, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    raise ParseError(f"无法从文本中提取有效的分享口令: {text[:100]}...")



def parse_wakeup_code(code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析WakeUp课程表分享口令

    Args:
        code: 分享口令或包含口令的分享文案
        config: 配置字典，包含：
            - apk_path: APK文件路径（必需）
            - android_id: Android设备ID（必需）
            - sdk_version: SDK版本（可选，默认35）
            - device_model: 设备型号（可选）
            - device_brand: 设备品牌（可选）
            - screen_size: 屏幕分辨率（可选）
            - cpu_abis: CPU架构（可选）
            - api_host: API服务器地址（可选）
            - antispam_host: 反作弊服务器地址（可选）
            - request_timeout: 请求超时时间（可选）

    Returns:
        解析后的课程表数据字典

    Raises:
        ConfigError: 配置错误
        ParseError: 解析错误
        NetworkError: 网络请求错误
    """
    # 从文本中提取口令
    code = extract_share_code(code)

    # 验证必需配置
    apk_path = config.get("apk_path")
    android_id = config.get("android_id")

    if not apk_path:
        raise ConfigError("缺少必需配置: apk_path")
    if not android_id:
        raise ConfigError("缺少必需配置: android_id")

    apk_path = Path(apk_path)
    if not apk_path.exists():
        raise ConfigError(f"APK文件不存在: {apk_path}")

    # 提取可选配置
    sdk_version = config.get("sdk_version", 35)
    device_model = config.get("device_model", "Pixel 7")
    device_brand = config.get("device_brand", "google")
    screen_size = config.get("screen_size", "1080x2400")
    cpu_abis = config.get("cpu_abis", "arm64-v8a")
    api_host = config.get("api_host", "https://api.wakeup.fun")
    antispam_host = config.get("antispam_host", "https://api.wakeup.fun")
    request_timeout = float(config.get("request_timeout", 15.0))

    try:
        # 步骤1: 解析APK信息
        manifest = sim.parse_manifest_info(apk_path)
        channel = sim.read_apk_text_entry(apk_path, "assets/channel")
        public_token = sim.read_public_token(apk_path)

        if not public_token:
            raise ParseError("无法从APK提取公钥token")

        # 步骤2: 读取签名证书
        signature_chars, cert_entry = sim.read_signature_chars(apk_path)

        # 步骤3: 生成设备标识
        cuid = sim.cuid_from_android_id(android_id)
        adid = sim.adid_from_android_id(android_id)

        # 步骤4: 生成反作弊签名A
        sign_a, rand10, sign_a_plain = sim.make_sign_a(cuid, signature_chars)

        # 步骤5: 构建通用参数
        common_params = sim.make_common_params(
            type('Args', (), {
                'area': '',
                'screensize': screen_size,
                'cuid': cuid,
                'city': '',
                'abis': cpu_abis,
                'channel': channel,
                'app_bit': '64',
                'device_id': '',
                'public_token': public_token,
                'adid': adid,
                'province': '',
                'app_id': 'wakeup',
                'download_type': '1',
                'sdk': sdk_version,
                'device': device_model,
                'brand': device_brand,
                'operatorid': '',
            })(),
            manifest
        )

        # 步骤6: 创建会话
        session = requests.Session()

        # 步骤7: 反作弊验证，获取signB
        antispam_url = antispam_host.rstrip("/") + "/pluto/app/antispam"
        antispam_request = sim.build_antispam_request(sign_a, common_params)

        try:
            antispam_resp = sim.post_form(
                antispam_url,
                antispam_request["body"],
                request_timeout,
                session=session,
                cuid=cuid,
                did='',
                adid=adid
            )
            antispam_resp.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError(f"反作弊验证请求失败: {e}")

        # 步骤8: 从响应提取signB
        try:
            antispam_payload = json.loads(antispam_resp.text)
            candidate = antispam_payload.get("data")
            if isinstance(candidate, dict):
                candidate = candidate.get("data")
            if not isinstance(candidate, str):
                result_obj = antispam_payload.get("result")
                candidate = result_obj.get("data") if isinstance(result_obj, dict) else None
            if not isinstance(candidate, str) or not candidate:
                raise ParseError(f"反作弊响应格式错误: {antispam_resp.text}")
            sign_b = candidate
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            raise ParseError(f"解析反作弊响应失败: {e}")

        # 步骤9: 从signB提取token
        antispam_token, sign_b_plain = sim.token_from_sign_b(sign_b, rand10)

        # 步骤10: 构建分享请求
        share_request = sim.build_share_request(
            code,
            antispam_token,
            manifest["version_code"],
            common_params,
            did=''
        )

        # 步骤11: 发送分享请求
        share_url = api_host.rstrip("/") + "/share_schedule/getv2"
        try:
            share_resp = sim.post_form(
                share_url,
                share_request["body"],
                request_timeout,
                session=session,
                cuid=cuid,
                did='',
                adid=adid
            )
            share_resp.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError(f"分享请求失败: {e}")

        # 步骤12: 解密响应
        decrypted = sim.decrypt_response_data(share_resp.text, share_request["rc4_key"])

        # 步骤13: 返回解密的课程表数据
        if isinstance(decrypted, dict) and "plain_json" in decrypted:
            return decrypted["plain_json"]
        else:
            # 解密失败，尝试直接解析原始响应
            try:
                response_data = json.loads(share_resp.text)
                if response_data.get("errNo") != 0:
                    error_msg = response_data.get("errStr", "未知错误")
                    raise ParseError(f"服务器返回错误: {error_msg}")
            except json.JSONDecodeError:
                pass

            raise ParseError(f"解密课程表数据失败: {decrypted}")

    except (OSError, IOError) as e:
        raise ConfigError(f"读取APK文件失败: {e}")
    except Exception as e:
        if isinstance(e, WakeUpDecoderError):
            raise
        raise ParseError(f"解析过程出现未知错误: {type(e).__name__}: {e}")


def main():
    """测试函数"""
    import os
    from dotenv import load_dotenv

    # 修复Windows控制台编码
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # 加载.env配置
    load_dotenv()

    # 测试配置
    config = {
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

    # 测试口令（从命令行参数或环境变量）
    test_code = sys.argv[1] if len(sys.argv) > 1 else "2bce137ad56d4ad19539c79834647dac"

    print(f"正在解析口令: {test_code}")
    print(f"使用APK: {config['apk_path']}")
    print("-" * 60)

    try:
        result = parse_wakeup_code(test_code, config)
        print("\n✓ 解析成功！\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except WakeUpDecoderError as e:
        print(f"\n✗ 解析失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
