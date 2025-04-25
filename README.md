# COE70A/B Recommendation System for Tourists
Software Engineering Capstone Project for Toronto Metropolitan University 2025

## Project Setup

### Requires Python `3.11` to run

### Python Virtual Env
``` 
python -m venv venv

# In cmd.exe
venv\Scripts\activate.bat
# In PowerShell
venv\Scripts\Activate.ps1
# In Git Bash
source venv/Scripts/activate

# Linux or MacOS
$ source venv/bin/activate
```

### To install dependencies inside venv
```
# Linux or MacOS
$ python3 -m pip install -r requirements.txt

# Windows
py -m pip install -r requirements.txt
```

### There may be problems with installing lightfm, to fix the problems:
```
# Run this command
$ pip install --upgrade pip setuptools wheel
```

## Running the API locally
Once all the dependencies are installed, run this command:
```
cp .env.dev .env
```
Go inside `.env` and fill in the credentials for each environment variable, then run this command:

```
uvicorn main:app --reload
```
You have sucessfully ran the API locally for development!
### The API has been deployed on Render
Link to the docs: https://tourism-recommendation-system.onrender.com/docs

## Notes
[Github Markdown Cheatsheet](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)  
[Pymongo vs. Motor](https://gist.github.com/anand2312/840aeb3e98c3d7dbb3db8b757c1a7ace)  

