from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors


class ReportGenerator:
    @staticmethod
    def export_movements_pdf(path, rows):
        doc = SimpleDocTemplate(path, pagesize=letter)
        elems = [Paragraph('Historial de Movimientos') , Spacer(1,12)]
        data = [['Fecha','Código','Tipo','Cantidad','Usuario','Stock']]
        for r in rows:
            data.append([r['fecha'], r['code'], r['tipo'], str(r['cantidad']), r.get('usuario',''), str(r.get('stock_resultante',''))])
        t = Table(data)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#5DADE2')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.4,colors.grey)]))
        elems.append(t)
        doc.build(elems)
        return True, 'PDF generado'


@staticmethod
def export_xlsx(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(['Fecha','Código','Tipo','Cantidad','Usuario','Stock'])
    for r in rows:
        ws.append([r['fecha'], r['code'], r['tipo'], r['cantidad'], r.get('usuario',''), r.get('stock_resultante','')])
    wb.save(path)
    return True, 'XLSX generado'