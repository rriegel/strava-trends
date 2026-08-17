from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import activities, trends, routes, auth, users, webhooks, uploads
from config import settings

app = FastAPI(
    title="Strava Trends API",
    description="Fitness analytics and trend visualization",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(activities.router, prefix="/activities", tags=["Activities"])
app.include_router(trends.router, prefix="/trends", tags=["Trends"])
app.include_router(routes.router, prefix="/routes", tags=["Routes"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(uploads.router, prefix="/uploads", tags=["File Uploads"])

@app.get("/")
async def root():
    return {"message": "Strava Trends API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
