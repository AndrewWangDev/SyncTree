import socket
import subprocess
import os
from PySide6.QtCore import QThread, Signal

class NetworkDiagThread(QThread):
    step_updated = Signal(int, int) # step, status (0:loading, 1:ok, 2:fail)
    
    def resolve_dns(self, host):
        try:
            return True, socket.gethostbyname(host)
        except:
            return False, None
            
    def ping_ip(self, ip):
        creation = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        if os.name == 'nt':
            cmd = ["ping", "-n", "1", "-w", "2000", ip]
        else:
            cmd = ["ping", "-c", "1", "-W", "2", ip]
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
        # 0: Net loopback
        self.step_updated.emit(0, 0)
        if self.ping_ip("127.0.0.1"):
            self.step_updated.emit(0, 1)
        else:
            self.step_updated.emit(0, 2)
            self.step_updated.emit(1, 2)
            self.step_updated.emit(2, 2)
            self.step_updated.emit(3, 2)
            self.step_updated.emit(4, 2)
            return

        # 1: DNS github.com
        self.step_updated.emit(1, 0)
        ok, ip = self.resolve_dns("github.com")
        if not ok:
            self.step_updated.emit(1, 2)
            self.step_updated.emit(2, 2)
            self.step_updated.emit(3, 2)
        else:
            self.step_updated.emit(1, 1)
            
            # 2: Ping Github IP
            self.step_updated.emit(2, 0)
            if self.ping_ip(ip):
                self.step_updated.emit(2, 1)
                
                # 3: Port 443
                self.step_updated.emit(3, 0)
                if self.check_port(ip, 443):
                    self.step_updated.emit(3, 1)
                else:
                    self.step_updated.emit(3, 2)
            else:
                self.step_updated.emit(2, 2)
                self.step_updated.emit(3, 2)
                
        # 4: GFW google.com
        self.step_updated.emit(4, 0)
        ok, g_ip = self.resolve_dns("google.com")
        if ok and self.ping_ip(g_ip):
            self.step_updated.emit(4, 1)
        else:
            self.step_updated.emit(4, 2)
