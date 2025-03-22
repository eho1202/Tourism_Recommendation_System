# COE70A/B Recommendation System for Tourists
Software Engineering Capstone Project for Toronto Metropolitan University 2025

## Project Setup

### Requires Python `3.11` or above to run

### Python Virtual Env
``` 
python -m venv venv

# In cmd.exe
venv\Scripts\activate.bat
# In PowerShell
venv\Scripts\Activate.ps1

# Linux or MacOS
$ source myvenv/bin/activate
```

### To install dependencies inside venv
```
# Linux or MacOS
$ python3 -m pip install -r requirements.txt

# Windows
py -m pip install -r requirements.txt
```

## Running FastAPI locally
Once all the dependencies are installed, run this command
```
uvicorn main:app --reload
```
### The API has been deployed on Render
Link to the docs: https://tourism-recommendation-system.onrender.com

## Notes
[Github Markdown Cheatsheet](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)  
[Pymongo vs. Motor](https://gist.github.com/anand2312/840aeb3e98c3d7dbb3db8b757c1a7ace)  

