# -*- coding: utf-8 -*-
"""
编译 upload/template 下的 Discuz 模板 CSS 为静态预览资源（GitHub Pages 演示页用）。

用法：在仓库根目录执行  python preview/compile.py
输出：preview/assets/*.css

原理：复刻 source/function/cache/cache_styles.php 的 writetocsscache() 编译管线——
1. 将模板 CSS 中的 {VARS} 占位符替换为 discuz_style_*.json 里的风格变量值；
2. module.css 的 /** 模块 **/ 标记按源码方式转为 [模块]（使标记后第一条规则失效）；
3. 相对 url() 统一加 /upload/ 前缀（Pages 站点上以 /upload/ 为论坛根目录），
   data:、http(s):、根路径与锚点不受影响。
"""
import json, re, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'upload'))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

def load_style(jsonpath):
    with open(jsonpath, encoding='utf-8') as f:
        return json.load(f)['Data']

def setcssbackground(value, styleimgdir):
    """Mirror setcssbackground() from cache_styles.php."""
    codes = value.split(' ')
    css = ''
    for i, c in enumerate(codes[:2]):
        if not c:
            continue
        if c.startswith('#'):
            css += c.upper() + ' '
        elif re.match(r'^(https?:)?//', c):
            css += 'url("%s") ' % c
        else:
            css += 'url("%s/%s") ' % (styleimgdir.rstrip('/'), c)
    css += ' '.join(codes[2:])
    css = css.strip()
    return 'background: ' + css if css else ''

def build_map(data, styleimgdir):
    m = {}
    style = data['style']
    for k, v in style.items():
        m[k] = str(v)
    # derived bgcode keys
    for k in list(style.keys()):
        if k.endswith('bgcolor'):
            m[k[:-5] + 'code'] = setcssbackground(style[k], styleimgdir)
    m['staticurl'] = 'static/'
    m['styleimgdir'] = styleimgdir
    m['imgdir'] = style.get('imgdir') or 'static/image/common'
    m['verhash'] = '123'
    return m

def expand(css, m, missing):
    css = re.sub(r'<\?.+?\?>\s*', '', css, flags=re.S)
    def sub(mo):
        tok = mo.group(1).lower()
        if tok not in m:
            missing.add(tok)
            return ''
        return m[tok]
    css = re.sub(r'\{([A-Z0-9]+)\}', sub, css)
    # 相对 url() 指向仓库 upload/ 目录（data:、http(s):、//、根路径与锚点不处理）。
    # 注意：不能用可选引号组 + 负向断言，正则回溯会让 url("data:...") 被误改写成
    # url(/upload/"data:...")，导致后续整个样式块被解析器吞掉。
    def prefix_url(mo):
        quote, nxt = mo.group(1), mo.group(2)
        if nxt.startswith(('data:', 'https:', 'http:', '//', '/', '#')):
            return mo.group(0)
        return 'url(%s/upload/%s' % (quote, nxt)
    css = re.sub(r'url\((["\']?)(.)', prefix_url, css)
    return css

def markers(css):
    # cache_styles.php:175-177 仅对 module 条目生效
    return re.sub(r'/\*\*\s*(.+?)\s*\*\*/', r'[\1]', css)

def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()

os.makedirs(OUT, exist_ok=True)

# ---- template/default（t6 天机蓝 extstyle）----
d1 = os.path.join(ROOT, 'template', 'default')
data1 = load_style(os.path.join(d1, 'discuz_style_default.json'))
m1 = build_map(data1, '')
missing1 = set()
with open(os.path.join(OUT, 'default_common.css'), 'w', encoding='utf-8') as f:
    f.write(expand(read(os.path.join(d1, 'common', 'common.css')), m1, missing1))
with open(os.path.join(OUT, 'default_module.css'), 'w', encoding='utf-8') as f:
    f.write(markers(expand(read(os.path.join(d1, 'common', 'module.css')), m1, missing1)))
with open(os.path.join(OUT, 't6_style.css'), 'w', encoding='utf-8') as f:
    f.write(read(os.path.join(d1, 'style', 't6', 'style.css')))
print('default template missing tokens:', sorted(missing1) or 'none')

# ---- template/discuzx5（天机蓝风格变量）----
d2 = os.path.join(ROOT, 'template', 'discuzx5')
data2 = load_style(os.path.join(d2, 'discuz_style_discuzx5.json'))
m2 = build_map(data2, 'template/discuzx5/static/')
missing2 = set()
# cache_styles.php 将 common+extend_common 与 module+extend_module 分别编译成两个文件
c2 = expand(read(os.path.join(d1, 'common', 'common.css')), m2, missing2) + '\n' + \
     expand(read(os.path.join(d2, 'common', 'extend_common.css')), m2, missing2)
m2css = expand(read(os.path.join(d1, 'common', 'module.css')), m2, missing2) + '\n' + \
        expand(read(os.path.join(d2, 'common', 'extend_module.css')), m2, missing2)
with open(os.path.join(OUT, 'discuzx5_common.css'), 'w', encoding='utf-8') as f:
    f.write(c2)
with open(os.path.join(OUT, 'discuzx5_module.css'), 'w', encoding='utf-8') as f:
    f.write(markers(m2css))
print('discuzx5 template missing tokens:', sorted(missing2) or 'none')
print('written to', OUT)
