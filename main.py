from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as query
from app.api.auth import router as auth
from app.config import settings

app = FastAPI(title="NLP to SQL API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth, prefix="/api", tags=["auth"])
app.include_router(query, prefix="/api", tags=["query"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )