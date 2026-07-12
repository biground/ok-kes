from ok import TriggerTask

from utils import (
    handle_next_step,
    find_box_at_point,
)


# ------------------------- 页面处理函数 -------------------------

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
    boxes = task.find_feature(feature_name="enterbattle", box=box)
    if boxes:
        task.log_info("检测到可进入战斗模式，点击进入")
        task.click_box(boxes[0])
        task.sleep(2)
        return True
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


# 剧情模式页面处理函数列表（按优先级排序）
PAGE_HANDLERS = [
    handle_enter_stage,  #入场按钮
    handle_enter_story,
    handle_enter_battle,
    handle_skip_story,
    handle_next_step,
]