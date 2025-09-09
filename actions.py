import pyautogui
import time
import yaml
import os
from pyautogui import ImageNotFoundException

class ImageNotFoundError(Exception):
    pass

def _execute_action(action, stop_event):
    # 待機の挙動
    if 'wait' in action:
        try:
            wait_time = float(action['wait'])
        except (ValueError, TypeError):
            raise ValueError(f"waitには数値を指定してください: {action['wait']}")
        # 0.1秒ごとに停止イベントをチェックし、待機を中断できるようにする
        end_time = time.time() + wait_time
        while time.time() < end_time:
            if stop_event.is_set():
                return 'global_break'
            time.sleep(0.1)

    # 画像クリックの挙動
    elif 'click' in action:
        target = action['click']
        if not os.path.exists(target):
            raise ImageNotFoundError(f"画面上に画像が見つかりません: {target}")
        try:
            location = pyautogui.locateCenterOnScreen(target, confidence=0.7)
            pyautogui.click(location)
        except ImageNotFoundException:
            raise ImageNotFoundError(f"画面上に画像が見つかりません: {target}")

    # 複数の画像のうち、最初に見つかったものをクリックする挙動
    elif 'click_any' in action:
        targets = action['click_any']
        if not isinstance(targets, list):
            raise ValueError(f"click_anyには画像のリストを指定してください: {targets}")

        found = False
        for target in targets:
            if not os.path.exists(target):
                # 1つの画像が存在しなくてもエラーにはせず、次の画像を探す
                print(f"警告: 画像ファイルが存在しません: {target}")
                continue
            try:
                location = pyautogui.locateCenterOnScreen(target, confidence=0.7)
                if location:
                    pyautogui.click(location)
                    found = True
                    break  # 最初に見つかった画像をクリックしてループを抜ける
            except ImageNotFoundException:
                continue # 見つからなければ次の画像へ

        if not found:
            raise ImageNotFoundError(f"指定された画像が画面上にいずれも見つかりませんでした: {targets}")

    # 画像が見つかった場合にbreakする挙動
    elif 'break_on_found' in action:
        target = action['break_on_found']
        if not os.path.exists(target):
            raise ImageNotFoundError(f"画像ファイルが存在しません: {target}")
        try:
            pyautogui.locateCenterOnScreen(target, confidence=0.7)
            return 'global_break'  # 画像が見つかったので全てのループを抜ける
        except ImageNotFoundException:
            return False  # 画像が見つからないのでループを継続

    # 現在のループのみbreakする挙動
    elif 'break_current_loop_on_found' in action:
        target = action['break_current_loop_on_found']
        if not os.path.exists(target):
            raise ImageNotFoundError(f"画像ファイルが存在しません: {target}")
        try:
            pyautogui.locateCenterOnScreen(target, confidence=0.7)
            return 'local_break'  # 画像が見つかったので現在のループだけを抜ける
        except ImageNotFoundException:
            return False  # 画像が見つからないのでループを継続

    # 座標クリックの挙動
    elif 'click_pos' in action:
        try:
            x, y = action['click_pos']
            x = int(x)
            y = int(y)
        except (ValueError, TypeError):
            raise ValueError(f"click_posには整数の座標ペアを指定してください: {action['click_pos']}")
        pyautogui.moveTo(x, y, duration=0.7)
        pyautogui.click(x, y)

    # 文字入力の挙動    
    elif 'input' in action:
        pyautogui.write(action['input'], interval=0.05)

    # キー入力の挙動
    elif 'key' in action:
        pyautogui.press(action['key'])

    # グローバルな中断
    elif 'break' in action:
        return 'global_break'

    # 現在のループのみ中断
    elif 'break_current_loop' in action:
        return 'local_break'

def process_steps(steps, stop_event):
    """
    ステップのリストを再帰的に処理します。
    中断の種類に応じて 'global_break', 'local_break', False のいずれかを返します。
    """
    for step in steps:
        if stop_event.is_set():
            return 'global_break'

        if 'loop' in step:
            loop_config = step['loop']
            if not isinstance(loop_config, dict):
                raise ValueError(f"loopの値は辞書形式でなければなりません: {loop_config}")
            count = loop_config.get('count', 1)
            loop_steps = loop_config.get('steps')  # Get raw value
            if loop_steps is None:  # If steps is null, treat as empty list
                loop_steps = []
            if not isinstance(loop_steps, list):
                raise ValueError(f"loopのstepsの値はリスト形式でなければなりません: {loop_steps}")
            # 'infinite' (string) or 'inf' (from unquoted yaml infinite)
            if str(count).lower() in ['infinite', 'inf']:
                while not stop_event.is_set():
                    break_signal = process_steps(loop_steps, stop_event)
                    if break_signal == 'global_break':
                        return 'global_break'
                    if break_signal == 'local_break':
                        break  # 無限ループを中断
            else:
                try:
                    loop_count = int(count)
                except (ValueError, TypeError):
                    raise ValueError(f"loopのcountには 'infinite' または整数を指定してください: {count}")

                for _ in range(loop_count):
                    if stop_event.is_set():
                        return 'global_break'
                    break_signal = process_steps(loop_steps, stop_event)
                    if break_signal == 'global_break':
                        return 'global_break'  # グローバルな中断を上に伝播
                    if break_signal == 'local_break':
                        break  # このループ(for _ in range)のみ中断
        elif 'if_condition' in step:
            config = step['if_condition']
            image_path = config['image']
            then_steps = config.get('then', [])
            else_steps = config.get('else', [])

            if not os.path.exists(image_path):
                raise ImageNotFoundError(f"画像ファイルが存在しません: {image_path}")
            
            try:
                pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
                # 画像が見つかった場合、thenブロックを実行
                result = process_steps(then_steps, stop_event)
                if result in ['global_break', 'local_break']:
                    return result
            except ImageNotFoundException:
                # 画像が見つからなかった場合、elseブロックを実行
                result = process_steps(else_steps, stop_event)
                if result in ['global_break', 'local_break']:
                    return result
        else:
            break_signal = _execute_action(step, stop_event)
            if break_signal:
                return break_signal  # 中断信号を上に伝播
    return False

def run_script(yaml_path, stop_event):
    """
    YAMLファイルを読み込み、アクションの実行を開始します。
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        steps = yaml.safe_load(f)
    process_steps(steps, stop_event)
