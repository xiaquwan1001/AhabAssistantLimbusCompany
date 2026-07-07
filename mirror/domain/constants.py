"""
AALC 常量定义

集中管理魔法数字和字符串，提高可读性与可维护性。
所有涉及缩放的计算放一个地方，避免散布在代码各处。
"""

from module.config import cfg

# ── 缩放相关 ──

# 基准分辨率宽度（参考设计值）
BASE_RESOLUTION_WIDTH = 1440

# 有些模块（如 select_theme_pack, search_road）使用 1080 基准
BASE_RESOLUTION_WIDTH_ALT = 1080


def get_scale(base: int = BASE_RESOLUTION_WIDTH) -> float:
    """返回当前窗口缩放比例因子（相对于基准分辨率）。

    调用示例:
        scale = get_scale()           # cfg.set_win_size / 1440
        scale = get_scale(1080)        # cfg.set_win_size / 1080
    """
    return cfg.set_win_size / base


# ── 各模块通用坐标偏移（scale 相关，供替换 190 * scale 等） ──

# 商店饰品网格：两列，x 间距
SHOP_GIFT_COLUMN_STEP = 190
SHOP_GIFT_ROW_STEP = 190
SHOP_GIFT_COLUMNS = 5

# 商店右侧偏移（从 shop_coins 位置计算）
SHOP_FIRST_GRID_OFFSET_X = 150
SHOP_REFRESH_STEP = 300
SHOP_COMMODITY_PER_LINE = 4

# 寻路相关偏移
ROAD_SETTING_OFFSET_X = 200

# 星光选择偏移
STARLIGHT_ROW_SPACING = 480

# ── 循环/重试次数常量 ──

# 镜牢主循环
MIRROR_MAIN_LOOP = 250

# 通用循环
DEFAULT_LOOP = 30
SHORT_LOOP = 15
MIN_LOOP = 10

# 购买重试
BUY_RETRY_CHANCES = 10
BUY_AGGRESSIVE_RETRY = 5

# 合成循环
FUSE_LOOP_TIMES = 15
FUSE_STARLIGHT_CHANCES = 5

# 识别计数
SCREENSHOT_RETRIES = 5

# 按钮点击次数
EVENT_CLICK_TIMES = 6
BLANK_CLICK_TIMES = 3

# 关键词刷新确认重试
KEYWORD_CONFIRM_RETRIES = 3

# 技能替换次数上限
SKILL_REPLACEMENT_MAX = 3

# 事件次数阈值
EVENT_HANDLING_THRESHOLD = 5

# ── 等待时间（秒）──
# 使用命名常量替代散落的 sleep() 调用

WAIT = {
    "SHORT": 0.5,
    "MEDIUM": 1.0,
    "LONG": 2.0,
    "VERY_LONG": 3.0,
    "EXTRA_LONG": 4.0,
    "POST_PURCHASE": 1.0,
    "POST_REFRESH": 3.0,
    "POST_FUSE": 2.0,
    "CLICK_INTERVAL": 0.5,
    "SCREENSHOT_RETRY": 0.75,
    "ROAD_NAVIGATE": 1.25,
}

# ── OCR / 识别阈值 ──

OCR_DEFAULT_THRESHOLD = 0.85
HIGH_THRESHOLD = 0.9
LOW_THRESHOLD = 0.78
FUSE_THRESHOLD = 0.97
GENERAL_THRESHOLD = 0.75

# 寻路 road.png 匹配阈值
ROAD_MATCH_THRESHOLD = 0.65

# ── 寻路常量 ──

# 默认最短路径长度（像素）
DEFAULT_MIN_PATH_LENGTH = 50

# 中线阈值
MID_LINE_THRESHOLD = 30

# ── 窗口/游戏常量 ──

# 队伍默认数量
DEFAULT_TEAM_COUNT = 3

# 罪人存活数量阈值
SINNER_LIVE_THRESHOLD = 10

# 战斗失败重试阈值
BATTLE_FAIL_RETRY_THRESHOLD = 5

# ── 坐标处理常量 ──

# 坐标分组阈值
COORDINATE_GROUP_THRESHOLD = 40
COORDINATE_PROTECT_THRESHOLD = 50

# ── 战斗识别常量 ──

SKILL3_MIN_PIXELS = 10
SKILL3_THRESHOLD = 40
SKILL3_MERGE_DISTANCE = 67
SKILL3_X_HALF = 33
SKILL3_Y_HALF = 13
SKILL3_SIMILAR_PIXELS = 26
