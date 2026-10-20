import os
import json
import sys

def get_config_dir():
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    
    app_dir = os.path.join(base, 'SyncTree')
    try:
        os.makedirs(app_dir, exist_ok=True)
    except Exception:
        pass
    return app_dir

def get_config_path():
    # 优先使用用户配置目录
    target_path = os.path.join(get_config_dir(), "config.json")
    # 如果目标目录文件尚不存在但工作目录有旧 config.json，执行平滑迁移
    local_path = "config.json"
    if not os.path.exists(target_path) and os.path.exists(local_path):
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            return local_path
    return target_path

CONFIG_PATH = get_config_path()

def load_config():
    cfg_file = get_config_path()
    default_config = {"local_path": "", "remote_url": "", "project_url": ""}
    if not os.path.exists(cfg_file):
        return default_config
    try:
        with open(cfg_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                default_config.update(data)
                return default_config
            return default_config
    except Exception:
        return default_config

def save_config(config):
    cfg_file = get_config_path()
    try:
        with open(cfg_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
