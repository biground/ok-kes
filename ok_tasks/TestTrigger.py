from ok import TriggerTask
import re

_hand_card_region = (0.159, 0.683, 0.836, 0.831)

def _card_key(text):
    table = str.maketrans("①②③④⑤⑥⑦⑧⑨⑩❶❷❸❹❺❻❼❽❾❿⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾０１２３４５６７８９",
                         "1234567890123456789012345678900123456789")
    text = text.translate(table)
    m = re.search(r"\d", text)
    return m.group(0) if m else None


def _read_hand_count(boxes, width, height):
    """从OCR结果中读取底部手牌数 x/10"""
    for b in boxes:
        cx = (b.x + b.width / 2) / width
        cy = (b.y + b.height / 2) / height
        if 0.45 <= cx <= 0.55 and 0.96 <= cy <= 0.99:
            match = re.search(r"(\d+)/10", b.name)
            if match:
                return int(match.group(1))
    return None


class TestTrigger(TriggerTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "测试trigger"
        self.description = "测试trigger"
        self.trigger_interval = 2
        self.instructions = """<a href="https://github.com/ok-oldking/ok-py">ok-py</a>"""

    def run(self):
        all_texts = self.ocr()

        # === 测试：优化后的手牌识别 ===
        x1, y1, x2, y2 = _hand_card_region

        # 读取手牌数
        hand_count = _read_hand_count(all_texts, self.width, self.height)
        self.log_info(f"底部手牌数: {hand_count}")

        # 1. 识别手牌区域内的所有文本框
        boxes_in_zone = [b for b in all_texts
                         if x1 <= (b.x + b.width / 2) / self.width <= x2
                         and y1 <= (b.y + b.height / 2) / self.height <= y2]

        self.log_info(f"手牌区域共识别到 {len(boxes_in_zone)} 个文本框")
        for b in boxes_in_zone:
            self.log_info(f"  box: name=「{b.name}」 x={b.x/self.width:.4f} y={b.y/self.height:.4f} w={b.width/self.width:.4f} h={b.height/self.height:.4f}")

        # 2. 分离卡牌名和按键
        # 卡牌名：不含数字按键、长度>1
        # 排除包含"攻击""强化""技能"的文本
        exclude_keywords = ["攻击", "强化", "技能"]
        card_names = [b for b in boxes_in_zone
                      if not _card_key(b.name)
                      and len(b.name) > 1
                      and not any(kw in b.name for kw in exclude_keywords)]

        # 按键：包含数字的
        keys = [(b.x / self.width, b.y / self.height, _card_key(b.name))
                for b in all_texts if _card_key(b.name)]

        self.log_info(f"识别到 {len(card_names)} 张卡牌名: {[b.name for b in card_names]}")
        self.log_info(f"识别到 {len(keys)} 个数字按键: {[(f'{kx:.4f}', f'{ky:.4f}', k) for kx, ky, k in keys]}")

        # 3. 按 x 排序卡牌名和按键
        card_names.sort(key=lambda b: b.x)
        keys.sort(key=lambda x: x[0])

        # 4. 配对：每个卡牌匹配其左上方最近的未使用按键
        used_keys = set()
        cards = []
        for i, name_box in enumerate(card_names):
            cx = name_box.x / self.width
            cy = name_box.y / self.height
            expected_num = i + 1

            # 筛选垂直范围+水平约束的未使用按键
            candidates = []
            for kx, ky, k in keys:
                if k in used_keys:
                    continue
                # 垂直：按键在卡牌名上方 0.03~0.06
                if not (cy - 0.06 <= ky <= cy - 0.03):
                    continue
                # 水平：按键在卡牌名左方，距离不超过 0.025
                if not (cx - 0.025 <= kx <= cx + 0.01):
                    continue
                candidates.append((kx, ky, k))

            if candidates:
                # 取水平最接近的
                best = min(candidates, key=lambda x: cx - x[0])
                used_keys.add(best[2])
                cards.append({"name": name_box.name, "key": best[2], "x": cx,
                              "key_x": best[0], "name_x": cx, "name_y": cy})
            else:
                self.log_info(f"卡牌「{name_box.name}」(x={cx:.4f}) 未找到对应按键（预期按键{expected_num}）")
                cards.append({"name": name_box.name, "key": None, "x": cx,
                              "key_x": None, "name_x": cx, "name_y": cy})

        # 5. 推断OCR遗漏的按键
        # 5a. 先用函数识别到的按键做首次分配
        self.log_info("=== 优化后配对结果 ===")
        for i, c in enumerate(cards):
            if c["key"]:
                self.log_info(f"  卡牌「{c['name']}」 x={c['name_x']:.4f} → 按键 {c['key']} (key_x={c['key_x']:.4f})")
            else:
                self.log_info(f"  卡牌「{c['name']}」 x={c['name_x']:.4f} → 无按键")

        # 5b. 整体推断：用手牌数和卡牌间距确定每张牌的按键
        self.log_info("=== 间距推断结果 ===")
        if hand_count is not None and len(cards) < hand_count:
            # 手牌数 > 识别到的卡牌数，说明OCR漏了卡牌
            # 先给识别到的按键的卡牌分配按键
            assigned = [None] * len(cards)
            assigned_keys = set()
            for i, c in enumerate(cards):
                if c["key"]:
                    assigned[i] = int(c["key"])
                    assigned_keys.add(int(c["key"]))

            # 对有按键的卡牌，验证按键是否与其位置匹配
            # 计算平均卡牌间距
            if len(cards) >= 2:
                total_gap = 0.0
                for i in range(1, len(cards)):
                    total_gap += cards[i]["x"] - cards[i-1]["x"]
                avg_gap = total_gap / (len(cards) - 1)

                # 检测哪些位置之间可能有遗漏的卡牌
                for i in range(1, len(cards)):
                    gap = cards[i]["x"] - cards[i-1]["x"]
                    if gap > avg_gap * 1.4:
                        # 这个间距明显偏大，中间可能漏了卡牌
                        missing_count = round(gap / avg_gap) - 1
                        self.log_info(f"  检测到卡牌[{i-1}]「{cards[i-1]['name']}」和卡牌[{i}]「{cards[i]['name']}」之间间距={gap:.4f} > avg={avg_gap:.4f}，可能遗漏了{missing_count}张")

                # 根据已有按键反推缺失位置的按键
                # 找到有按键的卡牌，按 key 值排序确定实际位置
                keyed_items = [(i, int(c["key"])) for i, c in enumerate(cards) if c["key"] is not None]
                keyed_items.sort(key=lambda x: x[1])

                if keyed_items:
                    # 检查按键序列是否连续
                    for idx in range(1, len(keyed_items)):
                        prev_i, prev_key = keyed_items[idx - 1]
                        cur_i, cur_key = keyed_items[idx]
                        expected_key_diff = cur_i - prev_i
                        actual_key_diff = cur_key - prev_key
                        if actual_key_diff > expected_key_diff:
                            self.log_info(f"  按键{prev_key}→{cur_key} 跨越{actual_key_diff-1}个值，位置偏移{expected_key_diff}，可能中间漏{actual_key_diff-expected_key_diff}张")

            # 最终推断：对于没有按键的卡牌，尝试推断
            # 策略：根据识别到的按键映射，通过位置间距推断缺失卡牌的按键
            # 先计算已有按键的卡牌的位置-按键映射，推断中间缺失的按键
            sorted_cards = sorted(enumerate(cards), key=lambda x: x[1]["x"])
            used_key_set = set()
            for idx, c in sorted_cards:
                if c["key"] is not None:
                    used_key_set.add(int(c["key"]))

            # 根据位置顺序依次分配按键
            next_key = 1
            final_keys = []
            for idx, c in sorted_cards:
                if c["key"] is not None:
                    final_keys.append((idx, int(c["key"])))
                    next_key = int(c["key"]) + 1
                else:
                    # 无按键：尝试推断
                    final_keys.append((idx, next_key))
                    next_key += 1

            # 按原始顺序输出
            for idx, key_val in final_keys:
                c = cards[idx]
                if c["key"] is not None and int(c["key"]) == key_val:
                    pass  # 已有按键且一致
                elif c["key"] is not None and int(c["key"]) != key_val:
                    self.log_info(f"  卡牌「{c['name']}」 x={c['x']:.4f} → 原按键{c['key']}，间距推断调整→ {key_val}")
                    c["key"] = str(key_val)
                else:
                    self.log_info(f"  卡牌「{c['name']}」 x={c['x']:.4f} → 间距推断→ {key_val}")
                    c["key"] = str(key_val)

        elif hand_count is not None and hand_count == len(cards):
            # 手牌数与识别数一致，直接用顺序分配
            for i, c in enumerate(cards):
                expected = i + 1
                if c["key"] is None:
                    self.log_info(f"  卡牌「{c['name']}」 x={c['x']:.4f} → 手牌数匹配，推断为 {expected}")
                    c["key"] = str(expected)
                elif int(c["key"]) != expected:
                    self.log_info(f"  卡牌「{c['name']}」 x={c['x']:.4f} → 原按键{c['key']}，调整为 {expected}")
                    c["key"] = str(expected)
        else:
            # 无法读取手牌数，用简单推断
            for i, c in enumerate(cards):
                if c["key"] is None:
                    expected = i + 1
                    self.log_info(f"  卡牌「{c['name']}」 x={c['x']:.4f} → 简单推断→ {expected}")
                    c["key"] = str(expected)

        # 最终结果汇总
        self.log_info("=== 最终配对结果 ===")
        for c in cards:
            self.log_info(f"  卡牌「{c['name']}」 x={c['x']:.4f} → 按键 {c['key']}")

        # 6. 旧版结果对比
        self.log_info("=== 旧版配对结果 ===")
        old_keys = [(b.x / self.width, _card_key(b.name)) for b in all_texts if _card_key(b.name)]
        old_used = set()
        for name_box in card_names:
            cx = name_box.x / self.width
            cy = name_box.y / self.height
            candidates = [(kx, k) for kx, k in old_keys
                          if k not in old_used and kx <= cx + 0.04]
            if candidates:
                best = max(candidates, key=lambda x: x[0])
                old_used.add(best[1])
                self.log_info(f"  卡牌「{name_box.name}」 x={cx:.4f} → 旧版匹配按键 {best[1]} (key_x={best[0]:.4f})")
            else:
                self.log_info(f"  卡牌「{name_box.name}」 x={cx:.4f} → 旧版无按键")