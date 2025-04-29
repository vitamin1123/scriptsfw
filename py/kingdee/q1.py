import oracledb
from oracle_db_wrapper import OracleDBWrapper




if __name__ == "__main__":
    user = "JD_CW"
    password = "JD_CW"
    instant_client_dir = r"C:\Users\xyy\Desktop\instantclient_11_2"
    host = '10.0.1.91'
    port = '1521'
    service_name = 'orcl'

    # 构建 DSN 使用服务名
    dsn = oracledb.makedsn(host, port, service_name=service_name)

    db = OracleDBWrapper(user, password, dsn, instant_client_dir)
    db.connect() 

    # 执行查询
    select_query = "select * from cosmic_fi.t_er_pubreimbill where fbillno = 'DGBX-250408-0044'"
    results = db.execute_query(select_query)
    if results:
        for row in results:
            print(row)

    db.close()