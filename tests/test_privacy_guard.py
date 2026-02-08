"""Repository privacy guard tests."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 仅扫描版本库已跟踪文件，避免本地未提交临时文件干扰检查。
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".sqlite",
    ".sqlite3",
    ".db",
}
SKIP_FILES = {"uv.lock"}

SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "email",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ),
    (
        "cn_mobile",
        re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    ),
    (
        "cn_id_card",
        re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    ),
    (
        "private_key_block",
        re.compile(r"BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY"),
    ),
    (
        "aws_access_key",
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ),
    (
        "google_api_key",
        re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    ),
    (
        "precise_coordinate_pair",
        re.compile(r"(?<!\d)-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}(?!\d)"),
    ),
    (
        "city_level_timezone",
        re.compile(r"\b(?:Asia|Europe|America|Australia|Africa)/[A-Za-z_]+\b"),
    ),
    (
        "street_level_address",
        re.compile(r"[\u4e00-\u9fffA-Za-z0-9]{0,24}(?:路|街|道|巷|弄)\d{1,5}号"),
    ),
)

SENSITIVE_CONTEXT_PATTERN = re.compile(
    r"(location_name|from_location_name|to_location_name|raw_name|raw_thoroughfare|"
    r"tags|note|remark|address|locality|sublocality)",
    re.IGNORECASE,
)
QUOTED_LITERAL_PATTERN = re.compile(r"""["']([^"'\n]{2,40})["']""")
HAS_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
COMMON_CN_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢"
    "邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛"
    "雷贺倪汤殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛"
    "汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾"
    "路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘"
    "缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程嵇邢滑裴陆荣翁荀羊於惠甄"
    "曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊"
    "宫宁仇栾暴甘厉戎祖武符刘景詹束龙叶司韶郜黎蓟薄印宿白怀蒲台从鄂索咸籍"
    "赖卓蔺屠蒙池乔阴胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛"
    "寿通边扈燕冀浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨"
    "居衡步都耿满弘国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷辛阚那"
    "简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"
)
PERSON_NAME_PATTERN = re.compile(rf"^[{COMMON_CN_SURNAMES}][\u4e00-\u9fff]{{1,2}}$")
LOCATION_SUFFIX_PATTERN = re.compile(
    r"[\u4e00-\u9fff]{2,24}(?:省|市|区|县|镇|乡|村|路|街|道|巷|弄|号|"
    r"花园|小区|社区|广场|大厦|中心|公寓|机场|车站|地铁站|高铁站)$"
)
SAFE_LITERAL_HINTS = (
    "示例",
    "未知",
    "测试",
    "中国",
    "中文",
    "某某",
)


def test_repository_contains_no_sensitive_literals() -> None:
    findings: list[str] = []
    for file_path in _iter_tracked_text_files():
        text = _read_text(file_path)
        if text is None:
            continue

        for label, pattern in SENSITIVE_PATTERNS:
            for match in pattern.finditer(text):
                findings.append(
                    f"{_rel(file_path)} | {label} | {match.group(0)[:32]}"
                )

        findings.extend(_scan_suspect_chinese_literals(file_path, text))

    assert not findings, "Privacy guard failed:\n" + "\n".join(sorted(findings))


def _iter_tracked_text_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    files: list[Path] = []
    for line in result.stdout.splitlines():
        rel_path = line.strip()
        if not rel_path:
            continue
        if rel_path in SKIP_FILES:
            continue
        path = ROOT / rel_path
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        files.append(path)
    return files


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _scan_suspect_chinese_literals(file_path: Path, text: str) -> list[str]:
    findings: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not SENSITIVE_CONTEXT_PATTERN.search(line):
            continue

        for match in QUOTED_LITERAL_PATTERN.finditer(line):
            literal = match.group(1).strip()
            if not literal:
                continue
            if not HAS_CJK_PATTERN.search(literal):
                continue
            if any(hint in literal for hint in SAFE_LITERAL_HINTS):
                continue
            if _is_suspect_cn_literal(literal):
                findings.append(
                    f"{_rel(file_path)}:{line_no} | suspect_cn_literal | {literal[:32]}"
                )

    return findings


def _is_suspect_cn_literal(literal: str) -> bool:
    if PERSON_NAME_PATTERN.fullmatch(literal):
        return True
    if LOCATION_SUFFIX_PATTERN.search(literal):
        return True
    return False
