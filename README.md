# 📄 Documentação da Azure Function  

## 📌 Visão Geral  

Esta **Azure Function** foi desenvolvida em **Python 3.10** usando o modelo **Azure Functions V2**.  
Ela é acionada automaticamente quando um arquivo é criado no diretório **`send-to-sharepoint`** dentro da **Storage Account** do Azure.  

A função realiza as seguintes etapas:  

1. **Recebe o arquivo** da Storage Account.  
2. **Compacta** o arquivo em formato ZIP.  
3. **Envia o arquivo compactado** para uma biblioteca de documentos no SharePoint usando a API Microsoft Graph.  
4. **Remove** os arquivos temporários utilizados no processo.  

## Pré-requisitos

Antes de implantar e executar esta função, certifique-se de que possui os seguintes pré-requisitos:

- **Azure Subscription** – Necessário para utilizar Azure Functions e Storage Account.
- **Permissões de Administrador Global no Tenant do Azure** – Para configurar autenticação e permissões.
- **App Registration** – O aplicativo precisa estar registrado no **Azure AD** para gerar tokens de acesso ao Microsoft Graph.
- **SharePoint Online** – Um site do SharePoint Online deve estar configurado para armazenar os arquivos.



---

## 📂 Estrutura do Código  

### 1️⃣ **Dependências**  
O código utiliza as seguintes bibliotecas:  

- `azure.functions`: Para configurar e disparar a função.  
- `azure.identity`: Para autenticação no Microsoft Graph.  
- `requests`: Para fazer requisições HTTP ao SharePoint.  
- `zipfile`: Para compactação do arquivo.  
- `os`: Para manipulação de arquivos e variáveis de ambiente.  
- `logging`: Para registrar logs de execução.  

---

### 2️⃣ **Autenticação no Microsoft Graph**  
A função **`get_access_token()`** autentica no Microsoft Graph utilizando as credenciais do aplicativo registradas no Azure AD:  

- **`TENANT_ID`** (ID do diretório do Azure AD)  
- **`CLIENT_ID`** (ID do aplicativo registrado)  
- **`CLIENT_SECRET`** (Segredo do cliente para autenticação)  

O token gerado é utilizado para autorização ao enviar o arquivo para o SharePoint.  

```python
def get_access_token():
    tenant_id = os.environ['TENANT_ID']
    client_id = os.environ['CLIENT_ID']
    client_secret = os.environ['CLIENT_SECRET']
    
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    token = credential.get_token("https://graph.microsoft.com/.default")
    
    return token.token
```

---

### 3️⃣ **Gatilho da Função**  
A função é acionada automaticamente sempre que um novo arquivo é criado no diretório **`send-to-sharepoint`** na Storage Account.  

```python
@app.blob_trigger(arg_name="myblob", path="send-to-sharepoint",
                               connection="functionsstorage_STORAGE") 
def blob_trigger_function(myblob: func.InputStream):
```

---

### 4️⃣ **Processamento do Arquivo**  
A função lê o conteúdo do arquivo recebido e obtém seu nome original:  

```python
file_content = myblob.read()
original_filename = os.path.basename(myblob.name)
```

Em seguida, gera os caminhos temporários para armazenar o arquivo original e o ZIP:  

```python
tmp_file_path = f"/tmp/{original_filename}"
zip_file_path = f"/tmp/{original_filename}.zip"
```

O arquivo é salvo temporariamente no diretório `/tmp/`:  

```python
with open(tmp_file_path, "wb") as tmp_file:
    tmp_file.write(file_content)
```

---

### 5️⃣ **Compactação do Arquivo**  
O arquivo salvo é compactado utilizando `zipfile.ZipFile`:  

```python
with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(tmp_file_path, original_filename)
```

---

### 6️⃣ **Envio para o SharePoint**  
O arquivo ZIP é enviado para a biblioteca de documentos do SharePoint usando a API Microsoft Graph:  

