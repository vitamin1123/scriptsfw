import mysql.connector
from mysql.connector import pooling
from queue import Queue, Empty
from threading import Thread, Lock, Timer
import threading
from wcferry import Wcf, WxMsg
import lz4.block
import xml.etree.ElementTree as ET

# 初始化 WCF
wcf = Wcf()

# 全局变量
people_dic = {}
people_dic_lock = Lock()  # 用于保护 people_dic 的锁
room_ids = '20290856837@chatroom'
# room_ids = '58166791226@chatroom'
# 测试 58166791226@chatroom
# 正式 20290856837@chatroom
# 定义队列
msg_queue = Queue()

# MySQL 连接池类
class MySQLPool:
    def __init__(self, host, user, password, database, pool_name="mypool", pool_size=5):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.pool_name = pool_name
        self.pool_size = pool_size
        self.pool = None
        self._create_pool()

    def _create_pool(self):
        """创建数据库连接池"""
        try:
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=self.pool_name,
                pool_size=self.pool_size,
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print(f"连接池 '{self.pool_name}' 已创建，大小: {self.pool_size}")
        except mysql.connector.Error as err:
            print(f"创建连接池失败: {err}")

    def get_connection(self):
        """从连接池中获取连接"""
        if self.pool:
            return self.pool.get_connection()
        else:
            raise Exception("连接池未创建")

# 初始化 MySQL 连接池
db_config = {
    'host': '10.0.0.1',
    'user': 'root',
    'password': '1234',
    'database': 'hahaha'
}
mysql_pool = MySQLPool(**db_config)

# 处理消息
def processMsg(msg: WxMsg):
    global people_dic
    if msg.from_group() and msg.roomid == room_ids:
        # 1 是文本消息，49 是引用消息
        if msg.type == 1 or msg.type == 49:
            # print('#'*10,'类型:', msg.type, '-- id:', msg.id, '-- sender:', people_dic.get(msg.sender, '未知'), '-- roomid:', msg.roomid)
            msg_queue.put(msg)  # 将消息入队

# 启动消息监听
def enableReceivingMsg():
    def innerWcFerryProcessMsg():
        while wcf.is_receiving_msg():
            try:
                msg = wcf.get_msg()
                processMsg(msg)
            except Empty:
                continue
            except Exception as e:
                print(f"ERROR: {e}")

    wcf.enable_receiving_msg()
    Thread(target=innerWcFerryProcessMsg, name="ListenMessageThread", daemon=True).start()

# 定时检查队列
def checkQueue():
    try:
        print('队列情况：', msg_queue.empty(),end='')
        if not msg_queue.empty():
            get_fangke_message()
            msg_queue.queue.clear()
            print('清空队列：', msg_queue.empty())
    except Exception as e:
        print(f"检查队列时发生错误: {e}")
    
    # 定时器
    threading.Timer(10.0, checkQueue).start()

def decompress_CompressContent(data):
    """
    解压缩Msg：CompressContent内容
    :param data: CompressContent内容 bytes
    :return:
    """
    if data is None or not isinstance(data, bytes):
        return None
    try:
        dst = lz4.block.decompress(data, uncompressed_size=len(data) << 8)
        dst = dst.replace(b'\x00', b'')  # 已经解码完成后，还含有0x00的部分，要删掉，要不后面ET识别的时候会报错
        uncompressed_data = dst.decode('utf-8', errors='ignore')
        return uncompressed_data
    except Exception as e:
        return data.decode('utf-8', errors='ignore')

# 查询数据库
# 测试群 58166791226@chatroom
def get_fangke_message():
    db_path = 'MSG0.db'
    query_sql = '''
        SELECT MsgSvrID,StrTalker,CreateTime,StrContent,CompressContent,Type,SubType,BytesExtra
        FROM "MSG"
        WHERE StrTalker='20290856837@chatroom' AND (Type='1' or Type='49')
        AND CreateTime >= strftime('%s', 'now', 'start of day', '-1 day') -- 昨天开始时间
        AND CreateTime < strftime('%s', 'now', '+1 day', 'start of day')
        ORDER BY CreateTime DESC
    '''
    # AND ( DATE(CreateTime) = DATE('now')
    # OR DATE(CreateTime) = DATE('now', '-1 day'))
    try:
        db_res = wcf.query_sql(db_path, query_sql)
        db_res_ids = {item['MsgSvrID'] for item in db_res}
        # 比较结果
        # 此处连接mysql

        # 使用连接池从 MySQL 获取连接
        conn = mysql_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        # 开启事务
        conn.start_transaction()

        mysql_query = """
            select * from guest_minip.messages
        """
        cursor.execute(mysql_query)
        db_res_mysql = cursor.fetchall()
        # 处理数据差异，决定插入还是删除
        
        db_res_mysql_ids = {item["MsgSvrID"] for item in db_res_mysql}
        # print('看看mysql的svrid：', db_res_mysql_ids)
        # print('看看db_res_ids:', db_res_ids)
        # 插入新数据（db_res 有但 MySQL 没有的）
        for item in db_res:
            #print('item: ',item['CompressContent'],item['Type'],item['SubType'])
            # print("item: ",type(item['MsgSvrID']))
            if item['Type'] == 49:
                compress_con = decompress_CompressContent(item['CompressContent'])
                root = ET.fromstring(compress_con)
                content_tmp = ''
                if item['SubType'] == 19:
                    content_tmp = root.find(".//des").text
                if item['SubType'] == 57:
                    content_tmp = root.find(".//title").text
            else:
                content_tmp = item['StrContent']   
            # print('id:',item['MsgSvrID'],'| 发送时间: ',item['CreateTime'], ' | 内容: ',item['StrContent'],content_tmp)
            # print('content_tmp: ',content_tmp)
            wxid = item['BytesExtra'].decode('cp437').split('<msgsource>')[0].split('\x1a')[1][5:]
            # print(f"id:{item['MsgSvrID']} | 发送时间: {item['CreateTime']} | 内容: {content_tmp} ")
            # print(f"大类: {item['Type']} | 子类: {item['SubType']} | 处理人: {people_dic.get(wxid, '未知')}")
            if item['MsgSvrID'] not in db_res_mysql_ids:
                insert_sql = """
                INSERT INTO guest_minip.messages (MsgSvrID, ope, content, created_at)
                VALUES (%s, %s, %s, FROM_UNIXTIME(%s))
                """
                cursor.execute(insert_sql, (
                    item['MsgSvrID'], people_dic.get(wxid, '未知'), content_tmp, item['CreateTime']
                ))
        # 删除MySQL中多余的消息
        for item in db_res_mysql:
            if item["MsgSvrID"] not in db_res_ids:
                delete_sql = "DELETE FROM guest_minip.messages WHERE MsgSvrID = %s"
                cursor.execute(delete_sql, (item["MsgSvrID"],))

        # 提交事务
        conn.commit()
            
    except Exception as e:
        if conn:
            conn.rollback()  # 回滚事务
        print(f"数据库更新失败: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    # 初始化群成员信息
    with people_dic_lock:
        people_dic = wcf.get_chatroom_members(room_ids)

    # 启动消息监听
    Thread(target=enableReceivingMsg, name="ListenMessageThread", daemon=True).start()

    # 启动队列检查
    Thread(target=checkQueue, name="CheckQueueThread", daemon=True).start()

    # 在另一个线程中执行数据库查询
    Thread(target=get_fangke_message, name="DatabaseQueryThread", daemon=True).start()

    # 保持程序运行
    wcf.keep_running()
