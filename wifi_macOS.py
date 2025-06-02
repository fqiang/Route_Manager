import tkinter as tk
from tkinter import messagebox # Keep for logic class, though GUI class also has it
import subprocess
import threading
import socket
import netifaces as ni
import json
import os
from route_gui import RouteManagerGUI

class RouteLogic:
    def __init__(self, gui_updater):
        self.gui = gui_updater
        self.json_file = os.path.expanduser("~/routes.json")
        self.en0_gateway = self.get_gateway_by_interface('en0')
        self.sudo_password = None
        self.routes = self.load_routes()

        if self.routes and self.routes.get("gateway") != self.en0_gateway:
            self.readd_routes()
        
        self.update_route_display_on_gui()

    def get_gateway_by_interface(self, interface_name):
        gateways = ni.gateways()
        for interface, gateway_info in gateways.items():
            if isinstance(gateway_info, list):
                for gateway in gateway_info:
                    if gateway[1] == interface_name:
                        return gateway[0]
        return None

    def load_routes(self):
        if os.path.exists(self.json_file):
            with open(self.json_file, "r") as file:
                data = json.load(file)
                if isinstance(data, dict) and "gateway" in data and "routes" in data:
                    return data
                else:
                    return {"gateway": None, "routes": []}
        return {"gateway": None, "routes": []}

    def save_routes(self):
        with open(self.json_file, "w") as file:
            json.dump(self.routes, file, indent=4)

    def readd_routes(self):
        old_gateway = self.routes.get("gateway")
        if old_gateway:
            for route in self.routes["routes"]:
                try:
                    self.execute_sudo_command(f"route delete {route}")
                except subprocess.CalledProcessError as e:
                    self.gui.show_error("Error", f"Failed to delete old route: {route} ({e})")
        self.routes["gateway"] = self.en0_gateway
        for route in self.routes["routes"]:
            try:
                self.execute_sudo_command(f"route -n add {route} {self.en0_gateway}")
            except subprocess.CalledProcessError as e:
                self.gui.show_error("Error", f"Failed to add new route: {route} ({e})")
        self.save_routes()
        self.update_route_display_on_gui()

    def update_route_display_on_gui(self):
        routes_output = []
        try:
            output = subprocess.check_output(["netstat", "-rn"]).decode("utf-8")
            for line in output.splitlines():
                if "default" in line:
                    continue
                fields = line.split()
                if len(fields) > 1 and fields[1] == self.en0_gateway:
                    routes_output.append(line)
            self.gui.update_route_display(routes_output)
        except subprocess.CalledProcessError as e:
            self.gui.show_error("Error", f"Failed to retrieve routing table: {e}")

    def validate_sudo_password(self):
        if not self.sudo_password:
            self.sudo_password = self.gui.ask_sudo_password()
            if not self.sudo_password:
                raise subprocess.CalledProcessError(1, "Password input canceled")

        process = subprocess.Popen(
            f'echo {self.sudo_password} | sudo -S -v',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            self.gui.show_error("Error", f"Password validation failed: {stderr}")
            self.sudo_password = None
            raise subprocess.CalledProcessError(process.returncode, "Password validation failed")

    def execute_sudo_command(self, command):
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
            self.gui.show_error("Error", f"Command execution failed: {stderr}")
            raise subprocess.CalledProcessError(process.returncode, command, output=stderr)
        return stdout

    def add_route(self, input_value):
        if not input_value:
            self.gui.show_error("Error", "Input cannot be empty")
            return

        urls = input_value.split(";")
        gateway = self.en0_gateway
        success_count = 0

        for url in urls:
            url = url.strip()
            if not url:
                continue
            try:
                ip_address = socket.gethostbyname(url)
            except socket.gaierror as e:
                self.gui.show_error("Error", f"Failed to resolve input: {url} ({e})")
                continue
            try:
                self.execute_sudo_command(f"route -n add {ip_address}/32 {gateway}")
                if f"{ip_address}/32" not in self.routes["routes"]:
                    self.routes["routes"].append(f"{ip_address}/32")
                success_count += 1
            except subprocess.CalledProcessError as e:
                self.gui.show_error("Error", f"Failed to add route: {url} ({e})")

        if success_count > 0:
            self.routes["gateway"] = self.en0_gateway
            self.save_routes()
            self.gui.show_info("Success", f"Successfully added {success_count} routes")
            self.update_route_display_on_gui()

    def delete_route(self, input_value_or_ip):
        if not input_value_or_ip:
            self.gui.show_error("Error", "Input cannot be empty")
            return

        ips_to_delete = []
        if ';' in input_value_or_ip: # Check if it's a ;-separated list from entry
            ips_to_delete = [ip.strip() for ip in input_value_or_ip.split(";") if ip.strip()]
        else: # Assume it's a single IP (e.g., from double-click)
            ips_to_delete = [input_value_or_ip.strip()]
        
        success_count = 0
        for ip in ips_to_delete:
            if not ip:
                continue
            try:
                self.execute_sudo_command(f"route delete {ip}")
                # Ensure we remove the correct format (e.g. with /32 if stored that way)
                route_to_remove = ip 
                if not '/' in ip and any(r.startswith(ip + '/') for r in self.routes["routes"]):
                    # find the full route string if only ip is provided
                    for r_full in self.routes["routes"]:
                        if r_full.startswith(ip + '/'):
                            route_to_remove = r_full
                            break
                if route_to_remove in self.routes["routes"]:
                    self.routes["routes"].remove(route_to_remove)
                success_count += 1
            except subprocess.CalledProcessError as e:
                self.gui.show_error("Error", f"Failed to delete route: {ip} ({e})")

        if success_count > 0:
            self.save_routes()
            self.gui.show_info("Success", f"Successfully deleted {success_count} routes")
            self.update_route_display_on_gui()

    def monitor_wifi_changes(self):
        process = subprocess.Popen(['tail', '-f', '/var/log/wifi.log'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                if 'Gateway' in line: # Simplified check, might need refinement
                    new_gateway = self.get_gateway_by_interface('en0')
                    if new_gateway != self.en0_gateway:
                        self.en0_gateway = new_gateway
                        self.gui.update_gateway_display(self.en0_gateway)
                        self.readd_routes()
                        self.update_route_display_on_gui()
        except KeyboardInterrupt:
            self.gui.show_error("Monitor Error", "WiFi monitor interrupted.")
        except Exception as e:
            self.gui.show_error("Monitor Error", f"WiFi monitor error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    # Create a dummy gui_updater for RouteLogic initialization
    # The actual GUI will be created and then its methods passed or the GUI instance itself
    class DummyGUIUpdater:
        def update_route_display(self, routes_output): pass
        def update_gateway_display(self, gateway): pass
        def show_error(self, title, message): print(f"Error: {title} - {message}")
        def show_info(self, title, message): print(f"Info: {title} - {message}")
        def ask_sudo_password(self): return "test_password" # Placeholder

    app_logic = RouteLogic(DummyGUIUpdater()) # Initialize logic first to get gateway
    app_gui = RouteManagerGUI(root, app_logic) # Pass logic to GUI
    app_logic.gui = app_gui # Now link the actual GUI to the logic class
    
    # Initial display updates
    app_gui.update_gateway_display(app_logic.en0_gateway)
    app_logic.update_route_display_on_gui()

    threading.Thread(target=app_logic.monitor_wifi_changes, daemon=True).start()
    root.mainloop()