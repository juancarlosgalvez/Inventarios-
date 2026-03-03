from PIL import Image # esta librería es para manejar imágenes
import os # esta librería es para manejar rutas y archivos
import io # esta librería es para manejar flujos de datos en memoria
import csv # esta librería es para manejar archivos CSV
import hashlib # esta librería es para manejar hashing (seguridad)
from datetime import datetime # esta librería es para manejar fechas y horas
import customtkinter as ctk # esta librería es para la interfaz gráfica
from tkinter import messagebox, filedialog # estas librerías son para diálogos en tkinter
import mysql.connector # esta librería es para conectar con MySQL
from openpyxl import Workbook # esta librería es para manejar archivos Excel
from reportlab.lib.pagesizes import letter # esta librería es para manejar páginas PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer 
#esta librería es para crear documentos PDF
from reportlab.lib import colors # esta librería es para manejar colores en PDF



# LDAP optional
LDAP_ENABLED = False # para activar LDAP
LDAP_CONFIG = {
    'server': 'ldap://ldap.example.com',
    'base_dn': 'DC=example,DC=com',
    'user_dn_template': 'CN={username},OU=Users,DC=example,DC=com',
}
if LDAP_ENABLED: #eso es para activar o desactivar ldap
    try:
        from ldap3 import Server, Connection, ALL 
    except Exception as e:
        LDAP_ENABLED = False # desactivar si no está disponible
        print('ldap3 not available, LDAP disabled:', e)

# ------------------ CONFIG ------------------
DB_CONFIG = { # configuración de la base de datos
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'inventario_dbv1'
}

# estos son los colores personalizados para la UI 
UI_COLORS = { 
    'sidebar_bg': "#150434", # rojo oscuro del sidebar
    'sidebar_top': "#0A0F3A", # rojo más oscuro para hover
    'card_bg': "#0A0F3A", # color de fondo de las tarjetas
    'accent': "#0A0F3A", # color de acento general
    'success': "#0A0F3A", # color para acciones exitosas
    'warning': "#0A0F3A" # color para advertencias
}

# estos son los tipos de movimiento en el inventario
TIPOS_MOVIMIENTO = { 
    'INGRESO': 'INGRESO',
    'SALIDA': 'SALIDA',
    'AJUSTE_POSITIVO': 'AJUSTE_POSITIVO',
    'AJUSTE_NEGATIVO': 'AJUSTE_NEGATIVO',
    'AJUSTE': 'AJUSTE'
}

# ------------------ DATABASE LAYER ------------------
class DBConn:
    def __init__(self, cfg): # inicializa la conexión a la base de datos
        self.cfg = dict(cfg)
        self.conn = None

    def connect(self): # conecta a la base de datos
       
        try:
            if self.conn and getattr(self.conn, 'is_connected', lambda: True)():
                return self.conn
            self.conn = mysql.connector.connect(**self.cfg)
            return self.conn
        except mysql.connector.Error as e:
             # esto es para manejar errores de conexión
            print(f"[DBConn] Error connecting to MySQL: {e}")
            raise

    def connect_without_db(self):
        # conecta sin especificar la base de datos (útil para crear la DB)
        cfg_no_db = {k: v for k, v in self.cfg.items() if k != 'database'}
        try:
            conn = mysql.connector.connect(**cfg_no_db)
            return conn
        except mysql.connector.Error as e:
            print(f"[DBConn] Error connecting to MySQL (without DB): {e}")
            raise

    def cursor(self):
        #retorna un cursor para ejecutar consultas
        return self.connect().cursor(buffered=True)

    def commit(self):
        if self.conn:
            self.conn.commit()

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None

DB = DBConn(DB_CONFIG)

