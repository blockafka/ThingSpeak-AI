#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for hermes engine core functionality."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from hermes.engine import (
    _cron_field_match,
    cron_matches,
    _resolve_token,
    build_command,
    _fix_skill_path,
    load_schedules,
)


class TestCronFieldMatch:
    """测试cron字段匹配逻辑。"""

    def test_star_matches_all(self):
        """* 匹配所有值。"""
        assert _cron_field_match("*", 0) is True
        assert _cron_field_match("*", 30) is True
        assert _cron_field_match("*", 59) is True

    def test_exact_match(self):
        """精确匹配。"""
        assert _cron_field_match("5", 5) is True
        assert _cron_field_match("5", 4) is False
        assert _cron_field_match("10", 10) is True

    def test_comma_separated(self):
        """逗号分隔多值匹配。"""
        assert _cron_field_match("1,3,5", 1) is True
        assert _cron_field_match("1,3,5", 3) is True
        assert _cron_field_match("1,3,5", 5) is True
        assert _cron_field_match("1,3,5", 2) is False

    def test_range_match(self):
        """范围匹配。"""
        assert _cron_field_match("1-5", 3) is True
        assert _cron_field_match("1-5", 1) is True
        assert _cron_field_match("1-5", 5) is True
        assert _cron_field_match("1-5", 0) is False
        assert _cron_field_match("1-5", 6) is False

    def test_step_match_star(self):
        """带步长的匹配（从*开始）。"""
        # */5 每5分钟
        assert _cron_field_match("*/5", 0) is True
        assert _cron_field_match("*/5", 5) is True
        assert _cron_field_match("*/5", 10) is True
        assert _cron_field_match("*/5", 3) is False
        assert _cron_field_match("*/5", 7) is False

    def test_step_match_from_base(self):
        """从指定起点开始的步长匹配。"""
        # 2-10/2 从2到10每2
        assert _cron_field_match("2-10/2", 2) is True
        assert _cron_field_match("2-10/2", 4) is True
        assert _cron_field_match("2-10/2", 6) is True
        assert _cron_field_match("2-10/2", 10) is True
        assert _cron_field_match("2-10/2", 3) is False
        assert _cron_field_match("2-10/2", 1) is False

    def test_complex_combination(self):
        """复杂组合测试。"""
        # 1,3,5-10,*/15
        assert _cron_field_match("1,3,5-10,*/15", 0) is True  # */15
        assert _cron_field_match("1,3,5-10,*/15", 1) is True  # 1
        assert _cron_field_match("1,3,5-10,*/15", 3) is True  # 3
        assert _cron_field_match("1,3,5-10,*/15", 7) is True  # 5-10
        assert _cron_field_match("1,3,5-10,*/15", 15) is True  # */15
        assert _cron_field_match("1,3,5-10,*/15", 2) is False


class TestCronMatches:
    """测试完整cron表达式匹配。"""

    def test_daily_at_9am(self):
        """测试每天9点的cron 0 9 * * *。"""
        # 匹配：分=0，时=9，任意日，任意月，任意周
        dt1 = datetime(2024, 1, 1, 9, 0)
        assert cron_matches("0 9 * * *", dt1) is True

        # 分不对
        dt2 = datetime(2024, 1, 1, 9, 1)
        assert cron_matches("0 9 * * *", dt2) is False

        # 时不对
        dt3 = datetime(2024, 1, 1, 8, 0)
        assert cron_matches("0 9 * * *", dt3) is False

    def test_every_10_minutes(self):
        """测试每10分钟。"""
        dt1 = datetime(2024, 1, 1, 10, 0)
        assert cron_matches("*/10 * * * *", dt1) is True
        dt2 = datetime(2024, 1, 1, 10, 10)
        assert cron_matches("*/10 * * * *", dt2) is True
        dt3 = datetime(2024, 1, 1, 10, 5)
        assert cron_matches("*/10 * * * *", dt3) is False

    def test_weekday_morning_9am(self):
        """测试工作日早上9点 0 9 * * 1-5。"""
        # 周一（cron_dow=1）
        dt1 = datetime(2024, 12, 2, 9, 0)  # 这是周一
        assert cron_matches("0 9 * * 1-5", dt1) is True
        # 周六（cron_dow=6）
        dt2 = datetime(2024, 12, 7, 9, 0)  # 周六
        assert cron_matches("0 9 * * 1-5", dt2) is False
        # 周日（cron_dow=0）
        dt3 = datetime(2024, 12, 8, 9, 0)  # 周日
        assert cron_matches("0 9 * * 1-5", dt3) is False

    def test_invalid_cron_wrong_field_count(self):
        """测试字段数不对的cron应该返回False。"""
        assert cron_matches("0 9 * *", datetime.now()) is False
        assert cron_matches("0 9 * * * *", datetime.now()) is False

    def test_sunday_correction(self):
        """测试周日的星期转换是否正确。"""
        # Python datetime isoweekday(): 周日是7 → mod 7 变成 0
        dt = datetime(2024, 12, 8)  # 周日
        assert dt.isoweekday() == 7
        # cron里0匹配周日
        assert cron_matches("* * * * 0", dt) is True
        assert cron_matches("* * * * 7", dt) is False


