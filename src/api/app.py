"""
iqromax.uz OTP Bot - FastAPI Application
Main application setup with middleware and error handlers
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config import settings
from src.models import init_db, redis_client
from src.utils import setup_logging, get_client_ip
from src.api.routes import router as api_router
from src.api.admin_routes import admin_router
from src.bot import telegram_bot


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting application...")
    
    # Setup logging
    setup_logging()
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Connect to Redis
    logger.info("Connecting to Redis...")
    await redis_client.connect()
    
    # Initialize bot only in webhook mode (in polling mode main.py initializes it)
    if settings.TELEGRAM_WEBHOOK_URL:
        logger.info("Initializing Telegram bot (webhook mode)...")
        await telegram_bot.initialize()
    else:
        logger.info("Bot will be initialized by main process (polling mode)")
    
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop bot only in webhook mode (in polling mode main.py stops it)
    if settings.TELEGRAM_WEBHOOK_URL:
        await telegram_bot.stop()
    
    # Disconnect Redis
    await redis_client.disconnect()
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## iqromax.uz OTP Verification Bot API
    
    Bu API iqromax.uz web saytida foydalanuvchi ro'yxatdan o'tishini 
    Telegram orqali tasdiqlash uchun ishlatiladi.
    
    ### Asosiy funksiyalar:
    - OTP yuborish (`/send-otp`)
    - OTP tasdiqlash (`/verify-otp`)
    - OTP qayta yuborish (`/resend-otp`)
    - OTP holatini tekshirish (`/otp-status`)
    
    ### Xavfsizlik:
    - API kaliti orqali autentifikatsiya
    - Rate limiting
    - Brute force himoyasi
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)


# ==========================================
# Middleware
# ==========================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Log all requests
    """
    import time
    import uuid
    
    # Generate request ID
    request_id = str(uuid.uuid4())[:8]
    
    # Get client info
    client_ip = get_client_ip(request)
    method = request.method
    path = request.url.path
    
    # Log request
    start_time = time.time()
    logger.info(f"[{request_id}] {method} {path} - {client_ip}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"[{request_id}] {method} {path} - {response.status_code} ({duration:.3f}s)"
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[{request_id}] {method} {path} - Error: {e} ({duration:.3f}s)")
        raise


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    Add security headers to responses
    """
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# ==========================================
# Exception Handlers
# ==========================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions
    """
    # If detail is already a dict, use it
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, format it
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "code": "http_error"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "code": "validation_error",
            "details": {"errors": errors}
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions
    """
    logger.exception(f"Unexpected error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "code": "internal_error"
        }
    )


# ==========================================
# Routes
# ==========================================

# Include API routes
app.include_router(api_router)
app.include_router(admin_router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "documentation": "/docs" if settings.DEBUG else "disabled",
        "timestamp": datetime.utcnow().isoformat()
    }


# Webhook endpoint for Telegram (production)
@app.post("/webhook/telegram", include_in_schema=False)
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint
    Handled by aiogram's webhook handler
    """
    # This is handled by the bot's webhook setup
    # This endpoint is just a placeholder for documentation
    return {"status": "ok"}