# ------------------ AUTH LAYER ------------------
class Auth:
    @staticmethod
    def sha256(text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @staticmethod
    def ldap_authenticate(username, password):
        if not LDAP_ENABLED:
            return False, 'LDAP disabled'
        try:
            server = Server(LDAP_CONFIG['server'], get_info=ALL)
            user_dn = LDAP_CONFIG['user_dn_template'].format(username=username)
            conn = Connection(server, user=user_dn, password=password, auto_bind=True)
            return True, 'LDAP OK'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def db_authenticate(username, password):
        try:
            cur = DB.cursor()
            cur.execute('SELECT id, password_hash, display_name, role FROM users WHERE username=%s', (username,))
            row = cur.fetchone()
            if not row:
                return False, 'Usuario no encontrado'
            uid, ph, dname, role = row
            if Auth.sha256(password) == ph:
                return True, {'id': uid, 'username': username, 'display_name': dname, 'role': role}
            else:
                return False, 'Contraseña incorrecta'
        except Exception as e:
            return False, str(e)

# ------------------ BUSINESS LOGIC (productos, movimientos, reportes) ------------------
class InventoryService:
    @staticmethod
    def init_schema():
        """
        Crea la base de datos y tablas si no existen.
        IMPORTANTE: usamos connect_without_db() para crear la DB si aún no existe.
        """
        try:
            # 1) conectar sin DB para crearla si no existe
            conn = DB.connect_without_db()
            cur = conn.cursor()
            cur.execute("CREATE DATABASE IF NOT EXISTS inventario_dbv1 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cur.execute("USE inventario_dbv1;")
            conn.commit()
            cur.close()
            conn.close()

            # 2) realizar conexión normal y crear tablas)
            cur = DB.cursor()
            statements = [
                "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(150) UNIQUE NOT NULL, password_hash VARCHAR(128) NOT NULL, display_name VARCHAR(200), role ENUM('admin','user') DEFAULT 'user')",
                "CREATE TABLE IF NOT EXISTS units (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL)",
                "CREATE TABLE IF NOT EXISTS groups_tbl (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL)",
                "CREATE TABLE IF NOT EXISTS products (id INT AUTO_INCREMENT PRIMARY KEY, code VARCHAR(100) UNIQUE NOT NULL, name VARCHAR(255) NOT NULL, unit VARCHAR(100), grp VARCHAR(100), stock_min INT DEFAULT 0)",
                "CREATE TABLE IF NOT EXISTS movements (id INT AUTO_INCREMENT PRIMARY KEY, product_code VARCHAR(100) NOT NULL, fecha DATETIME NOT NULL, tipo VARCHAR(50) NOT NULL, cantidad DECIMAL(15,4) NOT NULL, usuario VARCHAR(150), timestamp DATETIME, observaciones TEXT, stock_resultante DECIMAL(15,4))"
            ]
            for s in statements:
                cur.execute(s)
            DB.commit()
            InventoryService._ensure_defaults()
            return True, 'Esquema creado/validado'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _ensure_defaults():
        cur = DB.cursor()
        units = ['Unidades','Kilogramos','Gramos','Litros','Piezas','Cajas']
        groups = ['General','Consumibles','Herramientas']
        for u in units:
            try:
                cur.execute('INSERT IGNORE INTO units (name) VALUES (%s)', (u,))
            except Exception:
                pass
        for g in groups:
            try:
                cur.execute('INSERT IGNORE INTO groups_tbl (name) VALUES (%s)', (g,))
            except Exception:
                pass
        try:
            cur.execute('INSERT IGNORE INTO users (username, password_hash, display_name, role) VALUES (%s,%s,%s,%s)', ('admin', Auth.sha256('admin'), 'Administrador', 'admin'))
        except Exception:
            pass
        DB.commit()

    @staticmethod
    def register_product(prod: dict):
        try:
            code = str(prod.get('codigo','')).strip().upper()
            name = str(prod.get('nombre','')).strip()
            unit = prod.get('unidad')
            grp = prod.get('grupo')
            stock_min = int(prod.get('stockMin') or 0)
            if not code or not name:
                return False, 'Código y nombre son obligatorios'
            if len(name) < 2:
                return False, 'Nombre muy corto'
            cur = DB.cursor()
            cur.execute('INSERT INTO products (code,name,unit,grp,stock_min) VALUES (%s,%s,%s,%s,%s)', (code,name,unit,grp,stock_min))
            DB.commit()
            return True, 'Producto registrado'
        except mysql.connector.IntegrityError:
            return False, 'Código ya existe'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def calculate_stock(code: str):
        try:
            c = code.strip().upper()
            cur = DB.cursor()
            cur.execute('SELECT tipo,cantidad FROM movements WHERE product_code=%s ORDER BY fecha', (c,))
            rows = cur.fetchall()
            qty = 0.0
            for tipo, cantidad in rows:
                t = (tipo or '').upper()
                v = float(cantidad or 0)
                if t in (TIPOS_MOVIMIENTO['INGRESO'], TIPOS_MOVIMIENTO['AJUSTE_POSITIVO'], TIPOS_MOVIMIENTO['AJUSTE']):
                    qty += v
                elif t in (TIPOS_MOVIMIENTO['SALIDA'], TIPOS_MOVIMIENTO['AJUSTE_NEGATIVO']):
                    qty -= v
            if qty < 0:
                return 0.0
            return round(qty,4)
        except Exception as e:
            print('calc stock err', e)
            return 0.0

    @staticmethod
    def register_movement(mov: dict, usuario='Sistema'):
        try:
            code = str(mov.get('codigo','')).strip().upper()
            tipo = str(mov.get('tipo','')).strip().upper()
            cantidad = float(mov.get('cantidad') or 0)
            fecha = mov.get('fecha')
            if isinstance(fecha, str):
                try:
                    fecha_dt = datetime.fromisoformat(fecha)
                except:
                    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            elif isinstance(fecha, datetime):
                fecha_dt = fecha
            else:
                fecha_dt = datetime.now()
            if cantidad <= 0:
                return False, 'Cantidad debe ser > 0'
            if tipo not in TIPOS_MOVIMIENTO.values():
                return False, 'Tipo inválido'
            cur = DB.cursor()
            cur.execute('SELECT code FROM products WHERE code=%s', (code,))
            if not cur.fetchone():
                return False, 'Producto no existe'
            stock_actual = InventoryService.calculate_stock(code)
            if tipo in (TIPOS_MOVIMIENTO['SALIDA'], TIPOS_MOVIMIENTO['AJUSTE_NEGATIVO']) and stock_actual < cantidad:
                return False, f'Stock insuficiente (disponible {stock_actual})'
            stock_resultante = stock_actual
            if tipo in (TIPOS_MOVIMIENTO['INGRESO'], TIPOS_MOVIMIENTO['AJUSTE_POSITIVO'], TIPOS_MOVIMIENTO['AJUSTE']):
                stock_resultante += cantidad
            else:
                stock_resultante -= cantidad
            if stock_resultante < 0:
                stock_resultante = 0
            cur.execute('INSERT INTO movements (product_code,fecha,tipo,cantidad,usuario,timestamp,observaciones,stock_resultante) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (code, fecha_dt, tipo, cantidad, usuario, datetime.now(), mov.get('observaciones') or '', stock_resultante))
            DB.commit()
            return True, 'Movimiento registrado'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_all_stock():
        try:
            cur = DB.cursor()
            cur.execute('SELECT code,name,unit,grp,stock_min FROM products ORDER BY name')
            rows = cur.fetchall()
            out = []
            for r in rows:
                code = r[0]
                out.append({'code': r[0], 'name': r[1], 'unit': r[2], 'group': r[3], 'stock_min': int(r[4] or 0), 'stock': InventoryService.calculate_stock(code)})
            return out
        except Exception as e:
            print('get_all_stock err', e)
            return []

    @staticmethod
    def get_history(filters: dict):
        try:
            fd = filters.get('fechaDesde')
            fh = filters.get('fechaHasta')
            tipo = filters.get('tipo')
            params = []
            q = 'SELECT product_code,fecha,tipo,cantidad,usuario,observaciones,stock_resultante FROM movements WHERE 1=1'
            if fd:
                q += ' AND fecha >= %s'
                params.append(datetime.fromisoformat(fd + 'T00:00:00'))
            if fh:
                q += ' AND fecha <= %s'
                params.append(datetime.fromisoformat(fh + 'T23:59:59'))
            if tipo:
                q += ' AND tipo=%s'
                params.append(tipo)
            q += ' ORDER BY fecha DESC'
            cur = DB.cursor()
            cur.execute(q, tuple(params))
            rows = cur.fetchall()
            out = []
            for r in rows:
                out.append({'code': r[0], 'fecha': r[1].strftime('%d/%m/%Y %H:%M:%S'), 'tipo': r[2], 'cantidad': float(r[3]), 'usuario': r[4], 'observaciones': r[5], 'stock_resultante': float(r[6] or 0)})
            return out
        except Exception as e:
            print('get_history err', e)
            return []

    @staticmethod
    def get_summary():
        try:
            cur = DB.cursor()
            cur.execute('SELECT code,stock_min FROM products')
            rows = cur.fetchall()
            total = len(rows)
            cur.execute('SELECT COUNT(*) FROM movements')
            movs = cur.fetchone()[0]
            sin_stock = 0
            stock_bajo = 0
            for r in rows:
                code = r[0]
                stock_min = int(r[1] or 0)
                stock = InventoryService.calculate_stock(code)
                if stock <= 0:
                    sin_stock += 1
                elif stock <= stock_min and stock_min > 0:
                    stock_bajo += 1
            return {'totalProductos': total, 'totalMovimientos': movs, 'sinStock': sin_stock, 'stockBajo': stock_bajo}
        except Exception as e:
            print('summary err', e)
            return {'totalProductos': 0, 'totalMovimientos': 0, 'sinStock': 0, 'stockBajo': 0}

    @staticmethod
    def validate_integrity():
        errors = []
        try:
            cur = DB.cursor()
            # check tables
            for t in ['products', 'movements', 'users', 'units', 'groups_tbl']:
                cur.execute('SHOW TABLES LIKE %s', (t,))
                if not cur.fetchone():
                    errors.append(f'Tabla faltante: {t}')
            # product checks
            cur.execute('SELECT code,name,stock_min FROM products')
            prods = cur.fetchall()
            seen = set()
            for p in prods:
                if not p[0]:
                    errors.append('Producto sin codigo')
                c = str(p[0]).strip().upper()
                if c in seen:
                    errors.append(f'Código duplicado: {c}')
                seen.add(c)
                if not p[1] or len(str(p[1]).strip()) < 2:
                    errors.append(f'Nombre inválido: {c}')
            # movement checks
            cur.execute('SELECT product_code,tipo,cantidad FROM movements')
            movs = cur.fetchall()
            codes = set([x[0].strip().upper() for x in prods])
            for i, m in enumerate(movs, start=1):
                code = (m[0] or '').strip().upper()
                tipo = (m[1] or '').upper()
                cantidad = m[2]
                if code not in codes:
                    errors.append(f'Movimiento producto inexistente: {code} (fila {i})')
                if tipo and tipo not in TIPOS_MOVIMIENTO.values():
                    errors.append(f'Tipo inválido: {tipo} (fila {i})')
                try:
                    if cantidad is None or float(cantidad) <= 0:
                        errors.append(f'Cantidad inválida fila {i}')
                except:
                    errors.append(f'Cantidad no numérica fila {i}')
            return errors
        except Exception as e:
            return [str(e)]

# ------------------ EXPORT PDF (reportes avanzados) ------------------
class ReportGenerator:
    @staticmethod
    def export_movements_pdf(path, movimientos):
        try:
            doc = SimpleDocTemplate(path, pagesize=letter)
            elems = []
            elems.append(Paragraph('Historial de Movimientos', style=None))
            elems.append(Spacer(1, 12))
            data = [['Fecha', 'Código', 'Tipo', 'Cantidad', 'Usuario', 'Stock Resultante']]
            for m in movimientos:
                data.append([m['fecha'], m['code'], m['tipo'], str(m['cantidad']), m.get('usuario', ''), str(m.get('stock_resultante', ''))])
            t = Table(data, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A0F3A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
            ]))
            elems.append(t)
            doc.build(elems)
            return True, 'PDF generado'
        except Exception as e:
            return False, str(e)

# ------------------ UI (CustomTkinter) ------------------
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode('light')
        ctk.set_default_color_theme('blue')
        self.title('INVENTORY SYSTEM')
        self.geometry('1200x720')

        # sidebar
        self.sidebar = ctk.CTkFrame(self, width=240, fg_color=UI_COLORS['sidebar_bg'])
        self.sidebar.pack(side='left', fill='y')
        ctk.CTkLabel(self.sidebar, text=' JLM SYSTEM', font=('Arial', 20, 'bold'), text_color='BLACK').pack(pady=18)

        self.btns = []
        pages = [('Dashboard', DashboardPage), ('Nuevo producto', NewProductPage), ('Movimientos', MovementsPage), ('Inventario', InventoryPage), ('Reportes', ReportsPage), ('Buscar', SearchPage), ('Configuración', ConfigPage)]
        for txt, page in pages:
            b = ctk.CTkButton(self.sidebar, text=txt, width=200, fg_color=UI_COLORS['sidebar_bg'], hover_color=UI_COLORS['sidebar_top'], command=lambda p=page: self.show_page(p))
            b.pack(pady=8)
            self.btns.append(b)

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill='both', expand=True, padx=18, pady=18)

        self.page_instances = {}
        for _, PageCls in pages:
            p = PageCls(self.container, self)
            self.page_instances[PageCls] = p
            p.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_page(DashboardPage)

    def show_page(self, PageCls):
        for p in self.page_instances.values():
            p.lower()
        page = self.page_instances[PageCls]
        page.lift()
        if hasattr(page, 'refresh'):
            page.refresh()

