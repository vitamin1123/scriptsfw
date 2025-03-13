from queue import Queue, Empty
from threading import Thread, Lock, Timer
import threading
from wcferry import Wcf, WxMsg
import lz4.block
import xml.etree.ElementTree as ET
wcf = Wcf()
for i in wcf.get_contacts():
    if  i.get("remark") == "赵洁":
        # fangke = i
        # print(i.get("wxid"))
        wxid = i.get("wxid")
        tp = wcf.get_info_by_wxid(wxid)
        print(tp)