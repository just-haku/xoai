import asyncio
import click
import uvicorn
from motor.motor_asyncio import AsyncIOMotorClient

from xoai.config import settings


@click.group()
def cli():
    """🥭 XOAI — Multi-Agent AI Platform CLI"""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", default=8000, type=int, help="Bind port")
def start(host: str, port: int):
    """Start the XOAI backend server."""
    click.echo("🥭 Starting XOAI server...")
    uvicorn.run("xoai.main:create_app", factory=True, host=host, port=port, reload=False)


@cli.group()
def add():
    """Add a new admin or user."""
    pass


@add.command("admin")
@click.argument("email")
@click.argument("password")
@click.argument("name")
def add_admin(email: str, password: str, name: str):
    """Create an admin account: xoai add admin <email> <password> '<Name>'"""
    asyncio.run(_create_user(email, password, name, role="admin"))


@add.command("user")
@click.argument("email")
@click.argument("password")
@click.argument("name")
def add_user(email: str, password: str, name: str):
    """Create a pre-approved user: xoai add user <email> <password> '<Name>'"""
    asyncio.run(_create_user(email, password, name, role="user"))


@cli.command()
@click.argument("user_id")
def approve(user_id: str):
    """Approve a pending user and provision their workspace."""
    asyncio.run(_approve_user(user_id))


@cli.group("list")
def list_cmd():
    """List resources."""
    pass


@list_cmd.command("users")
def list_users():
    """List all users."""
    asyncio.run(_list_users())


# --- Async helpers ---

async def _create_user(email: str, password: str, name: str, role: str):
    import bcrypt
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client.get_default_database()

    existing = await db.users.find_one({"email": email})
    if existing:
        click.echo(f"❌ User with email '{email}' already exists.")
        return

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "name": name,
        "role": role,
        "status": "approved",
        "email_verified": True,
        "quota_used_bytes": 0,
        "lang": "EN",
    }
    result = await db.users.insert_one(user_doc)
    click.echo(f"✅ {role.capitalize()} '{name}' created. ID: {result.inserted_id}")
    client.close()


async def _approve_user(user_id: str):
    from bson import ObjectId
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client.get_default_database()

    result = await db.users.update_one(
        {"_id": ObjectId(user_id), "status": "pending"},
        {"$set": {"status": "approved"}},
    )
    if result.modified_count:
        click.echo(f"✅ User {user_id} approved.")
    else:
        click.echo(f"❌ User {user_id} not found or not in pending status.")
    client.close()


async def _list_users():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client.get_default_database()

    users = await db.users.find({}, {"password_hash": 0}).to_list(100)
    if not users:
        click.echo("No users found.")
        return

    click.echo(f"{'ID':<26} {'Email':<30} {'Name':<20} {'Role':<8} {'Status':<10}")
    click.echo("-" * 94)
    for u in users:
        click.echo(
            f"{str(u['_id']):<26} {u['email']:<30} {u['name']:<20} {u['role']:<8} {u['status']:<10}"
        )
    client.close()


if __name__ == "__main__":
    cli()
