# buscar datos de INALI en registros MARC del católogo del la biblioteca de COLMEX
# base URL: https://www.inali.gob.mx/clin-inali/
# creado por Brandon Aleson 6/17/20
# versión actualizado 8/16/20

import os
import csv
import json
import logging
import logging.config
from collections import Counter


# configuración de logging
log_level = 'INFO'
log_file_path = os.path.join('logs', 'buscar_registros_MARC.log')
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


# nuestro modelo de datos para los resultados de una búsqueda
# los 'fieldnames' de nuestro archivo de output hay que
# corresponder con los nombres de los llaves en este modelo
datos_del_registro = {
    'index': '',
    'id': '',
    'agrupaciones': [],
    'campos_de_agrupaciones': [],
    'variantes': [],
    'campos_de_variantes': []
}


def sacar_datos_de_carpetas(carpeta_mas_alta):
    datos_de_json = []
    for dirpath, dirname, filenames in os.walk(carpeta_mas_alta):
        if not dirname and filenames:
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r') as fpath:
                    dato_json = json.loads(fpath.read())
                    datos_de_json.append(dato_json)
    return datos_de_json


def escribir_al_archivo(archivo, datos):
    '''
    chequamos si el archivo ya existe; si no existe escribimos el 'header' primero
    si existe no queremos escribir el 'header' multiples veces
    usamos el modo 'a' en vez de 'w' para que nunca borremos un archivo que ya existe
    '''
    # estos fieldnames viene del los nombres de las llaves de nuestro modelo de datos
    fieldnames = ['index', 'id', 'agrupaciones', 'campos_de_agrupaciones',
                  'variantes', 'campos_de_variantes']

    if os.path.isfile(archivo):
        with open(archivo, 'a') as outfile:
            escritor = csv.DictWriter(outfile, fieldnames)
            escritor.writerow(datos_del_registro)
    else:
        with open(archivo, 'a') as outfile:
            escritor = csv.DictWriter(outfile, fieldnames)
            escritor.writeheader()
            escritor.writerow(datos_del_registro)


if __name__ == '__main__':
    # configuración de logging
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger('scrape_INALI')
    logger.info('* * * * * * * * * * * * * * * * *')
    logger.info('logging configured')

    INALI_carpeta = os.path.join('agrupaciones_de_INALI')  # los datos que ya sacamos de las páginas de INALI
    MARC_ejemplo = os.path.join('documentos', 'Jonathan_Israel_results_nahuatl.csv')  # un ejemplo de un archivo con multiple registros MARC del catálogo

    # inciamos nuestro archivo que guardará resultados positivos de una búsqueda
    output_archivo = os.path.join('documentos', 'MARC_busqueda_ejemplo.csv')

    # primero sacamos los datos de INALI, de los archivos en los carpetas bajo de INALI_carpeta
    logger.info('sacando los datos de INALI de sus carpetas...')
    datos_de_inali = sacar_datos_de_carpetas(INALI_carpeta)

    # agarrar todos los distintos agrupaciones lingüísticas de los datos de INALI para la búsqueda
    logger.info('sacando los distintos agrupaciones para la comparación...')
    agrupaciones = set()
    for dato in datos_de_inali:
        agrupaciones.add(dato['agrupacion_lingüística'])

    # cambiamos las agrups a minúsculo para comparación; haremos lo mismo con los variantes
    agrups_lower = [agrupacion.lower() for agrupacion in agrupaciones]

    # hacemos lo mismo con los variantes de los datos de INALI
    logger.info('sacando los variantes para la comparación...')
    variantes = [dato['variante'].lower() for dato in datos_de_inali]

    logger.info('tenemos {} agrupaciones y {} variantes para la búsqueda'.format(len(agrups_lower), len(variantes)))

    # iniciamos nuestro variable para el index del registro MARC como '0'
    # ya que en el archivo de registros MARC de hecho los datos empieza con index '1'
    registro_index = '0'

    # abrimos nuestro archivo de registros MARC
    logger.info('empezamos la búsqueda en el archivo {}'.format(MARC_ejemplo))
    with open(MARC_ejemplo, 'r') as marcs:
        marcs_reader = csv.reader(marcs)
        for row in marcs_reader:

            # si el index del row cambia, ya estamos en nuevo registro de MARC
            if row[0] != registro_index and int(row[0]) > 0:
                logger.info('encontramos nuevo registro de MARC con index {}'.format(row[0]))

                # si el index del registro es 1 o más, vemos si hay datos encontrados de la búsqueda
                if int(registro_index) >= 1:

                    # si hay datos encontrados, los escribimos a nuestro archivo de output
                    if len(datos_del_registro['agrupaciones']) > 0 or len(datos_del_registro['variantes']) > 0:
                        logger.info('escribiendo los datos del registro MARC con index {} a {}'.format(registro_index, output_archivo))
                        escribir_al_archivo(output_archivo, datos_del_registro)
                    else:
                        # si no hay resultados registrados de la búsqueda, no hay que escribir nada al archivo de output
                        logger.info('no encontramos datos en el registro MARC con index {}'.format(registro_index))

                # reiniciamos nuestros variables para el próximo registro
                datos_del_registro = {
                    'index': '',
                    'id': '',
                    'agrupaciones': [],
                    'campos_de_agrupaciones': [],
                    'variantes': [],
                    'campos_de_variantes': []
                }
                registro_index = row[0]
                datos_del_registro['index'] = registro_index
                continue  # no chequamos los datos de este primer row porque, como es el row 'LDR', no es relevante a la búsqueda
            else:
                if row[1] == '001':  # en el campo 001 tenemos la 'id' del sistema
                    datos_del_registro['id'] = row[4]
                else:
                    for value in row:
                        if value.lower() in agrups_lower:
                            datos_del_registro['agrupaciones'].append(value)
                            datos_del_registro['campos_de_agrupaciones'].append(row[1])
                        if value.lower() in variantes:
                            datos_del_registro['variantes'].append(value)
                            datos_del_registro['campos_de_variantes'].append(row[1])
