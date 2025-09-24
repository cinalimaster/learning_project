Creating a new Django project to develop in a Docker container with PostgreSQL using Visual Studio Code (VSCode) is a great setup for a scalable and isolated development environment. Below is a step-by-step guide to set this up correctly, ensuring Django, Docker, and PostgreSQL work seamlessly. I'll assume you're starting from scratch and using Python 3.12, as mentioned previously.

---

### Prerequisites
- **Docker**: Install Docker Desktop (or Docker CLI for Linux) and ensure it's running.
- **VSCode**: Install Visual Studio Code with the following extensions:
  - **Docker** (by Microsoft): For managing containers.
  - **Python** (by Microsoft): For Python support, including linting and debugging.
  - **Dev Containers** (by Microsoft): For developing inside a container (optional but recommended).
- **Basic Knowledge**: Familiarity with terminal commands and basic Django concepts.

---

### Step 1: Set Up Your Project Directory
1. **Create a Project Directory**:
   - Open a terminal and create a new directory for your project:
     ```bash
     mkdir my_django_project
     cd my_django_project
     ```

2. **Initialize a Git Repository** (Optional but recommended):
   ```bash
   git init
   echo "__pycache__/\n*.pyc\n.env\n" > .gitignore
   ```

3. **Open the Project in VSCode**:
   ```bash
   code .
   ```

---

### Step 2: Create the Django Project Structure
To avoid installing Django locally, we’ll create the Django project inside the Docker container later. For now, create the necessary configuration files.

1. **Create a `requirements.txt` File**:
   - In VSCode, create a file named `requirements.txt` in the project root:
     ```
     django>=4.2,<5.0
     psycopg2-binary>=2.9.9  # PostgreSQL adapter for Django
     ```
     - `psycopg2-binary` is used to connect Django to PostgreSQL.

2. **Create a `Dockerfile`**:
   - Create a file named `Dockerfile` in the project root:
     ```dockerfile
     # Use official Python 3.12 image
     FROM python:3.12-slim

     # Set working directory
     WORKDIR /app

     # Copy requirements file
     COPY requirements.txt .

     # Install dependencies
     RUN pip install --no-cache-dir -r requirements.txt

     # Copy project files
     COPY . .

     # Ensure permissions
     RUN chmod -R 755 /app

     # Expose port 8000 for Django
     EXPOSE 8000

     # Command to run Django development server
     CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
     ```
     - This sets up a lightweight Python 3.12 image, installs dependencies, and runs the Django server.

3. **Create a `docker-compose.yml` File**:
   - Create a file named `docker-compose.yml` in the project root to define the Django and PostgreSQL services:
     ```yaml
     version: '3.8'
     services:
       web:
         build:
           context: .
           dockerfile: Dockerfile
         command: python manage.py runserver 0.0.0.0:8000
         volumes:
           - .:/app
         ports:
           - "8000:8000"
         environment:
           - PYTHONPATH=/app
           - DJANGO_SETTINGS_MODULE=myproject.settings
           - POSTGRES_DB=${POSTGRES_DB}
           - POSTGRES_USER=${DB_USER}
           - POSTGRES_PASSWORD=${DB_PASSWORD}
           - POSTGRES_HOST=${DB_HOST}
           - POSTGRES_PORT=${DB_PORT}
         depends_on:
           - db
       db:
         image: postgres:15
         volumes:
           - postgres_data:/var/lib/postgresql/data
         environment:
           - POSTGRES_DB=${POSTGRES_DB}
           - POSTGRES_USER=${POSTGRES_USER}
           - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
     volumes:
       postgres_data:
     ```
     - **web**: The Django service, built from the `Dockerfile`.
     - **db**: The PostgreSQL service using the official `postgres:15` image.
     - **volumes**: Persists PostgreSQL data across container restarts.
     - **environment**: Sets database credentials and Django settings module (we’ll update `myproject` later).

