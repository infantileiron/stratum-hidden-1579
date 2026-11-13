from fastapi import APIRouter,Depends
from fastapi.responses import Response
from src.controllers import comparison as controller
from src.schemas.entities import ComparisonInput,RemapInput
from src.services.auth import current,editor
router=APIRouter(prefix="/comparisons",tags=["comparisons"])
@router.get("")
def list_items(user=Depends(current)): return controller.list_items()
@router.post("",status_code=201)
def create(data:ComparisonInput,user=Depends(editor)): return controller.create(data)
@router.get("/{id}")
def detail(id:str,user=Depends(current)): return controller.detail(id)
@router.post("/{id}/recompute",status_code=201)
def recompute(id:str,data:RemapInput,user=Depends(editor)): return controller.recompute(id,data)
@router.get("/{id}/download")
def download(id:str,user=Depends(current)):
    return Response(controller.download(id),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":f'attachment; filename="{id}.csv"'})
