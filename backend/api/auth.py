"""
backend/api/auth.py
====================
Authentication endpoints:
  POST /auth/register  — create new user
  POST /auth/login     — returns JWT access token
  GET  /auth/me        — returns current user info (requires token)
  POST /auth/logout    — client-side (token discard), returns confirmation
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from backend.db.database import get_connection, init_db

# ─── Config ──────────────────────────────────────────────────────────────────

SECRET_KEY   = "cte-secret-key-change-in-production-2026"   # ⚠️ change for prod
ALGORITHM    = "HS256"
TOKEN_EXPIRE = 8   # hours

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
router        = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── Schemas ─────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username:  str
    email:     EmailStr
    full_name: str
    password:  str
    role:      str = "analyst"   # analyst | admin

class UserOut(BaseModel):
    id:        int
    username:  str
    email:     str
    full_name: str
    role:      str
    is_active: bool
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut

# ─── Helpers ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_hours: int = TOKEN_EXPIRE) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_username(username: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None

# ─── Dependency: current logged-in user ──────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = get_user_by_id(int(user_id))
    if not user or not user["is_active"]:
        raise credentials_exc
    return user

# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest):
    """Register a new user. Returns the created user (without password)."""
    # Check duplicates
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (req.username, req.email),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username or email already registered.",
            )
        conn.execute(
            """INSERT INTO users (username, email, full_name, hashed_password, role)
               VALUES (?, ?, ?, ?, ?)""",
            (req.username, req.email, req.full_name,
             hash_password(req.password), req.role),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (req.username,)
        ).fetchone()
    return dict(row)


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Login with username + password. Returns JWT token + user info."""
    user = get_user_by_username(form.username)
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    token = create_token({"sub": str(user["id"]), "username": user["username"]})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id":        user["id"],
            "username":  user["username"],
            "email":     user["email"],
            "full_name": user["full_name"],
            "role":      user["role"],
            "is_active": bool(user["is_active"]),
            "created_at": user["created_at"],
        },
    }


@router.get("/me", response_model=UserOut)
def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/logout")
def logout():
    """
    Logout is handled client-side (discard token from localStorage).
    This endpoint confirms the action.
    """
    return {"message": "Logged out successfully."}
