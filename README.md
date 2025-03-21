# Recommendation System for Tourists

## Requires Python `3.11` or above to run

## Python Virtual Env
``` 
python -m venv venv

# In cmd.exe
venv\Scripts\activate.bat
# In PowerShell
venv\Scripts\Activate.ps1

# Linux or MacOS
$ source myvenv/bin/activate
```

## To install dependencies inside venv
```
# Linux or MacOS
$ python3 -m pip install -r requirements.txt

# Windows
py -m pip install -r requirements.txt
```

## Running FastAPI
Once all the dependencies are installed, run this command
```
uvicorn main:app --reload
```