# Pages below mirror previous design but with improved styling and functionality
class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, master):
        super().__init__(parent)
        ctk.CTkLabel(self, text='Dashboard General', font=('Arial', 24)).pack(anchor='nw', pady=12)
        self.kpi_frame = ctk.CTkFrame(self)
        self.kpi_frame.pack(fill='x', pady=10)
        self.vars = {k: ctk.StringVar(value='0') for k in ('totalProductos', 'totalMovimientos', 'sinStock', 'stockBajo')}
        for k in self.vars:
            f = ctk.CTkFrame(self.kpi_frame, corner_radius=8)
            f.pack(side='left', padx=10, pady=8)
            ctk.CTkLabel(f, textvariable=self.vars[k], font=('Arial', 20, 'bold')).pack(padx=20, pady=12)
            ctk.CTkLabel(f, text=k).pack(padx=10, pady=(0, 12))

    def refresh(self):
        r = InventoryService.get_summary()
        self.vars['totalProductos'].set(str(r['totalProductos']))
        self.vars['totalMovimientos'].set(str(r['totalMovimientos']))
        self.vars['sinStock'].set(str(r['sinStock']))
        self.vars['stockBajo'].set(str(r['stockBajo']))

class NewProductPage(ctk.CTkFrame):
    def __init__(self, parent, master):
        super().__init__(parent)
        ctk.CTkLabel(self, text='Registrar Nuevo Producto', font=('Arial', 20)).pack(anchor='nw', pady=10)
        frm = ctk.CTkFrame(self)
        frm.pack(fill='x', pady=8)
        self.codigo = ctk.CTkEntry(frm, placeholder_text='Código')
        self.codigo.grid(row=0, column=0, padx=6, pady=6)
        self.nombre = ctk.CTkEntry(frm, placeholder_text='Nombre')
        self.nombre.grid(row=0, column=1, padx=6, pady=6)
        self.unidad = ctk.CTkEntry(frm, placeholder_text='Unidad')
        self.unidad.grid(row=0, column=2, padx=6, pady=6)
        self.grupo = ctk.CTkEntry(frm, placeholder_text='Grupo')
        self.grupo.grid(row=0, column=3, padx=6, pady=6)
        self.stock_min = ctk.CTkEntry(frm, placeholder_text='Stock Mínimo')
        self.stock_min.grid(row=1, column=0, padx=6, pady=6)
        ctk.CTkButton(self, text='Registrar Producto', command=self.on_register, fg_color=UI_COLORS['success']).pack(pady=12)

    def on_register(self):
        prod = {'codigo': self.codigo.get(), 'nombre': self.nombre.get(), 'unidad': self.unidad.get(), 'grupo': self.grupo.get(), 'stockMin': self.stock_min.get()}
        ok, msg = InventoryService.register_product(prod)
        if ok:
            messagebox.showinfo('OK', msg)
            self.codigo.delete(0, 'end'); self.nombre.delete(0, 'end'); self.unidad.delete(0, 'end'); self.grupo.delete(0, 'end'); self.stock_min.delete(0, 'end')
        else:
            messagebox.showerror('Error', msg)

