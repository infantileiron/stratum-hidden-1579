from src.services import comparison as service
from src.utils import repository as repo
def list_items(): return service.list_comparisons()
def detail(id): return repo.get("comparisons",id)
def create(data): return service.create(data)
def recompute(id,data): return service.recompute(id,data)
def download(id): return service.download(id)
