# Route Manager Build Report

## Introduction
A Python script allows you to exclude specific websites from using a VPN on macOS by modifying the routing table.

## Installation
Simply download the wifi.app package to your Mac and double-click it to run.

## Motivation
The reason why I wanted to write this route manager tool is that one day, while searching for information on Google to do my homework, I used a VPN. However, after I finished my schoolwork, the network speed to reach my school portal was too slow. I wondered if there was a tool that could automatically set my computer's network route to avoid using the VPN when accessing websites that didn’t require it. I searched on the internet, but I didn’t find any tools that could satisfy my requirements. So, I decided to write a simple program to do this for me.


## How the python code works?
In mac zsh terminal, users can add or delete a network route like this.

```zsh
sudo route -n add/delete <target IP> <Gateway>
```
Then, the route added by the tool must have the Gateway which is the non-VPN default gateway.

To check the default gate way and which Network Port is the default wireless Gateway on. Can use this on zsh

```zsh
ifconfig
```

The default wireless Gateway is always on Network Interface **en0** on mac. So, I can write a python code to modify the routing table with the gateway on the Network Interface  **en0**. 

#### The python code are going to use following python libraries

    1.tkinter(Used for creating the GUI of the application)
    2.messagebox and simpledialog(Part of tkinter, used for displaying error messages and 3.prompting the user for input)
    4.subprocess(Used to execute shell commands, such as adding or deleting routes)
    5.threading(Used to run the network monitoring function in the background without blocking the main GUI thread)
    6.socket(Used to resolve domain names to IP addresses.)
    7.netifaces(Used to retrieve network interface information, such as the gateway.)
    8.json(Used to read and write routing information to a JSON file)
    9.os(Used to handle file paths and other operating system-related tasks.)

So we need to first import these libraries at the beginning of the code
```python
import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import threading
import socket
import netifaces as ni
import json
import os
```

#### Class Definition: RouteManagerApp
```python
class RouteManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Route Manager")  # 设置窗口标题
```

The RouteManagerApp class is the main class of the application.
The __init__ method initializes the application, setting up the GUI and loading routing information.

#### Initialization and Configuration
In order to change the route automatically, the code needs to make a json file to store the ips. 
```python
# 定义 JSON 文件路径
        self.json_file = os.path.expanduser("~/routes.json")
```
Defines the path to the JSON file where routing information is stored.

#### Get the gateway on Net interface en0
```python
        self.en0_gateway = self.get_gateway_by_interface('en0')
```
Retrieves the gateway for the en0 network interface using the get_gateway_by_interface method.

#### build a variable record the sudo password
```Python
        # 存储密码
        self.sudo_password = None
```
Stores the sudo password required for executing privileged commands.

#### configure GUI
```Python
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
```
Make the input frame(input url) and read-only frame(display gateway) and Configures the layout to ensure that the route listbox and scrollbar resize properly when the window is resized.

#### initialize the routes and interact methods
```python
        self.routes = self.load_routes()#Loads the routing information from the JSON file using the load_routes method.

        if self.routes and self.routes.get("gateway") != self.en0_gateway: #If the gateway has changed since the last run, it re-adds all routes using the 
            self.readd_routes()
        readd_routes method.
        
        self.update_route_display() #Calls the update_route_display method to populate the route listbox with the current routing table.
        
        self.route_listbox.bind("<Double-1>", self.delete_selected_route)
        self.route_listbox.bind("<Button-2>", self.delete_selected_route)
        #Binds double-click and middle-click events to the delete_selected_route method to allow users to delete routes directly from the listbox.

```

#### GUI Creation Methods
##### create input frame
```Python
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
```
This create_input_frame method creates a frame for user input, including a label, an entry field for IP addresses or URLs, and buttons for adding and deleting routes by using the tkinter libaray.

##### create gatewayframe
```python
    def create_gateway_frame(self):
        self.gateway_frame = tk.Frame(self.root)
        self.gateway_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        tk.Label(self.gateway_frame, text="en0 网关").grid(row=0, column=0, padx=5)
        self.gateway_entry = tk.Entry(self.gateway_frame, width=50)  # 显示 en0 网关
        self.gateway_entry.insert(0, self.en0_gateway)  # 填充 en0 网关
        self.gateway_entry.config(state='readonly')  # 设置为只读
        self.gateway_entry.grid(row=0, column=1, padx=5)
```
Creates a frame to display the gateway for the en0 interface. The entry field is set to read-only to prevent user modification.

##### create route frame
```Python
    def create_route_frame(self):
        self.route_frame = tk.Frame(self.root)
        self.route_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.route_listbox = tk.Listbox(self.route_frame, width=80, height=20)  # 路由列表
        self.route_listbox.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = tk.Scrollbar(self.route_frame, command=self.route_listbox.yview)  # 滚动条
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.route_listbox.config(yscrollcommand=self.scrollbar.set)
```
Creates a frame containing a listbox to display the routing table and a scrollbar for navigation.

#### Network and routing methods