- **`SITE_ID`** → Identificação do site no SharePoint.  
- **`DOCUMENT_LIBRARY`** → ID da biblioteca de documentos onde o arquivo será armazenado.  

A URL de upload é montada conforme a API do Microsoft Graph:  

```python
upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{doc_library}/root:/{zip_filename}:/content"
```

A requisição HTTP **PUT** é feita para enviar o arquivo:  

```python
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/octet-stream"
}

with open(zip_file_path, "rb") as zip_file:
    response = requests.put(upload_url, headers=headers, data=zip_file)
```

Se a resposta for **200** ou **201**, significa que o envio foi bem-sucedido. Caso contrário, um erro é registrado.  

---

### 7️⃣ **Remoção de Arquivos Temporários**  
Após o processamento, os arquivos temporários são excluídos para liberar espaço:  

```python
if os.path.exists(tmp_file_path):
    os.remove(tmp_file_path)

if os.path.exists(zip_file_path):
    os.remove(zip_file_path)
```

---

## 🔧 **Variáveis de Ambiente Necessárias**  

O arquivo **local.settings.json** deve conter as seguintes variáveis de ambiente:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "functionsstorage_STORAGE": "DefaultEndpointsProtocol=https;AccountName=functionsstorage;AccountKey= ## your key ##;EndpointSuffix=core.windows.net",
    "TENANT_ID": "your tenant id here",
    "CLIENT_ID": "your client id app here",
    "CLIENT_SECRET": "your client app secret here",
    "SITE_ID": "your site id here",
    "DOCUMENT_LIBRARY": "document library id here",
    "AUTHORITY_URL": "https://login.microsoftonline.com/your domain here",
    "SCOPE": "https://graph.microsoft.com/.default"
  }
}
```

| Variável          | Descrição |
|------------------|-----------|
| `AzureWebJobsStorage` | Conexão da Storage Account usada pelo Azure Functions |
| `FUNCTIONS_WORKER_RUNTIME` | Define que a função rodará em Python |
| `functionsstorage_STORAGE` | Conexão com a Storage Account onde os arquivos serão monitorados |
| `TENANT_ID` | ID do diretório do Azure AD |
| `CLIENT_ID` | ID do aplicativo no Azure AD |
| `CLIENT_SECRET` | Segredo do aplicativo para autenticação |
| `SITE_ID` | ID do site SharePoint onde os arquivos serão armazenados |
| `DOCUMENT_LIBRARY` | ID da biblioteca de documentos no SharePoint |
| `AUTHORITY_URL` | URL de autenticação do Azure AD |
| `SCOPE` | Escopo para acesso à API do Microsoft Graph |

---

## 📊 **Fluxo de Execução**  

1. O arquivo é criado no diretório **`send-to-sharepoint`** na Storage Account.  
2. A Azure Function é acionada automaticamente.  
3. A função obtém um **Access Token** no Microsoft Graph.  
4. O arquivo é **salvo temporariamente** no diretório `/tmp/`.  
5. O arquivo é **compactado** em um ZIP.  
6. O arquivo ZIP é **enviado** para o SharePoint.  
7. Após o envio, os arquivos temporários são **excluídos**.  

## Referências

Para mais informações sobre as tecnologias utilizadas, consulte os links abaixo:

- [Azure Functions - Blob Trigger](https://learn.microsoft.com/en-us/azure/azure-functions/functions-event-grid-blob-trigger?pivots=programming-language-python)
- [Azure AD - Registro de Aplicativo](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app?tabs=certificate)
- [SharePoint Online - Uso com Microsoft Graph](https://learn.microsoft.com/pt-br/sharepoint/dev/sp-add-ins-modernize/understanding-rsc-for-msgraph-and-sharepoint-online)


## 📌 **Conclusão**  
Esta **Azure Function** automatiza o processo de **compressão e envio** de arquivos para o SharePoint de forma eficiente, garantindo que os arquivos sejam armazenados corretamente e que os recursos temporários sejam liberados após o uso. 🚀