class MovementsPage(ctk.CTkFrame):
    def __init__(self, parent,master):
        super().__init__(parent)
        ctk.CTkLabel(self, text='Registro de Movimientos', font=('Arial', 20)).pack(anchor='nw', pady=10)
        frm = ctk.CTkFrame(self)
        frm.pack(fill='x', pady=8)
        self.codigo = ctk.CTkEntry(frm, placeholder_text='Código del producto')
        self.codigo.grid(row=0, column=0, padx=6, pady=6)
        self.fecha = ctk.CTkEntry(frm)
        self.fecha.insert(0, datetime.now().isoformat())
        self.fecha.grid(row=0, column=1, padx=6, pady=6)
        self.tipo = ctk.CTkComboBox(frm, values=list(TIPOS_MOVIMIENTO.values()))
        self.tipo.set(TIPOS_MOVIMIENTO['INGRESO'])
        self.tipo.grid(row=0, column=2, padx=6, pady=6)
        self.cantidad = ctk.CTkEntry(frm, placeholder_text='Cantidad')
        self.cantidad.grid(row=0, column=3, padx=6, pady=6)
        self.obs = ctk.CTkTextbox(self, height=80)
        self.obs.pack(fill='x', pady=8)
        ctk.CTkButton(self, text='Guardar Movimiento', command=self.on_save, fg_color=UI_COLORS['success']).pack(pady=6)

    def on_save(self):
        mov = {'codigo': self.codigo.get(), 'fecha': self.fecha.get(), 'tipo': self.tipo.get(), 'cantidad': self.cantidad.get(), 'observaciones': self.obs.get('1.0', 'end').strip()}
        ok, msg = InventoryService.register_movement(mov, usuario='usuario')
        if ok:
            messagebox.showinfo('OK', msg)
            self.codigo.delete(0, 'end'); self.cantidad.delete(0, 'end'); self.obs.delete('1.0', 'end')
        else:
            messagebox.showerror('Error', msg)

