import time
import pyautogui

time.sleep(5)
x, y = pyautogui.position()
print(f"Mouse position: ({x}, {y})")
