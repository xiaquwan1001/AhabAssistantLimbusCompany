import re
import time
from time import sleep

from typing import List, Optional

import cv2
import numpy as np

from module.config import TeamSetting
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.my_error.my_error import (
    InputAttributeError,
    backMainWinError,
    cannotOperateGameError,
    unableToFindTeamError,
)
from module.ocr import ocr
from tasks import all_systems, start_gift
from tasks.base.back_init_menu import back_init_menu
from tasks.base.make_enkephalin_module import make_enkephalin_module
from tasks.base.retry import retry
from tasks.battle import battle
from tasks.event import event_handling
from tasks.mirror.in_shop import Shop
from tasks.mirror.reward_card import get_reward_card
from tasks.mirror.search_road import (
    MirrorMap,
    search_road_default_distance,
    search_road_farthest_distance,
)
from tasks.mirror.select_theme_pack import select_theme_pack
from tasks.teams.team_formation import check_team, load_team_code_in_game, select_battle_team, team_formation
from utils.image_utils import ImageUtils
from utils.path_manager import path_manager

# ── 项目常量 ──
from tasks.mirror.constants import (
    MIRROR_MAIN_LOOP,
    DEFAULT_LOOP,
    SHORT_LOOP,
    MIN_LOOP,
    SINNER_LIVE_THRESHOLD,
    BATTLE_FAIL_RETRY_THRESHOLD,
    EVENT_CLICK_TIMES,
    get_scale,
)
from tasks.mirror.state_machine import MirrorStateMachine


# 输出时间统计
def to_log_with_time(msg: str, elapsed_time: float) -> None:
    # 将总秒数转换为小时、分钟和秒
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_string = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    log.info(f"{msg} 总耗时:{time_string}")


def extract_zh_floor(normalized_text: str) -> Optional[int]:
    for pattern in (r"第([1-5])层", r"第([1-5])层?", r"([1-5])层"):
        match = re.search(pattern, normalized_text)
        if match:
            return int(match.group(1))
    if "第" in normalized_text:
        for char in normalized_text[normalized_text.index("第") + 1 :]:
            if char in "12345":
                return int(char)
    return None


def extract_en_floor(normalized_text: str) -> Optional[int]:
    for pattern in (r"floor([1-5])", r"oor([1-5])", r"([1-5])f"):
        match = re.search(pattern, normalized_text)
        if match:
            return int(match.group(1))
    anchor_index = normalized_text.find("floor")
    if anchor_index == -1:
        anchor_index = normalized_text.find("oor")
    if anchor_index != -1:
        for char in normalized_text[anchor_index:]:
            if char in "12345":
                return int(char)
    return None


