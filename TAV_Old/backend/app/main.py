"""
TAV Engine - Main FastAPI Application Entry Point
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.api.v1.router import api_router as v1_router
from app.observability.middleware import LoggingMiddleware, MetricsMiddleware
from app.observability.logging import setup_logging
from app.observability.metrics import setup_metrics

# Setup logging first
setup_logging()

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="TAV Engine - Visual Workflow Automation Platform",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Custom Middleware (MUST be added BEFORE CORS for streaming to work)
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

# Request Size Limiter Middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """
    Enforce max content length from database settings.
    Protects server from large request attacks.
    """
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        
        # Get max size from database settings
        try:
            from app.database.session import SessionLocal
            from app.core.config.manager import SettingsManager
            
            db = SessionLocal()
            try:
                manager = SettingsManager(db)
                security_settings = manager.get_security_settings()
                max_size = security_settings.max_content_length
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to read max_content_length from DB, using default: {e}")
            max_size = 104857600  # 100MB default
        
        if content_length > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Request entity too large. Maximum size: {max_size / 1048576:.0f}MB"
            )
    
    return await call_next(request)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Important for SSE!
)

# GZip Middleware - DISABLED because it buffers SSE streams
# TODO: Implement conditional GZip that skips SSE endpoints
# app.add_middleware(GZipMiddleware, minimum_size=1000)

# Setup metrics endpoint
setup_metrics(app)

# Include API routers
app.include_router(v1_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    
    - Wipe all files on restart (fresh start)
    - Initialize database and tables
    - Create data directory if needed
    - Initialize default settings (if needed)
    - Auto-discover and register nodes
    - Initialize connections (database, cache, etc.)
    """
    logger.info("🚀 Starting TAV Engine...")
    
    # Initialize database (create tables, data directory, system user, etc.)
    try:
        from pathlib import Path
        from app.database.base import Base
        from app.database.session import engine, SessionLocal
        from app.database.models import User
        
        # Ensure data directory exists for SQLite databases
        if str(settings.DATABASE_URL).startswith("sqlite"):
            db_path = str(settings.DATABASE_URL).replace("sqlite:///", "")
            data_dir = Path(db_path).parent
            
            if not data_dir.exists():
                logger.info(f"📁 Creating data directory: {data_dir}")
                data_dir.mkdir(parents=True, exist_ok=True)
                logger.info("✅ Data directory created")
        
        # Create all database tables
        logger.info("🗄️  Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
        
        # Create default system user if not exists
        db = SessionLocal()
        try:
            existing_user = db.query(User).filter(User.user_name == "system").first()
            if not existing_user:
                logger.info("👤 Creating system user...")
                system_user = User(
                    id=1,
                    user_name="system",
                    user_email="system@tavengine.local",
                    user_password="",  # No password - not for login
                    user_firstname="System",
                    user_lastname="User"
                )
                db.add(system_user)
                db.commit()
                logger.info("✅ System user created")
            else:
                logger.info("ℹ️  System user already exists")
        except Exception as e:
            logger.warning(f"⚠️  Error creating system user: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise  # Crash if database setup fails
    
    # Check cleanup_on_startup setting and conditionally wipe files
    try:
        from app.database.session import SessionLocal
        from app.core.config.manager import SettingsManager
        from app.services.startup_cleanup import startup_cleanup
        
        db = SessionLocal()
        try:
            settings_manager = SettingsManager(db)
            storage_settings = settings_manager.get_storage_settings()
            
            if storage_settings.cleanup_on_startup:
                logger.warning("⚠️  CLEANUP_ON_STARTUP enabled - deleting all files (uploads, artifacts, temp)")
                startup_cleanup()
                logger.info("✅ Startup cleanup complete")
            else:
                logger.info("✅ Preserving user files (cleanup_on_startup=false)")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"⚠️  Could not check cleanup_on_startup setting: {e}")
        logger.info("ℹ️  Skipping startup cleanup (safe default)")
        # Continue startup even if cleanup check fails
    
    # Initialize default settings if not exists
    try:
        from app.database.session import SessionLocal
        from app.core.config.manager import init_settings_manager
        
        logger.info("⚙️  Checking application settings...")
        db = SessionLocal()
        try:
            settings_manager = init_settings_manager(db)
            logger.info("✅ Settings initialized")
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize settings: {e}")
        # Don't crash the app, settings will use defaults
    
    # Auto-discover and register all nodes
    try:
        from app.core.nodes.loader import discover_and_register_nodes
        
        logger.info("🔍 Auto-discovering nodes...")
        stats = discover_and_register_nodes()
        
        logger.info(
            f"✅ Node registry initialized: "
            f"{stats['nodes_registered']} nodes registered from "
            f"{stats['modules_scanned']} modules"
        )
        
        if stats.get("errors"):
            logger.warning(
                f"⚠️  {len(stats['errors'])} errors during node discovery"
            )
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize node registry: {e}", exc_info=True)
        # Don't crash the app, but log the error
    
    # Clean up orphaned executions from previous session
    try:
        from app.database.session import SessionLocal
        from app.core.execution.cleanup import cleanup_orphaned_executions_on_startup
        
        logger.info("🧹 Cleaning up orphaned executions from previous session...")
        db = SessionLocal()
        try:
            cleanup_orphaned_executions_on_startup(db)
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"⚠️  Failed to cleanup orphaned executions: {e}")
        # Don't crash the app, just log the warning
    
    # Initialize TriggerManager for persistent workflows
    try:
        from app.database.session import SessionLocal
        from app.core.execution.trigger_manager import TriggerManager
        from app.core.execution.orchestrator import WorkflowOrchestrator
        from app.core.execution.context import ExecutionMode
        
        logger.info("🔔 Initializing TriggerManager...")
        
        # Create execution callback (orchestrator wrapper)
        async def execution_callback(workflow_id: str, trigger_data: dict, execution_source: str) -> str:
            """Callback for triggers to spawn executions"""
            db = SessionLocal()
            try:
                orchestrator = WorkflowOrchestrator(db)
                execution_id = await orchestrator.execute_workflow(
                    workflow_id=workflow_id,
                    trigger_data=trigger_data,
                    execution_source=execution_source,
                    started_by=None,  # Triggers have no user
                    execution_mode=ExecutionMode.PARALLEL  # Triggers always use parallel mode
                )
                return execution_id
            finally:
                db.close()
        
        # Initialize TriggerManager singleton
        trigger_manager = TriggerManager(
            db_session_factory=SessionLocal,
            execution_callback=execution_callback
        )
        
        # Store in app state for dependency injection
        app.state.trigger_manager = trigger_manager
        
        logger.info("✅ TriggerManager initialized and ready")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize TriggerManager: {e}", exc_info=True)
        # Don't crash the app, but triggers won't work
        app.state.trigger_manager = None
    
    logger.info("✅ TAV Engine startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("🛑 Shutting down TAV Engine...")
    
    # Gracefully shutdown TriggerManager (stop all active triggers)
    try:
        if hasattr(app.state, 'trigger_manager') and app.state.trigger_manager:
            logger.info("🔔 Shutting down TriggerManager...")
            await app.state.trigger_manager.shutdown()
            logger.info("✅ TriggerManager shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error during TriggerManager shutdown: {e}", exc_info=True)
    
    logger.info("✅ TAV Engine shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs" if settings.ENVIRONMENT != "production" else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )

