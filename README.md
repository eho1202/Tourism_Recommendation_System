# Recommendation System for Tourists

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

## Installing Dependencies
```
pip install -r requirements.txt
```

## Running FastAPI
Once all the dependencies are installed, run this command
```
uvicorn main:app --reload
```