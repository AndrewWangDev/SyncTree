import socket
import subprocess
import os
from PySide6.QtCore import QThread, Signal
from core.i18n import tr

class EnvDiagThread(QThread):
    step_updated = Signal(int, int, str)
    
    def check_git_user(self):
        try:
            creation = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res_name = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                creationflags=creation
            )
            res_email = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                creationflags=creation
            )
            if res_name.stdout.strip() and res_email.stdout.strip():
                return 1, tr("diag_user_yes")
        except Exception:
            pass
        return 2, tr("diag_user_no")

    def check_local_nic(self):
        try:
            if self.ping_ip("127.0.0.1"):
                return True
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            s.close()
            return True
        except Exception:
            try:
                return socket.gethostbyname("localhost") == "127.0.0.1"
            except Exception:
                return False

    def check_ssh(self):
        creation = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            res = subprocess.run(
                ["ssh", "-T", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "git@github.com"], 
                capture_output=True, 
                text=True, 
                creationflags=creation,
                timeout=10
            )
            out = (res.stdout + res.stderr).lower()
            if "successfully authenticated" in out:
                return 1, tr("diag_ssh_yes")
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        return 2, tr("diag_ssh_no")

    def resolve_dns(self, host):
        try:
            return True, socket.gethostbyname(host)
        except Exception:
            return False, None
            
    def ping_ip(self, ip):
        creation = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        cmd = ["ping", "-n", "1", "-w", "2000", ip] if os.name == 'nt' else ["ping", "-c", "1", "-W", "2", ip]
        try:
            res = subprocess.run(cmd, capture_output=True, creationflags=creation)
            return res.returncode == 0
        except Exception:
            return False

    def check_port(self, ip_or_host, port, timeout=3):
        try:
            with socket.create_connection((ip_or_host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def run(self):
        self.setProperty("err_git_user", False)
        self.setProperty("err_ssh", False)
        self.setProperty("err_dns", False)
        self.setProperty("err_gfw", False)

        net_ok = False

        # 0: NIC 本地网卡测试
        self.step_updated.emit(0, 0, "")
        if self.check_local_nic():
            self.step_updated.emit(0, 1, "")
            
            # 1: DNS 解析测试
            self.step_updated.emit(1, 0, "")
            ok, ip = self.resolve_dns("github.com")
            if not ok:
                self.setProperty("err_dns", True)
                self.step_updated.emit(1, 2, "")
                self.step_updated.emit(2, 2, "")
                self.step_updated.emit(3, 2, "")
                self.step_updated.emit(4, 2, "")
            else:
                self.step_updated.emit(1, 1, "")
                
                # 2: IP 连通性测试 (通过 TCP 443 或 ICMP Ping 综合探测)
                self.step_updated.emit(2, 0, "")
                ip_reachable = self.check_port(ip, 443, timeout=3) or self.ping_ip(ip)
                if ip_reachable:
                    self.step_updated.emit(2, 1, "")
                    
                    # 3: GitHub 端口连通性 (TCP 443)
                    self.step_updated.emit(3, 0, "")
                    if self.check_port(ip, 443, timeout=3):
                        self.step_updated.emit(3, 1, "")
                        net_ok = True
                    else:
                        self.setProperty("err_gfw", True)
                        self.step_updated.emit(3, 2, "")
                else:
                    self.setProperty("err_gfw", True)
                    self.step_updated.emit(2, 2, "")
                    self.step_updated.emit(3, 2, "")
                
                # 4: GitHub API 连通性测试 (探测 api.github.com:443)
                self.step_updated.emit(4, 0, "")
                ok_g, g_ip = self.resolve_dns("api.github.com")
                if ok_g and (self.check_port(g_ip, 443, timeout=3) or self.ping_ip(g_ip)):
                    self.step_updated.emit(4, 1, "")
                else:
                    self.setProperty("err_gfw", True)
                    self.step_updated.emit(4, 2, "")
        else:
            self.setProperty("err_dns", True)
            self.step_updated.emit(0, 2, "")
            self.step_updated.emit(1, 2, "")
            self.step_updated.emit(2, 2, "")
            self.step_updated.emit(3, 2, "")
            self.step_updated.emit(4, 2, "")

        # 5: Git User
        self.step_updated.emit(5, 0, tr("diag_user_checking"))
        s, m = self.check_git_user()
        if s == 2:
            self.setProperty("err_git_user", True)
        self.step_updated.emit(5, s, m)
        
        # 6: SSH Key
        if not net_ok:
            self.step_updated.emit(6, 3, tr("diag_ssh_skip"))
        else:
            self.step_updated.emit(6, 0, tr("diag_ssh_checking"))
            s, m = self.check_ssh()
            if s == 2:
                self.setProperty("err_ssh", True)
            self.step_updated.emit(6, s, m)
