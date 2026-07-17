from ok import TriggerTask, og

import utils_sortie
from opencc import OpenCC
from config_io import make_export_callback, make_import_callback

_cc = OpenCC('t2s')  # 繁转简，用于OCR文本统一转换
_SORTIE_ENTRY_TITLE_AREA = (0.65, 0.10, 0.75, 0.18)
_GAME_LANGUAGE_BY_SORTIE_TITLE = {'出击': '简体中文', '出擊': '繁体中文'}


class SortieMode(TriggerTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自动出击模式"
        self.description = "1. 自动战斗依赖按键识别，请在游戏设置中打开快捷键显示，提升出牌准确率。\n2. 国际服玩家请到软件左下角设置页内将\"游戏语言\"设置为繁体中文。"
        self.instructions = """<a href="https://github.com/ok-oldking/ok-py">ok-py</a>"""
        self.trigger_interval = 1
        self.all_texts = []
        self.default_config["_enabled"] = False
        self.default_config["路线优先级"] = ["休息", "事件", "小怪", "boss"]
        self.default_config["主战员优先级"] = ["米卡", "尼娅", "蒂菲拉", "麦格纳", "卡修斯"]
        self.default_config["出战主战员优先级"] = ["海德玛丽", "九", "力", "绯"]
        self.default_config["获得卡牌优先级"] = ["展开极光", "剑雨", "一缕光芒","缕光芒","凝聚极光"]
        self.default_config["移除卡牌列表"] = ["剑幕"]
        self.default_config["复制卡牌列表"] = ["剑雨", "展开极光", "一缕光芒","缕光芒"]
        self.default_config["闪光卡牌列表"] = ["剑雨", "展开极光", "一缕光芒","缕光芒"]
        self.default_config["领取奖励"] = False
        self.default_config["出牌优先级"] = ["剑雨", "水之源", "一缕光芒", "万众英雄","极光剑", "展开极光","解放极光"]
        self.default_config["丢弃卡牌优先级"] = ["展开极光", "极光剑", "凝聚极光"]
        self.default_config["进入商店"] = False
        self.default_config["卡牌奖励优先级"] = ["梦之边境", "装备包"]
        self.default_config["任务优先级"] = ["选取随机3条命运","信用点增加", "移除"]
        self.default_config["命运优先级"] = [
            "丢弃诅咒", "移除的印记", "仓促移除", "轻盈的步伐", "轻量化", "切换战术", "战场武器", "守护盔甲",
            "生命的装饰", "受诅咒的遗物", "未来装备", "神圣锻造", "稀有装备专家", "敏捷的武装", "稀有装备收藏家",
            "收集扭曲", "收集调节", "精通：扭曲", "精通：调节", "靈機一動的靈感", "受诅咒的灵感", "意识重构",
            "神圣灵感", "维托的祝福", "戴奥斯的祝福", "赛克瑞德的祝福", "凯尔肯的祝福", "尼希隆的祝福", "卡利戈的祝福",
            "小小的奖励", "未知的引导", "黄金命运", "约定的命运", "银色的引导", "不稳定的契约", "无尽的贪婪",
            "粘稠的信用点数", "常客的特权", "强化攻势", "刹那的休息", "守护姿态", "集中攻势", "21", "翻涌的水波",
            "事前准备", "超出负荷的洞察", "点燃冲动", "不幸的否定", "最终幕", "红色命运", "蓝色命运", "优秀的调节",
            "唯一的审判者", "两条岔路",
        ]
        self.default_config["拉黑主战员"] = ["黛安娜", "阿黛尔海特"]
        self.default_config["跳过非优先级卡牌"] = True
        self.default_config["优先移除基础牌"] = True
        self.default_config["生命值大于多少优先闪光(百分比)"] = "60"
        # self.default_config["从右往左出牌"] = True
        self.node_status = {"shop": False, "flash_or_rest": False}

        self.config_type = {
            'export_config': {'type': 'button', 'text': '导出配置', 'callback': make_export_callback(self)},
            'import_config': {'type': 'button', 'text': '导入配置', 'callback': make_import_callback(self)},
        }

    def enable(self):
        """开启出击模式时自动禁用卡厄思模式。"""
        from ChaosMode import ChaosMode
        chaos = og.executor.get_task_by_class(ChaosMode)
        if chaos and chaos.enabled:
            chaos.disable()
        super().enable()

    def _ocr_and_simplify(self):
        """执行OCR并将所有识别文本转简体。"""
        texts = self.ocr()
        for b in texts:
            b.name = _cc.convert(b.name)
        return texts

    def fix_texts(self, detected_boxes):
        if not getattr(self, '_preserve_raw_ocr', False):
            super().fix_texts(detected_boxes)

    def _detect_game_language(self):
        if getattr(self, '_game_language_detected', False):
            return
        self._preserve_raw_ocr = True
        try:
            title_boxes = self.ocr(*_SORTIE_ENTRY_TITLE_AREA, threshold=0.8)
        finally:
            self._preserve_raw_ocr = False
        titles = {
            box.name for box in title_boxes or []
            if getattr(box, 'confidence', 0) >= 0.8 and box.name in _GAME_LANGUAGE_BY_SORTIE_TITLE
        }
        if len(titles) != 1:
            return
        evidence = titles.pop()
        new_language = _GAME_LANGUAGE_BY_SORTIE_TITLE[evidence]
        language_config = self.executor.global_config.get_config('游戏语言')
        old_language = language_config.get('游戏语言', '简体中文')
        self._game_language_detected = True
        self.log_info(
            f'自动检测游戏语言：检测依据「{evidence}」，旧值「{old_language}」，新值「{new_language}」'
        )
        if old_language != new_language:
            language_config['游戏语言'] = new_language
            from ok.gui.Communicate import communicate
            communicate.task_list_updated.emit()

    def run(self):
        self._detect_game_language()
        self.all_texts = self._ocr_and_simplify()
        for handle_page in utils_sortie.PAGE_HANDLERS:
            if handle_page(self):
                return
