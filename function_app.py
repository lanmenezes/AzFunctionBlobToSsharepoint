import logging
import os
import zipfile

import azure.functions as func
import requests
from azure.identity import ClientSecretCredential

app = func.FunctionApp()

def get_access_token():
    tenant_id = os.environ['TENANT_ID']
    client_id = os.environ['CLIENT_ID']
    client_secret = os.environ['CLIENT_SECRET']
    
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    token = credential.get_token("https://graph.microsoft.com/.default")
    
    if token is None:
        logging.info("sem acess token")
    else:
        logging.info(token)

    return token.token


@app.blob_trigger(arg_name="myblob", path="send-to-sharepoint",
                               connection="functionsstorage_STORAGE") 
def blob_trigger_function(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")
    
    
    site_id = os.environ['SITE_ID']
    doc_library = os.environ['DOCUMENT_LIBRARY']

    file_content = myblob.read()

    access_token = get_access_token()

    
    if not access_token:
        logging.error("Não foi possível obter o access token. Encerrando a função.")
        return

    original_filename = os.path.basename(myblob.name)
    zip_filename = f"{original_filename}.zip"

    tmp_file_path = f"/tmp/{original_filename}"
    zip_file_path = f"/tmp/{zip_filename}"

    try:
        # Salva o arquivo recebido no `/tmp/`
        with open(tmp_file_path, "wb") as tmp_file:
            tmp_file.write(file_content)

        logging.info(f"Arquivo salvo temporariamente em {tmp_file_path}")

        # Compacta o arquivo em um ZIP
        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(tmp_file_path, original_filename)

        logging.info(f"Arquivo compactado e salvo em {zip_file_path}")

        # Enviar para o Sharepoint
        upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{doc_library}/root:/{zip_filename}:/content"

        
        headers = {
            "Authorization": f"Bearer {access_token}",        
            "Content-Type": "application/octet-stream"  
            }
            
        # Enviando o arquivo para o SharePoint
        with open(zip_file_path, "rb") as zip_file:
            response = requests.put(upload_url, headers=headers, data=zip_file)  
        
       
        # # Verificando o resultado
        if response.status_code in [200, 201]:
            logging.info(f"Arquivo {zip_filename} {response.status_code} enviado com sucesso para o SharePoint!")
        else:
            logging.error(f"Falha ao enviar arquivo: {response.status_code} - {response.text}")

    except Exception as e:
        logging.error(f"Erro durante o processamento: {e}")

    finally:

        # Limpeza: Remove os arquivos temporários 
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            logging.info(f"Arquivo temporário removido: {tmp_file_path}")

        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
            logging.info(f"Arquivo ZIP removido: {zip_file_path}")

