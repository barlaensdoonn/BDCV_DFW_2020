# extraer datos de páginas de INALI sobre clasificación geográfica de lenguas indígenas
# base URL: https://www.inali.gob.mx/clin-inali/
# creado por Brandon Aleson 4/22/20
# versión actualizado 7/10/20

import os
import bs4
import json
import requests
import logging
import logging.config

# cada vez que hacemos una toca al inali.cob.mx, recibimos una alarma así:
# "InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised."
# creo q los certificados de INALI se han caducado
# por no ver la alarma cada vez que agarramos un vínculo de INALI, la deshabilitamos aquí
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# configuración de logging
log_level = 'INFO'
log_file_path = os.path.join('logs', 'scrape_INALI.log')
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 10485760,
            'backupCount': 2,
            'level': log_level,
            'formatter': 'standard',
            'filename': log_file_path,
            'encoding': 'utf8'
        },
        'stream': {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        '': {
            'handlers': ['file', 'stream'],
            'level': log_level,
            'propagate': False
        }
    }
}


# aquí tenemos nuestro modelo de datos para cada representación de un variante en su JSON file
modelo_de_representacion_JSON = {
    'agrupacion_lingüística': '',
    'familia_lingüística': '',
    'autodenominaciones': [['']],
    'variante': '',
    'representación_geográfica': [{}]  # esta es una lista de dictionaries porque un variante puede ser hablado en estados múltiples
}


def get_agrup_urls(caldo, base_url):
    '''
    por suerte todos los vínculos de agrupaciones lingüísticas
    se encuentran entre "rows" <tr></tr> en el base_url
    '''
    vinc_trs = caldo.find_all('tr')
    agrup_vincs = []

    # extraer los objetos que tienen el parte "href"
    for tr in vinc_trs:
        agrup_vincs.extend(tr.find_all('a'))
    logger.info('ha sacado {} vinculos de agrupaciones lingüísticas en {}'.format(len(agrup_vincs), base_url))

    # construimos los URLs completos
    return [os.path.join(base_url, agrup_vinc['href']) for agrup_vinc in agrup_vincs]


def sacar_agrup_y_familia(sopa):
    '''
    @sopa: debe ser la página de un nivel más alto que la que
           tiene todos los datos específicos de los variantes
           por ejemplo: https://www.inali.gob.mx/clin-inali/html/l_nahuatl.html
    'agrup' significa la Agrupación lingüística
    'familia' significa la Familia lingüística
    '''
    ling_queridos = []
    ling_indexes = {
        'agrupación': 0,
        'familia': -1
    }

    for key, value in ling_indexes.items():
        ling_querido = sopa.body.h4.contents[value].split(':')[-1].strip()
        logger.info('ha sacado el dato tipo {} de la sopa HTML: {}'.format(key, ling_querido))
        ling_queridos.append(ling_querido)
    return ling_queridos


def sacar_autodes(td):
    '''
    @td: debe ser el primer table de una row, en el que queda las autodenominaciones y el variante

    NOTA: este método de extraer las autodenominaciones presupone que siempre hay dos
    maneras de describir las autodes: primero como string y luego lo mismo de otra forma en brackets.
    entonces lo separamos con un newline '\n' como aparece en la página de INALI

    parace que el variante no queda entre "paragraph HTML tags" mientras las autodenominaciones sí,
    así que sacamos los autodes por buscar todos los paragraph tags <p></p> en el table
    '''
    pstrings = []
    for p in td.find_all('p'):
        for pstr in p.strings:
            pstrings.append(pstr.strip())

    # reconstruir los autodes como aparecen en la página.
    # a veces hay más que una autodenominacion en una agrupación lingüística,
    # así que las autodenominaciones var a ser un list de lists de strings,
    # y tendrá uno o más entradas siguiendo los datos
    autodes = []
    for i in range(len(pstrings)):
        if (i+1) % 2 == 0:
            # autode = '/n'.join[pstrings[i-1], pstrings[i]])
            autode = [pstrings[i-1], pstrings[i]]
            autodes.append(autode)

    logger.info('autodenominaciones extraidos del table: {}'.format(autodes))
    return autodes


def sacar_variante(td):
    '''@td: debe ser el mismo table que tiene las autodenominaciones'''
    variante = td.contents[-1].strip()
    variante = variante.strip('<>')
    logger.info('variante extraido del table: {}'.format(variante))
    return variante


def parse_datos_geos(datos_geos):
    '''@datos_geo debe ser un table de HTML'''
    repr_geo = {}

    for parte in datos_geos:
        # primero identificamos el estado, que siempre está en mayúsculas
        # esta parte del table is of class 'bs4.element.NavigableString'
        if parte.__class__ == bs4.element.NavigableString:
            if parte.isupper():
                estado = parte.strip(' :\t\r\n')
                repr_geo[estado] = {}
                continue

        # luego, si el parte tiene los bold HTML tags "<br></br>"
        # es otro tipo de bs4 object of class 'bs4.element.Tag'
        if parte.__class__ == bs4.element.Tag and parte.decode() != '<br/>':
            municipio = parte.text
            repr_geo[estado][municipio] = []

        # los localidades también son de la class 'bs4.element.NavigableString'
        # si ya tenemos el estado, sabemos que esta parte describe localidades
        if parte.__class__ == bs4.element.NavigableString and repr_geo[estado]:
            localidades = parte.strip(' :\n')
            repr_geo[estado][municipio].extend([localidades.strip('.')])

        # si hay multiples estados en los que se hablan la misma variante
        # van a ser separados por "linebreaks". entonces usamos el linebreak
        # como un flag para identificar que hay que construir otro repr_geo nuevo
        if parte.__class__ == bs4.element.Tag and parte.decode() == '<br/>':
            yield repr_geo
            repr_geo = {}

    # yield el último
    logger.info('hemos extraido todos los datos geográficos de este table')
    yield repr_geo


