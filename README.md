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

## run project
python manage.py runserver
