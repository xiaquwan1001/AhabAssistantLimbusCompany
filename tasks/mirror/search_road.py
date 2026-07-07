import time
from time import sleep

import cv2

from module.automation import auto
from module.config import cfg
from module.logger import log
from module.my_error.my_error import InputAttributeError
from tasks.base.retry import retry
from tasks.mirror.constants import get_scale


class MirrorMap:
    def __init__(self, floor=1, hard_mode=False, automation=None, config=None):
        self.floor = floor
        self.floor_map = []
        self.map = {}
        self.hard_mode = hard_mode
        if automation is None:
            from mirror.infra.legacy_adapters import get_automation
            automation = get_automation()
        if config is None:
            from mirror.infra.legacy_adapters import get_config
            config = get_config()
        self.auto = automation
        self.config = config

    def get_next_step(self):
        re_identify = False
        if len(self.floor_map) > 0:
            next_step = self.floor_map.pop(0)
            if next_step is not None:
                return next_step
            else:
                re_identify = True
        else:
            re_identify = True

        if re_identify is True:
            self.floor_map, self.floor_nodes = search_road_from_road_map(hard_mode=self.hard_mode)
            if self.floor_map is True and self.floor_nodes is True:
                return True
            if not isinstance(self.floor_map, list):
                self.floor_map = list(self.floor_map)
            self.map[f"floor{self.floor}"] = [self.floor_map[:], self.floor_nodes[:]]

        if len(self.floor_map) > 0:
            next_step = self.floor_map.pop(0)
            return next_step
        else:
            return False

    def enter_next_node(self, next_step):
        if self.config.mirror_keyboard_navigation:
            log.debug(f"通过键盘按键寻路: {next_step}")
            if next_step == "U":
                self.auto.key_press("up")
            elif next_step == "D":
                self.auto.key_press("down")
            elif next_step == "M":
                self.auto.key_press("right")
            sleep(0.5)
            self.auto.key_press("enter")
            sleep(1.25)
            if self.auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
            return True

        if next_position := self._get_next_position(next_step):
            self.auto.mouse_click(next_position[0], next_position[1])
            sleep(1.25)
            if self.auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
        if self.auto.click_element("mirror/mybus_default_distance.png", take_screenshot=True):
            sleep(1.25)
            if self.auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
        return False

    def _get_next_position(self, direction):
        scale = get_scale()
        three_roads = [
            [500 * scale, 50 * scale],
            [500 * scale, 450 * scale],
            [500 * scale, -400 * scale],
        ]
        if direction == "M":
            position = 0
        elif direction == "D":
            position = 1
        elif direction == "U":
            position = 2
        for _ in range(3):
            if bus_position := self.auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
                return [
                    bus_position[0] + three_roads[position][0],
                    bus_position[1] + three_roads[position][1],
                ]
            sleep(1)
        return None

    def next_floor(self):
        self.floor += 1
        self.floor_map = []

    def refresh_floor(self, floor):
        self.floor = floor



# TODO(strangler): inject via parameter
def get_node_weight(x, y):
    scale = get_scale()
    road_node_bbox = (
        x - 125 * scale,
        y - 125 * scale,
        x + 125 * scale,
        y + 125 * scale,
    )
    if auto.find_feature_element("mirror/road_in_mir/shop.png", road_node_bbox, 50):
        return 3
    elif auto.find_feature_element("mirror/road_in_mir/event.png", road_node_bbox):
        return 3
    elif auto.find_feature_element(
        "mirror/road_in_mir/battle.png",
        road_node_bbox,
    ):
        return 2
    elif auto.find_feature_element("mirror/road_in_mir/hard_battle.png", road_node_bbox):
        return 1
    elif auto.find_feature_element("mirror/road_in_mir/hard_battle2.png", road_node_bbox):
        return 0
    return -5


# 在默认缩放情况下，进行镜牢寻路
# TODO(strangler): inject via parameter
def search_road_default_distance():
    """默认缩放距离下的镜牢寻路。先检测权重3节点，再遍历全部节点。"""
    start_time = time.time()
    scale = get_scale()
    three_roads = _make_three_roads(scale)

    auto.mouse_to_blank()
    while auto.take_screenshot() is None:
        continue
    if retry() is False:
        return False

    # 优先选择高权重节点
    if _try_weighted_node(three_roads[:2], scale):
        return True

    bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
    if bus_position is None:
        return False

    # 将 bus 拖到垂直中心
    bus_position = _drag_bus_to_center(bus_position, scale, start_time)
    if bus_position is None:
        return False

    # 遍历所有节点，选权重最大的
    node_list = _build_node_list(bus_position, three_roads)
    all_node_weight = _compute_node_weights(bus_position, three_roads, node_list)
    for road in sorted(all_node_weight, key=all_node_weight.get, reverse=True):
        if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
            auto.mouse_click(road[0], road[1])
            sleep(0.75)
            if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
    return False


