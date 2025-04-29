import win32gui
import win32api
import win32con
import time


def get_window_handle(window_name):
    try:
        # 获取指定名称窗口的句柄
        hwnd = win32gui.FindWindow(None, window_name)
        return hwnd
    except Exception as e:
        print(f"获取窗口句柄时出错: {e}")
        return None


def get_relative_mouse_position(hwnd):
    try:
        # 获取鼠标的全局位置
        mouse_x, mouse_y = win32api.GetCursorPos()
        # 获取窗口的位置和大小
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        # 计算鼠标相对于窗口的位置
        relative_x = mouse_x - left
        relative_y = mouse_y - top
        return relative_x, relative_y
    except Exception as e:
        print(f"获取鼠标位置时出错: {e}")
        return None, None


def click_at_position(hwnd, x, y):
    # 激活窗口
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.1)  # 短暂等待窗口激活

    # 移动鼠标到指定位置
    win32api.SetCursorPos((x, y))
    # 模拟鼠标左键按下
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    # 模拟鼠标左键释放
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


if __name__ == "__main__":
    window_name = 'PopKart Client'
    hwnd = get_window_handle(window_name)
    if hwnd:
        print(f"成功获取到窗口: {window_name}")
        click_positions = [(1088, 589), (995, 757), (1038, 777), (1106, 784)]
        for _ in range(150):
            for i, (x, y) in enumerate(click_positions):
                click_at_position(hwnd, x, y)
                if i == 1:
                    time.sleep(4)
                else:
                    time.sleep(0.5)
    else:
        print(f"未找到名为 {window_name} 的窗口")
    