import mysql.connector


class DBConn:
    def __init__(self, cfg):
        self.cfg = cfg
        self.conn = None
    def connect(self):
        if self.conn and self.conn.is_connected():
            return self.conn
        self.conn = mysql.connector.connect(**self.cfg)
        return self.conn
    def cursor(self):
        return self.connect().cursor()
    def commit(self):
        if self.conn:
            self.conn.commit()
    def close(self):
        if self.conn:
            self.conn.close(); self.conn = None


# configure your DB here or import cfg from a secure place
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'inventario_dbv1'
}


_db = DBConn(DB_CONFIG)


def cursor():
    return _db.cursor()


def commit():
    _db.commit()


def close():
    _db.close()