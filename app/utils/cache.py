from pathlib import Path
import pickle

CACHE_DIR='data/cache'
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

def save_cache(name,data):
    with open(f'{CACHE_DIR}/{name}.pkl','wb') as f:
        pickle.dump(data,f)

def load_cache(name):
    path=f'{CACHE_DIR}/{name}.pkl'
    if not Path(path).exists():
        return None
    with open(path,'rb') as f:
        return pickle.load(f)
