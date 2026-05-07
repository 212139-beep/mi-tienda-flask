# TechStore — Proyecto de Comercio Electrónico & Sistemas Distribuidos

Tienda online funcional construida con Flask + PostgreSQL, desplegable en la nube.

## Tecnologías
- **Backend:** Python / Flask
- **ORM:** SQLAlchemy
- **Base de datos:** PostgreSQL (producción) / SQLite (local)
- **Frontend:** Jinja2 + CSS personalizado
- **Servidor WSGI:** Gunicorn
- **Despliegue:** Render.com (recomendado), GCP App Engine o AWS Elastic Beanstalk

---

## Ejecutar localmente

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar
python app.py
```

Abre http://localhost:5000

**Credenciales de admin:** admin@tienda.com / admin123

---

## Desplegar en Render.com (RECOMENDADO — gratis)

1. Sube este proyecto a GitHub
2. Ve a https://render.com y crea una cuenta
3. Crea un nuevo **Web Service** → conecta tu repositorio
4. Configura:
   - **Environment:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
5. Crea un **PostgreSQL** database en Render (gratis)
6. Copia la **Internal Database URL** y agrégala como variable de entorno:
   - `DATABASE_URL` = la URL de PostgreSQL
   - `SECRET_KEY` = cualquier texto secreto largo
7. Haz deploy → Render da una URL pública automáticamente ✅

---

## Desplegar en Google Cloud (App Engine)

1. Instala Google Cloud SDK
2. Crea proyecto en console.cloud.google.com
3. Crea archivo `app.yaml`:
```yaml
runtime: python311
entrypoint: gunicorn -b :$PORT app:app
env_variables:
  SECRET_KEY: "tu-clave-secreta"
  DATABASE_URL: "postgresql://..."
```
4. Ejecuta: `gcloud app deploy`

---

## Desplegar en AWS (Elastic Beanstalk)

1. Instala AWS CLI y EB CLI
2. Ejecuta: `eb init` → selecciona Python
3. Ejecuta: `eb create techstore-env`
4. Configura variables de entorno en la consola AWS

---

## Funcionalidades

| Funcionalidad | Ruta |
|---|---|
| Página inicio | / |
| Catálogo con filtros | /catalogo |
| Detalle de producto | /producto/<id> |
| Carrito de compras | /carrito |
| Checkout | /checkout |
| Mis pedidos | /mis-pedidos |
| Registro | /registro |
| Login / Logout | /login |
| Panel admin | /admin |
| **API REST productos** | /api/productos |
| **API REST producto** | /api/productos/<id> |

---

## Arquitectura (Sistemas Distribuidos)

```
Cliente (Browser)
       ↓ HTTP/HTTPS
   Gunicorn WSGI Server (en la nube)
       ↓
   Flask App (app.py)
       ↓
   SQLAlchemy ORM
       ↓
   PostgreSQL (servicio de base de datos en la nube)
```

El sistema implementa una arquitectura **cliente-servidor distribuida** donde:
- El cliente (browser) se comunica con el servidor mediante HTTP
- El servidor Flask procesa peticiones y consulta la base de datos
- La base de datos corre en un servicio separado (distribuido)
- La API REST permite consumo desde cualquier cliente externo
