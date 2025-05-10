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
        self.root.title("Route Manager")  # Set the window title

        # Define the path to the JSON file
        self.json_file = os.path.expanduser("~/routes.json")

        # Get the gateway of the en0 interface
        self.en0_gateway = self.get_gateway_by_interface('en0')

        # Store the sudo password
        self.sudo_password = None

        # Create the input frame and buttons
        self.create_input_frame()

        # Create a read-only field to display the en0 gateway
        self.create_gateway_frame()

        # Create the route display interface
        self.create_route_frame()

        # Configure weights to allow the route listbox and scrollbar to resize with the window
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.route_frame.grid_rowconfigure(0, weight=1)
        self.route_frame.grid_columnconfigure(0, weight=1)

        # Load routes from the JSON file
        self.routes = self.load_routes()

        # If the gateway has changed, re-add all routes
        if self.routes and self.routes.get("gateway") != self.en0_gateway:
            self.readd_routes()

        # Initialize the display of current routes
        self.update_route_display()

        # Bind double-click events
        self.route_listbox.bind("<Double-1>", self.delete_selected_route)
        self.route_listbox.bind("<Button-2>", self.delete_selected_route)

    def create_input_frame(self):
        self.frame = tk.Frame(self.root)
        self.frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        tk.Label(self.frame, text="Enter URLs or IPs (separated by ;)").grid(row=0, column=0, padx=5)
        self.ip_entry = tk.Entry(self.frame, width=50)  # Entry for URLs or IPs
        self.ip_entry.grid(row=0, column=1, padx=5)

        self.add_button = tk.Button(self.frame, text="Add", command=self.add_route)  # Add button
        self.add_button.grid(row=0, column=2, padx=5)

        self.delete_button = tk.Button(self.frame, text="Delete", command=self.delete_route)  # Delete button
        self.delete_button.grid(row=0, column=3, padx=5)

    def create_gateway_frame(self):
        self.gateway_frame = tk.Frame(self.root)
        self.gateway_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        tk.Label(self.gateway_frame, text="en0 Gateway").grid(row=0, column=0, padx=5)
        self.gateway_entry = tk.Entry(self.gateway_frame, width=50)  # Display en0 gateway
        self.gateway_entry.insert(0, self.en0_gateway)  # Populate with en0 gateway
        self.gateway_entry.config(state='readonly')  # Set to read-only
        self.gateway_entry.grid(row=0, column=1, padx=5)

    def create_route_frame(self):
        self.route_frame = tk.Frame(self.root)
        self.route_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.route_listbox = tk.Listbox(self.route_frame, width=80, height=20)  # Route list
        self.route_listbox.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = tk.Scrollbar(self.route_frame, command=self.route_listbox.yview)  # Scrollbar
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.route_listbox.config(yscrollcommand=self.scrollbar.set)

    def get_gateway_by_interface(self, interface_name):
        # Get the gateway for a specific interface
        gateways = ni.gateways()
        for interface, gateway_info in gateways.items():
            if isinstance(gateway_info, list):
                for gateway in gateway_info:
                    if gateway[1] == interface_name:
                        return gateway[0]
        return None

    def load_routes(self):
        # Load routes from the JSON file
        if os.path.exists(self.json_file):
            with open(self.json_file, "r") as file:
                data = json.load(file)
                if isinstance(data, dict) and "gateway" in data and "routes" in data:
                    return data
                else:
                    return {"gateway": None, "routes": []}
        return {"gateway": None, "routes": []}

    def save_routes(self):
        # Save routes to the JSON file
        with open(self.json_file, "w") as file:
            json.dump(self.routes, file, indent=4)

    def readd_routes(self):
        # Re-add all routes based on the new gateway
        old_gateway = self.routes.get("gateway")
        if old_gateway:
            for route in self.routes["routes"]:
                try:
                    self.execute_sudo_command(f"route delete {route}")
                except subprocess.CalledProcessError as e:
                    messagebox.showerror("Error", f"Failed to delete old route: {route} ({e})")
        self.routes["gateway"] = self.en0_gateway
        for route in self.routes["routes"]:
            try:
                self.execute_sudo_command(f"route -n add {route} {self.en0_gateway}")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to add new route: {route} ({e})")
        self.save_routes()
        self.update_route_display()

    def update_route_display(self):
        # Update the route display
        self.route_listbox.delete(0, tk.END)  # Clear current display
        try:
            # Get the current routing table
            output = subprocess.check_output(["netstat", "-rn"]).decode("utf-8")
            for line in output.splitlines():
                # Skip default route
                if "default" in line:
                    continue
                # Check if the gateway is the en0 gateway
                fields = line.split()
                if len(fields) > 1 and fields[1] == self.en0_gateway:
                    self.route_listbox.insert(tk.END, line)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to retrieve routing table: {e}")

    def validate_sudo_password(self):
        # Validate the sudo password
        if not self.sudo_password:
            self.sudo_password = simpledialog.askstring("Password", "Enter sudo password:", show='*')
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
            messagebox.showerror("Error", f"Password validation failed: {stderr}")
            self.sudo_password = None
            raise subprocess.CalledProcessError(process.returncode, "Password validation failed")

    def execute_sudo_command(self, command):
        # Execute a command that requires sudo privileges
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
            messagebox.showerror("Error", f"Command execution failed: {stderr}")
            raise subprocess.CalledProcessError(process.returncode, command, output=stderr)

        return stdout

    def add_route(self):
        # Get the user input for URLs or IPs
        input_value = self.ip_entry.get()
        if not input_value:
            messagebox.showerror("Error", "Input cannot be empty")  # Show error if input is empty
            return

        # Split the input URLs or IPs
        urls = input_value.split(";")

        gateway = self.en0_gateway
        success_count = 0

        for url in urls:
            url = url.strip()
            if not url:
                continue

            try:
                # Attempt to resolve the input to an IP address
                ip_address = socket.gethostbyname(url)
            except socket.gaierror as e:
                messagebox.showerror("Error", f"Failed to resolve input: {url} ({e})")
                continue

            try:
                # Use sudo to execute the route command to add the route
                self.execute_sudo_command(f"route -n add {ip_address}/32 {gateway}")
                if ip_address not in self.routes["routes"]:
                    self.routes["routes"].append(f"{ip_address}/32")
                success_count += 1
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to add route: {url} ({e})")

        if success_count > 0:
            self.routes["gateway"] = self.en0_gateway
            self.save_routes()
            messagebox.showinfo("Success", f"Successfully added {success_count} routes")
            self.update_route_display()  # Update route display

    def delete_route(self, ip_address=None):
        # Get the user input for IP addresses
        if ip_address is None:
            input_value = self.ip_entry.get()
            if not input_value:
                messagebox.showerror("Error", "Input cannot be empty")  # Show error if input is empty
                return

            # Split the input IP addresses
            ips = input_value.split(";")
        else:
            ips = [ip_address]

        success_count = 0

        for ip in ips:
            ip = ip.strip()
            if not ip:
                continue

            try:
                # Use sudo to execute the route command to delete the route
                self.execute_sudo_command(f"route delete {ip}")
                if ip in self.routes["routes"]:
                    self.routes["routes"].remove(ip)
                success_count += 1
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to delete route: {ip} ({e})")

        if success_count > 0:
            self.save_routes()
            messagebox.showinfo("Success", f"Successfully deleted {success_count} routes")
            self.update_route_display()  # Update route display

    def delete_selected_route(self, event):
        # Get the selected route entry from the double-click
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
                    self.gateway_entry.config(state='normal')  # Set to editable
                    self.gateway_entry.delete(0, tk.END)
                    self.gateway_entry.insert(0, self.en0_gateway)  # Populate with en0 gateway
                    self.gateway_entry.config(state='readonly')  # Set to read-only
                    self.readd_routes()
                    self.update_route_display()
        except KeyboardInterrupt:
            messagebox.showerror("Error")

if __name__ == "__main__":
    root = tk.Tk()  # Create the main window
    app = RouteManagerApp(root)  # Initialize the application
    threading.Thread(target=app.monitor_wifi_changes, args=(), daemon=True).start()
    root.mainloop()  # Start the event loop and display the window