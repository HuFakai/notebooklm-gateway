import os
import json
from pathlib import Path
from pydantic import BaseModel, EmailStr
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# 引入数据库和核心应用工厂
from gateway_server.database import DatabaseManager
from gateway_server.notebooklm.server.app import create_app
from fastapi.middleware.cors import CORSMiddleware

# 1. 继承原版核心应用，获得所有的 /v1 业务路由
app = create_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager()

# 获取全局 Admin Token 用于上传和管理页面鉴权
ADMIN_TOKEN = os.environ.get("NOTEBOOKLM_ADMIN_TOKEN", "admin_secret_token_change_me")

class CredentialsUpload(BaseModel):
    email: EmailStr
    api_key: str
    master_token: str
    storage_state: str

class StatusUpdateRequest(BaseModel):
    status: str

class KeyUpdateRequest(BaseModel):
    api_key: str


def verify_admin_token(request: Request):
    """管理员鉴权依赖"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # 补充：也支持从 query parameter 或 X-Admin-Token 获取，方便页面交互
        token = request.headers.get("X-Admin-Token") or request.query_params.get("admin_token")
    else:
        token = auth_header.split(" ")[1]

    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Admin Token"
        )
    return token

# =====================================================================
# 核心路由 1：桌面客户端一键上传同步凭证
# =====================================================================
@app.post("/v1/auth/credentials", tags=["Auth"])
async def upload_credentials(data: CredentialsUpload, _ = Depends(verify_admin_token)):
    """供本地客户端同步多账号凭证的接口"""
    # 检查 storage_state 格式
    try:
        json.loads(data.storage_state)
    except Exception:
        raise HTTPException(status_code=400, detail="storage_state must be a valid JSON string")

    # 检查 api_key 是否已被其他账号占用
    with db._get_connection() as conn:
        row = conn.execute(
            "SELECT email FROM accounts WHERE api_key = ?", 
            (data.api_key,)
        ).fetchone()
        if row and row["email"] != data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"The API Key is already occupied by another account ({row['email']}). Please choose a different key."
            )

    # 保存/覆盖到 SQLite 中
    success = db.save_account(
        email=data.email,
        api_key=data.api_key,
        master_token=data.master_token,
        storage_state=data.storage_state
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save credentials to database")
        
    # 清理该 api_key 可能已经缓存的旧客户端连接，实现热更新
    if hasattr(app.state, "client_pool"):
        if data.api_key in app.state.client_pool:
            try:
                # 尝试安全地关闭旧会话
                await app.state.client_pool[data.api_key].close()
            except Exception:
                pass
            del app.state.client_pool[data.api_key]
            
    return {"ok": True, "message": f"Credentials for {data.email} uploaded and updated successfully."}


# =====================================================================
# 核心路由 2：管理后台的 API 接口
# =====================================================================
@app.get("/admin/api/accounts", tags=["Admin"])
async def list_accounts(_ = Depends(verify_admin_token)):
    """获取系统所有托管账号列表"""
    accounts = db.get_all_accounts()
    return {"ok": True, "accounts": accounts}


@app.delete("/admin/api/accounts/{account_id}", tags=["Admin"])
async def delete_account(account_id: int, _ = Depends(verify_admin_token)):
    """删除账号并清除对应客户端缓存"""
    # 先查出账号对应的 api_key 方便删缓存
    with db._get_connection() as conn:
        row = conn.execute("SELECT api_key FROM accounts WHERE id = ?", (account_id,)).fetchone()
        
    if row:
        api_key = row["api_key"]
        if hasattr(app.state, "client_pool") and api_key in app.state.client_pool:
            try:
                await app.state.client_pool[api_key].close()
            except Exception:
                pass
            del app.state.client_pool[api_key]

    success = db.delete_account_by_id(account_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete account")
        
    return {"ok": True, "message": "Account deleted successfully."}


@app.put("/admin/api/accounts/{account_id}/status", tags=["Admin"])
async def update_account_status_api(account_id: int, data: StatusUpdateRequest, _ = Depends(verify_admin_token)):
    """更新账号会话状态（支持 active / expired 等）"""
    with db._get_connection() as conn:
        row = conn.execute("SELECT email FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    
    email = row["email"]
    success = db.update_account_status(email, data.status)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update account status")
    
    return {"ok": True, "message": f"Account status updated to {data.status}."}


@app.put("/admin/api/accounts/{account_id}/key", tags=["Admin"])
async def update_account_key_api(account_id: int, data: KeyUpdateRequest, _ = Depends(verify_admin_token)):
    """更新账号外部调用 API Key"""
    with db._get_connection() as conn:
        row = conn.execute("SELECT email, api_key FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
        
    email = row["email"]
    old_key = row["api_key"]
    new_key = data.api_key.strip()
    if not new_key:
        raise HTTPException(status_code=400, detail="API Key cannot be empty")
        
    with db._get_connection() as conn:
        dup = conn.execute("SELECT email FROM accounts WHERE api_key = ? AND id != ?", (new_key, account_id)).fetchone()
        if dup:
            raise HTTPException(
                status_code=400, 
                detail=f"The API Key is already occupied by another account ({dup['email']}). Please choose a different key."
            )

    try:
        with db._get_connection() as conn:
            conn.execute("UPDATE accounts SET api_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_key, account_id))
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update API Key: {e}")

    if hasattr(app.state, "client_pool"):
        if old_key in app.state.client_pool:
            try:
                await app.state.client_pool[old_key].close()
            except Exception:
                pass
            del app.state.client_pool[old_key]
        if new_key in app.state.client_pool:
            try:
                await app.state.client_pool[new_key].close()
            except Exception:
                pass
            del app.state.client_pool[new_key]

    return {"ok": True, "message": "API Key updated successfully."}


# =====================================================================
# 核心路由 3：精致的 Web 管理后台单文件返回
# =====================================================================
@app.get("/admin", response_class=HTMLResponse, tags=["Admin"])
async def admin_page():
    """返回极具现代感的网关管理后台单页"""
    template_path = Path(__file__).parent / "admin.html"
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Admin console template not found"
        )
    with open(template_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

