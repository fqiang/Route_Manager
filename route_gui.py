import tkinter as tk
from tkinter import messagebox, simpledialog

class RouteManagerGUI:
    def __init__(self, root, logic_handler):
        self.root = root
        self.logic = logic_handler
        self.root.title("Route Manager")

        self.create_input_frame()
        self.create_gateway_frame()
        self.create_route_frame()

        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.route_frame.grid_rowconfigure(0, weight=1)
        self.route_frame.grid_columnconfigure(0, weight=1)

        self.route_listbox.bind("<Double-1>", self.handle_delete_selected_route)
        self.route_listbox.bind("<Button-2>", self.handle_delete_selected_route)

    def create_input_frame(self):
        self.frame = tk.Frame(self.root)
        self.frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        tk.Label(self.frame, text="Enter URLs or IPs (separated by ;)").grid(row=0, column=0, padx=5)
        self.ip_entry = tk.Entry(self.frame, width=50)
        self.ip_entry.grid(row=0, column=1, padx=5)

        self.add_button = tk.Button(self.frame, text="Add", command=self.handle_add_route)
        self.add_button.grid(row=0, column=2, padx=5)

        self.delete_button = tk.Button(self.frame, text="Delete", command=self.handle_delete_route)
        self.delete_button.grid(row=0, column=3, padx=5)

    def create_gateway_frame(self):
        self.gateway_frame = tk.Frame(self.root)
        self.gateway_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        tk.Label(self.gateway_frame, text="en0 Gateway").grid(row=0, column=0, padx=5)
        self.gateway_entry = tk.Entry(self.gateway_frame, width=50)
        self.gateway_entry.insert(0, self.logic.en0_gateway)
        self.gateway_entry.config(state='readonly')
        self.gateway_entry.grid(row=0, column=1, padx=5)

    def create_route_frame(self):
        self.route_frame = tk.Frame(self.root)
        self.route_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.route_listbox = tk.Listbox(self.route_frame, width=80, height=20)
        self.route_listbox.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = tk.Scrollbar(self.route_frame, command=self.route_listbox.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.route_listbox.config(yscrollcommand=self.scrollbar.set)

    def handle_add_route(self):
        input_value = self.ip_entry.get()
        self.logic.add_route(input_value)

    def handle_delete_route(self):
        input_value = self.ip_entry.get()
        self.logic.delete_route(input_value)

    def handle_delete_selected_route(self, event):
        index = self.route_listbox.nearest(event.y)
        selected_route = self.route_listbox.get(index)
        fields = selected_route.split()
        if len(fields) > 0:
            ip_address = fields[0]
            self.logic.delete_route(ip_address)

    def update_route_display(self, routes_output):
        self.route_listbox.delete(0, tk.END)
        for line in routes_output:
            self.route_listbox.insert(tk.END, line)

    def update_gateway_display(self, gateway):
        self.gateway_entry.config(state='normal')
        self.gateway_entry.delete(0, tk.END)
        self.gateway_entry.insert(0, gateway)
        self.gateway_entry.config(state='readonly')

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def show_info(self, title, message):
        messagebox.showinfo(title, message)

    def ask_sudo_password(self):
        return simpledialog.askstring("Password", "Enter sudo password:", show='*')