def _make_three_roads(scale: float) -> list:
    """返回三条寻路偏移量 [x, y]。"""
    return [
        [500 * scale, 50 * scale],
        [500 * scale, 450 * scale],
        [500 * scale, -400 * scale],
    ]


# TODO(strangler): inject via parameter
def _try_weighted_node(roads: list, scale: float) -> bool:
    """检测 roads 中是否有权重3的节点，直接选择进入。"""
    if not (bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)):
        return False
    node_weight = {}
    for road in roads:
        weight = get_node_weight(bus_position[0] + road[0], bus_position[1] + road[1])
        node_weight[(bus_position[0] + road[0], bus_position[1] + road[1])] = weight
    if max(node_weight.values()) == 3:
        road_list = sorted(node_weight, key=node_weight.get, reverse=True)
        road = road_list[0]
        if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
            auto.mouse_click(road[0], road[1])
            sleep(0.75)
            if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
    return False


# TODO(strangler): inject via parameter
def _drag_bus_to_center(bus_position, scale: float, start_time: float):
    """将 bus 拖动到垂直中心区域 (600-700 y)。"""
    from tasks.base.retry import check_times

    while True:
        if auto.get_restore_time() is not None:
            start_time = max(start_time, auto.get_restore_time())
        if check_times(start_time, logs=False):
            from tasks.base.back_init_menu import back_init_menu
            back_init_menu()
            return None
        if 600 * scale < bus_position[1] < 700 * scale:
            break
        dy = 650 * scale - bus_position[1]
        auto.mouse_drag(bus_position[0], bus_position[1], drag_time=1.5, dx=0, dy=dy)
        sleep(1)
        auto.mouse_to_blank()
        bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
        if bus_position is None:
            break
    return bus_position


def _build_node_list(bus_position, three_roads: list) -> list:
    """构建三条路的节点坐标列表（中、下两路）。"""
    node_list = []
    for road in three_roads[:2]:
        node_list.append((bus_position[0] + road[0], bus_position[1] + road[1]))
    return node_list


def _compute_node_weights(bus_position, three_roads: list, node_list: list) -> dict:
    """计算中下上路所有节点的权重。返回 {坐标: 权重}。"""
    all_node_weight = dict(zip(node_list, [get_node_weight(x, y) for x, y in node_list]))
    for road in three_roads[2:]:
        all_node_weight[(bus_position[0] + road[0], bus_position[1] + road[1])] = get_node_weight(
            bus_position[0] + road[0], bus_position[1] + road[1]
        )
    all_node_weight[bus_position[0], bus_position[1]] = -6
    return all_node_weight


# 如果默认缩放无法镜牢寻路，进行滚轮缩放后继续寻路
# TODO(strangler): inject via parameter
def search_road_farthest_distance():
    scale = get_scale()
    auto.mouse_click_blank()
    if not auto.mouse_scroll():
        raise InputAttributeError("后台输入不支持滚轮操作!")
    while auto.take_screenshot() is None:
        continue
    if retry() is False:
        return False
    three_roads = [
        [250 * scale, -200 * scale],
        [250 * scale, 0],
        [250 * scale, 225 * scale],
    ]
    if bus_position := auto.find_element("mirror/mybus_maximum_distance.png"):
        for road in three_roads:
            road[0] += bus_position[0]
            road[1] += bus_position[1]
            if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
                auto.mouse_click(road[0], road[1])
                sleep(0.75)
                if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                    return True
        auto.mouse_click(bus_position[0], bus_position[1])
        if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
            return True
    return False