class TestPlaceholderResolve:
    """测试占位符替换逻辑。"""

    def test_single_placeholder(self):
        """单个占位符替换。"""
        env = {"TEST_VAR": "hello"}
        result = _resolve_token("${TEST_VAR}/path", env)
        assert result == "hello/path"

    def test_multiple_placeholders(self):
        """多个占位符替换。"""
        env = {"VAR1": "foo", "VAR2": "bar"}
        result = _resolve_token("${VAR1}/${VAR2}/file.txt", env)
        assert result == "foo/bar/file.txt"

    def test_missing_placeholder_keeps_intact(self):
        """缺失占位符保留原样。"""
        env = {"EXISTS": "yes"}
        result = _resolve_token("${EXISTS}/${MISSING}", env)
        # 缺失的保留原占位符
        assert result == "yes/${MISSING}"

    def test_empty_env_var_treated_as_missing(self):
        """空字符串视为缺失。"""
        env = {"EMPTY": ""}
        result = _resolve_token("${EMPTY}", env)
        assert result == "${EMPTY}"

    def test_no_placeholders_unchanged(self):
        """没有占位符不改变。"""
        env = {"VAR": "test"}
        result = _resolve_token("fixed/path", env)
        assert result == "fixed/path"


class TestFixSkillPath:
    """测试旧路径兼容转换。"""

    def test_convert_old_path(self):
        """转换旧路径。"""
        old = "hermes/skills/xhs-content-collector/script.py"
        new = _fix_skill_path(old)
        assert new == "skills/xhs_content_collector/script.py"

    def test_already_correct_path_no_change(self):
        """已经正确的路径不变。"""
        correct = "skills/xhs_content_collector/script.py"
        result = _fix_skill_path(correct)
        assert result == correct

    def test_no_xhs_in_path_unchanged(self):
        """不含xhs的路径不变。"""
        other = "skills/other-skill/script.py"
        result = _fix_skill_path(other)
        assert result == other


class TestBuildCommand:
    """测试命令构建功能。"""

    def test_build_command_with_placeholders(self):
        """测试带占位符的命令构建。"""
        schedule = {
            "command": [
                "python",
                "script.py",
                "--output",
                "${OUTPUT_DIR}",
                "--key",
                "${API_KEY}",
            ]
        }
        env = {
            "OUTPUT_DIR": "/output/path",
            "API_KEY": "secret123",
        }
        cmd = build_command(schedule, env)
        assert cmd == [
            "python",
            "script.py",
            "--output",
            "/output/path",
            "--key",
            "secret123",
        ]

    def test_build_command_fixes_old_path(self):
        """测试构建命令时自动修复旧路径。"""
        schedule = {
            "command": [
                "python",
                "hermes/skills/xhs-content-collector/test.py",
            ]
        }
        env = {}
        cmd = build_command(schedule, env)
        assert cmd[1] == "skills/xhs_content_collector/test.py"


class TestLoadSchedules:
    """测试加载schedule配置文件。"""

    def test_load_schedules_returns_dict(self):
        """加载返回字典。"""
        schedules = load_schedules()
        assert isinstance(schedules, dict)
        # 至少有一个示例schedule
        assert "xhs-designers-daily" in schedules
        xhs_sch = schedules["xhs-designers-daily"]
        assert xhs_sch["cron"] == "0 9 * * *"
        assert len(xhs_sch["command"]) > 0
        assert "secrets" in xhs_sch


def run_all_tests():
    """运行所有测试并输出结果。"""
    import inspect
    test_classes = [
        TestCronFieldMatch,
        TestCronMatches,
        TestPlaceholderResolve,
        TestFixSkillPath,
        TestBuildCommand,
        TestLoadSchedules,
    ]

    passed = 0
    failed = 0

    for cls in test_classes:
        methods = [
            m for m in inspect.getmembers(cls, predicate=inspect.isfunction)
            if m[0].startswith('test_')
        ]
        for name, method in methods:
            try:
                method(cls())
                print(f"✓ {cls.__name__}.{name} PASSED")
                passed += 1
            except AssertionError as e:
                print(f"✗ {cls.__name__}.{name} FAILED: AssertionError")
                failed += 1
            except Exception as e:
                print(f"✗ {cls.__name__}.{name} ERROR: {type(e).__name__}: {e}")
                failed += 1

    print(f"\n=== Test Summary: {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
