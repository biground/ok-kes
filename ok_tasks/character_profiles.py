import json
import os
import re
import shutil

from opencc import OpenCC


PROFILE_FILE_NAME = "sortie_character_profiles.json"
PROFILE_BACKUP_FILE_NAME = "sortie_character_profiles.backup.json"
PROFILE_VERSION = 1
MAIN_MEMBER_KEY = "主战员优先级"
BATTLE_MEMBER_KEY = "出战主战员优先级"
CONFIGURED_CARDS_KEY = "配置卡牌"
PROFILE_CARD_SOURCES_KEY = "_角色卡牌来源"
_cc = OpenCC("t2s")


class CharacterProfileError(ValueError):
    """角色档案格式错误。"""


def _split_values(value):
    if isinstance(value, str):
        values = re.split(r"[,，\n]+", value)
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        values = []
    return [str(item).strip() for item in values if str(item).strip()]


def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def normalize_profile(profile, index=0):
    """校验并规范单个角色档案。"""
    if not isinstance(profile, dict):
        raise CharacterProfileError(f"第 {index + 1} 个角色档案不是对象")
    name = str(profile.get("name", "")).strip()
    aliases = _unique(_split_values(profile.get("aliases", [])))
    cards = _split_values(profile.get("cards", []))
    if not name:
        raise CharacterProfileError(f"第 {index + 1} 个角色缺少角色名")
    if not aliases:
        raise CharacterProfileError(f"角色「{name}」至少需要一个识别名")
    if len(cards) != 8:
        raise CharacterProfileError(
            f"角色「{name}」需要配置固定的 8 张卡牌，当前为 {len(cards)} 张"
        )
    return {"name": name, "aliases": aliases, "cards": cards}


def normalize_profile_document(data):
    """校验角色档案文件并返回稳定格式。"""
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("characters")
    else:
        records = None
    if not isinstance(records, list):
        raise CharacterProfileError("角色档案必须包含 characters 列表")
    profiles = [normalize_profile(profile, index) for index, profile in enumerate(records)]
    names = [profile["name"] for profile in profiles]
    duplicate_names = [name for name in names if names.count(name) > 1]
    if duplicate_names:
        raise CharacterProfileError(f"角色名不能重复：{', '.join(_unique(duplicate_names))}")
    return {"version": PROFILE_VERSION, "characters": profiles}


def profile_file_path(task):
    """返回与任务配置同目录的角色档案路径。"""
    config_file = getattr(getattr(task, "config", None), "config_file", None)
    config_dir = os.path.dirname(os.path.abspath(config_file)) if config_file else os.path.abspath("configs")
    return os.path.join(config_dir, PROFILE_FILE_NAME)


def read_profile_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return normalize_profile_document(json.load(file))["characters"]


def write_profile_file(path, profiles):
    """原子写入角色档案。"""
    document = normalize_profile_document({"characters": profiles})
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary_path = f"{path}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(document, file, ensure_ascii=False, indent=2)
    os.replace(temporary_path, path)
    return document["characters"]


def load_task_profiles(task, create=True):
    """从独立文件加载角色档案并缓存到任务实例。"""
    path = profile_file_path(task)
    try:
        if not os.path.exists(path):
            profiles = []
            if create:
                write_profile_file(path, profiles)
        else:
            profiles = read_profile_file(path)
    except Exception as error:
        profiles = []
        log = getattr(task, "log_info", None)
        if callable(log):
            log(f"角色档案加载失败: {error}")
    task.character_profiles = profiles
    return profiles


def _profile_by_name(profiles, name):
    return next((profile for profile in profiles if profile["name"] == name), None)


def recognition_names_for(task, configured_name):
    """已配置角色使用识别别名；自由输入项继续按原字符串识别。"""
    profiles = getattr(task, "character_profiles", []) or []
    profile = _profile_by_name(profiles, configured_name)
    values = profile["aliases"] if profile else [configured_name]
    return _unique([_cc.convert(value).strip() for value in values if str(value).strip()])


def member_name_matches(task, configured_name, recognized_name):
    """用角色识别别名匹配已转简体的 OCR 名称。"""
    recognized = _cc.convert(str(recognized_name or "")).strip()
    if not recognized:
        return False
    for alias in recognition_names_for(task, configured_name):
        if alias in recognized or (len(recognized) >= 2 and recognized in alias):
            return True
    return False


def _config_list(task, key):
    value = getattr(task, "config", {}).get(key, [])
    return list(value) if isinstance(value, (list, tuple)) else []


def _notify_task_ui():
    try:
        from ok.gui.Communicate import communicate
        communicate.task_list_updated.emit()
    except Exception:
        pass


