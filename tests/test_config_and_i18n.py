import os
import sys
from core.config import get_config_dir, get_config_path, load_config, save_config
from core.i18n import i18n_dict, lang_manager, tr

def test_config_storage_directory():
    """【缺陷 25 验证】配置文件必须保存在系统标准应用目录，不能保存在 Temp 临时目录"""
    app_dir = get_config_dir()
    cfg_path = get_config_path()
    
    # 路径不应包含 PyInstaller 临时解压特征 _MEI
    assert "_MEI" not in cfg_path
    assert cfg_path.endswith("config.json")
    assert "SyncTree" in app_dir

def test_i18n_legend_terms():
    """【缺陷 18 验证】file_staged 必须翻译为 已暂存 / Staged，不能是 已提交 / Committed"""
    zh_staged = i18n_dict["zh"]["file_staged"]
    en_staged = i18n_dict["en"]["file_staged"]
    
    assert zh_staged == "已暂存", f"Expected '已暂存', got '{zh_staged}'"
    assert en_staged == "Staged", f"Expected 'Staged', got '{en_staged}'"
    
    assert "file_untracked" in i18n_dict["zh"]
    assert "file_untracked" in i18n_dict["en"]
    assert i18n_dict["zh"]["file_untracked"] == "未跟踪"
    assert i18n_dict["en"]["file_untracked"] == "Untracked"

def test_i18n_dictionary_parity():
    """【缺陷 24 验证】确保 zh 和 en 词条完全对称，无漏译"""
    zh_keys = set(i18n_dict["zh"].keys())
    en_keys = set(i18n_dict["en"].keys())
    
    missing_in_en = zh_keys - en_keys
    missing_in_zh = en_keys - zh_keys
    
    assert not missing_in_en, f"Keys missing in EN translation: {missing_in_en}"
    assert not missing_in_zh, f"Keys missing in ZH translation: {missing_in_zh}"

def test_i18n_toggle_and_lookup():
    """验证语言切换管理器的状态切换"""
    lang_manager.current_lang = "zh"
    assert tr("sync_latest") == "获取最新代码"
    
    lang_manager.toggle()
    assert lang_manager.current_lang == "en"
    assert tr("sync_latest") == "Sync Latest Code"
    
    # 还原为中文
    lang_manager.toggle()
    assert lang_manager.current_lang == "zh"