# TODO(strangler): inject via parameter
def search_road_from_road_map(hard_mode=False):
    """使用路网地图进行寻路。返回 (directions, road_class_list) 或 (False, [])。"""
    start_time = time.time()
    scale = get_scale()
    road = []
    bus = None

    if auto.click_element("mirror/mybus_default_distance.png", take_screenshot=True):
        sleep(0.75)
        if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
            return True, True

    bus = _align_bus_to_target(start_time, scale)
    if bus is None:
        return False, []

    bus_pos = auto.find_element("mirror/mybus_default_distance.png")
    all_nodes = identify_nodes(bus[0])
    if all_nodes is None:
        return [], []

    y_area = divide_the_area_by_y(all_nodes)
    reset_position = False
    initial_bus_pos = Position.MID

    if len(y_area) == 2:
        if bus_pos[1] > y_area[0][0][1][1] + 50 * scale:
            reset_position = "Bottom"
            initial_bus_pos = Position.BOTTOM
        else:
            reset_position = "Top"
            initial_bus_pos = Position.TOP
    elif len(y_area) == 1:
        all_road = divide_the_area_by_x(identify_road(bus[0]))
        if len(all_road) == 0:
            road = ["M"]
        else:
            road = ["D"] if all_road[0][0][0] == "DOWN" else ["U"]

    if reset_position:
        bus = _reposition_bus_by_y(start_time, scale, reset_position)
        if bus is None:
            return False, []
        all_nodes = identify_nodes(bus[0])
        if all_nodes is None:
            return [], []

    if road:
        return road, ["unknown"]

    return _build_and_search_route(all_nodes, bus, initial_bus_pos, hard_mode)


# TODO(strangler): inject via parameter
def _align_bus_to_target(start_time: float, scale: float):
    """将 bus 拖动到目标位置（675-700 y, <150 x）。返回 bus 坐标或 None。"""
    from tasks.base.retry import check_times

    bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
    if bus_position is None:
        return None
    change_times = 5
    while True:
        if auto.get_restore_time() is not None:
            start_time = max(start_time, auto.get_restore_time())
        if check_times(start_time, logs=False):
            from tasks.base.back_init_menu import back_init_menu
            back_init_menu()
            return None
        if 675 * scale < bus_position[1] < 700 * scale and 150 * scale > bus_position[0]:
            return bus_position
        dx = 80 * scale - bus_position[0]
        dy = 690 * scale - bus_position[1]
        auto.mouse_drag(bus_position[0], bus_position[1], drag_time=1.5, dx=dx, dy=dy)
        sleep(0.5)
        auto.mouse_to_blank()
        bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
        if bus_position is None:
            return None
        change_times -= 1
        if change_times <= 0:
            return bus_position


# TODO(strangler): inject via parameter
def _reposition_bus_by_y(start_time: float, scale: float, reset_position: str):
    """根据 y 区域重定位 bus。返回 bus 坐标或 None。"""
    from tasks.base.retry import check_times

    set_y_position = 1100 * scale if reset_position == "Bottom" else 250 * scale
    bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
    if bus_position is None:
        return None

    while True:
        if auto.get_restore_time() is not None:
            start_time = max(start_time, auto.get_restore_time())
        if check_times(start_time, logs=False):
            from tasks.base.back_init_menu import back_init_menu
            back_init_menu()
            return None
        if (
            set_y_position - 50 * scale < bus_position[1] < set_y_position + 50 * scale
            and 500 * scale < bus_position[0] < 600 * scale
        ):
            return bus_position
        dx = 550 * scale - bus_position[0]
        dy = set_y_position - bus_position[1]
        auto.mouse_drag(bus_position[0], bus_position[1], drag_time=1.5, dx=dx, dy=dy)
        sleep(0.5)
        auto.mouse_to_blank()
        bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
        if bus_position is None:
            return None


# TODO(strangler): inject via parameter
def _build_and_search_route(all_nodes, bus, initial_bus_pos, hard_mode):
    """构建路由图并搜索最优路径。返回 (directions, road_class_list)。"""
    bus_pos = auto.find_element("mirror/mybus_default_distance.png")
    all_nodes_layer = divide_the_area_by_x(all_nodes)
    all_road = divide_the_area_by_x(identify_road(bus[0]))

    route_graph = RouteGraph(all_nodes_layer, initial_bus_pos=initial_bus_pos, hard_mode=hard_mode)
    route_graph.init_road(all_road, bus[0], bus_pos[1])

    min_weight, path = route_graph.find_min_weight_route()
    if path:
        directions, road_class_list = route_graph.get_path_directions(path)
        log.debug(f"最小权重: {min_weight}")
        log.debug(f"路径方向: {directions}")
        log.debug(f"行走路径: {road_class_list}")
        return directions, road_class_list

    log.warning("未能检测到有效路径")
    return [], []


