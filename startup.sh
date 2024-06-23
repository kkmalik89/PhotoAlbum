# gunicorn -w 1 -k uvicorn.workers.UvicornWorker app:app
# python -m uvicorn app:app --host 0.0.0.0
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app:app