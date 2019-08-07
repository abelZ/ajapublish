import platform

def Settings( **kwargs ):
    if platform.system() == 'Darwin':
        return {
                'interpreter_path': 'venv/bin/python3'
                }
    elif platform.system() == 'Windows':
        return {
                'interpreter_path': 'venv/Scripts/python.exe'
                }