# battle 是常规遭遇战，boss_battle 是boss战，event 是事件，hard_battle 是集中遭遇战（非拉链），hard_battle_2 是精锐遭遇战（有拉链）
# shop 是商店，small_boss_battle 是异想体遭遇战


def identify_nodes(bus_x):
    """使用 ONNX YOLO 模型检测镜牢节点。返回 [class_name, (x, y)] 列表，无结果返回 None。"""
    detections = _run_yolo_inference()
    if detections is None:
        return None
    return _yolo_detections_to_nodes(detections, bus_x)


# ── ONNX YOLO 引擎（session 缓存，惰性加载） ──

_ONNX_SESSION = None
_ONNX_CLASSES = [
    "battle", "boss_battle", "event", "hard_battle",
    "hard_battle_2", "shop", "small_boss_battle",
]


def _get_onnx_session():
    """获取缓存的 ONNX 推理 session（惰性初始化）。"""
    global _ONNX_SESSION
    if _ONNX_SESSION is None:
        import onnxruntime as ort
        _ONNX_SESSION = ort.InferenceSession("./assets/model/best.onnx")
    return _ONNX_SESSION


# TODO(strangler): inject via parameter
def _run_yolo_inference() -> list | None:
    """截图 → YOLO 推理 → NMS 后处理。返回检测结果列表，无结果返回 None。"""
    import numpy as np

    session = _get_onnx_session()

    auto.take_screenshot(gray=False)
    original_image: np.ndarray = np.array(auto.screenshot)
    height, width = original_image.shape[:2]
    length = max(height, width)
    image = np.zeros((length, length, 3), np.uint8)
    image[0:height, 0:width] = original_image
    scale = length / 640

    blob = cv2.dnn.blobFromImage(image, scalefactor=1 / 255, size=(640, 640), swapRB=True)
    outputs = session.run(None, {session.get_inputs()[0].name: blob})
    outputs = outputs[0]
    outputs = np.array([cv2.transpose(outputs[0])])
    rows = outputs.shape[1]

    boxes, scores, class_ids = [], [], []
    for i in range(rows):
        classes_scores = outputs[0][i][4:]
        (_, maxScore, _, (_, maxClassIndex)) = cv2.minMaxLoc(classes_scores)
        if maxScore < 0.25:
            continue
        box = [
            outputs[0][i][0] - (0.5 * outputs[0][i][2]),
            outputs[0][i][1] - (0.5 * outputs[0][i][3]),
            outputs[0][i][2],
            outputs[0][i][3],
        ]
        boxes.append(box)
        scores.append(maxScore)
        class_ids.append(maxClassIndex)

    result_boxes = cv2.dnn.NMSBoxes(boxes, scores, 0, 0.4, 0.5)
    if len(result_boxes) == 0:
        return None

    detections = []
    for i in range(len(result_boxes)):
        index = result_boxes[i]
        box = boxes[index]
        detections.append({
            "class_id": class_ids[index],
            "class_name": _ONNX_CLASSES[class_ids[index]],
            "confidence": scores[index],
            "box": box,
            "scale": scale,
        })
    return detections


def _yolo_detections_to_nodes(detections: list, bus_x: float) -> list:
    """将 YOLO 检测结果转换为 [(class_name, (x, y)), ...]，过滤 bus 左侧的杂点。"""
    import numpy as np

    node_list = []
    for d in detections:
        box = d["box"]
        x1 = box[0].item()
        y1 = box[1].item()
        w = box[2].item()
        h = box[3].item()
        center_x = int((x1 + w / 2) * d["scale"])
        center_y = int((y1 + h / 2) * d["scale"])
        if center_x < bus_x + 50:
            continue
        node_list.append([d["class_name"], (center_x, center_y)])
    return node_list


# TODO(strangler): inject via parameter
def identify_road(bus_x, min_length=160, merge_distance=230):
    """
    增强版LSD对角线检测，完整输出模块，显示方向标记和中心点
    """
    import math

    import numpy as np

    min_length = min_length * get_scale()

    auto.take_screenshot()
    screenshot = np.array(auto.screenshot)
    raw_lines = _lsd_detect_lines(screenshot)
    if raw_lines is None or len(raw_lines) == 0:
        log.warning("⚠️ 未检测到任何线段")
        return []

    segments_data = _parse_segments(raw_lines)
    diagonal_candidates = _filter_diagonal_candidates(segments_data, min_length)
    if not diagonal_candidates:
        return []

    merged_records = _merge_lines(diagonal_candidates, merge_distance, min_length)

    return _build_segment_list(merged_records, bus_x)


