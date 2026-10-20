import os
import shutil
import tempfile
import pytest
from core.git_utils import GitPoller
from core.git_actions import GitActions

@pytest.fixture
def temp_repo():
    tmp_dir = tempfile.mkdtemp()
    poller = GitPoller(tmp_dir)
    actions = GitActions(poller)
    yield tmp_dir, poller, actions
    shutil.rmtree(tmp_dir, ignore_errors=True)

def test_run_cmd_no_repo():
    poller = GitPoller("/nonexistent/path/for/sure/12345")
    actions = GitActions(poller)
    out, err = actions.run_cmd(["status"])
    assert out is None
    assert err == "No repo"

def test_init_repo(temp_repo):
    tmp_dir, poller, actions = temp_repo
    out, err = actions.init_repo()
    assert err is None
    assert os.path.exists(os.path.join(tmp_dir, ".git"))

def test_unstage_without_head(temp_repo):
    """【缺陷 7 验证】新建仓库无任何 commit 时暂存并取消暂存，不应抛出 ambiguous argument HEAD 错误"""
    tmp_dir, poller, actions = temp_repo
    actions.init_repo()
    
    # 创建一个新文件并暂存
    test_file = os.path.join(tmp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("hello")
    actions.stage_all()
    
    # 验证未有 HEAD 时取消暂存成功
    out, err = actions.unstage_all()
    assert err is None
    
    # git status 应显示该文件处于未跟踪或未暂存状态
    out, err = actions.run_cmd(["status", "--porcelain"])
    assert "??" in out

def test_undo_single_commit(temp_repo):
    """【缺陷 7 验证】仅有 1 次初始提交时撤销提交，不应抛出 HEAD^ 不存在错误"""
    tmp_dir, poller, actions = temp_repo
    actions.init_repo()
    
    # 配置临时提交用户信息
    actions.run_cmd(["config", "user.name", "Tester"])
    actions.run_cmd(["config", "user.email", "tester@example.com"])
    
    test_file = os.path.join(tmp_dir, "initial.txt")
    with open(test_file, "w") as f:
        f.write("first commit")
    actions.stage_all()
    out, err = actions.commit("Initial commit")
    assert err is None
    
    # 撤销唯一的提交
    out, err = actions.undo_commit()
    assert err is None
    
    # 验证 HEAD 已被撤销，仓库回到尚未提交状态
    check, _ = actions.run_cmd(["rev-parse", "--verify", "HEAD"])
    assert check is None

def test_set_remote_add_and_clear(temp_repo):
    """【缺陷 13 验证】设置与清空远程地址，清空时应调用 remove 而不是产生非法 URL 报错"""
    tmp_dir, poller, actions = temp_repo
    actions.init_repo()
    
    # 添加远程
    actions.set_remote("https://github.com/example/repo.git")
    out, err = actions.run_cmd(["remote", "-v"])
    assert "https://github.com/example/repo.git" in out
    
    # 清空远程
    out, err = actions.set_remote("")
    assert err is None
    
    # 验证 origin 已被安全移除
    out, err = actions.run_cmd(["remote"])
    assert "origin" not in (out or "")

def test_preview_cleanup_and_execute(temp_repo):
    """【缺陷 1 验证】测试 dry-run 预览不删除文件，仅显式执行清理时才删除"""
    tmp_dir, poller, actions = temp_repo
    actions.init_repo()
    
    garbage_file = os.path.join(tmp_dir, "garbage.tmp")
    with open(garbage_file, "w") as f:
        f.write("temporary file")
        
    # 1. 预览清理：文件应依然存在！
    out, err = actions.preview_cleanup()
    assert "garbage.tmp" in (out or "")
    assert os.path.exists(garbage_file)
    
    # 2. 实际执行清理：文件被清理
    out, err = actions.cleanup_garbage()
    assert not os.path.exists(garbage_file)