class InventoryPage(ctk.CTkFrame):
    def __init__(self, parent, master):
        super().__init__(parent)
        ctk.CTkLabel(self, text='Control de Inventario', font=('Arial', 20)).pack(anchor='nw', pady=10)
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill='x', pady=6)
        ctk.CTkButton(toolbar, text='Actualizar', command=self.refresh).pack(side='left', padx=6)
        ctk.CTkButton(toolbar, text='Exportar CSV', command=self.export_csv).pack(side='left', padx=6)
        ctk.CTkButton(toolbar, text='Exportar XLSX', command=self.export_xlsx).pack(side='left', padx=6)
        self.list = ctk.CTkScrollableFrame(self)
        self.list.pack(fill='both', expand=True, pady=10)

    def refresh(self):
        for child in self.list.winfo_children():
            child.destroy()
        rows = InventoryService.get_all_stock()
        for r in rows:
            ctk.CTkLabel(self.list, text=f"{r['code']} - {r['name']} - {r['stock']} ({r['stock_min']})").pack(anchor='w', pady=6)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv')
        if not path: return
        ok, msg = export_stock_csv(path)
        messagebox.showinfo('Export', msg if ok else msg)

    def export_xlsx(self):
        path = filedialog.asksaveasfilename(defaultextension='.xlsx')
        if not path: return
        ok, msg = export_stock_xlsx(path)
        messagebox.showinfo('Export', msg if ok else msg)

