import pyautogui
import time

print("マウスの座標を取得中。Ctrl+Cで終了。")

try:
    while True:
        x, y = pyautogui.position()
        print(f"X={x}, Y={y}", end="\r")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n終了しました。")
