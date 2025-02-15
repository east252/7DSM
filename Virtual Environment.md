# Virtual Environment
This file is to help us easily track, in and out, of virtual environments in python.

## Python Environment:
python -m venv env
v.environment = venv
in path: .\env\Scripts\activate

Once activated, requirements.txt: pip install -r requirements.txt

Save requirements: pip freeze > requirements.txt

## New Environment:
git clone <repository-url>
cd <repository-directory>
python -m venv env
.\env\Scripts\activate  # For Windows
# source env/bin/activate  # For macOS and Linux
pip install -r requirements.txt