class ReportsPage(ctk.CTkFrame):
    def __init__(self, parent, master):
        super().__init__(parent)
        ctk.CTkLabel(self, text='Reportes y Análisis', font=('Arial', 20)).pack(anchor='nw', pady=10)
        frm = ctk.CTkFrame(self)
        frm.pack(fill='x', pady=6)
        self.fd = ctk.CTkEntry(frm, placeholder_text='Fecha Desde (YYYY-MM-DD)')
        self.fd.grid(row=0, column=0, padx=6, pady=6)
        self.fh = ctk.CTkEntry(frm, placeholder_text='Fecha Hasta (YYYY-MM-DD)')
        self.fh.grid(row=0, column=1, padx=6, pady=6)
        self.tipo = ctk.CTkComboBox(frm, values=['', 'INGRESO', 'SALIDA', 'AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO', 'AJUSTE'])
        self.tipo.grid(row=0, column=2, padx=6, pady=6)
        ctk.CTkButton(frm, text='Generar', command=self.generate).grid(row=0, column=3, padx=6)
        ctk.CTkButton(frm, text='Exportar PDF', command=self.export_pdf).grid(row=0, column=4, padx=6)
        self.out = ctk.CTkTextbox(self, height=250)
        self.out.pack(fill='both', pady=8)
        self.last_rows = []

    def generate(self):
        filtros = {'fechaDesde': self.fd.get(), 'fechaHasta': self.fh.get(), 'tipo': self.tipo.get()}
        rows = InventoryService.get_history(filtros)
        self.last_rows = rows
        self.out.delete('1.0', 'end')
        for r in rows:
            # añadir salto de línea para separar entradas
            self.out.insert('end', f"{r['fecha']} | {r['code']} | {r['tipo']} | {r['cantidad']} | {r['usuario']}\n")

    def export_pdf(self):
        if not self.last_rows:
            messagebox.showwarning('PDF', 'Genere el reporte primero')
            return
        path = filedialog.asksaveasfilename(defaultextension='.pdf')
        if not path:
            return
        ok, msg = ReportGenerator.export_movements_pdf(path, self.last_rows)
        messagebox.showinfo('PDF', msg if ok else msg)

