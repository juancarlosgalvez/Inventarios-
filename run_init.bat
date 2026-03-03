@echo off
:: usage: run_init.bat root_db_user root_db_password
set DB_USER=%1
set DB_PASS=%2
set DB_HOST=%3
if "%DB_HOST%"=="" set DB_HOST=localhost
mysql -u %DB_USER% -p%DB_PASS% -h %DB_HOST% < init_db.sql
for /f "delims=" %%h in ('python - <<PY 
import hashlib 
print(hashlib.sha256(b"admin").hexdigest())
PY
') do set HASH=%%h
mysql -u %DB_USER% -p%DB_PASS% -h %DB_HOST% -e "USE inventario_db; UPDATE users SET pass_hash='%HASH%' WHERE username='admin';"


echo Init finished. Admin password set to 'admin' (hashed).