"""应用状态枚举"""

from enum import Enum, auto


class AppState(Enum):
    """语音输入法的 5 个核心状态"""
    IDLE = auto()        # 待机, 面板隐藏
    LISTENING = auto()   # 录音中, 红色脉动指示灯
    PROCESSING = auto()  # 识别中, 黄色旋转指示灯
    PREVIEW = auto()     # 结果预览, 绿色静态指示灯
    ERROR = auto()       # 异常, 红色快闪指示灯