def _lsd_detect_lines(img) -> list | None:
    """LSD 线段检测。返回原始线段数据或 None。"""
    lsd = cv2.createLineSegmentDetector(0)
    detected = lsd.detect(img)
    if detected and detected[0] is not None:
        return detected[0]
    return None


def _parse_segments(raw_lines: list) -> list:
    """将原始 LSD 输出解析为结构化 segment 字典列表。"""
    import math

    segments_data = []
    for line_info in raw_lines:
        try:
            coords = line_info[0] if hasattr(line_info, "__len__") else line_info
            x1, y1, x2, y2 = map(float, coords[:4])
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            slope = dy / dx if dx != 0 else float("inf")
            angle = math.degrees(math.atan2(dy, dx)) % 180
            segments_data.append({
                "line": [int(x1), int(y1), int(x2), int(y2)],
                "length": length,
                "center": (center_x, center_y),
                "slope": slope,
                "angle": angle,
                "dx": dx,
                "dy": dy,
            })
        except Exception:
            continue
    return segments_data


def _filter_diagonal_candidates(segments_data: list, min_length: float) -> list:
    """筛选长度 >= min_length 的对角线段，不足时放宽到 50px。"""
    candidates = [s for s in segments_data if min_length <= s["length"] < 1000]
    if not candidates:
        candidates = [s for s in segments_data if 50 <= s["length"] < 1000]
    return candidates


def _merge_lines(diagonal_candidates: list, merge_distance: float, min_length: float) -> list:
    """按斜率/角度合并相邻线段。返回合并后的线段记录列表。"""
    import math
    import numpy as np

    merged_records = []
    for direction_name, angle_limits in [("45°", (30, 60)), ("135°", (120, 150))]:
        group = [s for s in diagonal_candidates if angle_limits[0] <= s["angle"] <= angle_limits[1]]
        if not group:
            continue
        group.sort(key=lambda x: x["length"], reverse=True)
        used = set()

        for i, base_info in enumerate(group):
            if i in used:
                continue
            cluster = [base_info]
            base_slope = base_info["slope"]
            base_center = base_info["center"]

            for j, other in enumerate(group):
                if j <= i or j in used:
                    continue
                slope_diff = abs(base_slope - other["slope"]) if base_slope != float("inf") else 0
                if slope_diff > 8 and base_slope != float("inf"):
                    continue
                distance = math.sqrt(
                    (base_center[0] - other["center"][0]) ** 2
                    + (base_center[1] - other["center"][1]) ** 2
                )
                if distance <= merge_distance:
                    cluster.append(other)
                    used.add(j)

            all_x = [pt[0] for info in cluster for pt in [info["line"][:2], info["line"][2:]]]
            all_y = [pt[1] for info in cluster for pt in [info["line"][:2], info["line"][2:]]]

            if len(set(all_x)) > 1:
                slope, intercept = np.polyfit(all_x, all_y, 1)
                min_x, max_x = int(min(all_x)), int(max(all_x))
                y_min = int(slope * min_x + intercept)
                y_max = int(slope * max_x + intercept)
                new_line = [min_x, y_min, max_x, y_max]
                new_center = ((min_x + max_x) / 2, (y_min + y_max) / 2)
                new_slope = slope
            else:
                new_line = cluster[0]["line"]
                new_center = cluster[0]["center"]
                new_slope = cluster[0]["slope"]

            merged_length = math.sqrt(
                (new_line[2] - new_line[0]) ** 2 + (new_line[3] - new_line[1]) ** 2
            )
            if merged_length >= min_length:
                merged_records.append({
                    "line": new_line,
                    "center": new_center,
                    "slope": new_slope,
                    "direction": direction_name,
                    "length": merged_length,
                    "merged_from": len(cluster),
                })
    return merged_records