def sync_task_character_cards(task, notify=False):
    """同步角色互斥选择和自动生成的卡牌列表。"""
    config = getattr(task, "config", None)
    if config is None:
        return False
    profiles = getattr(task, "character_profiles", None)
    if profiles is None:
        profiles = load_task_profiles(task)
    profile_map = {profile["name"]: profile for profile in profiles}

    main_members = _config_list(task, MAIN_MEMBER_KEY)
    battle_members = _config_list(task, BATTLE_MEMBER_KEY)
    main_profile_names = {name for name in main_members if name in profile_map}
    filtered_battle_members = [
        name for name in battle_members
        if not (name in profile_map and name in main_profile_names)
    ]
    changed = filtered_battle_members != battle_members
    if changed:
        config[BATTLE_MEMBER_KEY] = filtered_battle_members
        log = getattr(task, "log_info", None)
        if callable(log):
            log("角色配置同步: 已从出战主战员优先级移除与主战员重复的已配置角色")
    battle_members = filtered_battle_members

    selected_profiles = []
    for name in [*main_members, *battle_members]:
        if name in profile_map and name not in selected_profiles:
            selected_profiles.append(name)
    current_sources = {
        name: list(profile_map[name]["cards"])
        for name in selected_profiles
    }
    previous_sources = config.get(PROFILE_CARD_SOURCES_KEY, {})
    if not isinstance(previous_sources, dict):
        previous_sources = {}
    previous_managed_cards = {
        card
        for cards in previous_sources.values()
        if isinstance(cards, (list, tuple))
        for card in cards
    }
    current_managed_cards = {
        card
        for cards in current_sources.values()
        for card in cards
    }
    cards_to_remove = previous_managed_cards - current_managed_cards
    configured_cards = _config_list(task, CONFIGURED_CARDS_KEY)
    synced_cards = _unique([card for card in configured_cards if card not in cards_to_remove])
    for name in selected_profiles:
        for card in current_sources[name]:
            if card not in synced_cards:
                synced_cards.append(card)

    if synced_cards != configured_cards:
        config[CONFIGURED_CARDS_KEY] = synced_cards
        changed = True
    if current_sources != previous_sources:
        config[PROFILE_CARD_SOURCES_KEY] = current_sources
        changed = True
    if changed:
        log = getattr(task, "log_info", None)
        if callable(log):
            log(
                f"角色配置同步: 已选择角色={selected_profiles}, "
                f"自动配置卡牌={synced_cards}"
            )
        if notify:
            _notify_task_ui()
    return changed


def replace_task_profiles(task, profiles, notify=True):
    """保存新角色档案，删除已移除角色的选择项并同步卡牌。"""
    old_profiles = getattr(task, "character_profiles", []) or []
    old_names = {profile["name"] for profile in old_profiles}
    saved_profiles = write_profile_file(profile_file_path(task), profiles)
    task.character_profiles = saved_profiles
    new_names = {profile["name"] for profile in saved_profiles}
    removed_names = old_names - new_names
    if removed_names and getattr(task, "config", None) is not None:
        for key in (MAIN_MEMBER_KEY, BATTLE_MEMBER_KEY):
            values = _config_list(task, key)
            filtered = [value for value in values if value not in removed_names]
            if filtered != values:
                task.config[key] = filtered
    sync_task_character_cards(task, notify=notify)
    return saved_profiles


def make_manage_profiles_callback(task):
    def manage_profiles(_checked=False):
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QDialog,
            QDialogButtonBox,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QMessageBox,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
        )

        profiles = getattr(task, "character_profiles", None)
        if profiles is None:
            profiles = load_task_profiles(task)
        dialog = QDialog()
        dialog.setWindowTitle("角色卡牌档案")
        dialog.resize(1050, 560)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(
            "每行配置一个角色。角色名用于设置列表；识别名和卡牌均用逗号分隔，卡牌必须正好 8 张。"
        ))
        table = QTableWidget(0, 3, dialog)
        table.setHorizontalHeaderLabels(["角色名", "识别名（逗号分隔）", "8张卡牌（逗号分隔）"])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        def append_row(profile=None):
            row = table.rowCount()
            table.insertRow(row)
            profile = profile or {"name": "", "aliases": [], "cards": []}
            values = [
                profile["name"],
                ",".join(profile["aliases"]),
                ",".join(profile["cards"]),
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))

        for profile in profiles:
            append_row(profile)
        layout.addWidget(table)
        row_buttons = QHBoxLayout()
        add_button = QPushButton("新增角色")
        delete_button = QPushButton("删除选中角色")
        add_button.clicked.connect(lambda: append_row())

        def delete_rows():
            rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
            for row in rows:
                table.removeRow(row)

        delete_button.clicked.connect(delete_rows)
        row_buttons.addWidget(add_button)
        row_buttons.addWidget(delete_button)
        row_buttons.addStretch(1)
        layout.addLayout(row_buttons)
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.rejected.connect(dialog.reject)

        def save_and_close():
            records = []
            for row in range(table.rowCount()):
                values = [
                    table.item(row, column).text().strip() if table.item(row, column) else ""
                    for column in range(3)
                ]
                if not any(values):
                    continue
                records.append({"name": values[0], "aliases": values[1], "cards": values[2]})
            try:
                normalized = normalize_profile_document({"characters": records})["characters"]
                replace_task_profiles(task, normalized, notify=True)
            except Exception as error:
                QMessageBox.warning(dialog, "保存失败", str(error))
                return
            QMessageBox.information(dialog, "保存成功", f"已保存 {len(normalized)} 个角色档案。")
            dialog.accept()

        button_box.accepted.connect(save_and_close)
        layout.addWidget(button_box)
        dialog.exec()

    return manage_profiles


