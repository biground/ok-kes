from ok import TriggerTask

from utils import (
    handle_confirm,
    handle_enter,
    handle_close_page,
    handle_next_step,
    find_box_at_point,
)
from utils_chaos import handle_battle_auto_check


# ------------------------- 页面处理函数 -------------------------

# def handle_team_config(task: TriggerTask):
#     """队伍配置页面: 检测(0.122,0.047)处'配置队伍'文本，选择空槽位补充角色。"""
#     title_box = find_box_at_point(task, 0.122, 0.047)
#     if not (title_box and "配置队伍" in title_box.name):
#         return False
#     task.log_info("检测到队伍配置页面")
#     slots = [
#         (0.057, 0.611, 0.132, 0.456),
#         (0.270, 0.610, 0.344, 0.444),
#         (0.484, 0.608, 0.554, 0.436),
#     ]
#     for check_x, check_y, click_x, click_y in slots:
#         box = find_box_at_point(task, check_x, check_y)
#         if box is None or not box.name.strip():
#             task.log_info(f"槽位({check_x},{check_y})为空，点击({click_x},{click_y})补充角色")
#             task.click(click_x, click_y)
#             task.sleep(2)
#             return True
#     task.log_info("所有槽位已有角色，无需补充")
#     return False


def handle_enter_stage(task: TriggerTask):
    """入场按钮: 检测(0.820,0.931)位置的入场按钮并点击。"""
    box = find_box_at_point(task, 0.820, 0.931)
    if box and "入场" in box.name:
        task.log_info("检测到入场按钮，点击入场")
        task.click_box(box)
        task.sleep(1)
        return True
    return False


def handle_enter_story(task: TriggerTask):
    """可进入故事模式页面: 在指定区域内检测enterstory特征。"""
    box = task.box_of_screen(0.085, 0.124, 0.995, 0.874)
    boxes = task.find_feature(feature_name="enterstory", box=box)
    if boxes:
        task.log_info("检测到可进入故事模式，点击进入")
        task.click_box(boxes[0])
        task.sleep(2)
        return True
    return False


def handle_enter_battle(task: TriggerTask):
    """可进入战斗模式页面: 在指定区域内检测enterbattle特征。"""
    box = task.box_of_screen(0.085, 0.124, 0.995, 0.874)
    boxes = task.find_feature(feature_name="enterbattle", box=box, threshold=0.85)
    if boxes:
        for i, b in enumerate(boxes):
            task.log_info(f"  enterbattle匹配[{i}]: confidence={b.confidence:.4f}")
        task.log_info(f"检测到可进入战斗模式，点击进入（最高置信度={boxes[0].confidence:.2f}）")
        task.click_box(boxes[0])
        task.sleep(2)
        return True
    task.log_info("未检测到enterbattle特征")
    return False


def handle_skip_story(task: TriggerTask):
    """可跳过剧情页面: 检测到skipstory特征则点击跳过。"""
    boxes = task.find_feature(feature_name="skipstory")
    if boxes:
        task.log_info("检测到可跳过剧情页面，点击跳过")
        task.click_box(boxes[0])
        task.sleep(1)
        return True
    return False


def handle_observe(task: TriggerTask):
    """观测卡厄思关卡页面: 在区域内检测文本'观测'并点击。"""
    x1, y1, x2, y2 = 0.092, 0.214, 0.962, 0.792
    for b in task.all_texts:
        cx = (b.x + b.width / 2) / task.width
        cy = (b.y + b.height / 2) / task.height
        if x1 <= cx <= x2 and y1 <= cy <= y2 and b.name.strip() == "观测":
            task.log_info("检测到观测卡厄思关卡，点击观测")
            task.click_box(b)
            task.sleep(4)
            return True
    return False


# 剧情模式页面处理函数列表（按优先级排序）
PAGE_HANDLERS = [
    # handle_team_config,  #队伍配置（最高优先级）
    handle_confirm,  #确认按钮
    handle_enter,  #进入按钮
    handle_enter_stage,  #入场按钮
    handle_close_page,  #点击屏幕关闭页面
    handle_enter_story,
    handle_enter_battle,
    handle_skip_story,
    handle_observe,  #观测卡厄思关卡
    handle_next_step,
    handle_battle_auto_check,  #自动战斗检测
]