import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import threading
import socket
import netifaces as ni
import json
import os

class RouteManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Route Manager")  # 设置窗口标题

        # 定义 JSON 文件路径
        self.json_file = os.path.expanduser("~/routes.json")

        # 获取 en0 网口的网关
        self.en0_gateway = self.get_gateway_by_interface('en0')

        # 存储密码
        self.sudo_password = None

        # 创建输入框和按钮的界面部分
        self.create_input_frame()

        # 创建显示 en0 网关的只读框
        self.create_gateway_frame()

        # 创建显示路由的界面部分
        self.create_route_frame()

        # 配置权重，使路由列表框和滚动条能够随窗口大小调整
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.route_frame.grid_rowconfigure(0, weight=1)
        self.route_frame.grid_columnconfigure(0, weight=1)

        # 加载 JSON 文件中的路由信息
        self.routes = self.load_routes()

        # 如果网关发生变化，重新添加所有路由
        if self.routes and self.routes.get("gateway") != self.en0_gateway:
            self.readd_routes()

        # 初始化显示当前路由
        self.update_route_display()

        # 绑定双击事件
        self.route_listbox.bind("<Double-1>", self.delete_selected_route)
        self.route_listbox.bind("<Button-2>", self.delete_selected_route)

    def create_input_frame(self):
        self.frame = tk.Frame(self.root)
        self.frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        tk.Label(self.frame, text="输入网址或IP（用;隔开）").grid(row=0, column=0, padx=5)
        self.ip_entry = tk.Entry(self.frame, width=50)  # 输入网址或IP
        self.ip_entry.grid(row=0, column=1, padx=5)

        self.add_button = tk.Button(self.frame, text="添加", command=self.add_route)  # 添加按钮
        self.add_button.grid(row=0, column=2, padx=5)

        self.delete_button = tk.Button(self.frame, text="删除", command=self.delete_route)  # 删除按钮
        self.delete_button.grid(row=0, column=3, padx=5)

    def create_gateway_frame(self):
        self.gateway_frame = tk.Frame(self.root)
        self.gateway_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        tk.Label(self.gateway_frame, text="en0 网关").grid(row=0, column=0, padx=5)
        self.gateway_entry = tk.Entry(self.gateway_frame, width=50)  # 显示 en0 网关
        self.gateway_entry.insert(0, self.en0_gateway)  # 填充 en0 网关
        self.gateway_entry.config(state='readonly')  # 设置为只读
        self.gateway_entry.grid(row=0, column=1, padx=5)

    def create_route_frame(self):
        self.route_frame = tk.Frame(self.root)
        self.route_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.route_listbox = tk.Listbox(self.route_frame, width=80, height=20)  # 路由列表
        self.route_listbox.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = tk.Scrollbar(self.route_frame, command=self.route_listbox.yview)  # 滚动条
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.route_listbox.config(yscrollcommand=self.scrollbar.set)

    def get_gateway_by_interface(self, interface_name):
        # 获取指定网口的网关
        gateways = ni.gateways()
        for interface, gateway_info in gateways.items():
            if isinstance(gateway_info, list):
                for gateway in gateway_info:
                    if gateway[1] == interface_name:
                        return gateway[0]
        return None

    def load_routes(self):
        # 加载 JSON 文件中的路由信息
        if os.path.exists(self.json_file):
            with open(self.json_file, "r") as file:
                data = json.load(file)
                if isinstance(data, dict) and "gateway" in data and "routes" in data:
                    return data
                else:
                    return {"gateway": None, "routes": []}
        return {"gateway": None, "routes": []}

    def save_routes(self):
        # print(f"文件已保存到: {self.json_file}")
        # 保存路由信息到 JSON 文件
        with open(self.json_file, "w") as file:
            json.dump(self.routes, file, indent=4)

    def readd_routes(self):
        # 根据新的网关重新添加所有路由
        old_gateway = self.routes.get("gateway")
        if old_gateway:
            for route in self.routes["routes"]:
                try:
                    self.execute_sudo_command(f"route delete {route}")
                except subprocess.CalledProcessError as e:
                    messagebox.showerror("错误", f"删除旧路由失败: {route} ({e})")
        self.routes["gateway"] = self.en0_gateway
        for route in self.routes["routes"]:
            try:
                self.execute_sudo_command(f"route -n add {route} {self.en0_gateway}")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("错误", f"添加新路由失败: {route} ({e})")
        self.save_routes()
        self.update_route_display()

    def update_route_display(self):
        # 更新路由显示
        self.route_listbox.delete(0, tk.END)  # 清空当前显示
        try:
            # 获取当前路由表
            output = subprocess.check_output(["netstat", "-rn"]).decode("utf-8")
            for line in output.splitlines():
                # 跳过默认路由
                if "default" in line:
                    continue
                # 检查网关是否为 en0 网关
                fields = line.split()
                if len(fields) > 1 and fields[1] == self.en0_gateway:
                    self.route_listbox.insert(tk.END, line)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("错误", f"获取路由表失败: {e}")

    def validate_sudo_password(self):
        # 验证sudo密码是否正确
        if not self.sudo_password:
            self.sudo_password = simpledialog.askstring("密码", "请输入sudo密码:", show='*')
            if not self.sudo_password:
                raise subprocess.CalledProcessError(1, "密码输入取消")

        process = subprocess.Popen(
            f'echo {self.sudo_password} | sudo -S -v',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            messagebox.showerror("错误", f"密码验证失败: {stderr}")
            self.sudo_password = None
            raise subprocess.CalledProcessError(process.returncode, "密码验证失败")

    def execute_sudo_command(self, command):
        # 执行需要sudo权限的命令
        self.validate_sudo_password()

        process = subprocess.Popen(
            f'echo {self.sudo_password} | sudo -S {command}',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            messagebox.showerror("错误", f"命令执行失败: {stderr}")
            raise subprocess.CalledProcessError(process.returncode, command, output=stderr)

        return stdout

    def add_route(self):
        # 获取用户输入的网址或IP
        input_value = self.ip_entry.get()
        if not input_value:
            messagebox.showerror("错误", "输入不能为空")  # 如果输入为空，显示错误消息
            return

        # 分割输入的网址或IP
        urls = input_value.split(";")

        gateway = self.en0_gateway
        success_count = 0

        for url in urls:
            url = url.strip()
            if not url:
                continue

            try:
                # 尝试将输入解析为IP地址
                ip_address = socket.gethostbyname(url)
            except socket.gaierror as e:
                messagebox.showerror("错误", f"无法解析输入: {url} ({e})")
                continue

            try:
                # 使用sudo执行route命令添加路由
                self.execute_sudo_command(f"route -n add {ip_address}/32 {gateway}")
                if ip_address not in self.routes["routes"]:
                    self.routes["routes"].append(f"{ip_address}/32")
                success_count += 1
            except subprocess.CalledProcessError as e:
                messagebox.showerror("错误", f"添加路由失败: {url} ({e})")

        if success_count > 0:
            self.routes["gateway"] = self.en0_gateway
            self.save_routes()
            messagebox.showinfo("成功", f"成功添加 {success_count} 个路由")
            self.update_route_display()  # 更新路由显示

    def delete_route(self, ip_address=None):
        # 获取用户输入的IP地址
        if ip_address is None:
            input_value = self.ip_entry.get()
            if not input_value:
                messagebox.showerror("错误", "输入不能为空")  # 如果输入为空，显示错误消息
                return

            # 分割输入的IP地址
            ips = input_value.split(";")
        else:
            ips = [ip_address]

        success_count = 0

        for ip in ips:
            ip = ip.strip()
            if not ip:
                continue

            try:
                # 使用sudo执行route命令删除路由
                self.execute_sudo_command(f"route delete {ip}")
                if ip in self.routes["routes"]:
                    self.routes["routes"].remove(ip)
                success_count += 1
            except subprocess.CalledProcessError as e:
                messagebox.showerror("错误", f"删除路由失败: {ip} ({e})")

        if success_count > 0:
            self.save_routes()
            messagebox.showinfo("成功", f"成功删除 {success_count} 个路由")
            self.update_route_display()  # 更新路由显示

    def delete_selected_route(self, event):
        # 获取双击的路由条目
        index = self.route_listbox.nearest(event.y)
        selected_route = self.route_listbox.get(index)
        fields = selected_route.split()
        if len(fields) > 0:
            ip_address = fields[0]
            self.delete_route(ip_address)

    def monitor_wifi_changes(self):
        # Run the tail command to monitor the system log in real-time
        process = subprocess.Popen(['tail', '-f', '/var/log/wifi.log'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break

                # Check for WiFi connection change events
                if 'Gateway' in line:
                    self.en0_gateway = self.get_gateway_by_interface('en0')
                    self.gateway_entry.config(state='normal')  # 设置为只读
                    self.gateway_entry.delete(0, tk.END)
                    self.gateway_entry.insert(0, self.en0_gateway)  # 填充 en0 网关
                    self.gateway_entry.config(state='readonly')  # 设置为只读
                    self.readd_routes()
                    self.update_route_display()
        except KeyboardInterrupt:
            messagebox.showerror("错误")
        # finally:
        #     process.kill()

if __name__ == "__main__":
    root = tk.Tk()  # 创建主窗口
    app = RouteManagerApp(root)  # 初始化应用程序
    threading.Thread(target=app.monitor_wifi_changes, args=(), daemon=True).start()
    root.mainloop()  # 启动事件循环，显示窗口