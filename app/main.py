from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controller.manus_controller import router
from app.controller.consultation_controller import router as consultation_router
from app.db.session import create_tables
app=FastAPI(title="AI 客服助手")

@app.on_event("startup")
def startup() -> None:
  create_tables()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router,prefix="/api")
app.include_router(consultation_router, prefix="/api")
