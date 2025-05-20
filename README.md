# temupaper_app

## setup environment
- create venv: python -m venv venv
- active venv: .\venv\Scripts\Activate

## setup libary
- install library: pip install -r requirements.txt

## install kamus spacy
python -m spacy download en_core_web_lg

## create component
python manage.py startunicorn papers navbar
python manage.py startunicorn app navbar

## run project
python manage.py runserver

## preparation
- generate journal
http://127.0.0.1:8000/api/import-journal
- generate institution
http://127.0.0.1:8000/api/import-institution
- generate topic for scraping
http://127.0.0.1:8000/api/import-topic
