import socket
import subprocess
import os
from PySide6.QtCore import QThread, Signal

class EnvDiagThread(QThread):
    step_updated = Signal(int, int, str)
    
    def check_git_user(self):
        try:
            res = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if res.stdout.strip():
                return 1, "是否已创建用户: 是"
        except: pass
        return 2, "是否已创建用户: 否"

    def check_ssh(self):
        creation = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            res = subprocess.run(["ssh", "-T", "-o", "ConnectTimeout=5", "git@github.com"], capture_output=True, text=True, creationflags=creation)
            out = (res.stdout + res.stderr).lower()
            if "successfully authenticated" in out:
                return 1, "是否配置好SSH密钥: 是"
        except: pass
        return 2, "是否配置好SSH密钥: 否"

    def check_qq(self):
        try:
            res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq qq.exe"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if "qq.exe" in res.stdout.lower():
                return 3, "是否存在中国软件: 是"
        except: pass
        return 1, "是否存在中国软件: 否"

    def resolve_dns(self, host):
        try:
            return True, socket.gethostbyname(host)
        except:
            return False, None
            
    def ping_ip(self, ip):
        creation = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        cmd = ["ping", "-n", "1", "-w", "2000", ip] if os.name == 'nt' else ["ping", "-c", "1", "-W", "2", ip]
        try:
            res = subprocess.run(cmd, capture_output=True, creationflags=creation)
            return res.returncode == 0
        except:
            return False

    def check_port(self, ip, port, timeout=2):
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except:
            return False

    def run(self):
        self.setProperty("err_git_user", False)
        self.setProperty("err_ssh", False)
        self.setProperty("err_dns", False)
        self.setProperty("err_gfw", False)
        self.setProperty("err_qq", False)

        # 0: QQ
        self.step_updated.emit(0, 0, "是否存在中国软件: 检测中...")
        s, m = self.check_qq()
        if s == 3: self.setProperty("err_qq", True)
        self.step_updated.emit(0, s, m)

        net_ok = False

        # 1: NIC
        self.step_updated.emit(1, 0, "")
        if self.ping_ip("127.0.0.1"):
            self.step_updated.emit(1, 1, "")
            # 2: DNS
            self.step_updated.emit(2, 0, "")
            ok, ip = self.resolve_dns("github.com")
            if not ok:
                self.setProperty("err_dns", True)
                self.step_updated.emit(2, 2, "")
                self.step_updated.emit(3, 2, "")
                self.step_updated.emit(4, 2, "")
                self.step_updated.emit(5, 2, "")
            else:
                self.step_updated.emit(2, 1, "")
                # 3: Ping
                self.step_updated.emit(3, 0, "")
                if self.ping_ip(ip):
                    self.step_updated.emit(3, 1, "")
                    # 4: Port
                    self.step_updated.emit(4, 0, "")
                    if self.check_port(ip, 443):
                        self.step_updated.emit(4, 1, "")
                        net_ok = True
                    else:
                        self.setProperty("err_gfw", True)
                        self.step_updated.emit(4, 2, "")
                else:
                    self.setProperty("err_gfw", True)
                    self.step_updated.emit(3, 2, "")
                    self.step_updated.emit(4, 2, "")
                
                # 5: GFW Check google
                self.step_updated.emit(5, 0, "")
                ok_g, g_ip = self.resolve_dns("google.com")
                if ok_g and self.ping_ip(g_ip):
                    self.step_updated.emit(5, 1, "")
                else:
                    self.setProperty("err_gfw", True)
                    self.step_updated.emit(5, 2, "")
        else:
            self.setProperty("err_dns", True)
            self.step_updated.emit(1, 2, "")
            self.step_updated.emit(2, 2, "")
            self.step_updated.emit(3, 2, "")
            self.step_updated.emit(4, 2, "")
            self.step_updated.emit(5, 2, "")

        # 6: Git User
        self.step_updated.emit(6, 0, "是否已创建用户: 检测中...")
        s, m = self.check_git_user()
        if s == 2: self.setProperty("err_git_user", True)
        self.step_updated.emit(6, s, m)
        
        # 7: SSH Key
        if not net_ok:
            self.step_updated.emit(7, 3, "是否配置好SSH密钥: 网络中断，跳过检测")
        else:
            self.step_updated.emit(7, 0, "是否配置好SSH密钥: 检测中...")
            s, m = self.check_ssh()
            if s == 2: self.setProperty("err_ssh", True)
            self.step_updated.emit(7, s, m)
