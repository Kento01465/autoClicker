import tkinter as tk
from tkinter import filedialog, messagebox
from actions import run_script, ImageNotFoundError
import threading
import traceback

# スレッド間の停止信号
stop_event = threading.Event()

def start_script(file_path, root):
    """スクリプトを実行し、UIのボタン状態を管理する"""
    def update_ui_for_start():
        run_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)

    def update_ui_for_finish():
        run_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        stop_event.clear() # 次の実行のためにクリア

    root.after(0, update_ui_for_start)

    try:
        run_script(file_path, stop_event)

    except ImageNotFoundError as img_err:
        if not stop_event.is_set():
            root.after(0, lambda msg=str(img_err): messagebox.showerror("画像エラー", msg))
            with open("error.log", "a", encoding="utf-8") as f:
                f.write("[画像エラー]\n")
                f.write(str(img_err) + "\n\n")

    except Exception as err:
        if not stop_event.is_set():
            root.after(0, lambda msg=str(err): messagebox.showerror("不明なエラー", msg))
            with open("error.log", "a", encoding="utf-8") as f:
                f.write("[不明なエラー]\n")
                f.write(traceback.format_exc() + "\n\n")

    finally:
        root.after(0, update_ui_for_finish)

def choose_and_run():
    """ファイルを選択し、別スレッドでスクリプト実行を開始する"""
    file_path = filedialog.askopenfilename(filetypes=[("YAML Files", "*.yaml")])
    if not file_path:
        return
    
    stop_event.clear() # 実行前にクリア
    thread = threading.Thread(target=start_script, args=(file_path, root))
    thread.start()

def stop_script():
    """停止ボタンが押されたときに呼ばれ、停止イベントを設定する"""
    stop_event.set()
    stop_button.config(state=tk.DISABLED)

root = tk.Tk()
root.title("画面操作自動化ツール")

label = tk.Label(root, text="操作スクリプトを選択して実行してください")
label.pack(pady=10)

run_button = tk.Button(root, text="スクリプトを実行", command=choose_and_run)
run_button.pack(pady=10)

stop_button = tk.Button(root, text="停止", command=stop_script, state=tk.DISABLED)
stop_button.pack(pady=5)

root.mainloop()
