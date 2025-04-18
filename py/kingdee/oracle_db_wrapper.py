import oracledb


class OracleDBWrapper:
    def __init__(self, user, password, dsn, instant_client_dir=None):
        self.user = user
        self.password = password
        self.dsn = dsn
        self.instant_client_dir = instant_client_dir
        self.connection = None
        if instant_client_dir:
            oracledb.init_oracle_client(lib_dir=instant_client_dir)

    def connect(self):
        try:
            self.connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=self.dsn
            )
            print("成功连接到数据库")
        except oracledb.Error as e:
            print(f"连接数据库时出错: {e}")

    def execute_query(self, query):
        if self.connection is None:
            print("未连接到数据库，请先调用 connect 方法。")
            return
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except oracledb.Error as e:
            print(f"执行查询时出错: {e}")
            return []

    def execute_update(self, query):
        if self.connection is None:
            print("未连接到数据库，请先调用 connect 方法。")
            return
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            print("更新操作执行成功")
        except oracledb.Error as e:
            print(f"执行更新操作时出错: {e}")
            self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            print("数据库连接已关闭")


