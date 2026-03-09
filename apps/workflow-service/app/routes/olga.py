from fastapi import APIRouter, HTTPException
from app.services.olga_client import OlgaClient
from app.models.olga import OlgaFormSchema

router = APIRouter(prefix="/api/forms/olga", tags=["Olga Forms"])


@router.get("/{form_id}", response_model=OlgaFormSchema)
async def get_olga_form(form_id: str):
    try:
        data = await OlgaClient.get_form_by_id(form_id)
        return OlgaFormSchema(**data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Olga: {str(e)}")