class Mirror:
    def __init__(self, team_setting: TeamSetting, team_num: int, automation=None, config=None):
        if automation is None:
            from mirror.infra.legacy_adapters import get_automation
            automation = get_automation()
        if config is None:
            from mirror.infra.legacy_adapters import get_config
            config = get_config()
        self.auto = automation
        self.config = config
        self.logger = log
        self.team_order = team_num
        self.sinner_team = team_setting.sinner_order  # 选择的罪人序列
        self.team_number = team_setting.team_number  # 选择的编队名
        self.shop = Shop(team_setting)
        self.system = all_systems[team_setting.team_system]  # 选择的体系
        self.avoid_skill_3 = team_setting.avoid_skill_3  # 是否避免使用3技能
        # 开局星光加成
        self.opening_bonus = team_setting.opening_bonus
        self.use_starlight = team_setting.use_starlight
        # 自选奖励卡优先度
        self.reward_cards = team_setting.reward_cards
        self.reward_cards_select = team_setting.reward_cards_select
        # 自选开局饰品
        self.opening_items = team_setting.opening_items
        self.opening_items_select = team_setting.opening_items_select
        self.opening_items_system = team_setting.opening_items_system
        self.re_formation_each_floor = team_setting.re_formation_each_floor  # 是否每层重新配队
        # 第二体系
        self.second_system = team_setting.second_system  # 启用第二体系
        self.second_system_select = team_setting.second_system_select  # 选择的第二体系
        self.second_system_setting = team_setting.second_system_setting  # 第二体系策略

        self.observe_ego_gift = team_setting.observe_ego_gift  # 是否需要观测EGO饰品
        self.observe_ego_gift_selected = team_setting.observe_ego_gift_selected  # 用户选择的观测EGO饰品列表

        self.defense_first_round = team_setting.defense_first_round  # 是否第一回合全员防御

        self.start_time = time.time()
        self.first_battle = True  # 判断是否首次进入战斗，如果是则重新配队
        self.hard_switch = self.config.hard_mirror
        self.use_custom_theme_pack_weight = team_setting.use_custom_theme_pack_weight  # 是否启用自定义主题包权重
        # 统计时间
        self.find_road_total_time = 0
        self.battle_total_time = 0
        self.shop_total_time = 0
        self.event_total_time = 0
        self.event_times = 0

        self.floor = 0
        self.get_floor_num = True
        self.floor_times = [-9999.0 for i in range(5)]  # 负值代表缺失值
        self.LOOP_COUNT = MIRROR_MAIN_LOOP

        self.mirror_map = MirrorMap(hard_mode=self.hard_switch)

        self.pass_coins = None

        self.bequest_from_the_previous_game = False

    def road_to_mir(self):
        loop_count = DEFAULT_LOOP
        self.auto.model = "clam"
        self.first_battle = True
        while True:
            # 自动截图
            if self.auto.take_screenshot() is None:
                continue
            self.auto.mouse_to_blank()
            if retry() is False:
                return False
            if self.auto.find_element("home/first_prompt_assets.png", model="clam") and self.auto.find_element(
                "home/back_assets.png", model="normal"
            ):
                self.auto.click_element("home/back_assets.png")
                continue
            if self.auto.find_element("mirror/claim_reward/clear_assets.png"):
                self.bequest_from_the_previous_game = True
                return True
            if self.auto.find_element("mirror/shop/shop_coins_assets.png"):  # 防止卡死在商店
                break
            if self.auto.find_element("mirror/road_in_mir/legend_assets.png"):
                break
            if self.auto.click_element("mirror/road_to_mir/resume_assets.png"):
                break
            if self.auto.click_element("mirror/road_to_mir/enter_mirror_assets.png", threshold=0.78):
                break
            infinity_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/road_to_mir/infinity_mirror_bbox.png"))
            infinity_bbox = (
                infinity_bbox[2] - 70,
                infinity_bbox[1],
                infinity_bbox[2] + 100,
                infinity_bbox[3],
            )  # 临时修复措施，调整裁切大小
            if not self.auto.find_text_element(["off", "ff"], infinity_bbox):
                self.auto.click_element("mirror/road_to_mir/infinity_mirror_enter_assets.png")
            if self.auto.click_element("mirror/road_to_mir/enter_assets.png"):
                sleep(0.5)
                continue
            if self.auto.click_element("home/mirror_dungeons_assets.png"):
                continue
            if self.auto.find_element("home/inferno_bus_assets.png") and not self.auto.find_element(
                "home/mirror_dungeons_assets.png"
            ):
                sleep(1)
                if not self.auto.find_element("home/mirror_dungeons_assets.png"):
                    self.auto.click_element("home/window_assets.png")
                    continue
            if self.auto.find_element("base/renew_confirm_assets.png", model="clam") and self.auto.find_element(
                "home/drive_assets.png", model="normal"
            ):
                self.auto.click_element("base/renew_confirm_assets.png")
                back_init_menu()
                continue
            # bug已修复，从这里进可能会进轨道线，先注释掉
            # if self.auto.click_element("mirror/road_to_mir/quick_start_assets.png"):
            #     continue
            if self.auto.click_element("home/drive_assets.png", model="normal"):
                sleep(0.5)
                continue
            if self.auto.find_element("mirror/road_to_mir/select_team_stars_assets.png"):
                break
            if self.auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png"):
                # 防止卡在星光选择
                break
            if self.auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
                # 防止卡死在主题包页面
                break
            loop_count -= 1
            if loop_count < 20:
                self.auto.model = "normal"
            if loop_count < 10:
                self.auto.model = "aggressive"
            if loop_count < 0:
                log.error("无法进入镜牢,尝试回到初始界面")
                back_init_menu()
                break

    def _run_claim_check(self) -> bool:
        """检查镜牢结束奖励页，已结束则返回 True 触发 break。"""
        if self.auto.find_element("mirror/claim_reward/battle_statistics_assets.png"):
            if self.auto.click_element("mirror/claim_reward/claim_rewards_assets.png") is False:
                bbox = ImageUtils.get_bbox(
                    ImageUtils.load_image("mirror/claim_reward/claim_rewards_assets.png")
                )
                self.auto.mouse_click(
                    (bbox[0] + bbox[2]) / 2,
                    (bbox[1] + bbox[3]) / 2,
                )
            return True
        if self.auto.find_element("mirror/claim_reward/claim_rewards_assets.png") and self.auto.find_element(
            "mirror/claim_reward/complete_mirror_100%_assets.png"
        ):
            return True
        if self.auto.find_element(
            "mirror/claim_reward/use_enkephalin_assets.png",
            threshold=0.9,
            model="clam",
        ):
            return True
        return False

    def _run_theme_pack(self, main_loop_count: int) -> bool:
        """选择楼层主题包并记录楼层时间。处理成功返回 True。"""
        if not self.auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
            return False
        sleep(2)
        select_theme_pack(self.hard_switch, self.floor, self.team_order, self.use_custom_theme_pack_weight)
        if self.re_formation_each_floor:
            self.first_battle = True
        try:
            floor_num = self.floor
            if floor_num != 0:
                prev = self.floor_times[floor_num - 1]
                if prev > 0:
                    floor_time = time.time() - prev
                    msg = f"启动后第{self.floor}层卡包"
                else:
                    floor_time = time.time() - self.floor_times[0]
                    msg = f"启动后第{self.floor}层卡包，该楼层时间不完整"
                to_log_with_time(msg, floor_time)
            self.floor_times[floor_num] = time.time()
        except Exception:
            log.info("楼层异常，可能是OCR识别错误，本轮镜牢层间的时间记录无效")
        self.get_floor_num = True
        return True

    def _run_event_effect(self) -> bool:
        """处理选择增益事件（少见）。处理成功返回 True。"""
        if not self.auto.click_element("mirror/road_in_mir/event_effect_button.png", threshold=0.75):
            return False
        self.auto.click_element("mirror/road_in_mir/select_event_effect_confirm.png")
        return True

    def _run_road_navigation(self) -> bool:
        """在镜牢中寻路。返回 True 表示已处理。"""
        if not self.auto.find_element("mirror/road_in_mir/legend_assets.png"):
            return False
        self.auto.mouse_to_blank()
        while self.auto.take_screenshot() is None:
            continue
        if self.auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
            return True
        if self.auto.find_element("teams/identify_assets.png"):
            return True
        if self.auto.find_element("mirror/shop/shop_coins_assets.png", model="normal"):
            return True
        if self.auto.find_element("mirror/claim_reward/claim_rewards_assets.png") and self.auto.find_element(
            "mirror/claim_reward/complete_mirror_100%_assets.png"
        ):
            return True  # signals caller to break — handled in main loop dispatch
        retry()
        if self.get_floor_num:
            self.get_which_floor()
        if self.config.floor_3_exit and self.floor >= 4:
            return True
        while self.auto.take_screenshot() is None:
            continue
        if self.auto.find_element("mirror/road_in_mir/legend_assets.png"):
            self.find_road_total_time += self.search_road()
        return True

    # ── Main loop dispatch handlers ──

    def _run_enter_node(self) -> bool:
        """进入寻路线路节点。"""
        return bool(self.auto.click_element("mirror/road_in_mir/enter_assets.png"))

    def _run_team_select(self) -> bool:
        """选择镜牢队伍。"""
        if not self.auto.find_element("mirror/road_to_mir/select_team_stars_assets.png"):
            return False
        self.select_mirror_team()
        return True

    def _run_battle_fail_check(self) -> bool:
        """战斗失败次数过多时重开。"""
        if battle.fail_times < BATTLE_FAIL_RETRY_THRESHOLD:
            return False
        battle.fail_times = 0
        self.re_start()
        return True

    def _run_battle_deploy(self) -> bool:
        """战斗配队（含首次编队、罪人存活检测）。"""
        if not self.auto.find_element("teams/identify_assets.png"):
            return False
        if self.first_battle:
            team_formation(self.sinner_team)
            self.first_battle = False
            return True
        if self.auto.click_element("teams/none_sinner_assets.png", model="clam"):
            self.first_battle = True
            return True
        if not (
            self.auto.find_element("teams/12_sinner_live_assets.png")
            or self.auto.find_element("teams/11_sinner_live_assets.png")
            or self.auto.find_element("teams/10_sinner_live_assets.png")
        ):
            continue_mirror = check_team()
            if continue_mirror is False and self.first_battle is False:
                self.re_start()
        if self.auto.click_element("battle/chaim_to_battle_assets.png") or self.auto.click_element(
            "battle/normal_to_battle_assets.png"
        ):
            retry()
            return True
        return False

    def _run_no_team(self) -> bool:
        """没有配队时重置。"""
        if not self.auto.find_element("battle/select_none_assets.png"):
            return False
        self.auto.mouse_click_blank()
        self.first_battle = True
        return True

    def _run_battle(self, main_loop_count: int) -> bool:
        """战斗识别与执行（主战斗 + keyword/OCR fallback + win_rate）。"""
        in_battle = self.auto.find_element("battle/more_information_assets.png") or self.auto.find_element(
            "battle/in_mirror_assets.png"
        )
        if in_battle:
            self.battle_total_time += battle.fight(self.avoid_skill_3, self.defense_first_round)
            return True
        if battle.identify_keyword_turn and self.LOOP_COUNT - main_loop_count < 5:
            if self.auto.find_element("battle/turn_assets.png") or self.auto.find_element("battle/in_mirror_assets.png"):
                self.battle_total_time += battle.fight(self.avoid_skill_3, self.defense_first_round)
                return True
        turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
        turn_ocr_result = self.auto.find_text_element("turn", turn_bbox)
        if turn_ocr_result is not False:
            self.battle_total_time += battle.fight(self.avoid_skill_3, self.defense_first_round)
            return True
        if self.auto.find_element("battle/win_rate_card.png") and self.auto.find_element("battle/gear_right.png"):
            self.battle_total_time += battle.fight(self.avoid_skill_3, self.defense_first_round)
            return True
        return False

    def _run_starlight(self) -> bool:
        """镜牢星光选择。"""
        if not self.auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png", threshold=0.9):
            return False
        self.enter_mir_with_star()
        return True

    def _run_ego_gift_acquisition(self, main_loop_count: int) -> bool:
        """选择/拒绝EGO饰品（包含三种判定）。"""
        if self.auto.find_element("mirror/road_in_mir/acquire_ego_gift_card.png"):
            self.acquire_ego_gift()
            return True
        if (
            main_loop_count < 50
            and self.auto.find_element("mirror/road_in_mir/acquire_ego_gift_box_assets.png", model="clam")
            and self.auto.find_element("mirror/road_in_mir/acquire_ego_gift_refuse_assets.png", model="clam")
        ):
            self.acquire_ego_gift(type=2)
            return True
        if main_loop_count < 30 and self.auto.find_language_text("拒绝饰品", "refuse"):
            self.acquire_ego_gift(type=2)
            return True
        return False

    def _run_ego_gift_confirm(self) -> bool:
        """确认获取EGO饰品。"""
        return bool(self.auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"))

    def _run_event(self) -> bool:
        """事件处理。"""
        if not self.auto.click_element("event/skip_assets.png", times=EVENT_CLICK_TIMES):
            return False
        self.event_handling()
        return True

    def _run_shop(self) -> bool:
        """商店操作。"""
        if not self.auto.find_element("mirror/shop/shop_coins_assets.png"):
            return False
        self.shop_total_time += self.in_shop()
        return True

    def _run_reward_card(self) -> bool:
        """选择奖励卡。"""
        if not self.auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png"):
            return False
        if self.reward_cards:
            get_reward_card(self.reward_cards_select)
        else:
            get_reward_card()
        return True

    def _run_enter_mirror(self) -> bool:
        """从主界面/镜牢界面进入镜牢。返回 True 时调用者需检查 bequest。"""
        if self.auto.click_element("home/drive_assets.png") or self.auto.find_element("home/window_assets.png"):
            sleep(0.5)
            if self.road_to_mir() and self.bequest_from_the_previous_game:
                return True
            return True
        if self.auto.click_element("mirror/road_to_mir/enter_assets.png"):
            if self.road_to_mir() and self.bequest_from_the_previous_game:
                return True
            return True
        return False

    def _run_init_ego_gift(self) -> bool:
        """初始饰品选择。"""
        if not (
            self.auto.find_element("mirror/road_to_mir/activate_gift_search_on_assets.png")
            or self.auto.find_element("mirror/road_to_mir/activate_gift_search_off_assets.png")
        ):
            return False
        self.select_init_ego_gift()
        return True

    def _run_observe_ego_gift(self) -> bool:
        """观测EGO饰品。"""
        if not (
            self.auto.find_element("mirror/road_to_mir/observe_ego_gift/observe_bleed_assets.png", model="clam")
            or self.auto.find_element("mirror/road_to_mir/observe_ego_gift/observe_burn_assets.png", model="clam")
        ):
            return False
        self.select_observe_ego_gift()
        return True

    def _run_close_infinity(self) -> bool:
        """关闭无限镜牢弹窗。"""
        from module4_decision_layer.handlers.game import CloseInfinityHandler
        return CloseInfinityHandler()(auto=self.auto)

    def _run_dismiss_prompt(self) -> bool:
        """关闭首屏提示。"""
        from module4_decision_layer.handlers.game import DismissPromptHandler
        return DismissPromptHandler()(auto=self.auto)

    def run(self):
        """镜牢主循环：状态机驱动的优先级调度。"""
        start_time = time.time()

        if self.auto.click_element("home/drive_assets.png") or self.auto.find_element("home/window_assets.png"):
            sleep(0.5)
            make_enkephalin_module()

        sm = MirrorStateMachine(loop_count=self.LOOP_COUNT, floor_3_exit=self.config.floor_3_exit)

        while not sm.is_done:
            if sm.main_loop_count >= 50:
                self.auto.model = "clam"
            if self.auto.take_screenshot() is None:
                continue
            retry()

            # 提前退出（floor_3_exit）
            if sm.should_exit_early():
                if self.auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                    break
                if self.auto.click_element("mirror/road_in_mir/forfeit_assets.png"):
                    continue
                if self.auto.click_element("mirror/road_in_mir/setting_assets.png"):
                    continue

            # 优先级调度：按状态机指定的动作检测
            if self._run_claim_check():
                break

            if self._run_theme_pack(sm.main_loop_count):
                continue

            if self._run_event_effect():
                continue

            if self._run_road_navigation():
                continue

            if self._run_enter_node():
                continue

            if self._run_team_select():
                continue

            if self._run_battle_fail_check():
                continue

            if self._run_battle_deploy():
                continue

            if self._run_no_team():
                continue

            if self._run_battle(main_loop_count=sm.main_loop_count):
                continue

            if self._run_starlight():
                continue

            if self._run_ego_gift_acquisition(sm.main_loop_count):
                continue

            if self._run_ego_gift_confirm():
                continue

            if self._run_event():
                continue

            if self._run_shop():
                continue

            if self._run_reward_card():
                continue

            if self._run_enter_mirror():
                continue

            if self._run_init_ego_gift():
                continue

            if self._run_observe_ego_gift():
                continue

            if self._run_close_infinity():
                continue

            if self._run_dismiss_prompt():
                continue

            # 防卡死回退
            self.auto.mouse_click_blank()
            retry()
            sm.on_loop_tick()
            if sm.main_loop_count % 10 == 0:
                log.debug(f"镜牢道中识别次数剩余{sm.main_loop_count}次")
            if sm.should_switch_to_normal():
                self.auto.model = "normal"
                self.auto.mouse_to_blank(move_back=False)
                log.debug("识别模式切换到正常模式")
            if sm.should_switch_to_aggressive():
                self.auto.model = "aggressive"
                log.debug("识别模式切换到激进模式，警告，道中识别可能会出错")
            if sm.main_loop_count < 0:
                if sm.back_menu_count > 5:
                    raise backMainWinError("镜牢道中出错,请手动操作重试")
                log.error("镜牢道中识别失败次数达到最大值,正在返回主界面")
                back_init_menu()
                sm.on_back_to_menu()

        return self._claim_and_finalize(start_time)

    def _claim_and_finalize(self, start_time: float) -> bool:
        """镜牢完成后的奖励领取 + 时间统计输出。返回 True=成功。"""
        msg = "开始进行镜牢奖励领取"
        log.info(msg)

        if self.bequest_from_the_previous_game:
            self.get_reward_in_road()
            return True

        loop_count = 20
        self.auto.model = "clam"
        failed = None
        while True:
            if self.auto.take_screenshot() is None:
                self.auto.mouse_to_blank()
                continue
            if (
                not self.auto.find_element("mirror/claim_reward/complete_mirror_100%_assets.png")
                and failed is None
                and not self.config.floor_3_exit
            ):
                failed = True
            if self.auto.find_element("mirror/claim_reward/complete_mirror_100%_assets.png") or self.auto.find_element(
                "mirror/claim_reward/clear_assets.png"
            ):
                failed = False
                log.debug("镜牢完成度100%，能够正常领取奖励")
            if self.auto.find_element("home/drive_assets.png"):
                break
            if self.auto.click_element("battle/battle_finish_confirm_assets.png"):
                continue
            if self.auto.click_element("mirror/claim_reward/rewards_acquired_assets.png"):
                continue
            if self.auto.click_element("mirror/claim_reward/claim_rewards_confirm_assets.png", threshold=0.75, model="clam", take_screenshot=True):
                continue
            if failed:
                self.auto.mouse_click_blank()
                sleep(0.5)
                complete_mirror_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/claim_reward/complete_mirror_100%_assets.png"))
                if self.auto.find_text_element("100", complete_mirror_bbox):
                    failed = False
                    continue
                if self.auto.click_element("mirror/claim_reward/claim_rewards_assets.png"):
                    sleep(1)
                if self.auto.click_element("mirror/claim_reward/claim_forfeit_assets.png", model="normal", take_screenshot=True):
                    continue
            else:
                if self.hard_switch and self.config.save_rewards:
                    self.auto.click_element("mirror/claim_reward/claim_rewards_assets.png")
                    sleep(1)
                    pos = self.auto.find_element("mirror/claim_reward/use_enkephalin_assets.png", take_screenshot=True)
                    if pos:
                        self.auto.mouse_click(pos[0] - 300 * get_scale(), pos[1])
                        sleep(1)
                    continue
                elif self.auto.click_element("mirror/claim_reward/claim_rewards_assets.png"):
                    sleep(1)
                    if self.config.no_weekly_bonuses:
                        bonuses = self.auto.find_element("mirror/claim_reward/weekly_bonuses.png", find_type="image_with_multiple_targets", take_screenshot=True)
                        if bonuses and len(bonuses) >= 1:
                            for _ in range(len(bonuses)):
                                self.auto.mouse_click(bonuses.pop(-1)[0], bonuses.pop(-1)[1])
                    if self.config.hard_mirror_single_bonuses:
                        log.debug("开启了困牢单次领取奖励，如果存在多次奖励，则将单次领取")
                        sleep(1)
                        bonuses = self.auto.find_element("mirror/claim_reward/weekly_bonuses.png", find_type="image_with_multiple_targets", take_screenshot=True)
                        if bonuses:
                            bonuses = sorted(bonuses, key=lambda x: x[0])
                            if len(bonuses) > 1:
                                for _ in range(len(bonuses) - 1):
                                    self.auto.mouse_click(bonuses.pop(-1)[0], bonuses.pop(-1)[1])
                    self._read_pass_coins()
                    if self.auto.click_element("mirror/claim_reward/use_enkephalin_assets.png", take_screenshot=True):
                        sleep(1)
                    retry()
                    continue
            if self.auto.click_element("mirror/claim_reward/use_enkephalin_assets.png", threshold=0.75):
                sleep(1)
                continue
            if self.auto.click_element("home/close_anniversary_event_assets.png"):
                continue
            retry()
            loop_count -= 1
            if loop_count % 3 == 0:
                log.debug(f"镜牢奖励识别次数剩余{loop_count}次")
            if loop_count < 10:
                self.auto.model = "normal"
                self.auto.mouse_to_blank(move_back=False)
            if loop_count < 5:
                self.auto.model = "aggressive"
            if loop_count < 0:
                raise cannotOperateGameError("镜牢奖励领取出错,请手动操作重试")

        if failed:
            return False

        self._output_mirror_stats(start_time)
        return True

    def _read_pass_coins(self):
        """OCR 读取通行证经验数量。"""
        self.auto.take_screenshot()
        coins_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/claim_reward/coins_bbox.png"))
        for _ in range(5):
            try:
                sc = ImageUtils.crop(np.array(self.auto.screenshot), coins_bbox)
                result = ocr.run(sc)
                ocr_result = "".join(result.txts).lower()
                if "x" in ocr_result:
                    self.pass_coins = int(ocr_result.split("x")[-1])
                    break
            except Exception:
                continue
        if self.pass_coins is None:
            for _ in range(5):
                try:
                    scale = get_scale()
                    if coins_pos := self.auto.find_element("mirror/claim_reward/coins.png"):
                        coins_bbox = [coins_pos[0], coins_pos[1] - 40 * scale, coins_pos[0] + 100 * scale, coins_pos[1] + 40 * scale]
                        sc = ImageUtils.crop(np.array(self.auto.screenshot), coins_bbox)
                        result = ocr.run(sc)
                        ocr_result = "".join(result.txts).lower()
                        if "x" in ocr_result:
                            self.pass_coins = int(ocr_result.split("x")[-1])
                            break
                except Exception:
                    continue
        if self.pass_coins:
            log.info(f"本次镜牢领取{self.pass_coins}个通行证经验")
        else:
            log.warning("无法识别通行证经验数量，可能是UI发生变化")

    def _output_mirror_stats(self, start_time: float):
        """输出镜牢耗时统计。"""
        end_time = time.time()
        elapsed_time = end_time - start_time
        self._update_team_history(elapsed_time)
        try:
            last_floor_time = time.time() - self.floor_times[self.floor - 1]
            to_log_with_time(f"启动后第{self.floor}层卡包", last_floor_time)
        except Exception:
            log.info("楼层异常，可能是OCR识别错误，本轮镜牢层间的时间记录无效")
        to_log_with_time("此次镜牢在战斗", self.battle_total_time)
        log.info(f"此次镜牢走的事件次数{self.event_times}")
        to_log_with_time("此次镜牢在事件", self.event_total_time)
        to_log_with_time("此次镜牢中在商店", self.shop_total_time)
        to_log_with_time("此次镜牢中在寻路", self.find_road_total_time)
        log.debug(f"战斗时间:{self.battle_total_time} 事件时间:{self.event_total_time} 商店时间:{self.shop_total_time} 寻路时间:{self.find_road_total_time} 总时间:{elapsed_time}")
        to_log_with_time(f"此次镜牢使用{self.system}体系队伍", elapsed_time)

    def _update_team_history(self, elapsed_time: float):
        """更新编队历史时间数据。"""
        if not all(self.floor_times[i] > 0 for i in range(5)):
            return
        team = self.config.config.teams.get(f"{self.team_order}")
        if not team:
            return

        team_history = {
            "total_mirror_time_hard": team.total_mirror_time_hard,
            "mirror_hard_count": team.mirror_hard_count,
            "total_mirror_time_normal": team.total_mirror_time_normal,
            "mirror_normal_count": team.mirror_normal_count,
        }

        def calc_time(tl, et, cnt):
            ta = tl[0] if len(tl) > 0 else 0
            l5 = tl[1] if len(tl) > 1 else 0
            l10 = tl[2] if len(tl) > 2 else 0
            return [(ta * cnt + et) / (cnt + 1), (l5 * min(cnt, 4) + et) / min(cnt + 1, 5), (l10 * min(cnt, 9) + et) / min(cnt + 1, 10)]

        if self.hard_switch:
            cnt = team_history["mirror_hard_count"]
            team_history["total_mirror_time_hard"] = calc_time(team_history["total_mirror_time_hard"], elapsed_time, cnt)
            team_history["mirror_hard_count"] = cnt + 1
        else:
            cnt = team_history["mirror_normal_count"]
            team_history["total_mirror_time_normal"] = calc_time(team_history["total_mirror_time_normal"], elapsed_time, cnt)
            team_history["mirror_normal_count"] = cnt + 1

        team.total_mirror_time_hard = team_history["total_mirror_time_hard"]
        team.mirror_hard_count = team_history["mirror_hard_count"]
        team.total_mirror_time_normal = team_history["total_mirror_time_normal"]
        team.mirror_normal_count = team_history["mirror_normal_count"]
        log.debug(team_history)

    def enter_mir_with_star(self):
        coins = self.auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png", threshold=0.9)
        scale = self.config.set_win_size / 1440
        first_starlight = [coins[0] - 1800 * scale, coins[1] + 300 * scale]
        starlights_X = [first_starlight[0] + (i % 5) * 400 * scale for i in range(10)]
        starlights_Y = [first_starlight[1] + (i // 5) * 480 * scale for i in range(10)]

        first_single_plus = (first_starlight[0] - 80 * scale, first_starlight[1] + 320 * scale)
        double_plus_offset = 80 * scale * 2
        star_card_size = (400 * scale, 480 * scale)

        loop_count = 30
        self.auto.model = "clam"
        while True:
            # 自动截图
            if self.auto.take_screenshot() is None:
                continue

            if self.auto.find_element("mirror/road_to_mir/bleed_gift_assets.png"):
                break

            if self.use_starlight and self.auto.click_element(
                "mirror/road_to_mir/dreaming_star/no_convert_star_to_cost_assets.png"
            ):
                continue
            if not self.use_starlight and self.auto.click_element(
                "mirror/road_to_mir/dreaming_star/convert_star_to_cost_assets.png"
            ):
                continue

            if self.auto.click_element(
                "mirror/road_to_mir/dreaming_star/select_star_confirm_assets.png",
                model="normal",
            ):
                break

            bonus_num = len(self.opening_bonus)
            level_count = self.opening_bonus.count(1)
            level_plus_count = self.opening_bonus.count(2)
            level_plusplus_count = self.opening_bonus.count(3)
            if level_count == bonus_num:
                self.auto.click_element("mirror/road_to_mir/select_all_stars_assets.png")
            elif level_plus_count == bonus_num:
                self.auto.click_element("mirror/road_to_mir/select_all_stars_assets.png")
                self.auto.click_element("mirror/road_to_mir/dreaming_star/level_one_bonus_assets.png")
            elif level_plusplus_count == bonus_num:
                self.auto.click_element("mirror/road_to_mir/select_all_stars_assets.png")
                self.auto.click_element("mirror/road_to_mir/dreaming_star/level_two_bonus_assets.png")
            else:
                for i in range(bonus_num):
                    if self.opening_bonus[i] >= 1:
                        self.auto.mouse_action_with_pos((starlights_X[i], starlights_Y[i]))
                    if self.opening_bonus[i] == 2:
                        self.auto.mouse_action_with_pos(
                            (starlights_X[i] - 80 * scale, starlights_Y[i] + 320 * scale),
                        )
                    elif self.opening_bonus[i] == 3:
                        self.auto.mouse_action_with_pos(
                            (starlights_X[i] + 80 * scale, starlights_Y[i] + 320 * scale),
                        )

            if self.auto.click_element("mirror/road_to_mir/dreaming_star/dreaming_star_enter_assets.png"):
                sleep(0.5)
                continue

            if retry() is False:
                return False
            loop_count -= 1
            if loop_count % 5 == 0:
                log.debug(f"进入镜牢识别次数剩余{loop_count}次")
            if loop_count < 20:
                self.auto.model = "normal"
                self.auto.mouse_to_blank(move_back=False)
                log.debug("识别模式切换到正常模式")
            if loop_count < 10:
                self.auto.model = "aggressive"
                log.debug("识别模式切换到激进模式")
            if loop_count < 0:
                raise cannotOperateGameError("无法进入镜牢，不能进行下一步,请手动操作重试")

    def select_init_ego_gift(self):
        scroll = False
        select_system = False
        loop_count = 30
        self.auto.model = "clam"

        team_system = self.system
        if self.opening_items:
            team_system = all_systems[self.opening_items_system]
        log.debug("开始选择初始EGO")
        while True:
            # 自动截图
            if self.auto.take_screenshot() is None:
                continue

            if self.auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                self.auto.mouse_to_blank()
                continue

            # 如果未启用观测或启用了但未选择饰品，关闭观测饰品按钮
            if not self.observe_ego_gift or len(self.observe_ego_gift_selected) == 0:
                self.auto.click_element("mirror/road_to_mir/activate_gift_search_on_assets.png")
            # 如果已经进入观测饰品页面,则跳过初始EGO选择
            if (
                self.auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png")
                or self.auto.find_element("mirror/road_to_mir/observe_ego_gift/observe_bleed_assets.png")
                or self.auto.find_element("mirror/road_to_mir/observe_ego_gift/observe_burn_assets.png")
            ):
                break

            if (team_system == "slash" or team_system == "pierce" or team_system == "blunt") and not scroll:
                while slash_button := self.auto.find_element("mirror/road_to_mir/slash_gift_1.png"):
                    self.auto.mouse_drag(slash_button[0], slash_button[1], drag_time=0.2, dx=0, dy=-400)
                    sleep(0.5)
                    if self.auto.find_element(
                        "mirror/road_to_mir/blunt_gift_1_assets.png",
                        take_screenshot=True,
                    ):
                        scroll = True
                        break

            if self.auto.click_element(f"mirror/road_to_mir/{team_system}_gift_assets.png") and not select_system:
                select_system = True
                continue

            if self.opening_items:
                start_gift_order = start_gift[self.opening_items_select]
                self.auto.click_element(
                    f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_{start_gift_order[0]}.png"
                )
                self.auto.click_element(
                    f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_{start_gift_order[1]}.png"
                )
                self.auto.click_element(
                    f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_{start_gift_order[2]}.png"
                )
            else:
                self.auto.click_element(f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_1.png")
                self.auto.click_element(f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_2.png")
                self.auto.click_element(f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_3.png")

            # 如果选择观测饰品且选择了饰品，则开启观测饰品按钮
            if self.observe_ego_gift and self.observe_ego_gift_selected:
                self.auto.click_element("mirror/road_to_mir/activate_gift_search_off_assets.png")

            if self.auto.click_element("mirror/road_to_mir/select_init_ego_gifts_confirm_assets.png"):
                sleep(1)
                continue

            if retry() is False:
                return False
            loop_count -= 1
            if loop_count % 5 == 0:
                log.debug(f"选择藏品识别次数剩余{loop_count}次")
            if loop_count < 20:
                self.auto.model = "normal"
                self.auto.mouse_to_blank(move_back=False)
                log.debug("识别模式切换到正常模式")
            if loop_count < 10:
                self.auto.model = "aggressive"
                log.debug("识别模式切换到激进模式")
            if loop_count < 0:
                log.error("无法进入镜牢,尝试回到初始界面")
                back_init_menu()
                break

    def select_observe_ego_gift(self):
        """
        观测EGO饰品选择
        """

        def _select_gift(level_p):
            first_gift = (level_p[0], level_p[1] + 80 * my_scale)
            select_gift_point = (
                first_gift[0] + (gift_col - 1) * 165 * my_scale,
                first_gift[1] + (gift_row - 1) * 160 * my_scale,
            )
            if select_gift_point[1] < gift_box[-1]:
                self.auto.mouse_click(select_gift_point[0], select_gift_point[1])
            else:
                step = 300 * my_scale
                height = step
                if select_gift_point[1] - gift_box[-1] > step:
                    height = select_gift_point[1] - gift_box[-1]
                    result = [step] * int(height // step) + ([int(height % step)] if int(height % step) > 0 else [])
                else:
                    result = [step]
                for s in result:
                    self.auto.mouse_drag(
                        gift_box[-2] - 100 * my_scale,
                        gift_box[-1] - 100 * my_scale,
                        dy=-s,
                        drag_time=1.5,
                    )
                    sleep(1)
                self.auto.mouse_click(select_gift_point[0], select_gift_point[1] - height)

        log.debug("开始选择观测EGO饰品")
        self.auto.model = "clam"

        my_scale = self.config.set_win_size / 1440
        benchmark_point = None
        if point := self.auto.find_element(
            "mirror/road_to_mir/observe_ego_gift/observe_burn_assets.png", model="clam", take_screenshot=True
        ):
            benchmark_point = point
        elif self.auto.find_element("mirror/road_to_mir/observe_ego_gift/observe_bleed_assets.png", model="clam"):
            benchmark_point = (point[0] - 110 * my_scale, point[1])

        if not benchmark_point:
            return

        gift_box = ImageUtils.get_bbox(ImageUtils.load_image("mirror/road_to_mir/observe_ego_gift/gift_box_bbox.png"))

        # 选择观测饰品
        for gift_id in self.observe_ego_gift_selected:
            # 从文件名推断体系，如 "bleed_3_3_7.png" -> "bleed"
            gm = re.match(r"^([a-z]+)_", gift_id)
            if not gm:
                log.warning(f"无法解析饰品体系：{gift_id}，跳过")
                continue
            file_system = gm.group(1)
            gift_information = gift_id.split("_")[1:]
            gift_level = int(gift_information[0])
            gift_row = int(gift_information[1])  # 所在行
            gift_col = int(gift_information[2])  # 所在列

            # 选择体系
            if file_system == "general":
                system_index = 10
            else:
                system_index = [k for k, v in all_systems.items() if v == file_system][0]
            # 选择体系，先点一下其他体系，再点回来，重置页面
            self.auto.mouse_click(benchmark_point[0] + 110 * (system_index + 1) * my_scale, benchmark_point[1])
            sleep(0.2)
            self.auto.mouse_click(benchmark_point[0] + 110 * (system_index - 1) * my_scale, benchmark_point[1])
            sleep(0.2)
            self.auto.mouse_click(benchmark_point[0] + 110 * system_index * my_scale, benchmark_point[1])
            sleep(0.2)

            if level_point := self.auto.find_element(
                f"mirror/road_to_mir/observe_ego_gift/Level_{'I' * gift_level}.png", take_screenshot=True
            ):
                _select_gift(level_point)
            else:
                level_point = None
                for _ in range(5):
                    self.auto.mouse_drag(
                        gift_box[-2] - 100 * my_scale,
                        gift_box[-1] - 100 * my_scale,
                        dy=-(gift_box[-1] - gift_box[1]) / 2,
                        drag_time=1.5,
                    )
                    if p := self.auto.find_element(
                        f"mirror/road_to_mir/observe_ego_gift/Level_{'I' * gift_level}.png", take_screenshot=True
                    ):
                        level_point = p
                        break
                if level_point is None:
                    continue
                _select_gift(level_point)
                sleep(0.5)

        # 观测饰品选择完毕
        for _ in range(5):
            bbox = ImageUtils.get_bbox(
                ImageUtils.load_image("mirror/road_to_mir/observe_ego_gift/select_gift_bbox.png")
            )
            ocr_result = self.auto.find_language_text("选择", "select", bbox)
            if ocr_result:
                self.auto.mouse_click((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                sleep(1)
                if self.auto.click_element("mirror/shop/leave_shop_confirm_assets.png", take_screenshot=True):
                    break
        for _ in range(5):
            self.auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png", take_screenshot=True)

        for _ in range(3):
            bbox = ImageUtils.get_bbox(
                ImageUtils.load_image("mirror/road_to_mir/observe_ego_gift/reject_gift_bbox.png")
            )
            ocr_result = self.auto.find_language_text("拒绝", "reject", bbox)
            if ocr_result:
                self.auto.mouse_click((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                sleep(1)
                if self.auto.click_element("mirror/shop/leave_shop_confirm_assets.png", take_screenshot=True):
                    return

    def select_mirror_team(self):
        chance_to_select_team = 5
        while not select_battle_team(self.team_number):
            chance_to_select_team -= 1
            if chance_to_select_team < 0:
                log.error("无法寻得队伍")
                raise unableToFindTeamError("无法寻得队伍，请检查队伍名称是否为默认名称")
        # 加载编队码（如果启用）
        team_setting = self.config.config.teams.get(str(self.team_order))
        if team_setting and team_setting.use_team_code and team_setting.team_code:
            if not load_team_code_in_game(team_setting.team_code):
                log.warning("编队码加载失败，继续使用当前队伍配置")
        loop_count = 30
        self.auto.model = "clam"
        while self.auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png") is None:
            if self.auto.take_screenshot() is None:
                continue
            loop_count -= 1
            if loop_count % 5 == 0:
                log.debug(f"选择队伍识别次数剩余{loop_count}次")
            if loop_count < 20:
                self.auto.model = "normal"
                self.auto.mouse_to_blank(move_back=False)
                log.debug("识别模式切换到正常模式")
            if loop_count < 10:
                self.auto.model = "aggressive"
                log.debug("识别模式切换到激进模式")
            if loop_count < 5:
                if self.auto.find_language_text("平均", "current"):
                    self.auto.click_element("mirror/road_to_mir/enter_mirror_confirm.png")
            if loop_count < 0:
                log.error("无法进入镜牢,尝试回到初始界面")
                back_init_menu()
                break
            if retry() is False:
                return False
            if self.auto.click_element("mirror/road_to_mir/level_confirm_assets.png"):
                continue
            if self.auto.click_element("mirror/road_to_mir/select_team_confirm_assets.png"):
                sleep(0.5)
                loop_count -= 1
                continue

        time.sleep(3)

    @begin_and_finish_time_log(task_name="镜牢寻路")
    def search_road(self):
        try:
            if next_node := self.mirror_map.get_next_step():
                if next_node is True:
                    return True
                if self.mirror_map.enter_next_node(next_node):
                    return True
            log.debug("未能构建路线图，尝试使用最近节点法重新寻路")
        except Exception as e:
            log.debug(f"使用onnx模型寻路出错:{e}")
        finally:
            self.auto.mouse_to_blank()
        try:
            for _ in range(3):
                while self.auto.take_screenshot() is None:
                    continue
                if search_road_default_distance():
                    sleep(1)
                    return True
                if self.auto.click_element("mirror/road_in_mir/enter_assets.png"):
                    return True
                if retry() is False:
                    return False
            for _ in range(3):
                if self.config.background_click:
                    continue
                while self.auto.take_screenshot() is None:
                    continue
                if search_road_farthest_distance():
                    sleep(1)
                    return True
                if retry() is False:
                    return False
        except InputAttributeError as e:
            log.error(f"寻路出错:{e}, 尝试重进镜牢")
            pass
        except Exception as e:
            log.error(f"寻路出错:{e}")
            return False
        if self.auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
            return True
        start_time = time.time()
        log.info("寻路出错, 尝试重进镜牢")
        while True:
            from tasks.base.retry import check_times

            # 自动截图
            if self.auto.take_screenshot() is None:
                continue
            if self.auto.get_restore_time() is not None:
                start_time = max(start_time, self.auto.get_restore_time())
            if check_times(start_time):
                back_init_menu()
                return False
            self.auto.mouse_to_blank()
            if self.auto.click_element("mirror/road_in_mir/enter_assets.png"):
                return True
            if self.auto.click_element("home/drive_assets.png") or self.auto.find_element("home/window_assets.png"):
                sleep(0.5)
                break
            if self.auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                break
            if self.auto.click_element("mirror/road_in_mir/to_window_assets.png"):
                continue
            if self.auto.click_element("mirror/road_in_mir/setting_assets.png"):
                sleep(1)
                continue
            if retry() is False:
                return False

    def re_start(self):
        while True:
            # 自动截图
            if self.auto.take_screenshot() is None:
                continue
            if self.auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                break
            if self.auto.click_element("mirror/road_in_mir/forfeit_assets.png"):
                continue
            if self.auto.click_element("mirror/road_in_mir/setting_assets.png"):
                continue
            if self.auto.click_element("battle/give_up_assets.png"):
                continue
            self.auto.key_press("esc")
            time.sleep(1)
            if retry() is False:
                return False
        # TODO耗时
        msg = f"满 身 疮 痍 ！ 重 开 ！此次战败耗时{time.time() - self.start_time}"
        log.info(msg)
        self.first_battle = True
        self.start_time = time.time()

    def event_handling(self):
        # 遇到有SKIP的情况
        event_start_time = time.time()
        loop_count = 30
        self.auto.model = "clam"
        event_chance = 15
        while True:
            # 自动截图
            if self.auto.take_screenshot() is None:
                continue

            if retry() is False:
                return False

            # 如果在战斗中或回到镜牢路线图中，则跳出循环
            if self.auto.find_element("battle/turn_assets.png"):
                break
            if self.auto.find_element("mirror/road_in_mir/legend_assets.png"):
                break

            if event_chance == 0:
                if key_word_position := self.auto.find_language_text("判定", "check"):
                    self.auto.mouse_action_with_pos(key_word_position, offset=False)
                    event_chance += 5
            if 5 <= event_chance < 10:
                self.auto.click_element("event/select_first_option_assets.png")
                event_chance -= 1
            elif 5 > event_chance > 0:
                if coordinates := self.auto.find_element(
                    "event/select_first_option_assets.png", find_type="image_with_multiple_targets", threshold=0.75
                ):
                    for coordinate in coordinates:
                        self.auto.mouse_click(coordinate[0], coordinate[1])
                    retry()
                event_chance -= 1
            if event_chance < 0:
                finishes_bbox = ImageUtils.get_bbox(ImageUtils.load_image("event/continue_assets.png"))
                if self.auto.find_text_element(
                    [
                        "continue",
                        "proceed",
                        "commence",
                        "choices",
                        "confirm",
                        "行判",
                        "始战",
                        "继续",
                    ],
                    finishes_bbox,
                ):
                    self.auto.mouse_click(
                        (finishes_bbox[0] + finishes_bbox[2]) // 2,
                        (finishes_bbox[1] + finishes_bbox[3]) // 2,
                    )
                    break
                elif coordinates := self.auto.find_element(
                    "event/select_first_option_assets.png", find_type="image_with_multiple_targets", threshold=0.75
                ):
                    for coordinate in coordinates:
                        self.auto.mouse_click(coordinate[0], coordinate[1])
                    retry()
                else:
                    msg = "事件卡死，尝试返回主界面"
                    log.error(msg)
                    back_init_menu()
                    return

            # 针对不同事件进行处理，优先选???与直接获取的，再选需要判定的，再选后续事件的，最后第一个事项
            if self.auto.click_element("event/unknown_event.png"):
                event_chance -= 1
                continue
            if positions_list := self.auto.find_element(
                "event/select_to_gain_ego.png",
                find_type="image_with_multiple_targets",
                threshold=0.75,
            ):
                positions_list = sorted(positions_list, key=lambda x: (x[1], x[0]))
                self.auto.mouse_click(positions_list[0][0], positions_list[0][1])
                event_chance -= 1
                continue
            if self.auto.click_element("event/advantage_check.png"):
                event_chance -= 1
                continue
            if self.auto.click_element("event/gain_a_ego_depending_on_result.png"):
                event_chance -= 1
                continue

            # 如果需要罪人判定
            if self.auto.find_element("event/choices_assets.png") and self.auto.find_element(
                "event/select_first_option_assets.png"
            ):
                self.auto.click_element("event/select_first_option_assets.png")
                event_chance -= 1
            if self.auto.find_element("event/perform_the_check_feature_assets.png"):
                event_handling.decision_event_handling()
            if self.auto.click_element("event/continue_assets.png"):
                continue
            if self.auto.click_element("event/proceed_assets.png"):
                continue
            if self.auto.click_element("event/commence_assets.png"):
                continue
            if self.auto.click_element("event/commence_battle_assets.png"):
                continue

            if self.auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                continue

            if self.auto.click_element("event/skip_assets.png", times=6):
                continue

            loop_count -= 1
            if loop_count % 3 == 0:
                log.debug(f"事件处理识别次数剩余{loop_count}次")
            if loop_count < 20:
                self.auto.model = "normal"
                self.auto.mouse_to_blank(move_back=False)
                log.debug("识别模式切换到正常模式")
            if loop_count < 10:
                self.auto.model = "aggressive"
                log.debug("识别模式切换到激进模式")
            if loop_count < 0:
                log.error("无法解决事件,尝试回到初始界面")
                back_init_menu()
                break

        # 统计事件处理时间
        event_end_time = time.time()
        event_elapsed_time = event_end_time - event_start_time
        self.event_total_time += event_elapsed_time
        self.event_times += 1

    def acquire_ego_gift(self, type: int = 1):
        my_scale = self.config.set_win_size / 1440
        self.auto.model = "clam"
        self.auto.mouse_to_blank()
        if type == 2:
            pos = self.auto.find_element("mirror/road_in_mir/acquire_ego_gift_refuse_assets.png")
            self.auto.mouse_click(pos[0] - 500 * my_scale, pos[1] - 500 * my_scale)
            sleep(self.config.mouse_action_interval)
            self.auto.mouse_click(pos[0], pos[1] - 500 * my_scale)
            sleep(self.config.mouse_action_interval)
            self.auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
            time.sleep(2)
            if retry() is False:
                return False
            return
        while True:
            if self.auto.take_screenshot() is None:
                continue

            if self.auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                break
            try:
                acquire_card = self.auto.find_element(
                    "mirror/road_in_mir/acquire_ego_gift_card.png",
                    find_type="image_with_multiple_targets",
                )
                my_list = []
                if len(acquire_card) == 2:
                    for button in acquire_card:
                        bbox = (
                            button[0] - 50 * my_scale,
                            button[1] - 300 * my_scale,
                            button[0] + 450 * my_scale,
                            button[1] + 350 * my_scale,
                        )
                        if not self.config.not_skip_whitegossypium:
                            ocr_result = self.auto.find_language_text("白棉花", ["white", "gossypium"], bbox)
                            if isinstance(ocr_result, list):
                                if len(ocr_result) >= 2:
                                    continue
                        self.auto.mouse_click(button[0], button[1])
                        self.auto.click_element(
                            "mirror/road_in_mir/acquire_ego_gift_select_assets.png",
                            model="normal",
                        )
                        time.sleep(2)
                        if retry() is False:
                            return False
                        return
                elif len(acquire_card) == 1:
                    for button in acquire_card:
                        bbox = (
                            button[0] - 50 * my_scale,
                            button[1] - 300 * my_scale,
                            button[0] + 450 * my_scale,
                            button[1] + 350 * my_scale,
                        )
                        if not self.config.not_skip_whitegossypium:
                            ocr_result = self.auto.find_language_text("白棉花", ["white", "gossypium"], bbox)
                            if isinstance(ocr_result, list):
                                if len(ocr_result) >= 2:
                                    time.sleep(1)
                                    self.auto.click_element(
                                        "mirror/road_in_mir/refuse_gift_assets.png",
                                        take_screenshot=True,
                                    )
                                    sleep(1)
                                    self.auto.click_element(
                                        "mirror/road_in_mir/refuse_gift_confirm_assets.png",
                                        take_screenshot=True,
                                    )
                                    time.sleep(2)
                                    if retry() is False:
                                        return False
                                    return
                        self.auto.mouse_click(button[0], button[1])
                        time.sleep(1)
                        self.auto.click_element(
                            "mirror/road_in_mir/acquire_ego_gift_select_assets.png",
                            model="normal",
                        )
                        time.sleep(2)
                        if retry() is False:
                            return False
                        return
                else:
                    system_nums = 0
                    for button in acquire_card:
                        bbox = (
                            button[0] - 50 * my_scale,
                            button[1] - 300 * my_scale,
                            button[0] + 450 * my_scale,
                            button[1] + 350 * my_scale,
                        )
                        if not self.config.not_skip_whitegossypium:
                            ocr_result = self.auto.find_language_text("白棉花", ["white", "gossypium"], bbox)
                            if ocr_result:
                                continue
                        if self.auto.find_element(
                            f"mirror/road_in_mir/acquire_ego_gift/{self.system}.png",
                            my_crop=bbox,
                            threshold=0.85,
                        ):
                            my_list.insert(0, button)
                            system_nums += 1
                        else:
                            if self.second_system and (
                                self.second_system_setting == 0
                                or (self.second_system_setting == 1 and self.shop.fuse_IV)
                            ):
                                if self.auto.find_element(
                                    f"mirror/road_in_mir/acquire_ego_gift/{all_systems[self.second_system_select]}.png",
                                    my_crop=bbox,
                                    threshold=0.85,
                                ):
                                    my_list.insert(system_nums, button)
                                    continue
                            my_list.append(button)
                select_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/road_in_mir/ego_gift_get_bbox.png"))
                if select_bbox:
                    select_bbox = (
                        max(select_bbox[0] - 100, 0),  # 确保左上角 x 坐标不小于 0
                        max(select_bbox[1] - 100, 0),  # 确保左上角 y 坐标不小于 0
                        min(select_bbox[2] + 100, self.config.set_win_size * 16 / 9),  # 确保右下角 x 坐标不大于 图片宽
                        min(select_bbox[3] + 100, self.config.set_win_size),  # 确保右下角 y 坐标不大于 图片高
                    )
                if self.auto.find_text_element(["0/1", "01", "1/1", "11", "1/2", "12", "/1"], my_crop=select_bbox):
                    for gift in my_list[:1]:
                        self.auto.mouse_click(gift[0], gift[1])
                        sleep(self.config.mouse_action_interval)
                    self.auto.click_element(
                        "mirror/road_in_mir/acquire_ego_gift_select_assets.png",
                        model="normal",
                    )
                    time.sleep(2)
                    if retry() is False:
                        return False
                    return
                elif self.auto.find_text_element(["0/2", "02", "2/2", "22", "/2"], my_crop=select_bbox):
                    for gift in my_list[:2]:
                        self.auto.mouse_click(gift[0], gift[1])
                        sleep(self.config.mouse_action_interval)
                    self.auto.click_element(
                        "mirror/road_in_mir/acquire_ego_gift_select_assets.png",
                        model="normal",
                    )
                    time.sleep(2)
                    if retry() is False:
                        return False
                    return
                else:
                    for gift in my_list:
                        self.auto.mouse_click(gift[0], gift[1])
                        sleep(self.config.mouse_action_interval)
                    self.auto.click_element(
                        "mirror/road_in_mir/acquire_ego_gift_select_assets.png",
                        model="normal",
                    )
                    time.sleep(2)
                    if retry() is False:
                        return False
                    return

            except Exception as e:
                log.error(e)
                continue

    def get_reward_in_road(self):
        main_loop_count = 20
        self.auto.model = "clam"
        while True:
            if self.auto.take_screenshot() is None:
                self.auto.mouse_to_blank()
                continue
            # 如果回到主界面，退出循环
            if self.auto.click_element("mirror/claim_reward/rewards_acquired_assets.png"):
                return True
            if self.config.no_weekly_bonuses:
                bonuses = self.auto.find_element(
                    "mirror/claim_reward/weekly_bonuses.png",
                    find_type="image_with_multiple_targets",
                )
                if len(bonuses) >= 1:
                    for _ in range(len(bonuses)):
                        position = bonuses.pop(-1)
                        self.auto.mouse_click(position[0], position[1])
            if self.config.hard_mirror_single_bonuses:
                bonuses = self.auto.find_element(
                    "mirror/claim_reward/weekly_bonuses.png",
                    find_type="image_with_multiple_targets",
                )
                bonuses = sorted(bonuses, key=lambda x: x[0])
                if len(bonuses) > 1:
                    for _ in range(len(bonuses) - 1):
                        position = bonuses.pop(-1)
                        self.auto.mouse_click(position[0], position[1])
            if self.auto.click_element(
                "mirror/claim_reward/claim_rewards_confirm_assets.png",
                threshold=0.75,
                model="clam",
            ):
                continue
            if self.hard_switch and self.config.save_rewards:
                self.auto.click_element("mirror/claim_reward/claim_rewards_assets.png")
                sleep(1)
                pos = self.auto.find_element(
                    "mirror/claim_reward/use_enkephalin_assets.png",
                    take_screenshot=True,
                )
                if pos:
                    self.auto.mouse_click(pos[0] - 300 * (self.config.set_win_size / 1440), pos[1])
                    sleep(1)
                continue
            elif self.auto.click_element("mirror/claim_reward/claim_rewards_assets.png"):
                sleep(1)
                if self.auto.click_element(
                    "mirror/claim_reward/use_enkephalin_assets.png",
                    take_screenshot=True,
                ):
                    sleep(1)
                # TODO: 统计获取的coins
                continue
            if self.auto.click_element("mirror/claim_reward/use_enkephalin_assets.png", threshold=0.75):  # 降低识别阈值
                sleep(1)
                continue
            # 处理周年活动弹出的窗口
            if self.auto.click_element("home/close_anniversary_event_assets.png"):
                continue
            retry()
            main_loop_count -= 1
            if main_loop_count % 3 == 0:
                log.debug(f"镜牢奖励识别次数剩余{main_loop_count}次")
            if main_loop_count < 10:
                self.auto.model = "normal"
                self.auto.mouse_to_blank(move_back=False)
                log.debug("识别模式切换到正常模式")
            if main_loop_count < 5:
                self.auto.model = "aggressive"
                log.debug("识别模式切换到激进模式")
            if main_loop_count < 0:
                raise cannotOperateGameError("镜牢奖励领取出错,请手动操作重试")

    @begin_and_finish_time_log(task_name="镜牢商店")
    def in_shop(self):
        self.shop.in_shop(self.floor)

    def get_which_floor(self):
        def extract_floor_from_text(ocr_text):
            normalized_text = ocr_text.replace(" ", "").replace("\n", "").lower()
            if path_manager.current_language == "zh_cn":
                floor = extract_zh_floor(normalized_text)
            elif path_manager.current_language == "en":
                floor = extract_en_floor(normalized_text)
            else:
                floor = extract_zh_floor(normalized_text)
                if floor is not None:
                    path_manager.set_language("zh_cn")
                else:
                    floor = extract_en_floor(normalized_text)
                    if floor is not None:
                        path_manager.set_language("en")
                        if path_manager.eliminate_zh_cn_paths():
                            self.auto.clear_img_cache()
            if floor is None:
                return None
            return floor if 0 < floor <= 5 else None

        def handle_ocr(image, stage_name):
            ocr_result = ""
            try:
                result = ocr.run(image)
                if getattr(result, "txts", None):
                    ocr_result = "".join(result.txts)
                floor = extract_floor_from_text(ocr_result)
                if floor is not None:
                    log.debug(f"对于楼层信息OCR[{stage_name}]得到：{ocr_result}")
                    self.floor = floor
                    self.get_floor_num = False
                    return True, ocr_result
            except:
                pass
            return False, ocr_result

        this_floor = self.floor

        self.auto.take_screenshot(gray=False)
        get_floor_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/road_in_mir/get_floor_bbox.png"))
        previous_crop = ImageUtils.crop(np.array(self.auto.screenshot), get_floor_bbox)

        for i in range(5):
            self.auto.take_screenshot(gray=False)
            current_crop = ImageUtils.crop(np.array(self.auto.screenshot), get_floor_bbox)
            diff = cv2.absdiff(previous_crop, current_crop)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            _, binary_img = cv2.threshold(diff_gray, 5, 255, cv2.THRESH_BINARY)
            current_scaled = cv2.resize(current_crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            binary_img = cv2.resize(binary_img, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

            floor_found = False
            for stage_name, candidate_image in (
                ("current", current_crop),
                ("current_scaled", current_scaled),
                ("binary", binary_img),
            ):
                floor_found, _ = handle_ocr(candidate_image, stage_name)
                if floor_found:
                    break
            previous_crop = current_crop
            if floor_found and self.floor != this_floor:
                break

        log.debug(f"识别前楼层为{this_floor}，识别后为{self.floor}")

        if self.floor - 1 == self.mirror_map.floor:
            self.mirror_map.next_floor()
        elif self.floor == self.mirror_map.floor:
            pass
        else:
            self.mirror_map.refresh_floor(self.floor)