##### get gateway by interface
```Python
    def get_gateway_by_interface(self, interface_name):
        gateways = ni.gateways()
        for interface, gateway_info in gateways.items():
            if isinstance(gateway_info, list):
                for gateway in gateway_info:
                    if gateway[1] == interface_name:
                        return gateway[0]
        return None
```
Retrieves the gateway for a specified network interface using the netifaces library.

##### load_routes
```Python
    def load_routes(self):
        if os.path.exists(self.json_file):
            with open(self.json_file, "r") as file:
                data = json.load(file)
                if isinstance(data, dict) and "gateway" in data and "routes" in data:
                    return data
                else:
                    return {"gateway": None, "routes": []}
        return {"gateway": None, "routes": []}
```
Loads routing information from a JSON file. If the file does not exist or the data is invalid, it returns a default structure.

##### save_routes
```Python
    def save_routes(self):
        with open(self.json_file, "w") as file:
            json.dump(self.routes, file, indent=4)
```
Saves the current routing information to the JSON file.
##### readd_routes
```Python
    def readd_routes(self):
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
```
Re-adds all routes with the new gateway if the gateway has changed.
##### update_route_display
```Python
    def update_route_display(self):
        self.route_listbox.delete(0, tk.END)  # 清空当前显示
        try:
            output = subprocess.check_output(["netstat", "-rn"]).decode("utf-8")
            for line in output.splitlines():
                if "default" in line:
                    continue
                fields = line.split()
                if len(fields) > 1 and fields[1] == self.en0_gateway:
                    self.route_listbox.insert(tk.END, line)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("错误", f"获取路由表失败: {e}")
```
Updates the listbox with the current routing table by querying the system's routing table using netstat.

#### Entry of the python code
```python
if __name__ == "__main__":
    root = tk.Tk()  # creates the main window object root using tk.Tk()
    app = RouteManagerApp(root)  # Initialize the application
    threading.Thread(target=app.monitor_wifi_changes, args=(), daemon=True).start()
    root.mainloop()  # 启动事件循环，显示窗口
```
I use thread to run the monitor_wifi_changes method. This method is responsible for monitoring changes in the WiFi network (such as changes in the gateway) and updating the routing table accordingly

## Results

### learning about routing table usage in computer networks

The routing table may look like this on mac by using the command
```zsh
netstat -rn
```
    Internet:
    Destination        Gateway            Flags               Netif Expire
    default            10.168.1.1         UGScg                 en0       
    default            link#15            UCSIg             bridge0      !
    default            link#18            UCSIg           bridge100      !
    10.168.1/24        link#14            UCS                   en0      !
    10.168.1.1/32      link#14            UCS                   en0      !
    10.168.1.1         a0:c5:f2:bd:f2:f2  UHLWIir               en0   1195
    10.168.1.4         84:2f:57:43:de:a5  UHLWI                 en0    279
    10.168.1.9/32      link#14            UCS                   en0      !
    10.168.1.100       30:cd:a7:b6:d1:2d  UHLWI                 en0    209
    10.168.1.108       28:2:2e:71:f1:72   UHLWI                 en0    693
    10.168.1.112       44:23:7c:37:a8:6   UHLWI                 en0   1186
    10.168.1.120       64:9:80:2e:e:2c    UHLWI                 en0      !
    10.168.1.131       68:ab:bc:be:d3:23  UHLWI                 en0   1148

The Destination is the destiny the route points to. Gateway is the gateway that one route go through。Netif means net interface. Expire means the amount of seconds the route will be expired. Flags shows some property one route has and here are some following Flags.

    U: Indicates that the route is active (Up).
    G: Indicates that the route is routed through a gateway (Gateway), rather than being directly connected to the network or host.
    H: Indicates that the destination of the route is a specific host (Host), not a network.
    R: Indicates that the route has been reactivated by a dynamic routing protocol (Reinstate), such as a route re-added by a dynamic routing protocol.
    D: Indicates that the route was dynamically added through ICMP redirects or a dynamic routing protocol (e.g., RIP).
    M: Indicates that the route has been modified by a dynamic routing protocol (Modified).
    C: Indicates that the route is from the kernel's routing cache (Cache), meaning it is a cached entry.
    A: Indicates that the route was installed through address autoconfiguration (Addrconf).
    L: Indicates that the destination of the route is an address on the local machine (Local), typically used for loopback interfaces.
    B: Indicates that the destination of the route is a broadcast address (Broadcast).
    I: Indicates that the route uses the loopback interface (Loopback).
    W: Was Cloned (This route was cloned from a parent route. It indicates that the route was dynamically created based on some other route or configuration.)
    !: Indicates that the route is rejected (Reject), meaning packets destined for this route will be dropped.
### learning about software design 
When I was testing the python code,based on the interactive user requirements I improve and add functions in the code. For instance, the gui design using python, and backend data management usage json data file. 
### python programming and packaging as a mac app. 
In order to pack this python code into a .app package that mac users can double click to run, I used pyinstaller libaray to pack it.