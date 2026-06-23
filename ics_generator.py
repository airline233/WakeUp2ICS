#!/usr/bin/env python3
"""
ICS文件生成器
将WakeUp课程表数据转换为iCalendar格式
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from icalendar import Calendar, Event, Alarm
import pytz


class ICSGeneratorError(Exception):
    """ICS生成器错误"""
    pass


def parse_wakeup_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析WakeUp返回的原始数据

    Args:
        raw_data: 从decoder.py获取的原始数据

    Returns:
        解析后的结构化数据
    """
    share_data_str = raw_data.get("shareData", "")
    if not share_data_str:
        raise ICSGeneratorError("数据中缺少shareData字段")

    # shareData是多个JSON对象用换行连接的字符串
    lines = share_data_str.strip().split('\n')
    if len(lines) < 4:
        raise ICSGeneratorError("shareData格式不正确")

    # 解析各部分
    meta = json.loads(lines[0])  # 课程表元信息
    time_table = json.loads(lines[1])  # 时间表（节次对应的时间）
    schedule_info = json.loads(lines[2])  # 学期信息
    courses = json.loads(lines[3])  # 课程信息
    course_items = json.loads(lines[4])  # 课程安排

    return {
        "meta": meta,
        "time_table": time_table,
        "schedule_info": schedule_info,
        "courses": courses,
        "course_items": course_items
    }


def generate_ics(
    schedule_data: Dict[str, Any],
    semester_start: Optional[str] = None,
    reminder_minutes: int = 15,
    timezone: str = "Asia/Shanghai"
) -> bytes:
    """
    生成ICS文件

    Args:
        schedule_data: 课程表数据（从decoder.py获取）
        semester_start: 学期开始日期，格式YYYY-MM-DD（可选，从数据中读取）
        reminder_minutes: 上课前多少分钟提醒
        timezone: 时区

    Returns:
        ICS文件的字节内容
    """
    # 解析数据
    try:
        parsed = parse_wakeup_data(schedule_data)
    except (json.JSONDecodeError, KeyError) as e:
        raise ICSGeneratorError(f"解析课程数据失败: {e}")

    meta = parsed["meta"]
    time_table = parsed["time_table"]
    schedule_info = parsed["schedule_info"]
    courses = parsed["courses"]
    course_items = parsed["course_items"]

    # 获取学期开始日期
    if not semester_start:
        # 从数据中读取startDate
        start_date_str = schedule_info.get("startDate", "")
        if start_date_str:
            # 格式可能是 "2026-3-2"
            try:
                semester_start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                try:
                    semester_start_date = datetime.strptime(start_date_str, "%Y-%#m-%#d")
                except ValueError:
                    raise ICSGeneratorError(f"无法解析学期开始日期: {start_date_str}")
        else:
            raise ICSGeneratorError("未指定学期开始日期，且数据中也没有")
    else:
        try:
            semester_start_date = datetime.strptime(semester_start, "%Y-%m-%d")
        except ValueError:
            raise ICSGeneratorError(f"学期开始日期格式错误: {semester_start}，应为YYYY-MM-DD")

    # 构建时间表映射（节次 -> (开始时间, 结束时间)）
    time_map = {}
    for slot in time_table:
        node = slot["node"]
        start_time = slot["startTime"]
        end_time = slot["endTime"]
        time_map[node] = (start_time, end_time)

    # 构建课程映射（id -> 课程信息）
    course_map = {}
    for course in courses:
        course_map[course["id"]] = course

    # 创建日历
    cal = Calendar()
    cal.add('prodid', '-//WakeUp2ICS//Course Schedule//CN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', schedule_info.get("tableName", "课程表"))
    cal.add('x-wr-timezone', timezone)

    # 设置时区
    tz = pytz.timezone(timezone)

    # 为每个课程安排生成事件
    for item in course_items:
        course_id = item.get("id")
        if course_id is None or course_id not in course_map:
            continue

        course_info = course_map[course_id]
        course_name = course_info.get("courseName", "未命名课程")

        # 获取基本信息
        day_of_week = item.get("day")  # 1=周一, 7=周日
        start_week = item.get("startWeek")
        end_week = item.get("endWeek")
        start_node = item.get("startNode")
        step = item.get("step", 1)
        room = item.get("room", "")
        teacher = item.get("teacher", "")

        if not all([day_of_week, start_week, end_week, start_node]):
            continue

        # 计算节次范围
        end_node = start_node + step - 1

        # 获取时间
        if start_node not in time_map or end_node not in time_map:
            continue

        start_time_str, _ = time_map[start_node]
        _, end_time_str = time_map[end_node]

        # 检查是否使用自定义时间
        if item.get("ownTime"):
            start_time_str = item.get("startTime", start_time_str)
            end_time_str = item.get("endTime", end_time_str)

        # 为每个上课周生成一个事件
        for week in range(start_week, end_week + 1):
            # 计算日期
            # week=1表示第一周，day_of_week=1表示周一
            days_offset = (week - 1) * 7 + (day_of_week - 1)
            event_date = semester_start_date + timedelta(days=days_offset)

            # 解析时间
            try:
                start_hour, start_minute = map(int, start_time_str.split(':'))
                end_hour, end_minute = map(int, end_time_str.split(':'))
            except (ValueError, AttributeError):
                continue

            # 创建开始和结束时间
            start_dt = tz.localize(event_date.replace(hour=start_hour, minute=start_minute))
            end_dt = tz.localize(event_date.replace(hour=end_hour, minute=end_minute))

            # 创建事件
            event = Event()
            event.add('summary', course_name)
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)

            if room:
                event.add('location', room)

            # 构建描述
            description_parts = []
            if teacher:
                description_parts.append(f"教师: {teacher}")
            description_parts.append(f"第{week}周")
            description_parts.append(f"第{start_node}节" if step == 1 else f"第{start_node}-{end_node}节")
            event.add('description', '\n'.join(description_parts))

            # 添加提醒
            if reminder_minutes > 0:
                alarm = Alarm()
                alarm.add('action', 'DISPLAY')
                alarm.add('description', f'{course_name}即将开始')
                alarm.add('trigger', timedelta(minutes=-reminder_minutes))
                event.add_component(alarm)

            # 添加到日历
            cal.add_component(event)

    # 返回ICS内容
    return cal.to_ical()


def main():
    """测试函数"""
    import sys
    import os
    from dotenv import load_dotenv
    from decoder import parse_wakeup_code

    # 修复Windows控制台编码
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # 加载配置
    load_dotenv()

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

    # 测试口令
    test_code = sys.argv[1] if len(sys.argv) > 1 else "2bce137ad56d4ad19539c79834647dac"

    print(f"正在解析口令: {test_code}")

    # 解析课程表
    from decoder import parse_wakeup_code, WakeUpDecoderError
    try:
        schedule_data = parse_wakeup_code(test_code, config)
    except WakeUpDecoderError as e:
        print(f"解析失败: {e}")
        sys.exit(1)

    print("✓ 解析成功，正在生成ICS文件...")

    # 生成ICS
    try:
        semester_start = os.getenv("SEMESTER_START_DATE")
        reminder_minutes = int(os.getenv("REMINDER_MINUTES", "15"))

        ics_content = generate_ics(
            schedule_data,
            semester_start=semester_start,
            reminder_minutes=reminder_minutes
        )

        # 保存到文件
        output_file = "schedule.ics"
        with open(output_file, "wb") as f:
            f.write(ics_content)

        print(f"✓ ICS文件已生成: {output_file}")
        print(f"  文件大小: {len(ics_content)} 字节")

    except ICSGeneratorError as e:
        print(f"生成ICS失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