4. **Create a `.env` File** (Optional for security):
   - To avoid hardcoding sensitive data, create a `.env` file:
     ```
     POSTGRES_DB=myproject
     POSTGRES_USER=myuser
     POSTGRES_PASSWORD=mypassword
     ```
   - Update `docker-compose.yml` to use `.env` variables:
     ```yaml
     version: '3.8'
     services:
       web:
         build:
           context: .
           dockerfile: Dockerfile
         command: python manage.py runserver 0.0.0.0:8000
         volumes:
           - .:/app
         ports:
           - "8000:8000"
         environment:
           - PYTHONPATH=/app
           - DJANGO_SETTINGS_MODULE=myproject.settings
           - POSTGRES_DB=${POSTGRES_DB}
           - POSTGRES_USER=${POSTGRES_USER}
           - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
           - POSTGRES_HOST=db
           - POSTGRES_PORT=5432
         depends_on:
           - db
       db:
         image: postgres:15
         volumes:
           - postgres_data:/var/lib/postgresql/data
         env_file:
           - .env
     volumes:
       postgres_data:
     ```

---

### Step 3: Create the Django Project Inside the Container
Since we want to develop inside the container, we’ll create the Django project using Docker.

1. **Build and Start the Containers**:
   - Run the following to build the Docker images and start the services:
     ```bash
     docker-compose build
     docker-compose up -d
     ```
     - The `-d` flag runs containers in detached mode.

2. **Access the Container Shell**:
   - Open a shell inside the `web` container:
     ```bash
     docker-compose exec web bash
     ```

3. **Create the Django Project**:
   - Inside the container shell, create the Django project:
     ```bash
     django-admin startproject myproject .
     ```
     - This creates a Django project named `myproject` in the `/app` directory (mapped to your local project directory via volumes).
     - The project structure will include `manage.py` and a `myproject` directory with `settings.py`, `urls.py`, etc.

4. **Verify the Project**:
   - Exit the container shell (`exit`) and check your local project directory in VSCode. You should see:
     ```
     my_django_project/
     ├── .env
     ├── .gitignore
     ├── docker-compose.yml
     ├── Dockerfile
     ├── requirements.txt
     ├── manage.py
     ├── myproject/
     │   ├── __init__.py
     │   ├── settings.py
     │   ├── urls.py
     │   ├── asgi.py
     │   ├── wsgi.py
     ```

---

### Step 4: Configure Django for PostgreSQL
1. **Update `settings.py`**:
   - Open `myproject/settings.py` in VSCode and modify the `DATABASES` section to use PostgreSQL:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.postgresql',
             'NAME': 'myproject',
             'USER': 'myuser',
             'PASSWORD': 'mypassword',
             'HOST': 'db',  # Matches the service name in docker-compose.yml
             'PORT': '5432',
         }
     }
     ```
   - If using a `.env` file, you can make it dynamic using environment variables:
     ```python
     import os

     DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT'),
            }
        }
     ```

2. **Run Migrations**:
   - Access the container shell again:
     ```bash
     docker-compose exec web bash
     ```
   - Apply Django migrations to set up the database:
     ```bash
     python manage.py makemigrations
     python manage.py migrate
     ```

3. **Test the Django Server**:
   - If not already running, ensure the containers are up:
     ```bash
     docker-compose up -d
     ```
   - Open a browser and navigate to `http://localhost:8000`. You should see the Django welcome page.

---

### Step 5: Set Up VSCode for Development
1. **Install VSCode Extensions**:
   - Ensure the **Python**, **Docker**, and **Dev Containers** extensions are installed.
   - Optional: Install **PostgreSQL** (by Chris Kolkman) for database exploration.

2. **Configure Python Interpreter**:
   - Open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on Mac) and select **Python: Select Interpreter**.
   - Choose the Python interpreter from the Docker container (VSCode should detect it if the Dev Containers extension is installed). Alternatively, select the local Python 3.12 if you’re running commands locally.

3. **Use Dev Containers (Optional)**:
   - To develop directly inside the container, create a `.devcontainer/devcontainer.json` file:
     ```json
     {
       "name": "Django with PostgreSQL",
       "dockerComposeFile": "docker-compose.yml",
       "service": "web",
       "workspaceFolder": "/app",
       "extensions": [
         "ms-python.python",
         "ms-vscode-remote.remote-containers",
         "ms-azuretools.vscode-docker"
       ],
       "settings": {
         "python.pythonPath": "/usr/local/bin/python",
         "python.linting.enabled": true,
         "python.linting.pylintEnabled": true
       }
     }
     ```
   - Open the Command Palette and select **Dev Containers: Reopen in Container**. VSCode will restart inside the `web` container, with all dependencies pre-installed.

