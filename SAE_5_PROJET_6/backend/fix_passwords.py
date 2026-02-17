#!/usr/bin/env python3
import asyncio
from auth import get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal

async def fix_passwords():
    passwords = {
        'admin@pixtral.fr': 'Admin123!',
        'louna.dubois@pixtral.fr': 'Louna123!',
        'arthur.laurent@pixtral.fr': 'Arthur123!',
        'lea.roux@pixtral.fr': 'Lea123!'
    }
    
    async with AsyncSessionLocal() as db:
        from models import User
        from sqlalchemy import select
        
        for email, password in passwords.items():
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if user:
                user.hashed_password = get_password_hash(password)
                print(f"Updated password for {email}")
        
        await db.commit()
        print("All passwords updated!")

if __name__ == "__main__":
    asyncio.run(fix_passwords())
