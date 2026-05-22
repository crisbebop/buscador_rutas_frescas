# Instrucciones  
1. Clonar repo
```git clone```
2. Instalar Poetry  
```poetry install```
3. Configurar GEE  
Debes tener una cuenta de Google Earth Engine y crear un proyecto, luego en  
```config/gee/```  
Crear el archivo gee.yaml que contiene el id del proyecto en Google Earth Engine
```config/gee/gee_id.yaml```  
Usa el archivo de ejemplo para crear ```gee_id.yaml```  
4. Autenticarse en Google Drive  
En la carpeta ```secrets``` deben descargarse los credenciales y token para autenticarse con Google Drive  
```secrets/google_oauth_credentials.jason```  
```secrets/google_oauth_token.json```
