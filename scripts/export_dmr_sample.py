"""
export_dmr_sample.py
以 d_mr_other_1_20 为主，反查 d_mr（A48_A49 关联），
取 2020-01 月的前 5 条，导出为 DOCX（黑白、简体中文）。
列数太多（285+210），按每组 30 列分段建表，避免超宽乱版。
"""
import sys, pymysql
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding='utf-8')

DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=30)

SAMPLE_LIMIT = 5      # 示范行数（改成 None 可跑全量）
COLS_PER_TABLE = 30   # 每段表格列数（含2个Key列）
OUTPUT = r'd:\iCode\cursor\d_hos_backend_cc_20251230\scripts\dmr_sample.docx'

# ─── 取数 ─────────────────────────────────────────────────────────
print('连接数据库...')
conn = pymysql.connect(**DB)
cur = conn.cursor(pymysql.cursors.DictCursor)

# 获取列名
c2 = conn.cursor()
c2.execute("SHOW COLUMNS FROM d_mr_other_1_20")
other_cols = [r[0] for r in c2.fetchall()]

c2.execute("SHOW COLUMNS FROM d_mr")
mr_cols = [r[0] for r in c2.fetchall()]
c2.close()

# 以 other 为主，筛选 2020-01（通过关联 d_mr 的 B15 字段）
limit_clause = f"LIMIT {SAMPLE_LIMIT}" if SAMPLE_LIMIT else ""

cur.execute(f"""
    SELECT o.*, m.B15
    FROM d_mr_other_1_20 o
    INNER JOIN d_mr m ON CONCAT(m.A48,'_',m.A49) = CONCAT(o.A48,'_',o.A49)
    WHERE m.B15 LIKE '2020/1/%%'
    GROUP BY CONCAT(o.A48,'_',o.A49)
    {limit_clause}
""")
other_rows = cur.fetchall()
print(f'd_mr_other_1_20 样本行数: {len(other_rows)}')

if not other_rows:
    print('无数据，退出')
    conn.close()
    sys.exit(1)

# 取出匹配的 d_mr 行
keys = [f"CONCAT(A48,'_',A49)='{r['A48']}_{r['A49']}'" for r in other_rows]
cur.execute(f"""
    SELECT * FROM d_mr
    WHERE ({' OR '.join(keys)})
    AND B15 LIKE '2020/1/%%'
""")
mr_rows_raw = cur.fetchall()
mr_dict = {f"{r['A48']}_{r['A49']}": r for r in mr_rows_raw}
print(f'd_mr 匹配行数: {len(mr_dict)}')

cur.close(); conn.close()

# 去掉 other 中 B15 辅助列、去掉重复 A48/A49/ID/T_ID
SKIP_OTHER = {'ID', 'T_ID', 'B15'}
other_data_cols = [c for c in other_cols if c not in SKIP_OTHER]

# 合并列顺序：d_mr 全部列 + other 独有列（去 A48/A49）
other_only_cols = [c for c in other_data_cols if c not in {'A48', 'A49'}]
all_cols = mr_cols + other_only_cols   # 总列列表

# 合并行
combined = []
for r_other in other_rows:
    key = f"{r_other['A48']}_{r_other['A49']}"
    r_mr = mr_dict.get(key, {})
    merged = {}
    for c in mr_cols:
        merged[c] = r_mr.get(c, '')
    for c in other_only_cols:
        merged[c] = r_other.get(c, '')
    merged['__key__'] = key
    combined.append(merged)

print(f'合并后行数: {len(combined)}, 总列数: {len(all_cols)}')


# ─── 生成 DOCX ────────────────────────────────────────────────────
def set_cell_text(cell, text, font_size=6, bold=False):
    cell.text = ''
    para = cell.paragraphs[0]
    run = para.add_run(str(text) if text is not None else '')
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.name = '宋体'
    run.font.color.rgb = RGBColor(0, 0, 0)
    # 设置中文字体
    r = run._r
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '宋体')
    rPr.insert(0, rFonts)


def add_table_section(doc, title, rows_data, cols_chunk, all_rows):
    doc.add_paragraph(title).runs[0].font.size = Pt(9)
    doc.paragraphs[-1].runs[0].bold = True

    tbl = doc.add_table(rows=1 + len(all_rows), cols=len(cols_chunk))
    tbl.style = 'Table Grid'

    # 表头
    hdr = tbl.rows[0].cells
    for j, col in enumerate(cols_chunk):
        set_cell_text(hdr[j], col, font_size=6, bold=True)

    # 数据行
    for i, row in enumerate(all_rows):
        cells = tbl.rows[i + 1].cells
        for j, col in enumerate(cols_chunk):
            val = row.get(col, '')
            set_cell_text(cells[j], val, font_size=6)

    doc.add_paragraph('')   # 间隔


doc = Document()

# 页面设置：横向 A4，窄边距
section = doc.sections[0]
section.orientation = WD_ORIENT.LANDSCAPE
section.page_width, section.page_height = Cm(42), Cm(29.7)
section.top_margin = section.bottom_margin = Cm(1)
section.left_margin = section.right_margin = Cm(1)

# 标题
title_para = doc.add_paragraph('D_MR + D_MR_OTHER_1_20 合并数据（2020年1月 示范）')
title_para.runs[0].font.size = Pt(12)
title_para.runs[0].bold = True
title_para.runs[0].font.name = '宋体'
doc.add_paragraph(f'记录数：{len(combined)}  总字段数：{len(all_cols)}  关联键：A48_A49').runs[0].font.size = Pt(8)
doc.add_paragraph('')

# 按 COLS_PER_TABLE 分段
for start in range(0, len(all_cols), COLS_PER_TABLE):
    chunk = all_cols[start:start + COLS_PER_TABLE]
    seg = f'字段 {start+1}–{start+len(chunk)}（共 {len(all_cols)} 列）'
    add_table_section(doc, seg, combined, chunk, combined)

doc.save(OUTPUT)
print(f'\n已生成: {OUTPUT}')
