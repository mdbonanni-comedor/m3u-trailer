"""Arma, a partir del proyecto iptv-org/epg, un archivo de canales por país (canales/xx.channels.xml)
para después bajar la programación con su "grab". Lo usa .github/workflows/guia.yml.

  python3 armar_guias.py preparar RUTA_EPG "ar es it ..."   -> canales/xx.channels.xml + paises.json
  python3 armar_guias.py indice                              -> guias/index.json (países y cantidad de canales)

País de cada canal: el sufijo de su xmltv_id ("Telefe.ar@SD" -> ar) o, si no tiene, el del archivo del sitio
("mi.tv_ar.channels.xml" -> ar). Un canal aparece una sola vez por país (se prefiere el sitio de ese país).
"""
import glob, html, json, os, re, sys, unicodedata

MAX_POR_PAIS = int(os.environ.get('MAX_CANALES', '700'))   # tope para que cada país termine en un tiempo razonable
ALIAS = {'uk': 'gb'}                                         # iptv-org usa "uk"; la app usa el código ISO "gb"


def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\b(hd|fhd|uhd|sd|4k)\b', ' ', s)
    return re.sub(r'[^a-z0-9+]', '', s)


def preparar(epg, paises):
    quiero = set(paises.split())
    por_pais = {}
    for f in sorted(glob.glob(os.path.join(epg, 'sites', '*', '*.channels.xml'))):
        m = re.search(r'_([a-z]{2})(?:\d*)\.channels\.xml$', f)
        pais_archivo = ALIAS.get(m.group(1), m.group(1)) if m else ''
        x = open(f, encoding='utf-8').read()
        for c in re.finditer(r'<channel\b([^>]*)>(.*?)</channel>', x, re.S):
            attrs, nombre = c.group(1), html.unescape(c.group(2)).strip()
            xid = (re.search(r'xmltv_id="([^"]*)"', attrs) or [None, ''])[1]
            p = re.search(r'\.([a-z]{2})(?:@|$)', xid)
            pais = ALIAS.get(p.group(1), p.group(1)) if p else pais_archivo
            if not pais or pais not in quiero or not nombre:
                continue
            if not xid:   # sin identificador: se le arma uno con el nombre, para que salga en la guía
                xid = re.sub(r'[^A-Za-z0-9]', '', nombre) + '.' + pais
                attrs = re.sub(r'xmltv_id="[^"]*"', '', attrs) + ' xmltv_id="%s"' % xid
            clave = xid.lower().split('@')[0]   # un canal = un identificador (sin la variante "@SD", "@HD"...)
            d = por_pais.setdefault(pais, {})
            propio = pais_archivo == pais
            if clave in d and (d[clave][0] or not propio):
                continue
            d[clave] = (propio, '  <channel%s>%s</channel>' % (attrs, html.escape(nombre, quote=False)))
    os.makedirs('canales', exist_ok=True)
    hechos = []
    for pais, d in sorted(por_pais.items()):
        filas = [v[1] for v in sorted(d.values(), key=lambda v: not v[0])][:MAX_POR_PAIS]
        open('canales/%s.channels.xml' % pais, 'w', encoding='utf-8').write(
            '<?xml version="1.0" encoding="UTF-8"?>\n<channels>\n' + '\n'.join(filas) + '\n</channels>\n')
        hechos.append(pais)
        print(pais, len(filas), 'canales')
    json.dump(hechos, open('paises.json', 'w'))


def indice():
    out = []
    for f in sorted(glob.glob('guias/guia_*.xml')):
        x = open(f, encoding='utf-8').read()
        n, p = x.count('<channel '), x.count('<programme ')
        if p:
            out.append({'code': re.search(r'guia_([a-z]{2})\.xml$', f).group(1), 'channels': n, 'programmes': p})
    json.dump({'updated': __import__('time').strftime('%Y-%m-%d %H:%M UTC', __import__('time').gmtime()), 'countries': out},
              open('guias/index.json', 'w'), ensure_ascii=False)
    print(len(out), 'países con guía')


if __name__ == '__main__':
    if sys.argv[1] == 'preparar':
        preparar(sys.argv[2], sys.argv[3])
    else:
        indice()
