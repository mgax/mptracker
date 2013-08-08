web: chaussette --backend waitress manage.app `if [ "$USE_RELOADER" ]; then echo "--use-reloader"; fi` --port $PORT
redis: redis-server --port $PORT
worker: ./manage.py worker
