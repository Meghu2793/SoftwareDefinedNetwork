import MySQLdb

class MyDB:
    __user_name = "root"
    __password = "root"
    __db_name = "qos"
    __host = "localhost"

    def __init__(self):
        self.db = MySQLdb.connect(host=self.__host, user=self.__user_name, passwd=self.__password, db=self.__db_name)
        self.db.autocommit(True)

    def __build_query(self, transport_type, src_port, dst_port, src_mac, dst_mac, src_ip, dst_ip):
        query = "select action1 from qos where (transport_type = '%s' or transport_type = '*') and (src_port = '%s' " \
                "or src_port = '*') and (dst_port = '%s' or dst_port = '*') " \
                "and (src_mac = '*' or src_mac = '%s') " \
                "and (dst_mac = '*' or dst_mac = '%s')" \
                "and (src_ip = '*' or src_ip = '%s')" \
                "and (dst_ip = '*' or dst_ip = '%s')" \
                %(transport_type, src_port, dst_port, src_mac, dst_mac, src_ip, dst_ip)
        print query
        return query

    def get_action(self, transport_type, src_port, dst_port, src_mac, dst_mac, src_ip, dst_ip):
        cursor = self.db.cursor()
        query = self.__build_query(transport_type, src_port, dst_port, src_mac, dst_mac, src_ip, dst_ip)
        cursor.execute(query)
        rows = cursor.fetchall()
        if len(rows) == 0:
            cursor.close()
            return "ND"
        elif len(rows) == 1:
            cursor.close()
            return rows[0][0]
        else:
            cursor.close()
            print('Warning: More than one rows defined in DB')
            return rows[0][0]