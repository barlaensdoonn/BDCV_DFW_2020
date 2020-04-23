# extraer datos de páginas de INALI sobre clasificación geográfica de lenguas indígenas
# base URL: https://www.inali.gob.mx/clin-inali/
# creado por Brandon Aleson 4/22/20
# versión actualizado 4/22/20

import requests
from bs4 import BeautifulSoup


# esto es el URL donde se encuentra todos los vínculos de las agrupaciones lingüísticas
base_url = 'https://www.inali.gob.mx/clin-inali/'

# ver aquí más detalle sobre "verify" y certificates:
# https://stackoverflow.com/questions/28667684/python-requests-getting-sslerror
r = requests.get(base_url, verify=False)

# primero trabajamos en un ejemplo específico; luego lo generalizamos
# empezamos en esta página (l_nahuatl.html) para grabar la información de Familia Lingüística
nahuarl = 'https://www.inali.gob.mx/clin-inali/html/l_nahuatl.html'
r = requests.get(nahuarl, verify=False)
soup = BeautifulSoup(r.text, 'html.parser')
ag_lin = soup.body.h4.contents[0]    # Agrupación lingüística
fam_lin = soup.body.h4.contents[-1]  # Familia lingüística

# ya tenemos los datos que necesitamos de esta página,
# seguimos a un nivel más bajo, las agrupaciones lingüísticas
soup.find_all('a')  # para verificar si todos los vínculos están dirigidos a la misma página

# construimos el URL de una agrupación lingüística y sacamos el contenido
agrup_url = ''.join([base_url, 'html/', soup.body.a.attrs['href']])
r = requests.get(nahuarl, verify=False)
soup = BeautifulSoup(r.text, 'html.parser')
