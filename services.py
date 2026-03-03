from db import cursor, commit
from datetime import datetime
from auth import sha256


TIPOS = {
    'INGRESO':'INGRESO','SALIDA':'SALIDA','AJUSTE_POSITIVO':'AJUSTE_POSITIVO','AJUSTE_NEGATIVO':'AJUSTE_NEGATIVO','AJUSTE':'AJUSTE'
}


class InventoryService:
    @staticmethod
    def register_product(data):
        code = data.get('codigo','').strip().upper()
        name = data.get('nombre','').strip()
        unit = data.get('unidad')
        grp = data.get('grupo')
        stock_min = int(data.get('stockMin') or 0)
        if not code or not name:
            return False, 'Código y nombre obligatorios'
        cur = cursor()
        try:
            cur.execute('INSERT INTO products (code,name,unit,grp,stock_min) VALUES (%s,%s,%s,%s,%s)', (code,name,unit,grp,stock_min))
            commit()
            
            return True, 'OK'
        except Exception as e:
            return False, str(e)


# ... incluye calculate_stock, register_movement, get_all_stock, get_history, get_summary, validate_integrity
# (Copia el contenido lógico del services en el archivo original entregado arriba)