def _build_segment_list(merged_records: list, bus_x: float) -> list:
    """将合并后的线段记录转换为最终输出格式，过滤 bus 左侧杂点。"""
    segment_list = []
    for segment in merged_records:
        class_name = "DOWN" if segment["direction"] == "45°" else "UP"
        center = segment["center"]
        if center[0] < bus_x + 50 * get_scale():
            continue
        segment_list.append([class_name, center])

    # 返回结构化数据
    return segment_list


def divide_the_area_by_y(data):
    # 步骤1：按y坐标从小到大排序（确保相近的y相邻）
    sorted_by_y = sorted(data, key=lambda item: item[1][1])  # item[1]是坐标元组，item[1][1]是y值

    # 步骤2：分组（y相近的归为一组，阈值可根据需求调整）
    tolerance = 20  # y差值小于等于20视为相近（可根据实际数据调整）
    groups = []
    for item in sorted_by_y:
        current_y = item[1][1]
        if not groups:
            # 第一个元素，新建组
            groups.append([item])
        else:
            # 检查当前元素与最后一个组的最后一个元素的y差值
            last_group_last_y = groups[-1][-1][1][1]
            if current_y - last_group_last_y <= tolerance:
                # 加入最后一个组
                groups[-1].append(item)
            else:
                # 新建组
                groups.append([item])
    return groups


def divide_the_area_by_x(data):
    # 步骤1：按x坐标从小到大排序（确保相近的x相邻）
    sorted_by_x = sorted(data, key=lambda item: item[1][0])

    # 步骤2：分组（x相近的归为一组，阈值可根据需求调整）
    tolerance = 80  # x差值小于等于tolerance视为相近
    groups = []
    for item in sorted_by_x:
        current_x = item[1][0]
        if not groups:
            # 第一个元素，新建组
            groups.append([item])
        else:
            # 检查当前元素与最后一个组的最后一个元素的x差值
            last_group_last_x = groups[-1][-1][1][0]
            if current_x - last_group_last_x <= tolerance:
                # 加入最后一个组
                groups[-1].append(item)
            else:
                # 新建组
                groups.append([item])

    # 步骤3：每个组内按y坐标从小到大排序
    for group in groups:
        group.sort(key=lambda item: item[1][1])

    log.debug(f"识别到的节点/线段分组后：{groups}")

    return groups


import heapq
from enum import Enum

all_node_weight = {
    "battle": 30,
    "boss_battle": 1,
    "event": 18,
    "hard_battle": 75,
    "hard_battle_2": 100,
    "shop": 1,
    "small_boss_battle": 999,
}

DEFAULT_WEIGHT = 999  # 默认不可达权重
MID_LINE_THRESHOLD = 100  # 中间线偏移阈值


class Position(Enum):
    TOP = 1  # 上层位置
    MID = 0  # 中层位置
    BOTTOM = -1  # 下层位置


class Node:
    def __init__(self, node_class: str = None, weight: float = DEFAULT_WEIGHT):
        self.node_class = node_class  # 节点标识
        self.weight = weight  # 节点权重
        self.next_nodes = []  # 指向的下一层节点列表（Node对象）

    def add_next_node(self, next_node) -> None:
        """添加下一层节点（自动去重）"""
        if next_node not in self.next_nodes:
            self.next_nodes.append(next_node)

    def __repr__(self):
        return f"Node({self.node_class}, 权重={self.weight}, 指向={self.next_nodes})"


