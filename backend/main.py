from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils import init_database_tables
from routes.delete import router as delete_router
from routes.get import router as get_router
from routes.post import router as post_router
from routes.put import router as put_router


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Allow Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(delete_router)
app.include_router(get_router)
app.include_router(post_router)
app.include_router(put_router)


# Create tables if they don't exist
@app.on_event("startup")
async def startup_event():
    init_database_tables()
