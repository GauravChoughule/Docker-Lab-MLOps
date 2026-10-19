# Docker Lab 1 – Train and Serve an ML Model with Docker

The original lab built one Docker image that trained an Iris model inside a container and exited. The trained model stayed trapped inside the container and couldn't be used.

This version turns it into a small, realistic Docker setup:

1. A **multi-stage Dockerfile** that builds a smaller, more secure image
2. **Training settings passed in at runtime** with environment variables, so one image can train different models without rebuilding
3. **Docker Compose** running two containers from the same image: a `trainer` that trains and saves the model, and an `api` that serves it, connected by a shared **volume**
4. A **health check** so Docker knows when the API is actually ready

The model predicts whether a breast tumor is malignant or benign (scikit-learn's Breast Cancer Wisconsin dataset, 569 samples, 30 features).

---

## 1. What you need to install

You only need Docker and Git. Python does **not** need to be installed on your machine; it runs inside the containers.

| Tool | Version | Download |
|---|---|---|
| Docker Desktop (Windows/Mac) or Docker Engine (Linux) | 4.x or newer (Docker Engine 24+) | https://www.docker.com/products/docker-desktop/ |
| Docker Compose | v2 (included with Docker Desktop) | included |
| Git | any recent version | https://git-scm.com/downloads |

Windows users: Docker Desktop will ask to enable WSL 2 during setup. Accept it and restart if asked.

Check everything is installed (open a terminal, e.g. PowerShell or Terminal):

```bash
docker --version          # e.g. Docker version 27.x
docker compose version    # must say v2.x
git --version
```

**Make sure Docker Desktop is open and running** before continuing. The whale icon should be in your taskbar/menu bar.

---

## 2. Get the code

```bash
git clone https://github.com/GauravChoughule/MLOps.git
cd MLOps/Labs/Docker_Labs/Lab1
```

All commands below are run from this `Lab1` folder.

### Project structure
```
Lab1
├── dockerfile            # multi-stage image definition
├── docker-compose.yml    # runs trainer + api together
├── .dockerignore         # files kept out of the image
├── ReadMe.md
└── src
    ├── train.py          # trains the model (settings from env variables)
    ├── app.py            # FastAPI service that serves the model
    └── requirements.txt  # pinned Python packages
```

---

## 3. Run it with Docker Compose (main way)

```bash
docker compose up --build
```

The first run takes a few minutes while Docker downloads the Python base image and installs the packages. Later runs are much faster because of layer caching.

### What a successful run looks like

The `trainer` container trains, prints its results, and exits with code 0:

```
trainer-1  | Config: MODEL_TYPE=logreg, TEST_SIZE=0.2, RANDOM_STATE=42
trainer-1  | Test accuracy: 0.982
trainer-1  | ...classification report...
trainer-1  | The model training was successful. Saved to model/model.pkl
trainer-1 exited with code 0
```

Only then does the `api` container start:

```
api-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test the API

Open http://localhost:8000/docs in a browser. This page lists all endpoints and lets you try them.

- **GET /health** → `{"status": "healthy"}`
- **GET /model-info** → which model was trained, its accuracy, and when
- **POST /predict** → click "Try it out" and paste this sample (the first tumor in the dataset, which is malignant):

```json
{
  "features": [17.99, 10.38, 122.8, 1001.0, 0.1184, 0.2776, 0.3001, 0.1471, 0.2419, 0.0787,
               1.095, 0.9053, 8.589, 153.4, 0.0064, 0.049, 0.0537, 0.0159, 0.03, 0.0062,
               25.38, 17.33, 184.6, 2019.0, 0.1622, 0.6656, 0.7119, 0.2654, 0.4601, 0.1189]
}
```

Expected response: `{"prediction": "malignant", "confidence": 1.0}` (confidence may vary slightly).

Sending fewer or more than 30 numbers returns a **422** validation error.

You can also check the container health status in a second terminal:

```bash
docker compose ps
```
The `api` service should show `(healthy)` after about 10 seconds.

### Stop everything

Press `Ctrl+C`, then:

```bash
docker compose down        # stops and removes containers (keeps the trained model)
docker compose down -v     # also deletes the model volume
```

---

## 4. Train a different model without rebuilding

Training settings are environment variables, so you can change them at runtime.

**Mac/Linux:**
```bash
MODEL_TYPE=random_forest docker compose up
```

**Windows PowerShell:**
```powershell
$env:MODEL_TYPE="random_forest"; docker compose up
Remove-Item Env:MODEL_TYPE    # reset afterwards
```

| Variable | Options | Default |
|---|---|---|
| `MODEL_TYPE` | `logreg` (scaled Logistic Regression) or `random_forest` | `logreg` |
| `TEST_SIZE` | 0.05 – 0.5 | 0.2 |

The trainer prints `MODEL_TYPE=random_forest` and an accuracy around 0.956, and `/model-info` now shows the new model.

**Invalid settings fail safely.** Try `MODEL_TYPE=abc`. The trainer prints an error and exits with code 1, and the API **does not start**, because it only starts after training succeeds. This stops a broken model from being served.

---

## 5. Run without Compose (original lab commands)

The image still works the same way as the original lab:

```bash
docker build -t lab1:v2 .
docker run lab1:v2
```

Train a different model with `-e`:
```bash
docker run -e MODEL_TYPE=random_forest lab1:v2
```

Keep the trained model on your machine using a bind mount:
```bash
docker run -v "$(pwd)/model:/app/model" lab1:v2        # Mac/Linux
docker run -v "${PWD}/model:/app/model" lab1:v2        # Windows PowerShell
```
`model.pkl` and `metrics.json` appear in a local `model/` folder.

Save the image to a file:
```bash
docker save lab1:v2 > my_image.tar
```

---

## 6. Changes made to the original lab

| Area | Original lab | This version | Why it matters |
|---|---|---|---|
| Dockerfile | Single stage, full `python:3.10` image | **Multi-stage**: packages installed in a `builder` stage, only the result copied into a clean `python:3.10-slim` runtime | Much smaller image; no pip cache or build leftovers |
| Layer caching | Copies all code, then installs packages | Copies `requirements.txt` first, installs, then copies code | Changing code no longer reinstalls every package, so rebuilds take seconds |
| Security | Runs as root | Runs as a normal user (`appuser`) | If the container is compromised, the attacker doesn't have root |
| Configuration | Hardcoded in the script | `MODEL_TYPE`, `TEST_SIZE`, `RANDOM_STATE` env variables, validated on startup | One image, many experiments, no rebuild |
| Model output | Saved inside the container and lost | Saved to a **Docker volume** shared with the API | The model outlives the container that trained it |
| Containers | One container that trains and exits | **Docker Compose** with `trainer` + `api` from the same image | Mirrors a real train-then-serve workflow |
| Startup order | n/a | `api` waits for `trainer` to finish successfully | A failed training run never gets served |
| Health check | None | `api` health check calls `/health` every 10s | Docker reports whether the service is actually working, not just running |
| Volume access | n/a | API mounts the model volume **read-only** | The serving container can't change the model |
| Build context | Everything copied | `.dockerignore` excludes Git files, caches, models | Faster builds, nothing unneeded in the image |
| Dependencies | Unpinned | Exact versions pinned | Same build result every time |
| Model / data | Random Forest on Iris | Logistic Regression (or Random Forest) on Breast Cancer Wisconsin, with accuracy report and saved metrics | Shows results, and metrics travel with the model |

### Compare image sizes yourself
```bash
docker images lab1
```
You can build the original single-stage version and compare its size with `lab1:v2`.

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot connect to the Docker daemon` / `pipe not found` | Docker Desktop isn't running. Open it and wait until it says it's running. |
| `port is already allocated` | Something else is using port 8000. Stop it, or change `"8000:8000"` to `"8001:8000"` in `docker-compose.yml` and use http://localhost:8001/docs. |
| API never starts | Check the trainer logs: `docker compose logs trainer`. It probably exited with an error. |
| `/predict` returns 503 | The model volume is empty. Run `docker compose down -v`, then `docker compose up --build`. |
