import os
import shutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import router as api_router
from app.core.config import settings

app = FastAPI(title="AI Chatbot Local + PDF RAG")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ia-chatbot-front-n0fam43p3-francorumiskys-projects.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include API routes
app.include_router(api_router)