class SearchPage(ctk.CTkFrame):
    def __init__(self, parent, master):
        super().__init__(parent)
        ctk.CTkLabel(self, text='Búsqueda de Productos', font=('Arial', 20)).pack(anchor='nw', pady=10)
        frm = ctk.CTkFrame(self)
        frm.pack(fill='x', pady=6)
        self.q = ctk.CTkEntry(frm, placeholder_text='Escriba para buscar...')
        self.q.grid(row=0, column=0, padx=6, pady=6)
        ctk.CTkButton(frm, text='Buscar', command=self.on_search).grid(row=0, column=1, padx=6)
        self.out = ctk.CTkTextbox(self, height=300)
        self.out.pack(fill='both', pady=8)

    def on_search(self):
        txt = self.q.get()
        rows = InventoryService.search_products(txt) if hasattr(InventoryService, 'search_products') else InventoryService.get_all_stock()
        self.out.delete('1.0', 'end')
        for r in rows:
            self.out.insert('end', f"{r.get('code')} | {r.get('name')} | {r.get('stock')}\n")

class ConfigPage(ctk.CTkFrame):
    def __init__(self, parent, master):
        super().__init__(parent)
        ctk.CTkLabel(self, text='Configuración del Sistema', font=('Arial', 20)).pack(anchor='nw', pady=10)
        ctk.CTkButton(self, text='Inicializar sistema', command=self.init_system).pack(pady=6)
        ctk.CTkButton(self, text='Crear admin (admin/admin)', command=self.create_admin).pack(pady=6)
        ctk.CTkButton(self, text='Validar integridad', command=self.validate).pack(pady=6)
        self.out = ctk.CTkTextbox(self, height=200)
        self.out.pack(fill='both', pady=8)

    def init_system(self):
        ok, msg = InventoryService.init_schema()
        self.out.insert('end', msg + '\n')
        messagebox.showinfo('Init', msg if ok else msg)

    def create_admin(self):
        try:
            InventoryService._ensure_defaults()
            self.out.insert('end', 'Defaults asegurados\n')
            messagebox.showinfo('Admin', 'Defaults asegurados (incluye usuario admin)')
        except Exception as e:
            self.out.insert('end', f'Error al crear admin: {e}\n')
            messagebox.showerror('Admin', str(e))

    def validate(self):
        errs = InventoryService.validate_integrity()
        self.out.delete('1.0', 'end')
        if not errs:
            self.out.insert('end', 'Sin errores detectados\n')
            messagebox.showinfo('Validar', 'Sin errores')
        else:
            for e in errs:
                self.out.insert('end', e + '\n')
            messagebox.showwarning('Validar', f'{len(errs)} errores encontrados')

# ------------------ Utilities for export (CSV/XLSX) ------------------
def export_stock_csv(path):
    try:
        rows = InventoryService.get_all_stock()
        if not rows:
            return False, 'Sin datos'
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['Código', 'Nombre', 'Unidad', 'Grupo', 'Stock Mínimo', 'Stock Actual', 'Estado', 'Diferencia'])
            for p in rows:
                estado = 'Normal'
                if p['stock'] <= 0:
                    estado = 'Sin Stock'
                elif p['stock'] <= p['stock_min'] and p['stock_min'] > 0:
                    estado = 'Stock Bajo'
                diff = p['stock'] - p['stock_min']
                w.writerow([p['code'], p['name'], p['unit'], p['group'], p['stock_min'], p['stock'], estado, diff])
        return True, 'CSV exportado'
    except Exception as e:
        return False, str(e)


def export_stock_xlsx(path):
    try:
        rows = InventoryService.get_all_stock()
        if not rows:
            return False, 'Sin datos'
        wb = Workbook()
        ws = wb.active
        ws.append(['Código', 'Nombre', 'Unidad', 'Grupo', 'Stock Mínimo', 'Stock Actual', 'Estado', 'Diferencia'])
        for p in rows:
            estado = 'Normal'
            if p['stock'] <= 0:
                estado = 'Sin Stock'
            elif p['stock'] <= p['stock_min'] and p['stock_min'] > 0:
                estado = 'Stock Bajo'
            diff = p['stock'] - p['stock_min']
            ws.append([p['code'], p['name'], p['unit'], p['group'], p['stock_min'], p['stock'], estado, diff])
        wb.save(path)
        return True, 'XLSX exportado'
    except Exception as e:
        return False, str(e)

# ------------------ Add small search method to InventoryService for UI use ------------------
def _search_products(text):
    try:
        if not text:
            return InventoryService.get_all_stock()
        q = '%' + text + '%'
        cur = DB.cursor()
        cur.execute('SELECT code,name,unit,grp,stock_min FROM products WHERE code LIKE %s OR name LIKE %s OR grp LIKE %s ORDER BY name', (q, q, q))
        rows = cur.fetchall()
        out = []
        for r in rows:
            code = r[0]
            out.append({'code': r[0], 'name': r[1], 'unit': r[2], 'group': r[3], 'stock_min': int(r[4] or 0), 'stock': InventoryService.calculate_stock(code)})
        return out
    except Exception as e:
        print('search err', e)
        return []

