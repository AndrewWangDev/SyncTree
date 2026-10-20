import os
import shutil
import tempfile
import pytest
from core.git_utils import GitPoller
from core.git_actions import GitActions
from core.state import GitState

@pytest.fixture
def temp_repo():
    tmp_dir = tempfile.mkdtemp()
    poller = GitPoller(tmp_dir)
    actions = GitActions(poller)
    actions.init_repo()
    actions.run_cmd(["config", "user.name", "Tester"])
    actions.run_cmd(["config", "user.email", "tester@example.com"])
    yield tmp_dir, poller, actions
    poller.stop()
    shutil.rmtree(tmp_dir, ignore_errors=True)

def test_git_poller_init_attributes():
    """【缺陷 5 验证】GitPoller 实例必须拥有 repo_path 属性"""
    poller1 = GitPoller()
    assert hasattr(poller1, "repo_path")
    assert poller1.repo_path == ""
    
    poller2 = GitPoller("/some/path")
    assert poller2.repo_path == "/some/path"

def test_poll_git_state_detection(temp_repo):
    """验证 _poll_git 对工作区修改、暂存及未跟踪的准确识别"""
    tmp_dir, poller, actions = temp_repo
    
    # 初始状态
    state = poller._poll_git()
    assert state.isRepo is True
    assert state.hasModified is False
    assert state.hasStaged is False
    assert state.hasUpstream is False
    
    # 添加未跟踪文件
    f1 = os.path.join(tmp_dir, "file1.txt")
    with open(f1, "w") as f:
        f.write("content 1")
    
    state = poller._poll_git()
    assert state.hasModified is True # git porcelain 状态下 ?? 会触发 hasModified
    f1_key = os.path.realpath(f1).replace('\\', '/').lower()
    assert state.fileStatuses.get(f1_key) == "untracked"
    
    # 暂存该文件
    actions.stage_all()
    state = poller._poll_git()
    assert state.hasStaged is True
    assert state.fileStatuses.get(f1_key) == "staged"
    
    # 提交该文件
    actions.commit("Commit 1")
    state = poller._poll_git()
    assert state.hasStaged is False
    assert state.hasModified is False
    assert state.canUndo is False # 仅1次提交无父提交
    
    # 修改该文件成为未暂存
    with open(f1, "a") as f:
        f.write("modified")
    state = poller._poll_git()
    assert state.hasModified is True
    assert state.fileStatuses.get(f1_key) == "unstaged"

def test_poll_git_lightweight_caching(temp_repo):
    """【缺陷 20 验证】HEAD 无变动时复用 commitHistory 缓存，避免每次轮询重复跑 log -n 1000"""
    tmp_dir, poller, actions = temp_repo
    
    f = os.path.join(tmp_dir, "doc.txt")
    with open(f, "w") as fp:
        fp.write("v1")
    actions.stage_all()
    actions.commit("v1")
    
    # 首次轮询
    state1 = poller._poll_git()
    assert len(state1.commitHistory) > 0
    cached_history_id = id(state1.commitHistory)
    
    # 再次无任何提交时轮询，应复用缓存
    state2 = poller._poll_git()
    assert id(state2.commitHistory) == cached_history_id