def make_character_selection_callback(task, target_key, opposite_key):
    def select_characters(_checked=False):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMessageBox,
            QVBoxLayout,
        )

        profiles = getattr(task, "character_profiles", None)
        if profiles is None:
            profiles = load_task_profiles(task)
        if not profiles:
            QMessageBox.information(None, "没有角色档案", "请先点击“管理角色档案”添加角色。")
            return
        profile_names = [profile["name"] for profile in profiles]
        current = _config_list(task, target_key)
        opposite = set(_config_list(task, opposite_key))
        available_profiles = [profile for profile in profiles if profile["name"] not in opposite]

        dialog = QDialog()
        dialog.setWindowTitle(f"从角色档案选择：{target_key}")
        dialog.resize(520, 520)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(
            "勾选已配置角色；另一组已选择的角色不会出现在这里。任意 OCR 字符串仍可在原列表中手工添加。"
        ))
        list_widget = QListWidget(dialog)
        for profile in available_profiles:
            item = QListWidgetItem(profile["name"])
            item.setData(Qt.UserRole, profile["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if profile["name"] in current else Qt.Unchecked)
            item.setToolTip(
                f"识别名：{', '.join(profile['aliases'])}\n卡牌：{', '.join(profile['cards'])}"
            )
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.rejected.connect(dialog.reject)

        def apply_selection():
            selected = {
                list_widget.item(index).data(Qt.UserRole)
                for index in range(list_widget.count())
                if list_widget.item(index).checkState() == Qt.Checked
            }
            result = [
                value for value in current
                if value not in profile_names or value in selected
            ]
            for profile in available_profiles:
                name = profile["name"]
                if name in selected and name not in result:
                    result.append(name)
            task.config[target_key] = result
            sync_task_character_cards(task, notify=True)
            dialog.accept()

        button_box.accepted.connect(apply_selection)
        layout.addWidget(button_box)
        dialog.exec()

    return select_characters


def make_export_profiles_callback(task):
    def export_profiles(_checked=False):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        profiles = getattr(task, "character_profiles", None)
        if profiles is None:
            profiles = load_task_profiles(task)
        source_path = profile_file_path(task)
        target_path, _ = QFileDialog.getSaveFileName(
            None,
            "导出角色档案",
            source_path,
            "JSON 文件 (*.json)",
        )
        if not target_path:
            return
        if not target_path.lower().endswith(".json"):
            target_path += ".json"
        try:
            write_profile_file(target_path, profiles)
        except Exception as error:
            QMessageBox.warning(None, "导出失败", str(error))
            return
        QMessageBox.information(None, "导出成功", f"角色档案已导出到：\n{target_path}")
        task.log_info(f"角色档案导出成功: {target_path}")

    return export_profiles


def make_import_profiles_callback(task):
    def import_profiles(_checked=False):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        source_path, _ = QFileDialog.getOpenFileName(
            None,
            "导入角色档案",
            os.path.dirname(profile_file_path(task)),
            "JSON 文件 (*.json)",
        )
        if not source_path:
            return
        try:
            profiles = read_profile_file(source_path)
            destination = profile_file_path(task)
            if os.path.exists(destination) and os.path.abspath(source_path) != os.path.abspath(destination):
                shutil.copy2(destination, os.path.join(os.path.dirname(destination), PROFILE_BACKUP_FILE_NAME))
            replace_task_profiles(task, profiles, notify=True)
        except Exception as error:
            QMessageBox.warning(None, "导入失败", str(error))
            return
        QMessageBox.information(None, "导入成功", f"已导入 {len(profiles)} 个角色档案。")
        task.log_info(f"角色档案导入成功: {source_path}")

    return import_profiles
