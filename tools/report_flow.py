"""Render the CLI/model branches as one static 16:9 report figure."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/architecture/report-flow.svg'


def main():
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" '
             'font-family="Microsoft YaHei,Arial,sans-serif">',
             '<rect width="1600" height="900" fill="#f5f7f8"/>',
             '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
             '<path d="M0 0L8 4L0 8Z" fill="#557983"/></marker></defs>']

    def text(x, y, value, size=22, color='#243c46', bold=False):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
                     f'font-weight="{"bold" if bold else "normal"}">{escape(value)}</text>')

    def box(x, y, w, h, title, lines, color='#206b78'):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
                     f'fill="white" stroke="{color}" stroke-width="2"/>')
        text(x+18, y+33, title, 24, color, True)
        for i, line in enumerate(lines):
            text(x+18, y+65+29*i, line, 20)

    def wire(path, arrow=True):
        marker = ' marker-end="url(#arrow)"' if arrow else ''
        parts.append(f'<path d="{path}" fill="none" stroke="#557983" stroke-width="2"{marker}/>')

    text(45, 65, '程序流程：选择入口，再执行对应计算', 34, bold=True)
    text(45, 107, '各支路独立调用；NASA9物性、HP和喷管内核按模型需要复用。', 23)
    box(40, 330, 290, 182, '输入与校验', ['CLI / 交互菜单 / INI', '解析单位、范围、模型', '进入所选计算支路'])
    branches = [
        ('L0 理想喷管', ['给定 γ、R、T₀、P₀、面积与背压 → 定比热喷管；不经过HP'], '#206b78'),
        ('推力室', ['气态 / 液态入口焓与元素 → HP → 冻结喷管 → 流量与推力'], '#206b78'),
        ('给定热状态外排循环', ['泵 → 给定温度TP → 涡轮与分流 → 两喷管及所需热量Q'], '#206b78'),
        ('绝热开式 / 富氧补燃循环', ['泵后焓 → 预燃HP与轴功 → 分流或回流 → 主室HP / 喷管'], '#206b78'),
        ('regime 独立诊断入口', ['理想状态 → pa/pe、匹配面积比、0.4pa经验参考；不预测分离'], '#a26127'),
    ]
    wire('M330 421H365', False)
    wire('M365 219V699', False)
    wire('M1210 219V699', False)
    for i, (title, lines, color) in enumerate(branches):
        y = 170+120*i
        box(410, y, 765, 98, title, lines, color)
        wire(f'M365 {y+49}H404')
        wire(f'M1175 {y+49}H1210', False)
    wire('M1210 401H1248')
    box(1255, 300, 305, 240, '返回状态', ['成功：JSON / 中文表格', '失败：状态码与诊断', '计算失败不写回结果', '归档由运行工具完成'])
    text(45, 797, '附着喷管：pa > pe 返回越域。仅部分交互入口提供诊断；循环不会自动改换模型。', 23)
    text(45, 843, 'c*由喉部阻塞流量得到；给定温度循环的所需Q与绝热循环的Q=0分开处理。', 23)
    parts.append('</svg>')
    OUT.write_text('\n'.join(parts)+'\n', encoding='utf-8')
    print(OUT)


if __name__ == '__main__':
    main()