InventoryService.search_products = staticmethod(_search_products)

# ------------------ LOGIN DIALOG ------------------
class LoginDialog(ctk.CTkToplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.title("Login") # Título de la ventana
        self.geometry("600x450") # Tamaño de la ventana
        self.resizable(False, False) # No redimensionable

        base_dir = os.path.dirname(os.path.abspath(__file__)) # Directorio base del script

        # ===== FONDO GENERAL =====
        fondo_path = os.path.join(base_dir, "assets", "fondo.jpg")
        bg_image = ctk.CTkImage( # cargar imagen de fondo
            light_image=Image.open(fondo_path),
            size=(600, 450)
        )
        bg_label = ctk.CTkLabel(self, image=bg_image, text="")
        bg_label.place(relx=0, rely=0, relwidth=1, relheight=1) # colocar imagen de fondo

        # ===== TARJETA CENTRAL =====
        # ===== TARJETA CENTRAL =====
        self.card = ctk.CTkFrame(
            self,
            width=380,# ancho del card
            height=320, # alto del card
            corner_radius=20, # bordes redondeados
            fg_color="transparent" # color de fondo transparente
        )
        self.card.place(relx=0.5, rely=0.5, anchor="center") # centrar el card

# ===== FONDO DEL CARD (IMAGEN) =====
        card_bg_path = os.path.join(base_dir, "assets", "card_bg.jpg")
        card_bg_img = ctk.CTkImage(
            light_image=Image.open(card_bg_path), # cargar imagen de fondo del card
            size=(380, 320)# tamaño del card
        )

        card_bg_label = ctk.CTkLabel(
            self.card,
            image=card_bg_img,
            text=""
        )
        card_bg_label.place(relx=0, rely=0, relwidth=1, relheight=1) # colocar imagen de fondo del card

        # ===== LOGO =====
        logo_path = os.path.join(base_dir, "assets", "logo.png")
        logo_img = ctk.CTkImage( # cargar logo
            light_image=Image.open(logo_path),
            size=(60, 60)# tamaño del logo
        )
        ctk.CTkLabel(self.card, image=logo_img, text="").pack(pady=(20, 10)) # empaquetar logo con espaciado

        # ===== TITULO =====
        # ESTILO DEL TEXTO DEL TÍTULO, FUENTE MÁS GRANDE Y NEGRITA
        ctk.CTkLabel(
            self.card,
            text="INVENTORY SYSTEM",
            font=("Arial", 18, "bold")# Tamaño y estilo de fuente
        ).pack(pady=10) # Espaciado inferior

        # ===== USUARIO =====
        ctk.CTkLabel(self.card, text="Usuario").pack(pady=(10, 2))# Espaciado superior e inferior
        self.user = ctk.CTkEntry(self.card, width=200) # Ancho del campo de entrada
        self.user.pack() # Empaquetar el campo de entrada

        # ===== CONTRASEÑA =====
        ctk.CTkLabel(self.card, text="Contraseña").pack(pady=(10, 2))
        self.pw = ctk.CTkEntry(self.card, show="*", width=200)
        self.pw.pack()

        # ===== BOTÓN =====
        ctk.CTkButton(
            self.card,
            text="Entrar",
            width=200, # Ancho del botón
            command=self.try_login # Acción al hacer clic
        ).pack(pady=20) # Espaciado superior

        self.grab_set()

    def try_login(self):
        u = self.user.get().strip() # obtener usuario
        p = self.pw.get()
        if not u or not p:
            messagebox.showwarning("Error", "Ingrese usuario y contraseña")
            return
        ok, res = Auth.db_authenticate(u, p)
        if ok:
            self.on_success(res) # llamar callback con info usuario
            self.destroy()
        else:
            messagebox.showerror("Error", res)


# ------------------ START APPLICATION ------------------

def main():
    # Inicializar base de datos antes de todo
    InventoryService.init_schema()

    # Ventana raíz OCULTA solo para login
    root = ctk.CTk()
    root.withdraw()  # 👈 OCULTA la ventana principal

    def on_login_success(userinfo):
        root.destroy()  # cerrar ventana oculta

        app = MainApp()
        app.current_user = userinfo  # guardar usuario logueado
        app.mainloop()

    # Mostrar LOGIN primero
    LoginDialog(root, on_login_success)
    root.mainloop()


if __name__ == '__main__':
    main()


