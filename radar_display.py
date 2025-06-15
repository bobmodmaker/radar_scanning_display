import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox
from threading import Thread
import time

# 列出可用串口
def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("未找到可用串口！")
        return [""]
    print("可用串口：")
    for port in ports:
        print(f"{port.device}: {port.description}")
    return [port.device for port in ports]

# 雷達數據處理與可視化
class RadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 超聲波雷達")
        self.running = False
        self.ser = None

        # GUI 佈局
        self.frame = tk.Frame(self.root)
        self.frame.pack(padx=10, pady=10)

        # 串口選擇
        tk.Label(self.frame, text="選擇串口：").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.ports = list_serial_ports()
        if self.ports and self.ports[0]:  # 設置預設串口
            self.port_var.set(self.ports[0])
        else:
            self.port_var.set("無可用串口")
        self.port_menu = tk.OptionMenu(self.frame, self.port_var, *self.ports)
        self.port_menu.grid(row=0, column=1, sticky="w")

        # 啟動/停止按鈕
        self.start_button = tk.Button(self.frame, text="啟動掃描", command=self.start_scan)
        self.start_button.grid(row=1, column=0, pady=5)
        self.stop_button = tk.Button(self.frame, text="停止掃描", command=self.stop_scan, state="disabled")
        self.stop_button.grid(row=1, column=1, pady=5)

        # 顯示當前數據
        self.data_label = tk.Label(self.frame, text="角度: N/A, 距離: N/A cm")
        self.data_label.grid(row=2, column=0, columnspan=2, pady=5)

        # 雷達圖設置
        self.fig, self.ax = plt.subplots(subplot_kw={'projection': 'polar'})
        self.ax.set_ylim(0, 50)  #  最大距離 100cm
        self.ax.set_theta_zero_location('N')  # 北為 0 度
        self.ax.set_theta_direction(-1)  # 順時針
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().grid(row=3, column=0, columnspan=2)

        self.angles = []
        self.distances = []

    def start_scan(self):
        if not self.running:
            port = self.port_var.get()
            if not port or port == "無可用串口":
                messagebox.showerror("錯誤", "請選擇有效的串口！")
                return
            try:
                self.ser = serial.Serial(port, 115200, timeout=1)
                self.running = True
                self.start_button.config(state="disabled")
                self.stop_button.config(state="normal")
                Thread(target=self.read_serial, daemon=True).start()
            except serial.SerialException as e:
                messagebox.showerror("錯誤", f"無法打開串口 {port}: {e}")
                self.running = False

    def stop_scan(self):
        self.running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if self.ser and self.ser.is_open:
            self.ser.close()

    def update_radar(self, angle, distance):
        if angle == 0 or angle ==360:  # 新的一次掃描，清除舊資料
            self.angles.clear()
            self.distances.clear()

        self.angles.append(np.radians(angle))  # 轉換為弧度
        self.distances.append(distance if distance != -1 else 0)

        # 更新雷達圖
        self.ax.clear()
        self.ax.set_ylim(0, 50)  # 改為 0~100cm
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)
        self.ax.plot(self.angles, self.distances, 'g.-')
        self.ax.fill(self.angles, self.distances, 'g', alpha=0.1)
        self.canvas.draw()

        # 更新數據顯示
        self.data_label.config(text=f"角度: {angle:.1f}°, 距離: {distance:.1f} cm")


    def read_serial(self):
        while self.running:
            try:
                data = self.ser.readline().decode('utf-8').strip()
                if data:
                    try:
                        angle, distance = map(float, data.split(','))
                        print(f"角度: {angle}, 距離: {distance} cm")
                        self.root.after(0, self.update_radar, angle, distance)
                    except ValueError:
                        print("數據解析錯誤:", data)
            except serial.SerialException:
                print("串口斷開")
                self.stop_scan()
                self.root.after(0, lambda: messagebox.showerror("錯誤", "串口斷開！"))
                break
            time.sleep(0.01)

    def on_closing(self):
        self.stop_scan()
        self.root.destroy()

# 主程式
if __name__ == "__main__":
    root = tk.Tk()
    app = RadarGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()