4. **Debugging in VSCode**:
   - Create a `launch.json` for debugging:
     - Go to the **Run and Debug** tab in VSCode, click **create a launch.json file**, and select **Python**.
     - Add this configuration:
       ```json
       {
         "version": "0.2.0",
         "configurations": [
           {
             "name": "Django",
             "type": "python",
             "request": "launch",
             "program": "${workspaceFolder}/manage.py",
             "args": ["runserver", "0.0.0.0:8000"],
             "django": true,
             "justMyCode": false
           }
         ]
       }
       ```
   - This allows you to set breakpoints and debug the Django app.

---

### Step 6: Test the Setup
1. **Check PostgreSQL**:
   - Access the PostgreSQL container:
     ```bash
     docker-compose exec db psql -U myuser -d myproject
     ```
   - List tables to confirm Django migrations:
     ```sql
     \dt
     ```

2. **Create a Django App** (Optional):
   - Inside the `web` container shell:
     ```bash
     python manage.py startapp myapp
     ```
   - Add `myapp` to `INSTALLED_APPS` in `myproject/settings.py`:
     ```python
     INSTALLED_APPS = [
         ...
         'myapp',
     ]
     ```

3. **Verify Everything**:
   - Ensure containers are running: `docker-compose up -d`.
   - Visit `http://localhost:8000` in your browser.
   - Stop containers when done: `docker-compose down`.

---

### Step 7: Best Practices
- **Version Control**: Commit your changes to Git regularly.
- **Environment Variables**: Use `.env` files for sensitive data (e.g., database credentials).
- **Docker Volumes**: The `postgres_data` volume persists database data. To reset, run:
  ```bash
  docker-compose down -v
  ```
- **Code Linting**: Install `pylint` or `flake8` in `requirements.txt` for code quality:
  ```
  pylint
  flake8
  ```
- **Backup Database**: Periodically back up your PostgreSQL data:
  ```bash
  docker-compose exec db pg_dump -U myuser myproject > backup.sql
  ```

---

### Troubleshooting Tips
- **Django ImportError**: Ensure `django` and `psycopg2-binary` are in `requirements.txt` and installed (`docker-compose build --no-cache`).
- **Database Connection Issues**: Verify `POSTGRES_HOST=db` matches the service name in `docker-compose.yml`.
- **Port Conflicts**: If port 8000 is in use, change the `ports` mapping in `docker-compose.yml` (e.g., `8001:8000`).
- **VSCode Issues**: If the Python interpreter isn’t detected, restart VSCode or reinstall the Python extension.

---

### Final Project Structure
```
my_django_project/
├── .devcontainer/
│   ├── devcontainer.json
├── .env
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── manage.py
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
├── myapp/ (optional)
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── ...
```

---

### Next Steps
- Create Django models and views in `myapp` to build your application.
- Add more dependencies (e.g., `djangorestframework` for APIs) to `requirements.txt`.
- Explore Django admin by creating a superuser:
  ```bash
  docker-compose exec web python manage.py createsuperuser
  ```

## Quickstart (Local)

1) Create venv and install deps

```
python3 -m venv .venv --without-pip
. .venv/bin/activate
curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
pip install -U pip
pip install -r requirements.txt
```

2) Run DB migrations and start server (SQLite by default)

```
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

3) Open `http://localhost:8000` and use the floating chat widget.

API endpoints:
- POST `http://localhost:8000/api/ask/` with JSON `{ "question": "..." }`
- POST `http://localhost:8000/api/upload/` form-data file `file`
- GET  `http://localhost:8000/api/documents/<id>/status/`

Notes:
- Settings auto-fallback to SQLite if `DB_*` env vars are not set.
- FAISS index and documents are loaded from `documents/`.
- Tests: `pytest` (configured via `pytest-django`).

## Docker Compose

Docker setup includes Postgres, Redis, Ollama, Django web, and Celery worker. Ensure `.env` has DB credentials and `OLLAMA_MODEL_NAME`.

```
docker compose up --build -d
```

## Known Changes/Fixes

- Added DRF and API endpoints, SQLite fallback, caching, and pytest-django.
- Implemented `ChatInteraction` model and migrations.
- Added `advanced_splitter.py`, `services.py`, optional spaCy usage, and robust NLTK download handling.
- Fixed typos and imports (`rete_limiter`, Celery config, hybrid/entity retrievers).
- Adjusted FAISS and NumPy versions compatible with Python 3.13.
- Tests now pass: `5 passed`.