def output_variante_json(datos):
    '''construir un filename del nombre de variante y escribir los datos a un archivo de JSON'''
    variante_split = datos['variante'].strip('<>').split(' ')
    datos_file_ending = ('_').join([vsplit.strip(',') for vsplit in variante_split])

    # crear una carpeta por la agrupación si no existe
    outpath = os.path.join('agrupaciones_de_INALI', '_'.join(datos['agrupacion_lingüística'].split(' ')))
    try:
        os.makedirs(outpath)
        logger.info('carpeta {} creado'.format(outpath))
    except FileExistsError:
        pass

    outfile = os.path.join(outpath, 'datos_de_{}.json'.format(datos_file_ending))
    logger.info('escribiendo los datos del variante {} a "{}"'.format(datos_file_ending, outfile))
    with open(outfile, 'w') as outf:
        outf.write(json.dumps(datos))


if __name__ == '__main__':
    # configuración de logging
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger('scrape_INALI')
    logger.info('* * * * * * * * * * * * * * * * *')
    logger.info('logging configured')

    # esto es el URL donde se encuentra todos los vínculos de las agrupaciones lingüísticas
    # ver aquí más detalle sobre "verify" y certificates:
    # https://stackoverflow.com/questions/28667684/python-requests-getting-sslerror
    base_url = 'https://www.inali.gob.mx/clin-inali/'

    # sacamos todos los URLs de agrupaciones lingüísticas que hay en el base_url
    r = requests.get(base_url, verify=False)
    caldo = bs4.BeautifulSoup(r.text, 'html.parser')
    agrup_urls = get_agrup_urls(caldo, base_url)

    for agrup_url in agrup_urls:
        # TEMPORARY:
        if agrup_url in ['https://www.inali.gob.mx/clin-inali/html/l_mazahua.html', 'https://www.inali.gob.mx/clin-inali/html/l_qanjobal.html']:
            logger.warning('esta vínculo echa una Exception: {}'.format(agrup_url))
            logger.warning('seguimos con la próxima...')
            continue

        # empezamos en esta página (l_<variante>.html) para agarrar
        # la información de Agrupación y Familia Lingüística
        logger.info('sacando datos de {}'.format(agrup_url))
        r = requests.get(agrup_url, verify=False)
        sopa = bs4.BeautifulSoup(r.text, 'html.parser')
        agrup_ling, familia_ling = sacar_agrup_y_familia(sopa)

        # TEMPORARY:
        if agrup_ling in ['Chuj', 'kiliwa']:
            logger.warning('esta agrupación echa una Exception: {}'.format(agrup_ling))
            logger.warning('seguimos con la próxima')
            continue

        # construimos el vínculo de la agrupación
        var_url = ''.join([base_url, 'html/', sopa.body.a.attrs['href']])
        logger.info('ya bajamos un nivel para sacar los datos de los variantes de {}'.format(var_url))
        r = requests.get(var_url, verify=False)
        guisado = bs4.BeautifulSoup(r.text, 'html.parser')

        # los datos específicos que buscamos aparacen
        # entre los "rows" <tr></tr> tags que hay en una página
        # por ejemplo la página de nahuatl tiene 30 rows de contenido relevante
        all_trs = guisado.find_all('tr')
        all_trs.pop(0)  # (la primera row (representado por all_trs[0]) no nos importa porque no tiene un table)
        logger.info('hay {} variante(s) en esta agrupación lingüística: {}'.format(len(all_trs), agrup_ling))

        # más específicamente, los datos del los lenguajes quedan dentro
        # de los tables que así mismos están dentro de un "row"
        # es decir, encontramos los datos que nos interesa entre los tags <td></td>
        for tr in all_trs:
            all_tds = tr.find_all('td')
            # el primer table contiene las autdenominaciones y el nombre de variante
            autodes = sacar_autodes(all_tds[0])
            variante = sacar_variante(all_tds[0])

            # TEMPORARY:
            if variante in ['otomí de Ixtenco', 'otomí de Tilapa o del sur', 'zapoteco de San Felipe Tejalápam']:
                logger.warning('este variante echa una Exception: {}'.format(variante))
                logger.warning('seguimos con el próximo...')
                continue

            # seguimos con los datos geográficos, que están en el segundo table
            gdatos = all_tds[1]
            repr_geo = [geo for geo in parse_datos_geos(gdatos) if geo]

            # ya podemos usar nuestro modelo de JSON para colocar los datos
            datos_del_variante = {
                'agrupacion_lingüística': agrup_ling,
                'familia_lingüística': familia_ling,
                'autodenominaciones': autodes,
                'variante': variante,
                'representación_geográfica': repr_geo
            }

            # actualmente ya tenemos todos los datos, entonces los escribimos a un JSON file
            output_variante_json(datos_del_variante)
            logger.info('- - - - - - - - - - - - - - - - -')