class RouteGraph:
    def __init__(
        self,
        all_nodes: list,
        initial_bus_pos=Position.MID,
        mid_line=560,
        hard_mode=False,
    ):
        """
        初始化路线图
        """
        self.initial_bus_pos = initial_bus_pos  # 保存初始公交位置
        self.layer_nums = 0
        self.layers = {}  # 存储各层节点
        self._add_new_layer()
        self._set_node(1, initial_bus_pos, "bus", 1)
        self.mid_line = mid_line * get_scale(1080)
        self.hard_mode = hard_mode

        self._init_node(all_nodes, self.mid_line)

    def _add_new_layer(self):
        self.layers[f"layer{self.layer_nums + 1}"] = {
            Position.TOP: Node(),
            Position.MID: Node(),
            Position.BOTTOM: Node(),
        }
        self.layer_nums += 1

    def _set_node(self, layer_nums, position, class_name, weight):
        this_layer = self.layers[f"layer{layer_nums}"]
        this_layer[position].node_class = class_name
        this_layer[position].weight = weight

    def _init_node(self, all_nodes, mid_line):
        for layer_data in all_nodes:
            self._add_new_layer()
            for node_entry in layer_data:
                vertical_pos = Position.MID
                if node_entry[1][1] < mid_line - MID_LINE_THRESHOLD * get_scale():
                    vertical_pos = Position.TOP
                elif node_entry[1][1] > mid_line + MID_LINE_THRESHOLD * get_scale():
                    vertical_pos = Position.BOTTOM
                self._set_node(
                    self.layer_nums,
                    vertical_pos,
                    node_entry[0],
                    all_node_weight[node_entry[0]],
                )

        for i in range(1, self.layer_nums):
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if (
                    self.layers[f"layer{i}"][j].weight != DEFAULT_WEIGHT
                    and self.layers[f"layer{i + 1}"][j].weight != DEFAULT_WEIGHT
                ):
                    self.layers[f"layer{i}"][j].add_next_node(self.layers[f"layer{i + 1}"][j])

        if self.hard_mode is False:
            exit_flag = False
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if self.layers[f"layer{self.layer_nums}"][j].node_class in [
                    "shop",
                    "boss_battle",
                ]:
                    exit_flag = True
                    break
            if exit_flag is False:
                self._add_new_layer()
                self._set_node(self.layer_nums, Position.MID, "shop", 1)
                for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                    self.layers[f"layer{self.layer_nums - 1}"][j].add_next_node(
                        self.layers[f"layer{self.layer_nums}"][Position.MID]
                    )

            exit_flag = False
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if self.layers[f"layer{self.layer_nums}"][j].node_class in ["boss_battle"]:
                    exit_flag = True
                    break
            if exit_flag is False:
                self._add_new_layer()
                self._set_node(self.layer_nums, Position.MID, "boss_battle", 1)
                for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                    self.layers[f"layer{self.layer_nums - 1}"][j].add_next_node(
                        self.layers[f"layer{self.layer_nums}"][Position.MID]
                    )

    def init_road(self, all_road, bus_x, bus_y):
        if self.hard_mode is True:
            if len(all_road) > 2:
                all_road = all_road[:2]
        road_layer = 1
        for layer_road in all_road:
            if layer_road[0][1][0] < bus_x:
                continue
            for road in layer_road:
                if road[0] == "UP":
                    vertical_pos = Position.MID if bus_y > road[1][1] else Position.BOTTOM
                    if (
                        self.layers[f"layer{road_layer}"][vertical_pos].weight != DEFAULT_WEIGHT
                        and self.layers[f"layer{road_layer + 1}"][Position(vertical_pos.value + 1)].weight
                        != DEFAULT_WEIGHT
                    ):
                        self.layers[f"layer{road_layer}"][vertical_pos].add_next_node(
                            self.layers[f"layer{road_layer + 1}"][Position(vertical_pos.value + 1)]
                        )
                elif road[0] == "DOWN":
                    vertical_pos = Position.TOP if bus_y > road[1][1] else Position.MID
                    if (
                        self.layers[f"layer{road_layer}"][vertical_pos].weight != DEFAULT_WEIGHT
                        and self.layers[f"layer{road_layer + 1}"][Position(vertical_pos.value - 1)].weight
                        != DEFAULT_WEIGHT
                    ):
                        self.layers[f"layer{road_layer}"][vertical_pos].add_next_node(
                            self.layers[f"layer{road_layer + 1}"][Position(vertical_pos.value - 1)]
                        )
            road_layer += 1

    def get_node_layer_info(self, node: Node) -> tuple:
        """辅助方法：获取节点所在的层号、层内位置"""
        for layer_key, layer_nodes in self.layers.items():
            for pos, n in layer_nodes.items():
                if n == node:
                    layer_number = int(layer_key.replace("layer", ""))
                    return layer_key, layer_number, pos
        return None, None, None

    def find_min_weight_route(self) -> tuple[float, list[Node]]:
        """
        使用Dijkstra算法计算从入口到出口的最小权重路径
        返回：(最小总权重, 路径节点列表)
        """
        # 确定起点节点（layer1的初始公交位置）
        start_node = self.layers["layer1"][self.initial_bus_pos]

        # 收集所有终点节点（boss_battle）
        end_nodes = []
        for layer in self.layers.values():
            for pos_node in layer.values():
                if pos_node.node_class in ["boss_battle"]:
                    end_nodes.append(pos_node)

        if not end_nodes:
            # 确定目标层：至多三层，取当前最大层（不超过3）
            current_max_layer = self.layer_nums
            target_layer_num = min(current_max_layer, 3)
            target_layer = f"layer{target_layer_num}"

            # 检查目标层是否存在
            if target_layer not in self.layers:
                return float("inf"), []  # 目标层不存在，无法到达

            # 收集目标层的所有节点
            target_nodes = list(self.layers[target_layer].values())
            if not target_nodes:
                return float("inf"), []  # 目标层无节点，无法到达

            # 初始化距离字典，所有节点初始距离为无穷大，起点距离为自身权重
            distances = {
                node: float("inf")
                for layer in self.layers.values()
                for pos_node in layer.values()
                for node in [pos_node]
            }
            distances[start_node] = start_node.weight

            # 优先队列：(当前总权重, 节点唯一标识（避免比较Node）, 当前节点, 路径列表)
            heap = []
            heapq.heappush(heap, (start_node.weight, id(start_node), start_node, [start_node]))

            # 记录已处理的节点
            processed = set()

            min_total = float("inf")
            min_path = []

            while heap:
                current_total, _, current_node, current_path = heapq.heappop(heap)

                if current_node in processed:
                    continue
                processed.add(current_node)

                # 检查是否是目标节点（目标层的节点）
                if current_node in target_nodes:
                    # 更新最小路径
                    if current_total < min_total:
                        min_total = current_total
                        min_path = current_path.copy()

                # 遍历所有邻接节点
                for next_node in current_node.next_nodes:
                    if next_node in processed:
                        continue  # 已处理过，跳过

                    new_total = current_total + next_node.weight
                    new_path = current_path + [next_node]

                    # 如果找到更短路径，更新距离并加入队列
                    if new_total < distances[next_node]:
                        distances[next_node] = new_total
                        heapq.heappush(heap, (new_total, id(next_node), next_node, new_path))

            # 返回找到的最小路径，若没有则返回无穷大和空列表
            return (min_total, min_path) if min_total != float("inf") else (float("inf"), [])

        # 初始化距离字典，所有节点初始距离为无穷大，起点距离为自身权重
        distances = {
            node: float("inf") for layer in self.layers.values() for pos_node in layer.values() for node in [pos_node]
        }
        distances[start_node] = start_node.weight

        # 优先队列：(当前总权重, 节点唯一标识（避免比较Node）, 当前节点, 路径列表)
        heap = []
        heapq.heappush(heap, (start_node.weight, id(start_node), start_node, [start_node]))

        # 记录已处理的节点（优化：当节点第一次弹出时，已找到最短路径）
        processed = set()

        while heap:
            current_total, _, current_node, current_path = heapq.heappop(heap)  # 忽略辅助标识

            if current_node in processed:
                continue
            processed.add(current_node)

            # 到达终点，返回结果
            if current_node in end_nodes:
                return current_total, current_path

            # 遍历所有邻接节点
            for next_node in current_node.next_nodes:
                if next_node in processed:
                    continue  # 已处理过，跳过

                new_total = current_total + next_node.weight
                new_path = current_path + [next_node]

                # 如果找到更短路径，更新并加入队列
                if new_total < distances[next_node]:
                    distances[next_node] = new_total
                    # 添加辅助标识（id(next_node)）确保堆能正确排序
                    heapq.heappush(heap, (new_total, id(next_node), next_node, new_path))

        # 无可达路径
        return float("inf"), []

    def get_path_directions(self, path: list[Node]) -> tuple[list[str], list[str]]:
        """
        根据路径节点列表生成移动方向列表（U/D/M）和节点类别列表
        U: 下一个节点在当前节点上方，D: 下方，M: 同一层
        返回：(方向列表, 节点类别列表)
        """
        directions = []
        # 提取路径中所有节点的类别
        class_list = [node.node_class for node in path]

        if len(path) < 2:
            return directions, class_list  # 路径长度不足，无方向，但仍返回类别列表

        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]

            # 获取当前节点和下一个节点的层内位置
            _, _, current_pos = self.get_node_layer_info(current_node)
            _, _, next_pos = self.get_node_layer_info(next_node)

            if next_pos.value > current_pos.value:
                directions.append("U")  # 下一层更上层
            elif next_pos.value < current_pos.value:
                directions.append("D")  # 下一层更下层
            else:
                directions.append("M")  # 同一层

        return directions, class_list
