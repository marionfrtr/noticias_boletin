import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

BASE_URL = "https://www.boletinconcursal.cl"
LIST_URL = BASE_URL + "/boletin/getBuscarEspecificoFiltros"

MAIL_USER = os.environ.get("MAIL_USER")
MAIL_PASS = os.environ.get("MAIL_PASS")
MAIL_TO = os.environ.get("MAIL_TO", MAIL_USER)

def get_csrf_and_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
    })
    resp_get = session.get(LIST_URL)
    resp_get.raise_for_status()

    soup = BeautifulSoup(resp_get.text, "html.parser")
    csrf_input = soup.find("input", attrs={"name": "_csrf"})
    if not csrf_input:
        raise RuntimeError("Impossible de trouver le token _csrf")
    csrf_token = csrf_input["value"]
    return session, csrf_token

from datetime import datetime, timedelta

def scrap_table():
    session, csrf_token = get_csrf_and_session()

    # Date d'hier et aujourd'hui
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    # Format "DD/MM/YYYY"
    fch_inicio = yesterday.strftime("%d/%m/%Y")
    fch_fin = today.strftime("%d/%m/%Y")

    payload = {
        "procedimiento": "",
        "notificacionTribunal": "",
        "documento": "",
        "codigoValidacion": "",
        "subCategoria": "",
        "tipoProcedimiento": "",
        "rut": "",
        "nombre": "",
        "fch_inicio": fch_inicio,
        "fch_fin": fch_fin,
        "region": "0",
        "tribunal": "0",
        "rolCausa": "",
        "g-recaptcha-response": "",
        "_csrf": csrf_token,
    }

    headers_post = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": LIST_URL,
        "Origin": BASE_URL,
    }

    resp_post = session.post(LIST_URL, data=payload, headers=headers_post)
    resp_post.raise_for_status()

    tables = pd.read_html(resp_post.text)
    if not tables:
        raise RuntimeError("Aucune table trouvée dans la réponse")
    return tables[0]

def send_email(df):
    csv_data = df.to_csv(index=False)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    msg = EmailMessage()
    msg["Subject"] = f"Boletín concursal {today}"
    msg["From"] = MAIL_USER
    msg["To"] = MAIL_TO
    msg.set_content("Voir en pièce jointe le tableau du Boletín concursal.")

    msg.add_attachment(
        csv_data.encode("utf-8"),
        maintype="text",
        subtype="csv",
        filename=f"boletin_concursal_{today}.csv",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.send_message(msg)

def main():
    df = scrap_table()
    send_email(df)

if __name__ == "__main__":
    main()
